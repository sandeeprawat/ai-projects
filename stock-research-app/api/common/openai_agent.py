from __future__ import annotations

from typing import Any, Dict, List, Tuple, Optional
from markdown_it import MarkdownIt

try:
    # Azure OpenAI SDK via OpenAI 1.x
    from openai import AzureOpenAI  # type: ignore
except Exception:  # pragma: no cover
    AzureOpenAI = None  # type: ignore

from azure.identity import DefaultAzureCredential  # type: ignore
try:
    from azure.ai.projects import AIProjectsClient  # type: ignore
except Exception:  # pragma: no cover
    AIProjectsClient = None  # type: ignore
import time
from .config import Settings

import logging
logger = logging.getLogger("stock.openai_agent")

_md = MarkdownIt("commonmark")

def _synthesize_with_agent(symbols: List[str], sources_per_symbol: List[Dict[str, Any]], user_prompt: Optional[str] = None) -> Dict[str, Any]:
    """
    Use Azure AI Projects Agents with Managed Identity/AAD to produce the report.
    First try azure-ai-projects (project.agents.get_agent / create_response).
    Fallback to Azure OpenAI Assistants if available.
    """
    prompt = _build_prompt(symbols, sources_per_symbol, user_prompt)

    # 1) Preferred path: Azure AI Projects SDK
    projects_endpoint = getattr(Settings, "AZURE_AI_PROJECTS_ENDPOINT", "")
    projects_project = getattr(Settings, "AZURE_AI_PROJECTS_PROJECT", "")
    agent_id = getattr(Settings, "AZURE_AI_PROJECTS_AGENT_ID", "")
    if AIProjectsClient and projects_endpoint and projects_project and agent_id:
        logger.info("openai_agent: using Azure AI Projects Agents path")
        try:
            cred = DefaultAzureCredential(exclude_interactive_browser_credential=False)
            client = AIProjectsClient(endpoint=projects_endpoint, credential=cred, project=projects_project)  # type: ignore
            # Validate agent exists
            agent = client.agents.get_agent(agent_id=agent_id)  # type: ignore[attr-defined]
            if not getattr(agent, "id", None):
                raise RuntimeError("Agent not found")

            # Try simple one-shot response
            # Recent SDKs expose create_response(agent_id=..., input=...)
            try:
                resp = client.agents.create_response(agent_id=agent_id, input=prompt)  # type: ignore[attr-defined]
                text = getattr(resp, "output_text", None) or getattr(resp, "content", None) or ""
            except Exception:
                # Try session-based flow if available (best-effort)
                text = ""
                try:
                    session = client.agents.create_session(agent_id=agent_id)  # type: ignore[attr-defined]
                    client.agents.send_message(session_id=getattr(session, "id", None), role="user", content=prompt)  # type: ignore[attr-defined]
                    # naive polling for a composed output if SDK provides it
                    for _ in range(30):
                        try:
                            msgs = client.agents.list_messages(session_id=getattr(session, "id", None))  # type: ignore[attr-defined]
                            # attempt to gather assistant messages
                            latest = ""
                            for m in getattr(msgs, "data", []) or []:
                                if getattr(m, "role", "") == "assistant":
                                    val = getattr(getattr(m, "content", None), "text", None) or getattr(m, "content", None) or ""
                                    if isinstance(val, str) and val.strip():
                                        latest = val
                                        break
                            if latest:
                                text = latest
                                break
                        except Exception:
                            pass
                        time.sleep(1)
                except Exception:
                    pass

            if not isinstance(text, str) or not text.strip():
                raise RuntimeError("Empty agent response")

            title_line = next((line.strip("# ").strip() for line in text.splitlines() if line.startswith("# ")), None)
            title = title_line or f"Stock Research Report: {', '.join(symbols) or 'Prompted'}"
            md = text
            html = _md.render(md)
            citations: List[Dict[str, str]] = []
            for entry in sources_per_symbol:
                for s in entry.get("sources") or []:
                    u = s.get("url")
                    t = s.get("title") or "Source"
                    if u:
                        citations.append({"title": t, "url": u})
            return {"title": title, "markdown": md, "html": html, "citations": citations}
        except Exception as e:
            logger.warning("openai_agent: Azure AI Projects Agents path failed: %s", repr(e))
            # fall through to Azure OpenAI Assistants
            pass

    # 2) Fallback path: Azure OpenAI Assistants via AzureOpenAI using API key if available, else AAD token
    endpoint = Settings.AZURE_OPENAI_ENDPOINT
    api_version = Settings.AZURE_OPENAI_API_VERSION
    api_key = Settings.AZURE_OPENAI_API_KEY
    assistant_id = Settings.AZURE_OAI_ASSISTANT_ID
    if AzureOpenAI and endpoint and assistant_id:
        client = None
        if api_key:
            logger.info("openai_agent: using Azure OpenAI Assistants with API key")
            client = AzureOpenAI(azure_endpoint=endpoint, api_version=api_version, api_key=api_key)
        else:
            logger.info("openai_agent: using Azure OpenAI Assistants with AAD token")
            cred = DefaultAzureCredential(exclude_interactive_browser_credential=False)
            token = cred.get_token("https://cognitiveservices.azure.com/.default").token
            client = AzureOpenAI(azure_endpoint=endpoint, api_version=api_version, azure_ad_token=token)

        thread = client.beta.threads.create()
        client.beta.threads.messages.create(thread_id=thread.id, role="user", content=prompt)
        run = client.beta.threads.runs.create(thread_id=thread.id, assistant_id=assistant_id)

        for _ in range(60):
            run = client.beta.threads.runs.retrieve(thread_id=thread.id, run_id=run.id)
            status = getattr(run, "status", None)
            if status == "completed":
                break
            if status in ("failed", "cancelled", "expired"):
                raise RuntimeError(f"Assistant run status: {status}")
            time.sleep(2)

        msgs = client.beta.threads.messages.list(thread_id=thread.id)
        text = ""
        for m in getattr(msgs, "data", []):
            if getattr(m, "role", "") != "assistant":
                continue
            parts: List[str] = []
            for c in getattr(m, "content", []) or []:
                try:
                    parts.append(c.text.value)
                except Exception:
                    try:
                        parts.append(c.get("text", {}).get("value", ""))
                    except Exception:
                        pass
            if parts:
                text = "\n".join([p for p in parts if p])
                if text:
                    break

        if not text:
            raise RuntimeError("No assistant response content")

        title_line = next((line.strip("# ").strip() for line in text.splitlines() if line.startswith("# ")), None)
        title = title_line or f"Stock Research Report: {', '.join(symbols) or 'Prompted'}"
        md = text
        html = _md.render(md)

        citations: List[Dict[str, str]] = []
        for entry in sources_per_symbol:
            for s in entry.get("sources") or []:
                u = s.get("url")
                t = s.get("title") or "Source"
                if u:
                    citations.append({"title": t, "url": u})

        return {"title": title, "markdown": md, "html": html, "citations": citations}

    # If both strategies fail
    raise RuntimeError("Agent not configured")

def _build_prompt(symbols: List[str], sources_per_symbol: List[Dict[str, Any]], user_prompt: Optional[str] = None) -> str:
    lines: List[str] = []
    lines.append("You are an equity research assistant. Create a concise but detailed research brief.")
    lines.append("")
    if user_prompt:
        lines.append("User Research Prompt:")
        lines.append(user_prompt)
        lines.append("")
    lines.append(f"Symbols: {', '.join(symbols)}" if symbols else "Symbols: (provided via prompt)")
    lines.append("")
    for entry in sources_per_symbol:
        sym = entry.get("symbol") or ""
        lines.append(f"Sources for {sym}:")
        for s in entry.get("sources") or []:
            title = s.get("title") or ""
            url = s.get("url") or ""
            excerpt = (s.get("excerpt") or "").strip()
            lines.append(f"- {title} ({url})")
            if excerpt:
                lines.append(f"  Excerpt: {excerpt[:500]}")
        lines.append("")
    lines.append("Output markdown with sections: Overview, Recent Developments, Financials, Risks, Outlook.")
    lines.append("Cite sources inline as [n] and provide a Citations list at the end with title + URL.")
    return "\n".join(lines)

def _fallback_report(symbols: List[str], sources_per_symbol: List[Dict[str, Any]], user_prompt: Optional[str] = None) -> Tuple[str, str, List[Dict[str, str]]]:
    title = f"Stock Research Report: {', '.join(symbols) or 'Prompted'}"
    citations: List[Dict[str, str]] = []
    idx = 1
    sections: List[str] = [f"# {title}", ""]
    sections.append("## Overview")
    sections.append("This is a locally generated summary.")
    if user_prompt:
        sections.append("")
        sections.append("## User Prompt")
        sections.append(user_prompt)
        sections.append("")
    sections.append("")
    for entry in sources_per_symbol:
        sym = entry.get("symbol") or ""
        sections.append(f"## {sym} - Recent Sources")
        for s in entry.get("sources") or []:
            t = s.get("title") or "Source"
            u = s.get("url") or ""
            ex = (s.get("excerpt") or "").strip()
            if u:
                citations.append({"title": t, "url": u})
                sections.append(f"- {t} [{idx}]")
                if ex:
                    sections.append(f"  - {ex[:300]}")
                idx += 1
        sections.append("")
    if citations:
        sections.append("## Citations")
        for i, c in enumerate(citations, start=1):
            sections.append(f"[{i}] {c.get('title')}: {c.get('url')}")
    md = "\n".join(sections)
    return title, md, citations

def synthesize_report(symbols: List[str], sources_per_symbol: List[Dict[str, Any]], user_prompt: Optional[str] = None) -> Dict[str, Any]:
    """
    Returns: {"title": str, "markdown": str, "html": str, "citations": [...]}
    """
    endpoint = Settings.AZURE_OPENAI_ENDPOINT
    api_version = Settings.AZURE_OPENAI_API_VERSION
    deployment = Settings.AZURE_OPENAI_DEPLOYMENT
    api_key = Settings.AZURE_OPENAI_API_KEY

    # 1) Prefer Azure AI Projects Agents if configured, else try Assistants
    try:
        if (Settings.AZURE_AI_PROJECTS_ENDPOINT and Settings.AZURE_AI_PROJECTS_PROJECT and Settings.AZURE_AI_PROJECTS_AGENT_ID) or (Settings.AZURE_OAI_ASSISTANT_ID and endpoint):
            logger.info("openai_agent: attempting agent/assistants path")
            return _synthesize_with_agent(symbols, sources_per_symbol, user_prompt)
    except Exception as e:
        logger.warning("openai_agent: agent/assistants path raised: %s", repr(e))
        # fall through to other strategies
        pass

    # 2) Fallback to Chat Completions with API key if configured
    if AzureOpenAI and api_key and endpoint and deployment:
        logger.info("openai_agent: using Chat Completions with API key")
        prompt = _build_prompt(symbols, sources_per_symbol, user_prompt)
        client = AzureOpenAI(api_key=api_key, api_version=api_version, azure_endpoint=endpoint)
        try:
            completion = client.chat.completions.create(
                model=deployment,
                messages=[
                    {"role": "system", "content": "You are a helpful financial research assistant."},
                    {"role": "user", "content": prompt},
                ],
                temperature=0.2,
                max_tokens=2000,
            )
            text = (completion.choices[0].message.content or "").strip()
            if not text:
                raise RuntimeError("Empty completion")
            title_line = next((line.strip("# ").strip() for line in text.splitlines() if line.startswith("# ")), None)
            title = title_line or f"Stock Research Report: {', '.join(symbols) or 'Prompted'}"
            md = text
            html = _md.render(md)

            citations: List[Dict[str, str]] = []
            for entry in sources_per_symbol:
                for s in entry.get("sources") or []:
                    u = s.get("url")
                    t = s.get("title") or "Source"
                    if u:
                        citations.append({"title": t, "url": u})
            return {"title": title, "markdown": md, "html": html, "citations": citations}
        except Exception:
            pass

    # 3) Final fallback: local synthesizer
    logger.warning("openai_agent: falling back to local synthesizer")
    title, md, citations = _fallback_report(symbols, sources_per_symbol, user_prompt)
    html = _md.render(md)
    return {"title": title, "markdown": md, "html": html, "citations": citations}
