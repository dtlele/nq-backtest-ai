from fastapi import FastAPI
from fastapi.responses import HTMLResponse
import uvicorn
import os

app = FastAPI()

LOG_FILE_PATH = r"C:\Users\Mauro\Documents\nq-backtest-clean\output\run_4weeks.log"

@app.get("/", response_class=HTMLResponse)
def dashboard_home():
    log_content = "Nessun log trovato."
    if os.path.exists(LOG_FILE_PATH):
        try:
            with open(LOG_FILE_PATH, "r", encoding="utf-8") as f:
                lines = f.readlines()
        except UnicodeDecodeError:
            with open(LOG_FILE_PATH, "r", encoding="utf-16") as f:
                lines = f.readlines()
        log_content = "".join(lines[-100:])
    
    html = f"""
    <html>
        <head>
            <title>NQ Dashboard - Live Sync</title>
            <meta http-equiv="refresh" content="3"> <!-- Auto refresh every 3 seconds -->
            <style>
                body {{ font-family: sans-serif; padding: 20px; background-color: #f4f4f9; }}
                pre {{ background: #222; color: #0f0; padding: 15px; border-radius: 5px; overflow-x: auto; white-space: pre-wrap; }}
                h1 {{ color: #333; }}
            </style>
            <script>
                // Auto scroll to bottom
                window.onload = function() {{
                    window.scrollTo(0, document.body.scrollHeight);
                }}
            </script>
        </head>
        <body>
            <h1>NQ Dashboard - Log Live (Ultimi 100 messaggi)</h1>
            <h3>File: {LOG_FILE_PATH}</h3>
            <pre>{log_content}</pre>
        </body>
    </html>
    """
    return html

if __name__ == "__main__":
    import sys
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 5173
    uvicorn.run("run:app", host="0.0.0.0", port=port, reload=False)
