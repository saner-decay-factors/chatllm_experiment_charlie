from __future__ import annotations

import json
import logging

import httpx

logger = logging.getLogger(__name__)

from backend.config import OPENROUTER_API_KEY, OPENROUTER_API_URL, OPENROUTER_MODEL_DEFAULT


class OpenRouterConfigError(RuntimeError):
    pass


_SYSTEM_PROMPT = (
    "Keep your answers short and concise. "
    "When writing mathematical expressions, use LaTeX notation: "
    r"\( ... \) for inline math and $$ ... $$ for display/block math. "
    "When writing currency values (e.g. dollar amounts), always escape the dollar sign as the HTML entity &#36; "
    "(e.g. write &#36;5.00 instead of $5.00) so it is never confused with a LaTeX delimiter."
)


def _build_messages(*, user_message: str, history: list[dict]) -> list[dict]:
    messages: list[dict] = [{"role": "system", "content": _SYSTEM_PROMPT}]
    for item in history:
        role = item.get("role")
        content = item.get("content")
        if role in {"user", "assistant"} and isinstance(content, str) and content.strip():
            messages.append({"role": role, "content": content.strip()})

    messages.append({"role": "user", "content": user_message.strip()})
    return messages


def _build_headers() -> dict[str, str]:
    return {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json",
        "HTTP-Referer": "http://localhost",
        "X-Title": "ChatLLM Experiment",
    }


async def generate_reply(*, user_message: str, history: list[dict], model: str | None = None) -> tuple[str, str]:
    if not OPENROUTER_API_KEY:
        raise OpenRouterConfigError(
            "OPENROUTER_API_KEY nao definido. Configure em .env ou environment variables."
        )

    resolved_model = model or OPENROUTER_MODEL_DEFAULT
    messages = _build_messages(user_message=user_message, history=history)

    payload = {
        "model": resolved_model,
        "messages": messages,
    }

    async with httpx.AsyncClient(timeout=60.0) as client:
        response = await client.post(OPENROUTER_API_URL, json=payload, headers=_build_headers())

    if response.status_code >= 400:
        raise RuntimeError(f"OpenRouter retornou erro {response.status_code}: {response.text}")

    data = response.json()
    content = data.get("choices", [{}])[0].get("message", {}).get("content", "")

    reply = content.strip()
    if not reply:
        raise RuntimeError("OpenRouter nao retornou conteudo de resposta.")

    return reply, resolved_model


_TITLE_PROMPT = (
    "You are a conversation title generator. Based on the user's message and the assistant's reply below, "
    "generate a short and descriptive title (maximum 6 words) for this conversation. "
    "Return ONLY the title text, nothing else. No quotes, no punctuation at the end."
)


async def generate_title(*, user_message: str, assistant_reply: str) -> str:
    """Faz uma chamada extra ao OpenRouter para gerar um titulo curto para a conversa."""
    if not OPENROUTER_API_KEY:
        raise OpenRouterConfigError(
            "OPENROUTER_API_KEY nao definido. Configure em .env ou environment variables."
        )

    messages = [
        {"role": "system", "content": _TITLE_PROMPT},
        {
            "role": "user",
            "content": (
                f"User message: {user_message}\n\n"
                f"Assistant reply: {assistant_reply}"
            ),
        },
    ]

    payload = {
        "model": OPENROUTER_MODEL_DEFAULT,
        "messages": messages,
        "max_tokens": 30,
    }

    async with httpx.AsyncClient(timeout=15.0) as client:
        response = await client.post(OPENROUTER_API_URL, json=payload, headers=_build_headers())

    if response.status_code >= 400:
        logger.warning(
            "generate_title falhou HTTP %s: %s",
            response.status_code,
            response.text[:200],
        )
        return None

    data = response.json()
    title = data.get("choices", [{}])[0].get("message", {}).get("content", "").strip()
    if not title:
        logger.warning("generate_title: resposta vazia da API")
        return None

    logger.info("generate_title: '%s'", title)
    return title[:100]


async def stream_reply(*, user_message: str, history: list[dict], model: str | None = None):
    if not OPENROUTER_API_KEY:
        raise OpenRouterConfigError(
            "OPENROUTER_API_KEY nao definido. Configure em .env ou environment variables."
        )

    resolved_model = model or OPENROUTER_MODEL_DEFAULT
    payload = {
        "model": resolved_model,
        "messages": _build_messages(user_message=user_message, history=history),
        "stream": True,
    }

    async with httpx.AsyncClient(timeout=90.0) as client:
        async with client.stream("POST", OPENROUTER_API_URL, json=payload, headers=_build_headers()) as response:
            if response.status_code >= 400:
                body = await response.aread()
                raise RuntimeError(
                    f"OpenRouter retornou erro {response.status_code}: {body.decode(errors='replace')}"
                )

            async for line in response.aiter_lines():
                if not line or not line.startswith("data:"):
                    continue

                data = line[len("data:") :].strip()
                if data == "[DONE]":
                    break

                try:
                    parsed = json.loads(data)
                except json.JSONDecodeError:
                    continue

                choices = parsed.get("choices") or []
                if not choices:
                    continue
                delta = choices[0].get("delta", {}).get("content")
                if isinstance(delta, str) and delta:
                    yield delta
