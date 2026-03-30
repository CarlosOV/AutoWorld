import os
import requests

OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY", "")
DEFAULT_MODEL = os.getenv("LLM_MODEL", "minimax/minimax-m2.5:free")
MAX_TOKENS = int(os.getenv("LLM_MAX_TOKENS", "0"))  # 0 = no limit (let model decide)

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

    # If LLM_MAX_TOKENS is set, use it; otherwise don't send the param (model decides)
    payload = {"model": DEFAULT_MODEL, "messages": messages}
    limit = MAX_TOKENS or max_tokens if MAX_TOKENS else None
    if limit:
        payload["max_tokens"] = limit

    resp = requests.post(
        "https://openrouter.ai/api/v1/chat/completions",
        headers=headers,
        json=payload,
        timeout=120,
    )
    if not resp.ok:
        raise Exception(f"OpenRouter error {resp.status_code}: {resp.text}")

    data = resp.json()
    message = data.get("choices", [{}])[0].get("message", {})
    content = message.get("content")

    # Fallback: some reasoning models put output only in 'reasoning' when tokens run out
    if not content:
        reasoning = message.get("reasoning") or ""
        # Try to extract JSON from reasoning as last resort
        start = reasoning.rfind("{")
        end = reasoning.rfind("}") + 1
        if start >= 0 and end > start:
            content = reasoning[start:end]
        else:
            raise Exception(f"Model returned no content. finish_reason: {data.get('choices',[{}])[0].get('finish_reason')}")

    return content.strip()
