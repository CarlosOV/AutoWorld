import os
import time
import requests

OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY", "")
DEFAULT_MODEL = os.getenv("LLM_MODEL", "minimax/minimax-m2.5:free")
FALLBACK_MODEL = os.getenv("LLM_FALLBACK_MODEL", "")  # empty = no fallback
MAX_TOKENS = int(os.getenv("LLM_MAX_TOKENS", "0"))  # 0 = no limit (let model decide)
WORLD_LANGUAGE = os.getenv("WORLD_LANGUAGE", "Spanish")  # language for all LLM outputs

# Pollinations.ai — free, no API key needed, OpenAI-compatible
POLLINATIONS_BASE = "https://text.pollinations.ai/openai"
POLLINATIONS_MODEL = os.getenv("LLM_POLLINATIONS_MODEL", "openai-fast")
USE_POLLINATIONS = os.getenv("USE_POLLINATIONS", "false").lower() == "true"


def _call_pollinations(messages: list, limit: int = None) -> str:
    """Call Pollinations.ai free API (no key needed)."""
    payload = {"model": POLLINATIONS_MODEL, "messages": messages}
    if limit:
        payload["max_tokens"] = limit
    resp = requests.post(
        f"{POLLINATIONS_BASE}/chat/completions",
        headers={"Content-Type": "application/json"},
        json=payload,
        timeout=120,
    )
    if not resp.ok:
        raise Exception(f"Pollinations error {resp.status_code}: {resp.text}")
    data = resp.json()
    content = data.get("choices", [{}])[0].get("message", {}).get("content")
    if not content:
        raise Exception("Pollinations returned no content")
    return content.strip()


def _call_model(model: str, messages: list, limit: int = None) -> str:
    """Single attempt to call a specific model via OpenRouter. Returns content string or raises."""
    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json",
        "HTTP-Referer": "https://github.com/autoworld",
    }
    payload = {"model": model, "messages": messages}
    if limit:
        payload["max_tokens"] = limit

    resp = requests.post(
        "https://openrouter.ai/api/v1/chat/completions",
        headers=headers,
        json=payload,
        timeout=120,
    )
    if resp.status_code == 429:
        retry_after = int(resp.headers.get("Retry-After", 60))
        raise Exception(f"RATE_LIMIT:{retry_after}:{resp.text}")
    if not resp.ok:
        raise Exception(f"OpenRouter error {resp.status_code}: {resp.text}")

    data = resp.json()
    message = data.get("choices", [{}])[0].get("message", {})
    content = message.get("content")

    if not content:
        reasoning = message.get("reasoning") or ""
        start = reasoning.rfind("{")
        end = reasoning.rfind("}") + 1
        if start >= 0 and end > start:
            content = reasoning[start:end]
        else:
            raise Exception(f"Model returned no content. finish_reason: {data.get('choices',[{}])[0].get('finish_reason')}")

    return content.strip()


def ask_llm(prompt: str, system: str = "", max_tokens: int = 500, language: str = None) -> str:
    """
    Call the LLM with automatic fallback.
    Primary:  LLM_MODEL env var (default: minimax/minimax-m2.5:free)
    Fallback: LLM_FALLBACK_MODEL env var (default: google/gemini-2.0-flash-exp:free)
    """
    lang = language or WORLD_LANGUAGE
    lang_instruction = f"Always respond in {lang}. All names, descriptions, and narratives must be in {lang}."
    messages = [
        {"role": "system", "content": (system + "\n\n" + lang_instruction).strip() if system else lang_instruction},
        {"role": "user", "content": prompt},
    ]
    limit = MAX_TOKENS if MAX_TOKENS else None

    # If Pollinations mode is enabled, use it directly (free, no key needed)
    if USE_POLLINATIONS:
        return _call_pollinations(messages, limit)

    # Try primary model (OpenRouter)
    try:
        return _call_model(DEFAULT_MODEL, messages, limit)
    except Exception as e:
        err = str(e)
        print(f"[llm] Primary model ({DEFAULT_MODEL}) failed: {err}")
        if not FALLBACK_MODEL or FALLBACK_MODEL == DEFAULT_MODEL:
            # Try Pollinations as last resort if no fallback configured
            print("[llm] Trying Pollinations.ai as last resort (free)...")
            time.sleep(1)
            return _call_pollinations(messages, limit)

    # Try configured fallback model
    print(f"[llm] Trying fallback model: {FALLBACK_MODEL}")
    time.sleep(2)
    return _call_model(FALLBACK_MODEL, messages, limit)
