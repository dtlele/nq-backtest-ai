import sys
try:
    with open('scratch/transcript.json', 'r', encoding='utf-16le') as f:
        content = f.read()
    with open('scratch/transcript.txt', 'w', encoding='utf-8') as f:
        f.write(content)
    print("Converted successfully.")
except Exception as e:
    print("Error:", e)
