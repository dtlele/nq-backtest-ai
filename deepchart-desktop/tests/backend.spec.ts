import { test, expect } from '@playwright/test';

test.describe('Python Backend Integration', () => {
  test('WebSocket streams valid tick/candle data', async ({ page }) => {
    // Apriamo la root solo per avere un contesto browser valido
    await page.goto('/');
    
    // Iniettiamo codice JS direttamente nel browser per testare la latenza e la validità del WS
    const wsResult = await page.evaluate(() => {
      return new Promise<any>((resolve) => {
        const ws = new WebSocket('ws://localhost:8765');
        
        // Timeout di 10 secondi per ricevere il primo tick dal backtester
        const timer = setTimeout(() => {
          ws.close();
          resolve({ error: 'Timeout 10s: Nessun dato ricevuto dal server Python.' });
        }, 10000);
        
        ws.onmessage = (event) => {
          clearTimeout(timer);
          ws.close();
          try {
            const data = JSON.parse(event.data);
            resolve({ payload: data });
          } catch (e: any) {
            resolve({ error: 'Dati JSON malformati ricevuti dal server: ' + e.message });
          }
        };
        
        ws.onerror = () => {
          clearTimeout(timer);
          resolve({ error: 'Connessione WS rifiutata dal server Python (porta 8765 chiusa)' });
        };
      });
    });
    
    // Verifica che non ci siano errori
    expect(wsResult.error).toBeUndefined();
    
    // Verifica la struttura del payload dal backtester
    expect(wsResult.payload).toBeDefined();
    expect(wsResult.payload.type).toBe('candle_update');
    expect(wsResult.payload.data).toHaveProperty('bar_close');
    expect(wsResult.payload.data).toHaveProperty('bar_volume');
    expect(wsResult.payload.data).toHaveProperty('bar_delta');
  });
});
