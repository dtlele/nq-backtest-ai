import sys
import subprocess
import time

questions = [
    "Fabio menziona mai la possibilità di abbassare la soglia di partecipazione minima (es. i 4.000 contratti) durante giornate a bassa volatilità, oppure la considera una regola invalicabile su NQ?",
    "Dopo un assorbimento M5, Fabio aspetta rigorosamente la chiusura della candela M5 successiva per validare l'accettazione, o anticipa l'ingresso sul Footprint M1 non appena il prezzo supera il livello per ottimizzare il R:R?",
    "Come gestisce esattamente lo Stop Loss per evitare le cagge agli stop (Liquidity Sweeps)? Usa un Hard Stop stretto pre-calcolato dietro al Big Trade o uno stop tecnico alla chiusura della candela M5?",
    "Quando compare 'Conflict in institutional flow' (es. venditori assorbiti e subito dopo compratori assorbiti sull'altro lato del range), Fabio usa il Cumulative Volume Delta per sbilanciarsi o sta flat finché non avviene un breakout?"
]

print("# NotebookLM Interview regarding Fabio Valentini's Rules\n")

for i, q in enumerate(questions):
    print(f"## Domanda {i+1}:\n{q}\n")
    print("### NotebookLM Answer:")
    
    start = time.time()
    try:
        result = subprocess.run(
            [sys.executable, "-m", "notebooklm", "ask", q],
            capture_output=True, text=True, timeout=120
        )
        
        # strip out the Matched/Continuing noise output
        out = result.stdout
        clean_lines = []
        for line in out.splitlines():
            if line.startswith("Matched:") or line.startswith("Continuing conversation"):
                continue
            clean_lines.append(line)
        
        answer = "\n".join(clean_lines).strip()
        if not answer:
            answer = f"[ERROR: No output or auth expired]\nStderr:\n{result.stderr.strip()}"
        print(answer)
        
    except Exception as e:
        print(f"Exception trying to ask NLM: {e}")
        
    print("\n---")
    print(f"(Elapsed: {time.time() - start:.1f}s)\n")
