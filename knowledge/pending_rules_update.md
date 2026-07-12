# Piano: Aggiornamento Dynamic Rules post-analisi video

## Stato video
- [x] xUyqIjCfZzg - Fabio Valentini & Carmine Rosato (3h49m) - COMPLETATO
- [ ] tvERE-Beu2U - #1 Scalper in the WORLD (3h34m) - in corso (task-340)
- [ ] hvyf6frvCcA - 74% Win Rate OrderFlow Strategy (1h33m) - in corso (task-342)
- [ ] DyS79Eb92Ug - BEST Scalper in the World (2h21m) - in corso (task-344)

## Logica del piano
Aspettare la fine di tutti e 4 i video prima di aggiornare dynamic_rules.json e i prompt.
Motivo: ogni video potrebbe confermare, raffinare o contraddire le regole degli altri.
L'aggiornamento in batch garantisce coerenza e riduce il rischio di regole conflittuali.

## Step da eseguire quando tutti i video sono completati

### Step 1 - Eseguire knowledge extraction su ogni video
  python scripts/extract_video_knowledge.py --video-id "tvERE-Beu2U" --title "..."
  python scripts/extract_video_knowledge.py --video-id "hvyf6frvCcA" --title "..."
  python scripts/extract_video_knowledge.py --video-id "DyS79Eb92Ug" --title "..."

### Step 2 - Consolidare i gap da tutti i video
  Leggere tutti i file knowledge/video_knowledge_gaps_*.md
  Trovare regole confermate da piu video (alta priorita) vs singoli video (media)

### Step 3 - Aggiungere le nuove dynamic_rules (BATCH 1 - alta priorita)
  Regole proposte da xUyqIjCfZzg, da confermare/raffinare con gli altri video:

  AMT_RULE_327 - RNI Filter: skip_trade se footprint in fase Response
    (volumi alti + delta divergente/piatto + range stretto)

  AMT_RULE_328 - Second Drive Confirmation: wait_for_second_drive
    su Failed Auction (primo test = probe, secondo = entry valida)

  AMT_RULE_331 - Failed Auction Checklist: tutti e 3 obbligatori
    1. Spring (wick viola livello chiave)
    2. Delta Divergence (delta opposto sul wick)
    3. Second Drive (initiative + delta confermato entro 1-3 candele)

### Step 4 - Aggiungere BATCH 2 (dopo calibrazione, se confermato da piu video)
  AMT_RULE_329 - Stacked Imbalances Filter (3+ celle >= 3:1)
  AMT_RULE_330 - Exhaustion vs Absorption discrimination

### Step 5 - Estendere audit_agent.py con nuovi campi JSON
  rni_phase_detected: "response | initiative | unclear"
  failed_auction_components_present: ["spring", "delta_div", "second_drive"]
  stacked_imbalances_count: N
  absorption_vs_exhaustion: "absorption | exhaustion | neither"

### Step 6 - Aggiornare prompt degli agenti
  Aggiungere sezione [RNI_OPERATIONAL_FRAMEWORK] al system prompt:
    ENTRY_REQUIRES_INITIATIVE: True
    RESPONSE_PHASE: HARD_SKIP
    SECOND_DRIVE_REQUIRED_FOR_FAILED_AUCTIONS: True
    STACKED_IMBALANCES_AS_CONFLUENCE: 3+ cells, ratio >= 3:1

## Prossimi video suggeriti (dopo questi 4)
  ALTA priorita:
    - FVG / Single Prints operativi
    - ICT / Smart Money Concepts (order blocks, liquidity sweeps)
  MEDIA priorita:
    - Wyckoff Method avanzato
    - Volume Profile avanzato (LVN rejection, HVN support)
    - Bookmap / Jigsaw configurazione avanzata
