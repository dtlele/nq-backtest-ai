"""
Simulazione OFFLINE dei desk_gates sulle decisioni del log v4 e sui trade aperti nella v1.

Obiettivo: validare che i nuovi gate meccanici (time/participation/anchor) non
avrebbero (a) bocciato trade profittevoli della v1, e (b) avrebbero bocciato
i setup scartati dall'auditor v4 (validazione incrociata).

NON chiama LLM. Lavora solo sui log gia' in nostro possesso.
"""
import re
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path

sys.path.insert(0, '.')
from src.agents.desk_gates import check_time_gate, check_participation, has_structural_anchor
from src.agents.institutional_bias import compute_institutional_bias
from src import CandidateBar, Bar, SessionContext

# === UTILITIES ===
_ET_OFFSET = timedelta(hours=-5)
def to_et(ts):
    if ts.tzinfo is None: ts = ts.replace(tzinfo=timezone.utc)
    return ts.astimezone(timezone(_ET_OFFSET)).replace(tzinfo=None)


# === PARSING LOG V4 (decisioni + audit) ===
def parse_v4_log(log_path):
    """Estrae (timestamp, direction, confidence, audit_outcome) dal log v4.
    NOTA: il runner logga 'FABIO long(50) -> SKIP' SOLO per proposte con conf<55.
    Le proposte conf>=55 vanno direttamente all'audit e non appaiono nella riga FABIO.
    Quindi: parsing rovesciato — partiamo da 'DEEP AUDIT TRIGGERED' e torniamo indietro.
    """
    with open(log_path) as f:
        lines = f.readlines()
    decisions = []
    for i, line in enumerate(lines):
        if 'DEEP AUDIT TRIGGERED' not in line:
            continue
        m = re.search(r'(long|short) \(Conf: (\d+)\)', line)
        if not m:
            continue
        direction, conf = m.group(1), int(m.group(2))
        # Cerca la riga FABIO long/short piu' vicina PRIMA (entro 20 righe)
        ts_str = None
        for j in range(max(0, i-20), i):
            tm = re.match(r'\s*(\d{2}:\d{2}) UTC FABIO (long|short)\(\d+\)', lines[j])
            if tm and tm.group(2) == direction:
                ts_str = tm.group(1)
        if not ts_str:
            # fallback: timestamp della riga DEEP AUDIT stessa
            tm = re.search(r'(\d{2}:\d{2}) UTC', line)
            ts_str = tm.group(1) if tm else '00:00'
        ts = datetime(2025, 2, 4, int(ts_str[:2]), int(ts_str[3:]))
        # Esito audit
        audit = ('UNKNOWN', 'no esito letto')
        for j in range(i+1, min(i+5, len(lines))):
            if 'DEEP AUDIT REJECTED' in lines[j]:
                audit = ('REJECT', lines[j].strip())
                break
            if 'DEEP AUDIT CONFIRMED' in lines[j]:
                audit = ('CONFIRM', lines[j].strip())
                break
        decisions.append({'ts': ts, 'direction': direction, 'conf': conf, 'audit': audit})
    return decisions


# === PARSING LOG V1 (trade aperti) ===
def parse_v1_log(log_path):
    """Estrae i trade aperti dalla v1 con entry/stop/target/timestamp."""
    trades = []
    with open(log_path) as f:
        lines = f.readlines()
    for i, line in enumerate(lines):
        m = re.search(r'\[TRADE OPEN\] dir=(\w+) entry=([\d.]+) stop=([\d.]+) target=([\d.]+)', line)
        if m:
            direction = m.group(1)
            entry, stop, target = float(m.group(2)), float(m.group(3)), float(m.group(4))
            ts, conf = None, None
            # cerca FABIO long/short fino a 30 righe prima
            for j in range(max(0, i-30), i):
                tm = re.search(r'(\d{2}:\d{2}) UTC FABIO (long|short)\((\d+)\)', lines[j])
                if tm and tm.group(2) == direction:
                    ts = datetime(2025, 2, 4, int(tm.group(1)[:2]), int(tm.group(1)[3:]))
                    conf = int(tm.group(3))
                    break
            if not ts: continue
            trades.append({'ts': ts, 'direction': direction, 'entry': entry,
                          'stop': stop, 'target': target, 'conf': conf})
    return trades


def parse_v1_pnl(log_path):
    """Estrae P&L per ogni trade dal log v1 (se disponibile)."""
    pnls = {}
    with open(log_path) as f:
        for line in f:
            m = re.search(r'\[TRADE CLOSE\] .* P&L=([+-]?[\d.]+).* direction=(\w+)', line)
            if m:
                pnls[m.group(2)] = float(m.group(1))
    return pnls


# === SIMULAZIONE GATES SU DECISIONI V4 ===
def build_fake_candidate(ts, direction, conf, audit_outcome):
    """Costruisce un CandidateBar minimo per i gate (senza dati reali).
    Useremo direction implicita + orario ET per time gate + niente wall/big trades
    per structural anchor."""
    # Bar con timestamp UTC
    bar = Bar(timestamp=ts, open=21600, high=21620, low=21580, close=21600,
              volume=5000, buy_volume=2500, sell_volume=2500, delta=0,
              delta_pct=0.0, cvd=0, vwap=21600.0, big_trades=[])
    ctx = SessionContext(date=ts.strftime('%Y-%m-%d'),
                        ib_high=21620, ib_low=21580, ib_range=40, ib_complete=True,
                        vp=None, prev_day_vp=None, atr_5day=120)
    return CandidateBar(bar=bar, session_ctx=ctx, wall_level=0, wall_side='none',
                        wall_trade_count=0, wall_max_size=0, proximity_to='none',
                        proximity_level=0, bars_in_session=10, is_second_test=False,
                        setup_category='momentum' if direction != 'none' else 'none')


def simulate_gates_on_decision(decision):
    """Applica time gate + structural anchor alla decisione."""
    direction = decision.get('direction', 'none')
    if direction == 'none':
        return ['NO_TRADE_PROPOSED']

    cand = build_fake_candidate(decision['ts'], direction, decision['conf'], decision.get('audit'))
    bias = compute_institutional_bias(cand)
    vetoes = []
    # 1. Time gate
    v = check_time_gate(cand.bar.timestamp, direction, bias.regime)
    if v: vetoes.append(f"TIME: {v}")
    # 2. Structural anchor (con recent_bars vuoto)
    has_anchor, src = has_structural_anchor(cand, direction)
    if not has_anchor:
        vetoes.append(f"ANCHOR: no wall/bigtrade/proximity ({src})")
    return vetoes or ['PASS']


# === MAIN ===
def main():
    base = Path('.')
    v4_log = base / 'output/week_glm52_scalper_v4.log'
    v1_log = base / 'output/week_glm52_scalper.log'

    print('='*80)
    print('SIMULAZIONE OFFLINE DESK_GATES')
    print('='*80)

    # PARTE 1: Decisioni V4 (solo quelle con audit, le altre erano gia' SKIP da conf<55)
    print('\n--- V4: proposte con audit del 04/02 ---')
    decisions = parse_v4_log(v4_log)
    print(f'Trovate {len(decisions)} proposte con audit')

    trade_props = decisions
    rejects = [d for d in trade_props if d['audit'] and d['audit'][0] == 'REJECT']
    confirms = [d for d in trade_props if d['audit'] and d['audit'][0] == 'CONFIRM']
    no_audit = [d for d in trade_props if not d['audit'] or d['audit'][0] == 'UNKNOWN']

    print(f'  Proposte trade: {len(trade_props)}')
    print(f'  Audit REJECT: {len(rejects)}')
    print(f'  Audit CONFIRM: {len(confirms)}')
    print(f'  Senza audit (conf<55): {len(no_audit)}')

    print(f'\n  Dettaglio REJECT (cosa avrebbero fatto i desk_gates?):')
    for d in rejects:
        gates = simulate_gates_on_decision(d)
        print(f"    {d['ts'].strftime('%H:%M')} {d['direction']}({d['conf']}) audit={d['audit'][1][:60]}")
        print(f"      Gates: {gates}")

    # PARTE 2: Trade aperti V1 (profittevoli)
    print('\n--- V1: trade aperti ---')
    v1_trades = parse_v1_log(v1_log)
    v1_pnls = parse_v1_pnl(v1_log)
    print(f'Trovati {len(v1_trades)} trade aperti in V1')
    for t in v1_trades:
        if not t.get('ts'): continue
        gates = simulate_gates_on_decision(t)
        pnl = v1_pnls.get(t['direction'], 'N/A')
        veto_count = sum(1 for g in gates if g != 'PASS' and g != 'NO_TRADE_PROPOSED')
        status = 'VETO' if veto_count > 0 else 'PASS'
        print(f"  {t['ts'].strftime('%H:%M')} {t['direction']} conf={t.get('conf', '?')} P&L={pnl}")
        print(f"    Gates: {gates} -> {status}")

    # PARTE 3: Verdetto
    print('\n' + '='*80)
    print('VERDETTO SIMULAZIONE')
    print('='*80)
    v1_with_gates_passed = 0
    v1_with_gates_vetoed = 0
    for t in v1_trades:
        if not t['ts']: continue
        cand = build_fake_candidate(t['ts'], t['direction'], t.get('conf', 70), None)
        gates = simulate_gates_on_decision(t)
        if any('TIME' in g for g in gates) or any('ANCHOR' in g for g in gates):
            v1_with_gates_vetoed += 1
        else:
            v1_with_gates_passed += 1
    print(f'\nTrade V1 che i nuovi gate AVREBBERO APERTO: {v1_with_gates_passed}')
    print(f'Trade V1 che i nuovi gate AVREBBERO VETATO: {v1_with_gates_vetoed}')
    print(f'\n  (Nota: structural anchor gate ha veto forte perche i CandidateBar finti')
    print(f'   non hanno wall ne big_trades. Nel live i dati reali passerebbero se')
    print(f'   il wall fosse valido. Serve test live per validare quel gate specifico.)')

    v4_reject_with_gates = 0
    for d in rejects:
        gates = simulate_gates_on_decision(d)
        if any('TIME' in g for g in gates) or any('ANCHOR' in g for g in gates):
            v4_reject_with_gates += 1
    print(f'\nReject V4 che i nuovi gate AVREBBERO BLOCCATO PRIMA dell\'audit: {v4_reject_with_gates}/{len(rejects)}')
    print('(Se >=2/4: i gate meccanici avrebbero risparmiato 1-2 chiamate audit)')


if __name__ == '__main__':
    main()
