# Lightweight AI helper utilities (title generation, classification)
from __future__ import annotations

import logging
from typing import Optional

logger = logging.getLogger(__name__)


def generate_title(prompt: str, symbols: list[str] | None = None) -> Optional[str]:
    """Use Azure OpenAI to generate a short, descriptive title from a prompt."""
    from .config import Settings

    endpoint = Settings.AZURE_OPENAI_ENDPOINT
    api_key = Settings.AZURE_OPENAI_API_KEY
    api_version = Settings.AZURE_OPENAI_API_VERSION
    deployment = Settings.AZURE_OPENAI_DEPLOYMENT

    if not (endpoint and api_key and deployment):
        return None

    # Build context for the model
    context = prompt[:2000] if len(prompt) > 2000 else prompt
    if symbols:
        context = f"Symbols: {', '.join(symbols)}\n\n{context}"

    system_msg = (
        "Generate a short, descriptive title (max 10 words) for a research report "
        "based on the user's research prompt below. The title should capture the core "
        "topic or intent. Do NOT include quotes or punctuation wrapping the title. "
        "Respond with ONLY the title text, nothing else."
    )

    try:
        from openai import AzureOpenAI
        client = AzureOpenAI(api_key=api_key, api_version=api_version, azure_endpoint=endpoint)
        completion = client.chat.completions.create(
            model=deployment,
            messages=[
                {"role": "system", "content": system_msg},
                {"role": "user", "content": context},
            ],
            temperature=0.3,
            max_tokens=30,
        )
        title = (completion.choices[0].message.content or "").strip().strip('"\'')
        return title if title else None
    except Exception as exc:
        logger.warning("generate_title failed: %s", exc)
        return None
