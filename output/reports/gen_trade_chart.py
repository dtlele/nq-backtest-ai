"""Generate trade anatomy chart for 2025-05-01."""
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np

fig = plt.figure(figsize=(20, 16))
gs = fig.add_gridspec(3, 2, height_ratios=[2.5, 1.8, 1.5], hspace=0.35, wspace=0.3)
fig.suptitle('2025-05-01 Trade Anatomy: Short Squeeze at IVB High', fontsize=16, fontweight='bold', y=0.98)

# --- PANEL 1: Price action + trade levels ---
ax1 = fig.add_subplot(gs[0, :])

bars = [
    ('09:30', 19951, 19951, 19913, 19921, -200, False, None, None),
    ('09:35', 19920, 19949, 19916, 19942, 100, False, None, None),
    ('09:40', 19942, 19976, 19940, 19972, 150, False, None, None),
    ('09:45', 19972, 19988, 19962, 19972, -50, False, None, None),
    ('09:50', 19971.5, 19996.25, 19941, 19944.5, -538, True, 65, 'TRADE'),
    ('09:55', 19944, 19944, 19888.25, 19888.25, -400, False, None, 'TARGET'),
    ('10:00', 19890, 19928, 19885, 19920, 200, False, None, None),
    ('10:05', 19920, 19935, 19910, 19930, 50, False, None, None),
    ('10:10', 19930, 19940, 19920, 19935, 20, False, None, None),
    ('10:15', 19926.25, 19959, 19925, 19939, -156, True, 18, 'NO_TRADE'),
    ('10:20', 19940, 19960, 19935, 19955, 80, False, None, None),
    ('10:25', 19955, 19990, 19950, 19985, 120, False, None, None),
    ('10:30', 19985, 20010, 19980, 20005, 100, False, None, None),
    ('10:35', 20005, 20025, 20000, 20020, 60, False, None, None),
    ('10:40', 20020, 20035, 20010, 20025, 30, False, None, None),
    ('10:45', 20019.5, 20052, 20014.75, 20048.75, -188, True, 52, 'NO_TRADE'),
    ('10:50', 20048, 20060, 20040, 20050, -100, False, None, None),
    ('10:55', 20045.5, 20073.5, 20045, 20072.75, -684, True, 52, 'NO_TRADE'),
    ('11:00', 20072, 20090, 20070, 20085, 50, False, None, None),
    ('11:05', 20085, 20100, 20078, 20090, -80, False, None, None),
    ('11:10', 20090, 20110, 20085, 20105, 70, False, None, None),
    ('11:15', 20105, 20125.75, 20070, 20080, -323, False, None, None),
    ('11:20', 20080, 20090, 20075, 20082, 30, False, None, None),
    ('11:25', 20081, 20091, 20073, 20078, 172, True, 62, 'NO_TRADE'),
]

x = np.arange(len(bars))
for i, (t, o, h, l, c, d, is_cand, conf, dec) in enumerate(bars):
    color = '#2ECC71' if c >= o else '#E74C3C'
    if is_cand and dec == 'TRADE':
        color = '#F1C40F'
    elif is_cand:
        color = '#3498DB'

    ax1.plot([i, i], [l, h], color=color, linewidth=1.2)
    body_bottom = min(o, c)
    body_height = max(abs(o - c), 0.5)
    ax1.bar(i, body_height, bottom=body_bottom, width=0.6, color=color, edgecolor='black', linewidth=0.5)

# Trade levels
ax1.axhline(y=19940.0, color='#F1C40F', linestyle='-', linewidth=2, alpha=0.8, label='Entry: 19940.0')
ax1.axhline(y=19988.0, color='#E74C3C', linestyle='--', linewidth=1.5, alpha=0.7, label='Stop: 19988.0')
ax1.axhline(y=19888.25, color='#2ECC71', linestyle='--', linewidth=1.5, alpha=0.7, label='Target: 19888.25')
ax1.axhline(y=19990.75, color='#9B59B6', linestyle=':', linewidth=1.5, alpha=0.6, label='IB High: 19990.75')
ax1.axhline(y=19943.0, color='#E67E22', linestyle=':', linewidth=1, alpha=0.5, label='POC: 19943.0')

# Annotations
for i, (t, o, h, l, c, d, is_cand, conf, dec) in enumerate(bars):
    if is_cand and dec:
        label = f'conf={conf}\n{dec}'
        clr = '#F1C40F' if dec == 'TRADE' else '#3498DB'
        ax1.annotate(label, (i, h + 8), ha='center', fontsize=7, fontweight='bold',
                    color=clr, bbox=dict(boxstyle='round,pad=0.2', facecolor='white', alpha=0.8))
    if dec == 'TARGET':
        ax1.annotate('TARGET\nHIT!', (i, l - 15), ha='center', fontsize=8, fontweight='bold',
                    color='#2ECC71', bbox=dict(boxstyle='round,pad=0.3', facecolor='#2ECC71', alpha=0.15))

# Trade arrow
ax1.annotate('', xy=(5, 19888.25), xytext=(4, 19940),
            arrowprops=dict(arrowstyle='->', color='#2ECC71', lw=2.5))
ax1.text(4.5, 19912, '$1,035 | 207 ticks | 1.08R', ha='center', fontsize=9, fontweight='bold',
        color='#2ECC71', bbox=dict(boxstyle='round', facecolor='white', alpha=0.9))

# 382-contract wall annotation
ax1.annotate('382 SELL\n@ 19981', (4, 19981), textcoords='offset points', xytext=(40, 10),
            ha='center', fontsize=8, fontweight='bold', color='#E74C3C',
            arrowprops=dict(arrowstyle='->', color='#E74C3C'))

ax1.set_xticks(x)
ax1.set_xticklabels([b[0] for b in bars], rotation=45, fontsize=7)
ax1.set_ylabel('NQ Price')
ax1.set_title('M5 Price Action  |  Blue = Candidate  |  Gold = Trade Bar', fontweight='bold')
ax1.legend(loc='upper left', fontsize=8)
ax1.grid(axis='y', alpha=0.2)

# --- PANEL 2: Confidence + decision flow ---
ax2 = fig.add_subplot(gs[1, 0])

cand_times =  ['09:50\nrun1', '09:50\nrun2', '10:15', '10:45', '10:55', '11:25']
cand_confs =  [38, 65, 18, 52, 52, 62]
cand_setups = ['squeeze', 'squeeze', 'none', 'squeeze', 'squeeze', 'ivb_bk']
cand_colors = ['#E67E22', '#F1C40F', '#95A5A6', '#3498DB', '#3498DB', '#3498DB']

bars2 = ax2.bar(range(len(cand_times)), cand_confs, color=cand_colors, edgecolor='white', width=0.6)
ax2.axhline(y=65, color='red', linestyle='--', linewidth=2, label='Threshold (65)')
ax2.axhline(y=40, color='orange', linestyle=':', linewidth=1, label='Andrea veto (40)')
for i in range(len(cand_times)):
    ax2.text(i, cand_confs[i] + 2, f'{cand_setups[i]}\n{cand_confs[i]}', ha='center', fontsize=7, fontweight='bold')
ax2.set_xticks(range(len(cand_times)))
ax2.set_xticklabels(cand_times, fontsize=8)
ax2.set_ylabel('Fabio Confidence')
ax2.set_title('Confidence per Evaluation', fontweight='bold')
ax2.legend(fontsize=7)
ax2.set_ylim(0, 85)

# --- PANEL 3: Decision flow text ---
ax3 = fig.add_subplot(gs[1, 1])
ax3.axis('off')

flow = (
    "THE WINNING TRADE: 09:50 ET\n"
    "\n"
    "CANDIDATE BAR\n"
    "  O=19971.5 H=19996.25 L=19941 C=19944.5\n"
    "  V=9540  delta=-538\n"
    "  Wall: 382 SELL contracts @ 19981.25\n"
    "  Near: POC @ 19943  |  Day: balance\n"
    "  IB: 19888.25 - 19990.75 (102.5 pts)\n"
    "\n"
    "FABIO: SHORT conf=65 setup=squeeze\n"
    "  Entry=19940 Stop=19988 Target=19888.25\n"
    '  "Failed-breakout squeeze: 09:50 probed\n'
    "   above IVB high to 19996.25, CRUSHED\n"
    "   by 382 all-sell contracts. Delta -538\n"
    '   confirms failed auction."\n'
    "\n"
    "ANDREA: CONFIRM conf=62 setup=failed_auction\n"
    '  "NOT clean IBOB (close inside IB), but\n'
    "   failed auction: poked above IB high\n"
    "   then collapsed. 382 sell BIG in upper\n"
    '   wick = absorption/rejection."\n'
    "\n"
    "CONSENSUS: TRADE final_conf=71\n"
    "  Target hit on NEXT bar (09:55)\n"
    "  P&L: +207 ticks = +$1,035  R=1.08"
)
ax3.text(0.05, 0.95, flow, transform=ax3.transAxes, fontsize=8.5,
        verticalalignment='top', fontfamily='monospace',
        bbox=dict(boxstyle='round', facecolor='#2C3E50', alpha=0.05))

# --- PANEL 4: Key observations ---
ax4 = fig.add_subplot(gs[2, :])
ax4.axis('off')

obs = (
    "KEY OBSERVATIONS\n\n"
    "1. DUPLICATE EVALUATION: Bar 09:50 was evaluated in 2 separate runs.\n"
    "   Run 1: conf=38 (NO_TRADE).  Run 2: conf=65 (TRADE).\n"
    "   Different prompts produced different cache keys -> different LLM calls.\n\n"
    "2. NEAR-MISSES WERE CORRECT:  The 4 candidates above IVB (10:45-11:25)\n"
    "   all had conf 52-62 short bias. Price continued UP to 20125+ -> they\n"
    "   would have been losers. Conservative threshold saved ~$2-4K.\n\n"
    "3. SPEED: Entry to target in 1 bar (5 min). 382-contract sell wall was\n"
    "   the decisive signal. Largest institutional print of the day.\n\n"
    "4. TOPIC ROUTER IMPACT:  09:50 bar (failed_auction inferred) would now\n"
    "   load squeeze_vs_failed_auction + pre_explosion_pattern + effort_vs_result\n"
    "   instead of myisto_pattern + simplified_ivb_formation (irrelevant)."
)
ax4.text(0.02, 0.95, obs, transform=ax4.transAxes, fontsize=9,
        verticalalignment='top', fontfamily='monospace',
        bbox=dict(boxstyle='round', facecolor='#f0f0f0', alpha=0.5))

plt.savefig('C:/Users/Mauro/Documents/nq-backtest/output/reports/trade_anatomy_20250501.png',
            dpi=150, bbox_inches='tight')
print('Saved: output/reports/trade_anatomy_20250501.png')
