import os
from openai import AsyncOpenAI
from dotenv import load_dotenv

load_dotenv()

# Dictionary to map providers to their respective clients/models
PROVIDERS = {
    "gemini": {
        "api_key": os.getenv("GEMINI_API_KEY"),
        "base_url": "https://generativelanguage.googleapis.com/v1beta/openai/",
        "model": "gemini-1.5-pro" # default model, we can switch if needed
    },
    "groq": {
        "api_key": os.getenv("GROQ_API_KEY"),
        "base_url": "https://api.groq.com/openai/v1",
        "model": "llama-3.3-70b-versatile"
    },
    "openrouter": {
        "api_key": os.getenv("OPENROUTER_API_KEY"),
        "base_url": "https://openrouter.ai/api/v1",
        "model": "google/gemini-2.0-pro-exp-02-05:free" # using a free model by default
    }
}

def get_client(provider_name: str) -> AsyncOpenAI:
    provider = PROVIDERS.get(provider_name)
    if not provider:
        raise ValueError(f"Unknown provider: {provider_name}")

    api_key = provider.get("api_key")
    if not api_key:
        raise ValueError(f"API key missing for provider: {provider_name}")

    return AsyncOpenAI(
        api_key=api_key,
        base_url=provider.get("base_url")
    )

async def ask_copilot(provider_name: str, messages: list) -> str:
    """
    Asks the selected copilot provider for a response given a conversation history.
    `messages` should be a list of dicts: [{"role": "system"/"user"/"assistant", "content": "..."}]
    """
    provider = PROVIDERS.get(provider_name)
    if not provider:
        raise ValueError(f"Unknown provider: {provider_name}")

    client = get_client(provider_name)
    model = provider.get("model")

    try:
        response = await client.chat.completions.create(
            model=model,
            messages=messages,
            temperature=0.7
        )
        return response.choices[0].message.content
    except Exception as e:
        return f"Error connecting to {provider_name}: {str(e)}"
