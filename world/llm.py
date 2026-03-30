import os
import requests

OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY", "")
DEFAULT_MODEL = os.getenv("LLM_MODEL", "minimax/minimax-m2.5:free")

def ask_llm(prompt: str, system: str = "", max_tokens: int = 500) -> str:
    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json",
        "HTTP-Referer": "https://github.com/autoworld",
    }
    messages = []
    if system:
        messages.append({"role": "system", "content": system})
    messages.append({"role": "user", "content": prompt})

    resp = requests.post(
        "https://openrouter.ai/api/v1/chat/completions",
        headers=headers,
        json={"model": DEFAULT_MODEL, "messages": messages, "max_tokens": max_tokens},
        timeout=30,
    )
    if not resp.ok:
        raise Exception(f"OpenRouter error {resp.status_code}: {resp.text}")
    return resp.json()["choices"][0]["message"]["content"].strip()
