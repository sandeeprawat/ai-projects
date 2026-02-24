from __future__ import annotations

from typing import Any, Dict, List, Tuple, Optional
from markdown_it import MarkdownIt

try:
    # Azure OpenAI SDK via OpenAI 1.x
    from openai import AzureOpenAI
except Exception:  # pragma: no cover
    AzureOpenAI = None

from azure.identity import DefaultAzureCredential
# Try multiple SDK import variants to support newer packages
AIProjectsClient = None
try:
    # Prefer the Azure AI Projects client; if unavailable, disable Agents path.
    from azure.ai.projects import AIProjectClient as _AIProjectsClient
    AIProjectsClient = _AIProjectsClient
except Exception:  # pragma: no cover
    AIProjectsClient = None
# Try to import agent thread/run models for create_thread_and_process_run
try:
    from azure.ai.agents.models import AgentThreadCreationOptions, ThreadMessage, ThreadMessageOptions, ListSortOrder, MessageTextContent, DeepResearchTool
except Exception:  # pragma: no cover
    AgentThreadCreationOptions = None
    ThreadMessageOptions = None
    ListSortOrder = None
    MessageTextContent = None
    DeepResearchTool = None

import time
import os
import html
from .config import Settings

import logging
logger = logging.getLogger("stock.openai_agent")
logger.info("openai_agent: availability - AIProjectsClient=%s, AzureOpenAI=%s", bool(AIProjectsClient), bool(AzureOpenAI))
# Log installed azure-ai-projects version for diagnostics
try:
    import azure.ai.projects as _ai_projects_mod
    logger.info("azure-ai-projects version: %s", getattr(_ai_projects_mod, "__version__", "unknown"))
except Exception as _e:
    logger.info("azure-ai-projects version: unavailable (%s)", repr(_e))

# Log which client symbol we resolved to (AIProjectClient vs AgentsClient)
try:
    _client_name = getattr(AIProjectsClient, "__name__", None)
    logger.info("ai_projects: resolved client symbol: %s", _client_name)
except Exception:
    pass

_md = MarkdownIt("gfm-like", {"linkify": False, "html": True})

def _normalize_url(u: str) -> str:
    """
    Ensure URLs are absolute and clickable. Adds https:// for bare domains or www.*, and resolves //scheme-relative.
    Returns empty string for invalid input.
    """
    try:
        if not isinstance(u, str):
            return ""
        s = u.strip()
        if not s:
            return ""
        if s.startswith("//"):
            return "https:" + s
        if s.startswith("http://") or s.startswith("https://"):
            return s
        if s.startswith("www."):
            return "https://" + s
        import re as _re
        if _re.match(r"^[A-Za-z0-9.-]+\.[A-Za-z]{2,}(/.*)?$", s):
            return "https://" + s
        return s
    except Exception:
        return ""

def _esc_attr(s: str) -> str:
    """Escape attribute values for safe HTML injection."""
    try:
        return html.escape(s or "", quote=True)
    except Exception:
        return s or ""

def _extract_url_citations_from_message(msg : ThreadMessage) -> List[Dict[str, str]]:
    """
    Extract URL citations from a ThreadMessage, matching the raw schema:
      content[*].text.annotations[*].url_citation.{url,title}
    Falls back to .details if SDK maps to that name.
    """
    results: List[Dict[str, str]] = []
    try:
        anns = msg.url_citation_annotations
        if not anns:
            return results
        for a in anns:
            url = ""
            title = "Source"
            try:
                details = a.url_citation
                if details:
                    _u = getattr(details, "url", "") or ""
                    url = _normalize_url(_u)
                    title = getattr(details, "title", None) or "Source"
            except Exception:
                url = ""
                title = "Source"
            if url:
                results.append({"title": str(title), "url": str(url)})
    except Exception as _e:
        logger.debug("extract url citations failed: %s", repr(_e))
    return results

def _debug_log_url_annotations(msg) -> None:
    try:
        anns = getattr(msg, "url_citation_annotations", None) or []
        for i, a in enumerate(anns):
            try:
                marker = getattr(a, "text", None) or ""
                start = getattr(a, "start_index", None)
                end = getattr(a, "end_index", None)
                details = getattr(a, "url_citation", None) or getattr(a, "details", None)
                url = getattr(details, "url", "") if details else ""
                title = getattr(details, "title", "") if details else ""
                logger.debug("url_annotation[%d]: text=%r start=%s end=%s url=%s title=%s", i, marker, start, end, url, title)
            except Exception:
                pass
    except Exception:
        pass

def _build_marker_map(msg) -> Dict[str, Dict[str, str]]:
    """
    Build a mapping from inline marker text (e.g., '【3:0†source】') to {url,title}
    from a ThreadMessage's url_citation_annotations.
    """
    mapping: Dict[str, Dict[str, str]] = {}
    try:
        anns = getattr(msg, "url_citation_annotations", None) or []
        for a in anns:
            try:
                marker = getattr(a, "text", None) or ""
                details = getattr(a, "url_citation", None) or getattr(a, "details", None)
                raw_url = getattr(details, "url", "") if details else ""
                url = _normalize_url(raw_url)
                title = getattr(details, "title", None) or "Source"
                if marker and url:
                    mapping[str(marker)] = {"url": str(url), "title": str(title)}
            except Exception:
                pass
    except Exception:
        pass
    return mapping

def _inject_superscripts_from_annotations(text: str, marker_map: Dict[str, Dict[str, str]]) -> Tuple[str, List[Dict[str, str]], Dict[str, int]]:
    """
    Replace inline marker substrings (e.g., '【3:0†source】') with superscripted
    citation links (<sup><a href="#cite-n">[n]</a></sup>) based on the provided marker_map.
    Returns: (new_text, ordered_citations, url_index_map)
    """
    if not isinstance(text, str) or not text or not marker_map:
        return text, [], {}
    import re
    pattern = re.compile(r"【[^】]+】")

    url_to_index: Dict[str, int] = {}
    next_idx = 1
    out_parts: List[str] = []
    last = 0
    replaced = 0

    for m in pattern.finditer(text):
        marker = m.group(0)
        meta = marker_map.get(marker) or {}
        url = meta.get("url") or ""
        title = meta.get("title") or "Source"

        out_parts.append(text[last:m.start()])
        if url:
            idx = url_to_index.get(url)
            if idx is None:
                idx = next_idx
                url_to_index[url] = idx
                next_idx += 1
            safe_url = _esc_attr(url)
            safe_title = _esc_attr(title)
            replacement = f'<sup><a href="{safe_url}" title="{safe_title}" target="_blank" rel="noopener noreferrer">[{idx}]</a></sup>'
        else:
            replacement = f"<sup>{_esc_attr(marker)}</sup>"
        out_parts.append(replacement)
        last = m.end()
        replaced += 1

    out_parts.append(text[last:])
    new_text = "".join(out_parts)

    citations: List[Dict[str, str]] = []
    for url, idx in sorted(url_to_index.items(), key=lambda kv: kv[1]):
        # Find a title for this URL from any marker entry
        title = "Source"
        try:
            for v in marker_map.values():
                if (v.get("url") or "") == url:
                    title = v.get("title") or "Source"
                    break
        except Exception:
            pass
        citations.append({"title": title, "url": url})

    try:
        logger.debug("superscripts injected: replacements=%d, urls=%d", replaced, len(url_to_index))
    except Exception:
        pass
    return new_text, citations, url_to_index

def _resolve_projects_config(mode: str):
    """
    Resolve Azure AI Projects endpoint/project (and agent_id for AgentMode) based on mode.
    Falls back to Settings.* when specific env vars are not set.
    Modes: "AgentMode", "DeepResearch"
    """
    if mode == "AgentMode":
        ep = os.getenv("AZURE_AI_PROJECTS_AGENTMODE_ENDPOINT") or getattr(Settings, "AZURE_AI_PROJECTS_ENDPOINT", "")
        pr = os.getenv("AZURE_AI_PROJECTS_AGENTMODE_PROJECT") or getattr(Settings, "AZURE_AI_PROJECTS_PROJECT", "")
        ag = os.getenv("AZURE_AI_PROJECTS_AGENTMODE_AGENT_ID") or getattr(Settings, "AZURE_AI_PROJECTS_AGENT_ID", "")
        return ep, pr, ag
    if mode == "DeepResearch":
        ep = os.getenv("AZURE_AI_PROJECTS_DEEPRESEARCH_ENDPOINT") or getattr(Settings, "AZURE_AI_PROJECTS_ENDPOINT", "")
        pr = os.getenv("AZURE_AI_PROJECTS_DEEPRESEARCH_PROJECT") or getattr(Settings, "AZURE_AI_PROJECTS_PROJECT", "")
        return ep, pr, None
    return getattr(Settings, "AZURE_AI_PROJECTS_ENDPOINT", ""), getattr(Settings, "AZURE_AI_PROJECTS_PROJECT", ""), getattr(Settings, "AZURE_AI_PROJECTS_AGENT_ID", "")

def _synthesize_with_deep_research(symbols: List[str], sources_per_symbol: List[Dict[str, Any]], user_prompt: Optional[str] = None) -> Dict[str, Any]:
    """
    Use Azure AI Projects Agents with the Deep Research tool to produce the report.
    Follows the Python sample: create DeepResearchTool, create an agent with that tool, run, collect output.
    """
    if not (AIProjectsClient and DeepResearchTool):
        raise RuntimeError("Deep Research not available (client or tool missing)")

    projects_endpoint, projects_project, _ = _resolve_projects_config("DeepResearch")
    logger.info("ai_projects (DeepResearch): endpoint=%r project=%r", projects_endpoint, projects_project)
    if not projects_endpoint:
        raise RuntimeError("PROJECT endpoint not configured")

    # Resolve model deployments and Bing connection
    model_name = os.getenv("MODEL_DEPLOYMENT_NAME") or getattr(Settings, "AZURE_OPENAI_DEPLOYMENT", "") or "gpt-4o"
    deep_model = os.getenv("DEEP_RESEARCH_MODEL_DEPLOYMENT_NAME") or "o3-deep-research"

    conn_id = ""
    bing_name = os.getenv("BING_RESOURCE_NAME", "")
    try:
        if bing_name:
            cred = DefaultAzureCredential(exclude_interactive_browser_credential=False)
            client_tmp = AIProjectsClient(endpoint=projects_endpoint, credential=cred)
            logger.info("ai_projects: attempting to resolve Bing connection by name=%r", bing_name)
            project_obj = None
            try:
                if hasattr(client_tmp, "get_project"):
                    project_obj = client_tmp.get_project(projects_project)
                elif hasattr(client_tmp, "projects") and hasattr(client_tmp.projects, "get_project"):
                    project_obj = client_tmp.projects.get_project(projects_project)
            except Exception as pe:
                logger.debug("ai_projects: get_project failed: %s", repr(pe))
                project_obj = None
            connections_svc = getattr(project_obj, "connections", None) if project_obj is not None else getattr(client_tmp, "connections", None)
            logger.info("ai_projects: connections_svc=%s (from project_obj=%s)", type(connections_svc).__name__ if connections_svc else None, project_obj is not None)
            if connections_svc is not None and hasattr(connections_svc, "get"):
                conn = connections_svc.get(name=bing_name)
                conn_id = getattr(conn, "id", "") or ""
                logger.info("ai_projects: resolved Bing connection id=%r", conn_id)
    except Exception as e:
        logger.warning("ai_projects: failed to resolve Bing connection: %s", repr(e))
    
    if not conn_id:
        raise RuntimeError(f"Bing connection id not configured - could not resolve BING_RESOURCE_NAME={bing_name!r} to a connection id")

    cred = DefaultAzureCredential(exclude_interactive_browser_credential=False)
    client = AIProjectsClient(endpoint=projects_endpoint, credential=cred)
    agents_svc = client.agents 
    # Create Deep Research tool and agent
    dr_tool = DeepResearchTool(
        bing_grounding_connection_id=conn_id,
        deep_research_model=deep_model,
    )
    default_instructions = "You are a helpful Agent that performs deep web research and produces a well-cited markdown report."
    base_dir = os.path.dirname(__file__)
    instructions_path = os.path.join(os.path.dirname(base_dir), "deepresearch.md")
    try:
        with open(instructions_path, "r", encoding="utf-8") as f:
            instructions = f.read().strip() or default_instructions
    except Exception:
        instructions = default_instructions
    agent = agents_svc.create_agent(
        model=model_name,
        name="deep-research-agent",
        instructions=instructions,
        tools=dr_tool.definitions,
    )

    # Build prompt and run
    prompt = user_prompt.strip() if user_prompt else _build_prompt(symbols, sources_per_symbol, None)
    thread = agents_svc.threads.create()
    agents_svc.messages.create(thread_id=getattr(thread, "id", None), role="user", content=prompt)
    run = agents_svc.runs.create(thread_id=getattr(thread, "id", None), agent_id=getattr(agent, "id", None))

    # Poll until completion
    for _ in range(1200):
        status = getattr(run, "status", None)
        if status in ("completed", "succeeded"):
            break
        if status in ("failed", "cancelled", "expired", "timed_out", "canceled"):
            raise RuntimeError(f"DeepResearch run status: {status}")
        time.sleep(1)
        run = agents_svc.runs.get(thread_id=getattr(thread, "id", None), run_id=getattr(run, "id", None))

    # Collect latest assistant message
    text = ""
    url_citations: List[Dict[str, str]] = []
    try:
        last_msg = None
        if hasattr(agents_svc, "messages") and hasattr(agents_svc.messages, "get_last_message_by_role"):
            last_msg = agents_svc.messages.get_last_message_by_role(thread_id=getattr(thread, "id", None), role="assistant")
        if last_msg is None:
            messages = agents_svc.messages.list(thread_id=getattr(thread, "id", None), order=(ListSortOrder.ASCENDING if ListSortOrder else None))
            for msg in messages:
                if getattr(msg, "role", "") == "assistant":
                    last_msg = msg
        collected: List[str] = []
        if last_msg is not None:
            if hasattr(last_msg, "text_messages") and last_msg.text_messages:
                for t in last_msg.text_messages:
                    val = getattr(getattr(t, "text", None), "value", "") or ""
                    if val:
                        collected.append(val)
            else:
                for part in getattr(last_msg, "content", []) or []:
                    if (MessageTextContent is not None) and isinstance(part, MessageTextContent):
                        val = getattr(getattr(part, "text", None), "value", "") or ""
                    elif isinstance(part, dict):
                        val = (part.get("text", {}) or {}).get("value", "") or ""
                    elif isinstance(part, str):
                        val = part
                    else:
                        val = ""
                    if val:
                        collected.append(val)
        if collected:
            # Log each assistant text segment
            try:
                for i, seg in enumerate(collected):
                    logger.debug("deep_research assistant part[%d]: %s", i, seg)
            except Exception:
                pass
            text = "\n".join(collected).strip()
        # Extract URL citation annotations if available
        try:
            if last_msg is not None:
                url_citations = _extract_url_citations_from_message(last_msg)
                logger.debug("deep_research url_citation_annotations: %s", url_citations)
                _debug_log_url_annotations(last_msg)
        except Exception:
            pass
    except Exception:
        pass
    finally:
        try:
            # Clean up ephemeral agent
            if hasattr(agents_svc, "delete_agent") and getattr(agent, "id", None):
                agents_svc.delete_agent(getattr(agent, "id", None))
        except Exception:
            pass

    try:
        logger.debug("deep_research assistant raw text:\n%s", text)
    except Exception:
        pass
    if not isinstance(text, str) or not text.strip():
        raise RuntimeError("Empty DeepResearch agent response")

    title_line = next((line.strip("# ").strip() for line in text.splitlines() if line.startswith("# ")), None)
    title = title_line or f"Deep Research Report: {', '.join(symbols) or 'Prompted'}"
    ann_citations: List[Dict[str, str]] = []
    try:
        marker_map = _build_marker_map(last_msg) if last_msg is not None else {}
    except Exception:
        marker_map = {}
    if marker_map:
        try:
            text_with_sup, ann_citations, _url_idx = _inject_superscripts_from_annotations(text, marker_map)
            if text_with_sup and text_with_sup != text:
                text = text_with_sup
        except Exception:
            pass
    md = text
    html = _md.render(md)
    citations: List[Dict[str, str]] = []
    seen_urls = set()
    # Prefer annotation-derived ordering for consistent numbering with superscripts
    for c in (ann_citations or []):
        u = _normalize_url(c.get("url") or "")
        t = c.get("title") or "Source"
        if u and u not in seen_urls:
            citations.append({"title": t, "url": u})
            seen_urls.add(u)
    for a in (url_citations or []):
        u = _normalize_url(a.get("url") or "")
        t = a.get("title") or "Source"
        if u and u not in seen_urls:
            citations.append({"title": t, "url": u})
            seen_urls.add(u)
    for entry in sources_per_symbol:
        for s in entry.get("sources") or []:
            u = _normalize_url(s.get("url") or "")
            t = s.get("title") or "Source"
            if u and u not in seen_urls:
                citations.append({"title": t, "url": u})
                seen_urls.add(u)
    logger.debug("deep_research combined citations: %s", citations)
    return {"title": title, "markdown": md, "html": html, "citations": citations}

def _synthesize_with_agent(symbols: List[str], sources_per_symbol: List[Dict[str, Any]], user_prompt: Optional[str] = None) -> Dict[str, Any]:
    """
    Use Azure AI Projects Agents with Managed Identity/AAD to produce the report.
    Modern flow: create_thread_and_process_run on the Agents surface (project.agents or client.agents), no deprecated create_response/create_session.
    Fallback to Azure OpenAI Assistants if available.
    """
    prompt = _build_prompt(symbols, sources_per_symbol, user_prompt) if not user_prompt else user_prompt.strip()

    # 1) Preferred path: Azure AI Projects SDK
    projects_endpoint, projects_project, agent_id = _resolve_projects_config("AgentMode")
    logger.info(
        "ai_projects gating: client=%s endpoint_set=%s project_set=%s agent_set=%s",
        bool(AIProjectsClient), bool(projects_endpoint), bool(projects_project), bool(agent_id)
    )
    logger.info("ai_projects (AgentMode): endpoint=%r project=%r agent_id=%r", projects_endpoint, projects_project, agent_id)
    # Extra diagnostics to trace why agent_set might be False
    try:
        logger.info("ai_projects Settings values: endpoint=%r project=%r agent_id=%r", projects_endpoint, projects_project, agent_id)
        _env_ep = os.getenv("AZURE_AI_PROJECTS_ENDPOINT")
        _env_pr = os.getenv("AZURE_AI_PROJECTS_PROJECT")
        _env_ag = os.getenv("AZURE_AI_PROJECTS_AGENT_ID")
        logger.info("ai_projects os.getenv values: endpoint=%r project=%r agent_id=%r", _env_ep, _env_pr, _env_ag)
        _keys = [k for k in os.environ.keys() if k.startswith("AZURE_AI_PROJECTS")]
        logger.info("ai_projects env keys present: %s", _keys)
    except Exception as _e:
        logger.info("ai_projects env dump failed: %s", repr(_e))
    if not (AIProjectsClient and projects_endpoint and projects_project and agent_id):
        logger.info(
            "ai_projects not used: client=%s endpoint_set=%s project_set=%s agent_set=%s",
            bool(AIProjectsClient), bool(projects_endpoint), bool(projects_project), bool(agent_id)
        )
    if AIProjectsClient and projects_endpoint and projects_project and agent_id:
        logger.info("openai_agent: using Azure AI Projects Agents path")
        try:
            logger.info("ai_projects: creating DefaultAzureCredential and AIProjectsClient (endpoint=%s, project_set=%s)", projects_endpoint, bool(projects_project))
            cred = DefaultAzureCredential(exclude_interactive_browser_credential=False)
            client = AIProjectsClient(endpoint=projects_endpoint, credential=cred)
            
            # Validate agent exists
            agent = client.agents.get_agent(agent_id=agent_id)
            logger.info("ai_projects: got agent response (id=%s)", agent.id if agent else "none")
            if not getattr(agent, "id", None):
                raise RuntimeError("Agent not found")

            # One-shot thread+run using typed models
            thread_payload = AgentThreadCreationOptions(
                messages=[ThreadMessageOptions(role="user", content=prompt)]
            ) if (AgentThreadCreationOptions and ThreadMessageOptions) else {
                "messages": [{"role": "user", "content": prompt}]
            }
            logger.info("ai_projects: calling agents.create_thread_and_process_run on agent_id=%s", agent_id)
            run = client.agents.create_thread_and_process_run(
                agent_id=agent_id,
                thread=thread_payload,
            )
            # Collect assistant messages from the completed thread
            text = ""
            messages = client.agents.messages.list(
                thread_id=getattr(run, "thread_id", None),
                order=(ListSortOrder.ASCENDING if ListSortOrder else None),
            )
            url_citations: List[Dict[str, str]] = []
            marker_map: Dict[str, Dict[str, str]] = {}
            collected: List[str] = []
            for msg in messages:
                if getattr(msg, "role", "") != "assistant":
                    continue
                # Collect URL citation annotations if available
                try:
                    anns = _extract_url_citations_from_message(msg)
                    if anns:
                        url_citations.extend(anns)
                    _debug_log_url_annotations(msg)
                    try:
                        mm = _build_marker_map(msg)
                        if mm:
                            for k, v in mm.items():
                                if k not in marker_map:
                                    marker_map[k] = v
                    except Exception:
                        pass
                except Exception:
                    pass
                try:
                    if hasattr(msg, "text_messages") and msg.text_messages:
                        for t in msg.text_messages:
                            val = getattr(getattr(t, "text", None), "value", "") or ""
                            if val and (not collected or collected[-1] != val):
                                collected.append(val)
                    else:
                        for part in getattr(msg, "content", []) or []:
                            if (MessageTextContent is not None) and isinstance(part, MessageTextContent):
                                val = getattr(getattr(part, "text", None), "value", "") or ""
                            elif isinstance(part, dict):
                                val = (part.get("text", {}) or {}).get("value", "") or ""
                            elif isinstance(part, str):
                                val = part
                            else:
                                val = ""
                            if val and (not collected or collected[-1] != val):
                                collected.append(val)
                except Exception:
                    pass
            if collected:
                try:
                    for i, seg in enumerate(collected):
                        logger.debug("agent assistant part[%d]: %s", i, seg)
                except Exception:
                    pass
                text = "\n".join(collected).strip()
            if not text:
                text = getattr(run, "output_text", None) or getattr(run, "content", None) or ""
            try:
                logger.debug("agent raw assistant text length=%d", len(text or ""))
            except Exception:
                pass
            try:
                logger.debug("agent assistant raw text:\n%s", text)
            except Exception:
                pass
            
            if not isinstance(text, str) or not text.strip():
                raise RuntimeError("Empty agent response")

            title_line = next((line.strip("# ").strip() for line in text.splitlines() if line.startswith("# ")), None)
            title = title_line or f"Deep Research Report: {', '.join(symbols) or 'Prompted'}"
            ann_citations: List[Dict[str, str]] = []
            try:
                if marker_map:
                    text_with_sup, ann_citations, _url_idx = _inject_superscripts_from_annotations(text, marker_map)
                    if text_with_sup and text_with_sup != text:
                        text = text_with_sup
            except Exception:
                pass
            md = text
            html = _md.render(md)
            citations: List[Dict[str, str]] = []
            seen_urls = set()
            # Prefer annotation-derived ordering
            for c in (ann_citations or []):
                u = _normalize_url(c.get("url") or "")
                t = c.get("title") or "Source"
                if u and u not in seen_urls:
                    citations.append({"title": t, "url": u})
                    seen_urls.add(u)
            for a in (url_citations or []):
                u = _normalize_url(a.get("url") or "")
                t = a.get("title") or "Source"
                if u and u not in seen_urls:
                    citations.append({"title": t, "url": u})
                    seen_urls.add(u)
            for entry in sources_per_symbol:
                for s in entry.get("sources") or []:
                    u = _normalize_url(s.get("url") or "")
                    t = s.get("title") or "Source"
                    if u and u not in seen_urls:
                        citations.append({"title": t, "url": u})
                        seen_urls.add(u)
            logger.debug("agent combined citations: %s", citations)
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
        title = title_line or f"Deep Research Report: {', '.join(symbols) or 'Prompted'}"
        md = text
        html = _md.render(md)

        citations: List[Dict[str, str]] = []
        for entry in sources_per_symbol:
            for s in entry.get("sources") or []:
                u = _normalize_url(s.get("url") or "")
                t = s.get("title") or "Source"
                if u:
                    citations.append({"title": t, "url": u})

        return {"title": title, "markdown": md, "html": html, "citations": citations}

    # If both strategies fail
    raise RuntimeError("Agent not configured")

def _build_prompt(symbols: List[str], sources_per_symbol: List[Dict[str, Any]], user_prompt: Optional[str] = None) -> str:
    lines: List[str] = []
    lines.append("You are an expert research assistant.")
    lines.append("")
    if user_prompt:
        lines.append("User Research Prompt:")
        lines.append(user_prompt)
        lines.append("")

    if symbols:
        lines.append(f"Symbols: {', '.join(symbols)}")
        lines.append("")
    
    lines.append("Output markdown with sections: Overview, Recent Developments, Financials, Risks, Outlook.")
    lines.append("Cite sources inline as [n] and provide a Citations list at the end with title + URL.")
    return "\n".join(lines)

def _fallback_report(symbols: List[str], sources_per_symbol: List[Dict[str, Any]], user_prompt: Optional[str] = None) -> Tuple[str, str, List[Dict[str, str]]]:
    title = f"Deep Research Report: {', '.join(symbols) or 'Prompted'}"
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
            u = _normalize_url(s.get("url") or "")
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
            t = c.get("title") or "Source"
            u = c.get("url") or ""
            sections.append(f"[{i}] [{t}]({u})")
    md = "\n".join(sections)
    return title, md, citations

def synthesize_report(symbols: List[str], sources_per_symbol: List[Dict[str, Any]], user_prompt: Optional[str] = None, deep_research: bool = False) -> Dict[str, Any]:
    """
    Returns: {"title": str, "markdown": str, "html": str, "citations": [...]}
    """
    if deep_research:
        try:
            return _synthesize_with_deep_research(symbols, sources_per_symbol, user_prompt)
        except Exception as e:
            logger.warning("openai_agent: deep research path failed: %s", repr(e))
            # fall through to other strategies

    endpoint = Settings.AZURE_OPENAI_ENDPOINT
    api_version = Settings.AZURE_OPENAI_API_VERSION
    deployment = Settings.AZURE_OPENAI_DEPLOYMENT
    api_key = Settings.AZURE_OPENAI_API_KEY

    # 1) Prefer Azure AI Projects Agents if configured, else try Assistants
    try:
        _ep, _pr, _ag = _resolve_projects_config("AgentMode")
        if (_ep and _pr and _ag) or (Settings.AZURE_OAI_ASSISTANT_ID and endpoint):
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
            title = title_line or f"Deep Research Report: {', '.join(symbols) or 'Prompted'}"
            md = text
            html = _md.render(md)

            citations: List[Dict[str, str]] = []
            for entry in sources_per_symbol:
                for s in entry.get("sources") or []:
                    u = _normalize_url(s.get("url") or "")
                    t = s.get("title") or "Source"
                    if u:
                        citations.append({"title": t, "url": u})

            return {"title": title, "markdown": md, "html": html, "citations": citations}
        except Exception:
            pass
