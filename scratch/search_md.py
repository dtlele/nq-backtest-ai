import os
import re

def search_markdown_files():
    folders = [
        r'c:\Users\Mauro\Documents\nq-backtest',
        r'C:\Users\Mauro\.gemini\antigravity\brain\e86b7458-2bf7-4121-9908-1844e8f5d6dd'
    ]
    pattern = re.compile(r'2025-07|july|luglio', re.IGNORECASE)
    
    for folder in folders:
        for dirpath, _, filenames in os.walk(folder):
            if any(x in dirpath for x in ['.git', '__pycache__', '.pytest_cache', 'dashboard', 'node_modules']):
                continue
                
            for filename in filenames:
                if filename.endswith('.md') or filename.endswith('.txt'):
                    path = os.path.join(dirpath, filename)
                    try:
                        with open(path, 'r', encoding='utf-8', errors='ignore') as f:
                            for line_no, line in enumerate(f, 1):
                                if pattern.search(line):
                                    print(f"File: {os.path.relpath(path, folder)} | Line {line_no}: {line.strip()[:120]}")
                    except Exception as e:
                        pass

if __name__ == '__main__':
    search_markdown_files()
