import json
d1=json.load(open('knowledge/trader_lessons_graph/graphify-out/sequences/bt_sequences_2025.json', 'r', encoding='utf-8'))
d2=json.load(open('knowledge/trader_lessons_graph/graphify-out/sequences/bt_sequences_2026.json', 'r', encoding='utf-8'))
raw=d1+d2

passed_cvd = 0
passed_all_filters = 0
total_valid_vol = 0

for s in raw:
    cvd = s['steps'][-1].get('session_cvd', 0)
    # Simulator filter logic
    if abs(cvd) < 1200:
        passed_cvd += 1

print(f"Total sequences: {len(raw)}")
print(f"Passed CVD Climax filter alone (<1200): {passed_cvd}")
