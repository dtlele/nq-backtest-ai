import sys
import subprocess
import time

notebook_id = "4c868e52"

questions = [
    ("Threshold", "Fabio, riguardo alla soglia di partecipazione di 4.000 contratti su NQ: è una regola invalicabile o può essere flessibile (es. 3.500-3.900) se i Big Trades sono estremamente concentrati o se c'è un assorbimento massiccio rilevato sul Delta?"),
    ("Timing", "Dopo un assorbimento M5, Fabio aspetta rigorosamente la chiusura della candela M5 successiva per validare l'accettazione, o anticipa l'ingresso sul Footprint M1 non appena il prezzo supera il livello per ottimizzare il R:R?"),
    ("Stop_Loss", "Come gestisce esattamente lo Stop Loss per evitare le 'cacce agli stop' (Liquidity Sweeps)? Usa un Hard Stop stretto pre-calcolato dietro al Big Trade o uno stop tecnico alla chiusura della candela M5?"),
    ("Conflict", "Quando compare 'Conflict in institutional flow' (es. venditori assorbiti e subito dopo compratori assorbiti sull'altro lato del range), Fabio usa il Cumulative Volume Delta per sbilanciarsi o sta flat finché non avviene un breakout?")
]

results = []

print(f"Starting NotebookLM Interview (Notebook: {notebook_id})...\n")

for title, q in questions:
    print(f"--- Asking: {title} ---")
    start = time.time()
    try:
        # Use 'use' first to be safe
        subprocess.run([sys.executable, "-m", "notebooklm", "use", notebook_id], capture_output=True)
        
        result = subprocess.run(
            [sys.executable, "-m", "notebooklm", "ask", q],
            capture_output=True, text=True, timeout=180
        )
        
        out = result.stdout
        # Basic cleanup
        clean_lines = []
        for line in out.splitlines():
            if line.startswith("Matched:") or line.startswith("Continuing conversation") or line.strip().startswith("+--"):
                continue
            clean_lines.append(line)
        
        answer = "\n".join(clean_lines).strip()
        if not answer:
             answer = f"[ERROR: No output]\nStderr: {result.stderr}"
        
        print(f"Answer received ({time.time() - start:.1f}s)")
        results.append(f"## {title}\n**Question:** {q}\n\n**Answer:**\n{answer}\n")
        
    except Exception as e:
        print(f"Exception: {e}")
        results.append(f"## {title}\n**Error:** {e}\n")

with open('scratch/nlm_interview_results.md', 'w', encoding='utf-8') as f:
    f.write("# NotebookLM Strategy Interview Results\n\n")
    f.write("\n\n---\n\n".join(results))

print("\nInterview complete. Results saved to scratch/nlm_interview_results.md")
