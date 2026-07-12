import asyncio
import websockets
import json
import os
import time

LOG_FILE = "agent_memory/reasoning_log.jsonl"
TRADES_FILE = "agent_memory/trades_log.jsonl"

async def tail_file(filename, queue, msg_type):
    if not os.path.exists(filename):
        # Wait for file to be created
        while not os.path.exists(filename):
            await asyncio.sleep(1)
            
    with open(filename, 'r', encoding='utf-8') as f:
        # Move to the end of the file if you only want new data, 
        # but for a backtest dashboard we might want to stream the whole thing fast.
        # Let's stream from the beginning to build the chart, then tail.
        while True:
            line = f.readline()
            if not line:
                await asyncio.sleep(0.1)
                continue
            try:
                data = json.loads(line.strip())
                await queue.put({"type": msg_type, "data": data})
                # Add a tiny sleep to simulate streaming speed if reading history
                await asyncio.sleep(0.01)
            except json.JSONDecodeError:
                pass

async def broadcast(websocket):
    print(f"Client connected: {websocket.remote_address}")
    queue = asyncio.Queue()
    
    # Start tailing tasks
    task1 = asyncio.create_task(tail_file(LOG_FILE, queue, "candle_update"))
    task2 = asyncio.create_task(tail_file(TRADES_FILE, queue, "trade_update"))
    
    try:
        while True:
            msg = await queue.get()
            await websocket.send(json.dumps(msg))
    except websockets.exceptions.ConnectionClosed:
        print("Client disconnected.")
    finally:
        task1.cancel()
        task2.cancel()

async def main():
    server = await websockets.serve(broadcast, "localhost", 8765)
    print("WebSocket server started on ws://localhost:8765")
    await server.wait_closed()

if __name__ == "__main__":
    asyncio.run(main())
