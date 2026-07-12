import json
from pathlib import Path

ROOT = Path(__file__).parent.parent.absolute()

def main():
    cache_file = ROOT / "agent_memory" / "llm_cache.json"
    if not cache_file.exists():
        print("Cache file not found.")
        return
        
    with open(cache_file, encoding="utf-8") as f:
        cache = json.load(f)
        
    # Elenco esatto delle chiavi estratte dal log
    keys_list = [
        "af6b15d69bce6025b66eef7f9871f4bd095211aa9bfcced165e23e372bc99117",  # Chunk 1
        "e41f2b6d43e06e4541caffe35d8198dfada777627c3d8532031f0973f924462a",  # Chunk 2
        "afd6962bcc1f6599307eb947e25686dfa810910563c0641cf57202e4538a9bbd",  # Chunk 3
        "183f02eff16df64390c9a5dec9c93685489c5e69f1b7ba5cb927b1b15b10fb09",  # Chunk 4
        "827cb3fc9d15c961d87b350eed79b98103c8d5e1da8b8854cfcb5d6787be3aef",  # Chunk 5
        "9cba9c9a48fe355fda4f5e84d8a6e16c2b0137fc4522eed9f3a72ce9868561e4",  # Chunk 6
        "434bd50fab3ddb3e30341ded25d2b3e1330b0523aeaeeba2c21aa946f4371e54",  # Chunk 7
        "93b8bc8d1ae5a868eab28cfc5da48f747a597a7c124df346e01f698f5033c712",  # Chunk 8
        "5bc5f17dcb93c273afdb52de8c30d6fcd905796e6910226621ec4b1e39dae83c",  # Chunk 9
        "e55d86627fcd20152a1e23142cde05e10411df708c0a84a56e2bc1b686cfc799",  # Chunk 10
        "21553cb7b797f0a10eaa66b64bbc53d386e31cb35ae3baa49866f09d334d4656",  # Chunk 11
        "e9abf343ddc8ff1712fdf2447c26c7a876bb08a197a21de299480f807fbe8157",  # Chunk 12
        "03c4a472016bf72bdfa50f39b29279e20cd11a6c530b53dbce29515f2f2a1d88",  # Chunk 13
        "8a0f58ffdd222b4d3e40acec185d25434c5f3a8fffe73d05469ade3e18a93f0f",  # Chunk 14
        "0792fe8a8f047ea3c0eb77f81ffe7fd8c0f627a887567515c150ffb6f22aac94"   # Chunk 15
    ]
    
    output_dir = ROOT / "output" / "chunks_DyS79Eb92Ug"
    output_dir.mkdir(parents=True, exist_ok=True)
    
    print(f"Dumping {len(keys_list)} chunks to {output_dir}...")
    for idx, k in enumerate(keys_list):
        if k in cache:
            val = cache[k]
            chunk_num = idx + 1
            out_file = output_dir / f"chunk_{chunk_num:02d}.md"
            out_file.write_text(val, encoding="utf-8")
            print(f"[OK] Chunk {chunk_num:02d} written successfully.")
        else:
            print(f"[ERR] Key not found in cache: {k}")
            
    print("Done!")

if __name__ == "__main__":
    main()
