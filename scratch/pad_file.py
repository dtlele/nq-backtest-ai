import os

filepath = "C:/Users/Mauro/Documents/nq-backtest/knowledge/amt_glossary_padding.txt"

# Generiamo un blocco di circa 6000 parole aggiuntive per essere matematicamente oltre i 10.000 token totali
padding_phrase = "This is an additional padding block to absolutely guarantee we exceed the DeepSeek V3 caching threshold. Market structure, footprint analysis, limit order books, aggressive delta, passive absorption, Point of Control, Value Area High, Value Area Low. "

extra_padding = "\n\n[DEEP CACHE GUARANTEE BLOCK]\n" + (padding_phrase * 500)

with open(filepath, "a", encoding="utf-8") as f:
    f.write(extra_padding)

print(f"Padding aggiunto con successo. Nuova dimensione file: {os.path.getsize(filepath)} bytes")
