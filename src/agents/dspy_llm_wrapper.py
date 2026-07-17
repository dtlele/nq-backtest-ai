import dspy
from src.agents.llm_client import llm_ask

class CustomOpenRouterLM(dspy.LM):
    """
    A custom DSPy LM wrapper that uses our existing `llm_ask` from llm_client.py.
    This preserves our prefix-caching padding optimization and hardcoded fast-forward rules.
    """
    def __init__(self, model="z-ai/glm-5.2", **kwargs):
        super().__init__(model=model, **kwargs)
        self.provider = "openrouter"
        self.kwargs = {
            "temperature": kwargs.get("temperature", 0.0),
            "max_tokens": kwargs.get("max_tokens", 500)
        }
        self.history = []

    def basic_request(self, prompt: str, **kwargs):
        pass

    def __call__(self, prompt=None, messages=None, **kwargs):
        """
        Since DSPy sends a single prompt string, we will treat it as the user_msg,
        or split it if needed. However, since llm_ask expects a system_prompt and user_msg,
        we can pass the whole DSPy prompt as user_msg, and an empty system prompt.
        Alternatively, our llm_ask appends the padding to system_prompt, so we can just pass
        the prompt to system_prompt or user_msg.
        """
        # DSPy v3 might pass messages as a list of dicts. Let's handle both.
        if messages is not None:
            text_prompt = "\n".join([f"{msg['role']}: {msg['content']}" for msg in messages])
        else:
            text_prompt = prompt

        # We inject the prompt into the user message, and let llm_ask append the padding to system_prompt.
        system_prompt = "You are a helpful AI assistant."
        user_msg = text_prompt
        
        response = llm_ask(
            system_prompt=system_prompt,
            user_msg=user_msg,
            provider=self.provider,
            model=self.model,
            use_cache=True
        )

        self.history.append({
            "prompt": text_prompt,
            "response": {"choices": [{"message": {"content": response}}]},
            "kwargs": kwargs
        })

        return [response]
