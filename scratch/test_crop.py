import os
import subprocess
from pathlib import Path
import static_ffmpeg

# Aggiunge ffmpeg al path
static_ffmpeg.add_paths()

tmp_dir = Path("tmp_data")
tmp_dir.mkdir(parents=True, exist_ok=True)

url = "https://www.youtube.com/watch?v=xUyqIjCfZzg"
start_sec = 0
end_sec = 180  # 3 minuti

start_str = f"{start_sec // 3600:02d}:{(start_sec % 3600) // 60:02d}:{start_sec % 60:02d}"
end_str = f"{end_sec // 3600:02d}:{(end_sec % 3600) // 60:02d}:{end_sec % 60:02d}"

temp_template = str(tmp_dir / "yt_test_crop.%(ext)s")

# Rimuovi file precedenti
for f in tmp_dir.glob("yt_test_crop*"):
    f.unlink()

print(f"Avvio download sezione: {start_str} - {end_str}")

cmd = [
    "python", "-m", "yt_dlp",
    "--format", "worst[ext=mp4]/worst",
    "-o", temp_template,
    "--download-sections", f"*{start_str}-{end_str}",
    "--force-keyframes-at-cuts",
    url
]

result = subprocess.run(cmd, capture_output=True, text=True)
print("Return code:", result.returncode)
print("Stdout:", result.stdout)
print("Stderr:", result.stderr)

print("File scaricati in tmp_data:")
for f in tmp_dir.glob("yt_test_crop*"):
    print(f" - {f.name} ({f.stat().st_size / (1024*1024):.2f} MB)")
