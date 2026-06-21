# Graph Report - C:\Users\Mauro\Documents\nq-backtest\knowledge\trader_lessons_graph  (2026-06-20)

## Corpus Check
- cluster-only mode — file stats not available

## Summary
- 130 nodes · 110 edges · 37 communities (17 shown, 20 thin omitted)
- Extraction: 98% EXTRACTED · 1% INFERRED · 1% AMBIGUOUS · INFERRED: 1 edges (avg confidence: 0.8)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `148c19f4`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- [[_COMMUNITY_Squeeze Entry Triggers|Squeeze Entry Triggers]]
- [[_COMMUNITY_Failed Auction Variants|Failed Auction Variants]]
- [[_COMMUNITY_Trend vs Mean Reversion|Trend vs Mean Reversion]]
- [[_COMMUNITY_Balance Day Confirmation|Balance Day Confirmation]]
- [[_COMMUNITY_Footprint Delta Analysis|Footprint Delta Analysis]]
- [[_COMMUNITY_Confirmation Timeframe|Confirmation Timeframe]]
- [[_COMMUNITY_Imbalance Cluster Definition|Imbalance Cluster Definition]]
- [[_COMMUNITY_Conflicting Walls Resolution|Conflicting Walls Resolution]]
- [[_COMMUNITY_Institutional Activity|Institutional Activity]]
- [[_COMMUNITY_Rotation Within VA|Rotation Within VA]]
- [[_COMMUNITY_Trade Management Rules|Trade Management Rules]]
- [[_COMMUNITY_Pre-Market Levels Usage|Pre-Market Levels Usage]]
- [[_COMMUNITY_Stop Placement and Targets|Stop Placement and Targets]]
- [[_COMMUNITY_Acceptance Definition|Acceptance Definition]]
- [[_COMMUNITY_IB Breakout Rules|IB Breakout Rules]]
- [[_COMMUNITY_Best Setups Statistics|Best Setups Statistics]]
- [[_COMMUNITY_Squeeze Setup Andrea|Squeeze Setup Andrea]]
- [[_COMMUNITY_Balance vs Failed Auction|Balance vs Failed Auction]]
- [[_COMMUNITY_IB Extension Targets|IB Extension Targets]]
- [[_COMMUNITY_IVB 15 vs 30 Minutes|IVB 15 vs 30 Minutes]]
- [[_COMMUNITY_IVB Breakout vs False Balance|IVB Breakout vs False Balance]]
- [[_COMMUNITY_IVB Breakout vs False Balance|IVB Breakout vs False Balance]]
- [[_COMMUNITY_IVB Breakout vs False Balance|IVB Breakout vs False Balance]]
- [[_COMMUNITY_IVB Protection Level|IVB Protection Level]]
- [[_COMMUNITY_Losing Trade Anatomy|Losing Trade Anatomy]]
- [[_COMMUNITY_Max Daily Loss|Max Daily Loss]]
- [[_COMMUNITY_Multi-Timeframe Analysis|Multi-Timeframe Analysis]]
- [[_COMMUNITY_Partial Exits|Partial Exits]]
- [[_COMMUNITY_Position Building|Position Building]]
- [[_COMMUNITY_Pre-Explosion Pattern|Pre-Explosion Pattern]]
- [[_COMMUNITY_Repeated Level Test|Repeated Level Test]]
- [[_COMMUNITY_Win Rate by Setup|Win Rate by Setup]]
- [[_COMMUNITY_Community 32|Community 32]]
- [[_COMMUNITY_Community 33|Community 33]]
- [[_COMMUNITY_Community 34|Community 34]]
- [[_COMMUNITY_Community 35|Community 35]]
- [[_COMMUNITY_Community 36|Community 36]]

## God Nodes (most connected - your core abstractions)
1. `Failed Auction Definition` - 7 edges
2. `Trend Vs Mean Reversion Model` - 6 edges
3. `Big Trades Filter` - 5 edges
4. `Coherence Of Information` - 5 edges
5. `Confidence 40 60 Zone` - 5 edges
6. `Masterclass Document — Video Trading Analysis` - 5 edges
7. `Andrea Balance Day Confirmation` - 4 edges
8. `Andrea Vp Session Scope` - 4 edges
9. `Composite Profile` - 4 edges
10. `Balance Vs Imbalance` - 3 edges

## Surprising Connections (you probably didn't know these)
- `Bolle Filter` --references--> `Andrea Balance Day Confirmation`  [AMBIGUOUS]
  rule_andrea_bolle_filter.md → rule_andrea_andrea_balance_day_confirmation.md
- `Conflicting Walls Resolution` --conceptually_related_to--> `Entry Iceberg`  [INFERRED]
  rule_andrea_conflicting_walls_resolution.md → rule_andrea_entry_iceberg.md
- `Entry Pbd B` --references--> `Failed Auction Definition`  [EXTRACTED]
  rule_andrea_entry_pbd_b.md → rule_andrea_failed_auction_definition.md
- `Entry Pbd P` --references--> `Failed Auction Definition`  [EXTRACTED]
  rule_andrea_entry_pbd_p.md → rule_andrea_failed_auction_definition.md
- `Failed Auction Definition` --references--> `Failed Auction Variants`  [EXTRACTED]
  rule_andrea_failed_auction_definition.md → rule_andrea_failed_auction_variants.md

## Import Cycles
- None detected.

## Communities (37 total, 20 thin omitted)

### Community 0 - "Squeeze Entry Triggers"
Cohesion: 0.22
Nodes (10): Squeeze Definition, Squeeze Entry Trigger, Squeeze Vs Failed Auction, Squeeze Vs Ivb Priority Balance, Statistical Levels, Stop Placement, Target Selection Hierarchy, Targets High Volatility (+2 more)

### Community 1 - "Failed Auction Variants"
Cohesion: 0.28
Nodes (9): Entry Pbd B, Entry Pbd P, Failed Auction Definition, Failed Auction Variants, Footprint Reading, Gap Open Ivb Interaction, Hvn Lvn, Ibob Relaxed Conditions (+1 more)

### Community 2 - "Trend vs Mean Reversion"
Cohesion: 0.25
Nodes (8): Trailing Stop, Trapped Buyers, Trapped Sellers, Trend Day Second Drive Confirmation, Trend Vs Mean Reversion Model, Vp Includes Overnight, Vp Session Scope, Wall Size Minimum Balance

### Community 3 - "Balance Day Confirmation"
Cohesion: 0.38
Nodes (7): Absorption vs. Exhaustion, Andrea Balance Day Confirmation, Andrea Overnight Gap Va, Andrea Stop Per Setup, Andrea Vp Session Scope, Balance Vs Imbalance, Bolle Filter

### Community 4 - "Footprint Delta Analysis"
Cohesion: 0.62
Nodes (7): Big Trades Filter, Breakeven Rules, Coherence Of Information, Confidence 40 60 Zone, Conflict Resolution Pingpong, Counter Trend On Trend Day, Counter Trend Rules

### Community 5 - "Confirmation Timeframe"
Cohesion: 0.33
Nodes (7): Cvd As Leading Indicator, Cvd In Simplified Model, Effort Vs Result, Entry Mechanics, Failed Auction Is The Setup, Footprint Delta, Hvn Big Wall Rules

### Community 6 - "Imbalance Cluster Definition"
Cohesion: 0.33
Nodes (6): Edge on Trading, Framework Quantitativi, Masterclass Document — Video Trading Analysis, PayQRS Research Terminal, Relatore Sezione 1 (Edge on Trading), Video Sales Letter (VSL)

### Community 7 - "Conflicting Walls Resolution"
Cohesion: 0.60
Nodes (5): Composite Profile, Confirmation Timeframe, Confirmation Without Ibob, Day Type Classification, Entry Failed Auction

### Community 8 - "Institutional Activity"
Cohesion: 0.40
Nodes (5): Imbalance Cluster Definition, Initiative Vs Response, Multi Timeframe, Overnight Gaps, Pbd Shapes

### Community 9 - "Rotation Within VA"
Cohesion: 0.50
Nodes (4): Conflicting Walls Resolution, Cvd Divergence, Delta Thresholds, Entry Iceberg

### Community 10 - "Trade Management Rules"
Cohesion: 0.67
Nodes (4): Institutional Activity, Losing Trade Characteristics, Lunch Effect, No Trade Rules

### Community 11 - "Pre-Market Levels Usage"
Cohesion: 0.50
Nodes (4): Range Acceptance, Rotation Within Va, Second Drive Andrea, Session Times

### Community 12 - "Stop Placement and Targets"
Cohesion: 0.50
Nodes (4): Trade Management, Trend Day Rules, Value Area Definition, Volume Floor

### Community 13 - "Acceptance Definition"
Cohesion: 0.50
Nodes (4): Participation Baseline, Pre Market Levels Usage, Session Schedule, Setup Time Cutoff

### Community 14 - "IB Breakout Rules"
Cohesion: 1.00
Nodes (3): Rr Ratio, Stop Placement All, Target Rules

### Community 15 - "Best Setups Statistics"
Cohesion: 0.67
Nodes (3): Acceptance Definition Exact, Aplus Setup, Avoid Times

### Community 16 - "Squeeze Setup Andrea"
Cohesion: 0.67
Nodes (3): Ib Bias, Ib Breakout Rules, Ib Definition

## Ambiguous Edges - Review These
- `Andrea Balance Day Confirmation` → `Bolle Filter`  [AMBIGUOUS]
  rule_andrea_bolle_filter.md · relation: references

## Knowledge Gaps
- **70 isolated node(s):** `Absorption vs. Exhaustion`, `Andrea Minimum Rr`, `Andrea Overnight Gap Va`, `Best Setups Statistics`, `Bolle Filter` (+65 more)
  These have ≤1 connection - possible missing edges or undocumented components.
- **20 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **What is the exact relationship between `Andrea Balance Day Confirmation` and `Bolle Filter`?**
  _Edge tagged AMBIGUOUS (relation: references) - confidence is low._
- **What connects `Absorption vs. Exhaustion`, `Andrea Minimum Rr`, `Andrea Overnight Gap Va` to the rest of the system?**
  _78 weakly-connected nodes found - possible documentation gaps or missing edges._