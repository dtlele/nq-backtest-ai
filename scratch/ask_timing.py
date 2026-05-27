import subprocess
import os

NOTEBOOK_ID = "4c868e52"

question = "Dopo che è stato identificato un assorbimento o una Failed Auction su grafico M5, Fabio aspetta rigorosamente la chiusura della candela M5 (per confermare l'accettazione del rigetto) o entra a mercato non appena vede il segnale sul Footprint M1 (es. inversione del Delta o Big Trade contrario) per ottimizzare il Risk/Reward?"

def ask(q):
    print(f"Asking: {q}")
    # Using the notebooklm CLI via subprocess
    cmd = ["python", "-m", "notebooklm", "ask", q, "--notebook", NOTEBOOK_ID]
    result = subprocess.run(cmd, capture_output=True, text=True, encoding='utf-8')
    if result.returncode == 0:
        return result.stdout
    else:
        return f"Error: {result.stderr or 'Unknown error'}"

answer = ask(question)

with open('scratch/nlm_timing_answer.md', 'w', encoding='utf-8') as f:
    f.write(f"# Timing Answer\n\n**Question:** {question}\n\n**Answer:**\n{answer}\n")

print("Saved answer to scratch/nlm_timing_answer.md")
