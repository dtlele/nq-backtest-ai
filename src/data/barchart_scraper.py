import asyncio
from playwright.async_api import async_playwright
import json
from pathlib import Path

async def scrape_barchart_sentiment(symbol="QQQ"):
    """
    Scraper headless per Barchart Options Flow.
    Estrae le transazioni anomale (Sweeps/Blocks), calcola il Net Premium
    e restituisce il Sentiment direzionale (LONG, SHORT, CHOP).
    """
    url = "https://www.barchart.com/options/options-flow"
    
    print(f"Avvio scraper Barchart Options Flow per {symbol}...")
    
    async with async_playwright() as p:
        # Usa un browser con header realistici per evitare blocchi base
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )
        page = await context.new_page()
        
        try:
            # Va sulla pagina e aspetta che la tabella dinamica si carichi
            await page.goto(url, wait_until="networkidle")
            
            # Attende che il container della tabella dei dati sia visibile
            # Nota: i selettori potrebbero cambiare se Barchart aggiorna il sito
            await page.wait_for_selector("div.bc-table-scrollable-inner", timeout=15000)
            
            # Estraiamo i dati valutando il JS direttamente nella pagina
            trades_data = await page.evaluate('''() => {
                const rows = Array.from(document.querySelectorAll('div.bc-table-scrollable-inner tbody tr'));
                return rows.map(row => {
                    const cells = row.querySelectorAll('td');
                    if(cells.length < 10) return null;
                    return {
                        symbol: cells[0].innerText.trim(),
                        time: cells[1].innerText.trim(),
                        type: cells[5].innerText.trim(), // Call / Put
                        trade_type: cells[7].innerText.trim(), // Block / Sweep
                        sentiment: cells[8].innerText.trim(), // Bullish / Bearish
                        premium: cells[9].innerText.trim() // Es: 1.2M
                    };
                }).filter(t => t !== null);
            }''')
            
        except Exception as e:
            print(f"Errore durante lo scraping di Barchart (probabile blocco anti-bot): {e}")
            trades_data = []
        finally:
            await browser.close()

    # Se lo scraper ha fallito o è stato bloccato, ritorniamo un set neutro
    if not trades_data:
        return {"sentiment": "UNKNOWN", "net_premium": 0, "bullish_premium": 0, "bearish_premium": 0, "status": "failed_or_empty"}

    # CALCOLO DEL SENTIMENT DI FABIO
    bullish_premium = 0.0
    bearish_premium = 0.0
    
    for trade in trades_data:
        # Filtriamo solo il simbolo di interesse (di default QQQ come proxy per NQ)
        if symbol not in trade['symbol']:
            continue
            
        # Filtriamo solo gli ordini ultra-aggressivi (Sweep) per il momentum
        # Se vuoi considerare anche i Block, togli questa condizione
        if trade['trade_type'].lower() != 'sweep':
            continue
            
        # Convertiamo la stringa "1.2M" o "500K" in numeri
        premium_str = trade['premium'].replace('$', '').replace(',', '')
        val = 0.0
        if 'M' in premium_str:
            val = float(premium_str.replace('M', '')) * 1_000_000
        elif 'K' in premium_str:
            val = float(premium_str.replace('K', '')) * 1_000
        else:
            try:
                val = float(premium_str)
            except ValueError:
                val = 0.0
                
        # Assegnazione
        if 'bullish' in trade['sentiment'].lower():
            bullish_premium += val
        elif 'bearish' in trade['sentiment'].lower():
            bearish_premium += val

    net_premium = bullish_premium - bearish_premium
    
    # LOGICA DI VERDETTO
    # Soglia minima di sbilanciamento (es. 1 milione di differenza) per avere "convinzione"
    threshold = 1_000_000 
    
    if net_premium > threshold:
        final_sentiment = "LONG"
    elif net_premium < -threshold:
        final_sentiment = "SHORT"
    else:
        final_sentiment = "CHOP"
        
    result = {
        "status": "success",
        "symbol_analyzed": symbol,
        "final_sentiment": final_sentiment,
        "net_premium_usd": net_premium,
        "bullish_premium_usd": bullish_premium,
        "bearish_premium_usd": bearish_premium
    }
    
    # Salviamo l'output
    out_file = Path("C:/Users/Mauro/Documents/nq-backtest-clean/output/barchart_sentiment.json")
    out_file.parent.mkdir(exist_ok=True)
    with open(out_file, 'w') as f:
        json.dump(result, f, indent=2)
        
    return result

if __name__ == "__main__":
    # Test script in locale
    res = asyncio.run(scrape_barchart_sentiment("QQQ"))
    print(json.dumps(res, indent=2))
