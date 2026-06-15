"""Generic OpenAI-compatible chat client (Groq / Ollama / Gemini / OpenAI / Claude).

Uses plain `requests` so there's no provider SDK to install. Swapping providers is
purely config (LLM_BASE_URL / LLM_API_KEY / LLM_MODEL) — no code change. This is the
"Splunk-hosted-ready" seam: point LLM_BASE_URL at a Splunk-hosted model later.
"""
from __future__ import annotations

import json

import requests


class LLMError(Exception):
    pass


class OpenAICompatLLM:
    def __init__(self, base_url: str, api_key: str, model: str, timeout: float = 45.0):
        self.base = base_url.rstrip("/")
        self.key = api_key
        self.model = model
        self.timeout = timeout

    @property
    def name(self) -> str:
        return self.model

    def chat(self, messages: list[dict], temperature: float = 0.2,
             max_tokens: int = 900) -> str:
        body = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        try:
            resp = requests.post(
                f"{self.base}/chat/completions",
                headers={"Authorization": f"Bearer {self.key}",
                         "Content-Type": "application/json"},
                json=body, timeout=self.timeout,
            )
        except requests.RequestException as exc:
            raise LLMError(f"LLM request failed: {exc}") from exc
        if resp.status_code >= 400:
            raise LLMError(f"LLM {resp.status_code}: {resp.text[:200]}")
        try:
            return resp.json()["choices"][0]["message"]["content"] or ""
        except (KeyError, IndexError, ValueError) as exc:
            raise LLMError(f"Unexpected LLM response: {str(exc)[:120]}") from exc


def extract_json(text: str) -> dict:
    """Best-effort: pull the first JSON object out of an LLM reply (handles code fences)."""
    t = text.strip()
    if t.startswith("```"):
        t = t.strip("`")
        if t[:4].lower() == "json":
            t = t[4:]
    start, end = t.find("{"), t.rfind("}")
    if start == -1 or end == -1 or end < start:
        raise LLMError(f"No JSON object in LLM reply: {text[:120]}")
    return json.loads(t[start:end + 1])
