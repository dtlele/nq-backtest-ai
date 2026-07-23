"""V2.0 — LLM Policy.
- Budget giornaliero rigido.
- Cache SQLite (niente JSON riscritto interamente — bug #26).
- Cache key include prompt_version + model → invalidazione esplicita.
- Se calibratore non attivo: LLM può SOLO vetare (default allow).
- Se attivo: trade solo se prob_calibrata >= soglia (validata walk-forward).
"""
from __future__ import annotations
import hashlib
import json
import os
import sqlite3
from pathlib import Path

from .models import SignalEvent
from .state import SessionState
from .config import Config
from .prompt_fabio import FabioPromptBuilder
from .calibration import ConfidenceCalibrator


class LLMPolicy:
    def __init__(self, cfg: Config, calibrator: ConfidenceCalibrator):
        self.cfg = cfg
        self.cal = calibrator
        self.builder = FabioPromptBuilder(cfg)
        self.calls_today = 0
        db = Path(cfg.llm.cache_db)
        db.parent.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(str(db))
        self.conn.execute(
            "CREATE TABLE IF NOT EXISTS cache "
            "(key TEXT PRIMARY KEY, response TEXT, model TEXT, created TEXT)")
        self.conn.commit()

    def new_day(self) -> None:
        self.calls_today = 0

    def _key(self, system: str, user: str) -> str:
        raw = f"{self.cfg.llm.prompt_version}\x00{self.cfg.llm.model}\x00{system}\x00{user}"
        return hashlib.sha256(raw.encode()).hexdigest()

    def _ask(self, system: str, user: str) -> str:
        key = self._key(system, user)
        row = self.conn.execute("SELECT response FROM cache WHERE key=?", (key,)).fetchone()
        if row:
            return row[0]

        if not self.cfg.llm.enabled:
            return '{"vote":"abstain","confidence":50,"key_evidence":"llm disabled","veto_reason":""}'

        from openai import OpenAI
        client = OpenAI(base_url="https://openrouter.ai/api/v1",
                        api_key=os.environ["OPENROUTER_API_KEY"],
                        timeout=self.cfg.llm.timeout_s)
        resp = client.chat.completions.create(
            model=self.cfg.llm.model,
            messages=[{"role": "system", "content": system},
                      {"role": "user", "content": user}],
            max_tokens=400)
        text = resp.choices[0].message.content.strip()
        self.conn.execute("INSERT OR REPLACE INTO cache VALUES (?,?,?,datetime('now'))",
                          (key, text, self.cfg.llm.model))
        self.conn.commit()
        return text

    def evaluate(self, sig: SignalEvent, state: SessionState) -> dict:
        """Ritorna decisione finale. Scrive llm_* features sul segnale."""
        if self.calls_today >= self.cfg.llm.daily_budget:
            sig.features.update(llm_vote="budget_exceeded", llm_confidence=0, calibrated_prob=0.0)
            return {"allow": False, "reason": "llm_budget"}

        self.calls_today += 1
        system, user = self.builder.build(sig, state)
        try:
            raw = self._ask(system, user)
            if raw.startswith("```"):
                raw = raw.split("```")[1].lstrip("json").strip()
            data = json.loads(raw)
        except Exception as e:
            sig.features.update(llm_vote="error", llm_confidence=0, calibrated_prob=0.0)
            # CHANGED: fail-CLOSED. Se l'LLM ha un errore, NON apriamo il trade.
            # Il vecchio fail-open permetteva a trade non validati di passare in caso
            # di problemi LLM, mascherando bug. In V2 il LLM e' un gate di sicurezza
            # che deve essere attivo per approvare.
            return {"allow": False, "reason": f"llm_error_veto({type(e).__name__})"}

        vote = str(data.get("vote", "no_trade"))
        conf = int(data.get("confidence", 0))
        conf = max(0, min(100, conf + int(sig.features.get("gex_conf_delta", 0))))

        # veto esplicito o voto contro la direzione del detector
        if vote == "no_trade" or (vote in ("long", "short") and vote != sig.direction.value):
            sig.features.update(llm_vote=vote, llm_confidence=conf, calibrated_prob=0.0)
            return {"allow": False, "reason": f"llm_veto({vote})"}

        prob = self.cal.prob(conf) if self.cal.active else 0.0
        sig.features.update(llm_vote=vote, llm_confidence=conf, calibrated_prob=round(prob, 3),
                            llm_evidence=str(data.get("key_evidence", ""))[:200])

        if not self.cal.active:
            # veto-only mode finché non ci sono abbastanza trade loggati
            return {"allow": True, "reason": "veto_only_mode"}

        if prob < self.cfg.llm.min_calibrated_prob:
            return {"allow": False, "reason": f"calibrated_prob({prob:.2f}<{self.cfg.llm.min_calibrated_prob})"}
        return {"allow": True, "reason": f"llm_ok(p={prob:.2f})"}