from src.agents.llm_client import llm_ask
import time

if __name__ == "__main__":
    print("Testing OpenRouter (DeepSeek V3)...")
    system_prompt = "You are a helpful AI assistant. Always respond concisely."
    user_msg = "Please say 'Hello, OpenRouter works!' and tell me your model name."
    
    t0 = time.time()
    try:
        # Pass use_cache=False to avoid hitting our local disk cache
        response = llm_ask(system_prompt, user_msg, use_cache=False)
        t1 = time.time()
        print("\n--- RESPONSE ---")
        print(response)
        print("----------------")
        print(f"\nSuccess! Took {t1 - t0:.2f} seconds.")
    except Exception as e:
        print(f"\nFailed: {e}")
