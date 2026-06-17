from src.agents.llm_client import llm_ask

def main():
    try:
        res = llm_ask("You are a helpful assistant.", "Say 'hello world'", use_cache=False)
        print("Response:", res)
    except Exception as e:
        print("Error calling LLM:", e)

if __name__ == '__main__':
    main()
