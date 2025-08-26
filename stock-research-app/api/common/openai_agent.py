from __future__ import annotations

from typing import Any, Dict, List, Tuple, Optional
from markdown_it import MarkdownIt

try:
    # Azure OpenAI SDK via OpenAI 1.x
    from openai import AzureOpenAI  # type: ignore
except Exception:  # pragma: no cover
    AzureOpenAI = None  # type: ignore

from azure.identity import DefaultAzureCredential  # type: ignore
# Try multiple SDK import variants to support newer packages
AIProjectsClient = None  # type: ignore
try:
    # Newer azure-ai-projects exposes AIProjectClient (singular)
    from azure.ai.projects import AIProjectClient as _AIProjectsClient  # type: ignore
    AIProjectsClient = _AIProjectsClient  # type: ignore
except Exception:
    try:
        # azure-ai-agents exposes AgentsClient with a compatible endpoint/credential signature
        from azure.ai.agents import AgentsClient as _AIProjectsClient  # type: ignore
        AIProjectsClient = _AIProjectsClient  # type: ignore
    except Exception:  # pragma: no cover
        AIProjectsClient = None  # type: ignore
# Try to import agent thread/run models for create_thread_and_process_run
try:
    from azure.ai.agents.models import AgentThreadCreationOptions, ThreadMessageOptions, ListSortOrder, MessageTextContent, DeepResearchTool  # type: ignore
except Exception:  # pragma: no cover
    AgentThreadCreationOptions = None  # type: ignore
    ThreadMessageOptions = None  # type: ignore
    ListSortOrder = None  # type: ignore
    MessageTextContent = None  # type: ignore
    DeepResearchTool = None  # type: ignore

import time
import os
from .config import Settings

import logging
logger = logging.getLogger("stock.openai_agent")
logger.info("openai_agent: availability - AIProjectsClient=%s, AzureOpenAI=%s", bool(AIProjectsClient), bool(AzureOpenAI))
# Log installed azure-ai-projects version for diagnostics
try:
    import azure.ai.projects as _ai_projects_mod  # type: ignore
    logger.info("azure-ai-projects version: %s", getattr(_ai_projects_mod, "__version__", "unknown"))
except Exception as _e:
    logger.info("azure-ai-projects version: unavailable (%s)", repr(_e))

# Log which client symbol we resolved to (AIProjectClient vs AgentsClient)
try:
    _client_name = getattr(AIProjectsClient, "__name__", None)
    logger.info("ai_projects: resolved client symbol: %s", _client_name)
except Exception:
    pass

_md = MarkdownIt("commonmark", {"linkify": True})


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

    conn_id = os.getenv("AZURE_BING_CONNECTION_ID") or os.getenv("AZURE_BING_CONECTION_ID") or ""
    try:
        if not conn_id:
            # Optionally resolve by name via project connections
            bing_name = os.getenv("BING_RESOURCE_NAME", "")
            if bing_name:
                cred = DefaultAzureCredential(exclude_interactive_browser_credential=False)
                client_tmp = AIProjectsClient(endpoint=projects_endpoint, credential=cred)  # type: ignore
                project_obj = None
                try:
                    if hasattr(client_tmp, "get_project"):
                        project_obj = client_tmp.get_project(projects_project)  # type: ignore[attr-defined]
                    elif hasattr(client_tmp, "projects") and hasattr(client_tmp.projects, "get_project"):
                        project_obj = client_tmp.projects.get_project(projects_project)  # type: ignore[attr-defined]
                except Exception:
                    project_obj = None
                connections_svc = getattr(project_obj, "connections", None) if project_obj is not None else getattr(client_tmp, "connections", None)
                if connections_svc is not None and hasattr(connections_svc, "get"):
                    conn = connections_svc.get(name=bing_name)  # type: ignore[attr-defined]
                    conn_id = getattr(conn, "id", "") or ""
    except Exception:
        pass
    if not conn_id:
        raise RuntimeError("Bing connection id not configured (AZURE_BING_CONNECTION_ID or BING_RESOURCE_NAME)")

    cred = DefaultAzureCredential(exclude_interactive_browser_credential=False)
    client = AIProjectsClient(endpoint=projects_endpoint, credential=cred)  # type: ignore
    # Resolve agents service (project-scoped when available)
    project_obj = None
    try:
        if hasattr(client, "get_project"):
            project_obj = client.get_project(projects_project)  # type: ignore[attr-defined]
        elif hasattr(client, "projects") and hasattr(client.projects, "get_project"):
            project_obj = client.projects.get_project(projects_project)  # type: ignore[attr-defined]
    except Exception:
        project_obj = None
    agents_svc = getattr(project_obj, "agents", None) if project_obj is not None else getattr(client, "agents", None)

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
    agent = agents_svc.create_agent(  # type: ignore[attr-defined]
        model=model_name,
        name="deep-research-agent",
        instructions=instructions,
        tools=dr_tool.definitions,
    )

    # Build prompt and run
    prompt = user_prompt.strip() if user_prompt else _build_prompt(symbols, sources_per_symbol, None)
    thread = agents_svc.threads.create()  # type: ignore[attr-defined]
    agents_svc.messages.create(thread_id=getattr(thread, "id", None), role="user", content=prompt)  # type: ignore[attr-defined]
    run = agents_svc.runs.create(thread_id=getattr(thread, "id", None), agent_id=getattr(agent, "id", None))  # type: ignore[attr-defined]

    # Poll until completion
    for _ in range(1200):
        status = getattr(run, "status", None)
        if status in ("completed", "succeeded"):
            break
        if status in ("failed", "cancelled", "expired", "timed_out", "canceled"):
            raise RuntimeError(f"DeepResearch run status: {status}")
        time.sleep(1)
        run = agents_svc.runs.get(thread_id=getattr(thread, "id", None), run_id=getattr(run, "id", None))  # type: ignore[attr-defined]

    # Collect latest assistant message
    text = ""
    try:
        last_msg = None
        if hasattr(agents_svc, "messages") and hasattr(agents_svc.messages, "get_last_message_by_role"):
            last_msg = agents_svc.messages.get_last_message_by_role(thread_id=getattr(thread, "id", None), role="assistant")  # type: ignore[attr-defined]
        if last_msg is None:
            messages = agents_svc.messages.list(thread_id=getattr(thread, "id", None), order=(ListSortOrder.ASCENDING if ListSortOrder else None))  # type: ignore[attr-defined]
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
            text = "\n".join(collected).strip()
    except Exception:
        pass
    finally:
        try:
            # Clean up ephemeral agent
            if hasattr(agents_svc, "delete_agent") and getattr(agent, "id", None):
                agents_svc.delete_agent(getattr(agent, "id", None))  # type: ignore[attr-defined]
        except Exception:
            pass

    if not isinstance(text, str) or not text.strip():
        raise RuntimeError("Empty DeepResearch agent response")

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
            client = AIProjectsClient(endpoint=projects_endpoint, credential=cred)  # type: ignore
            # Resolve project-scoped agents service when available
            project_obj = None
            try:
                if hasattr(client, "get_project"):
                    project_obj = client.get_project(projects_project)  # type: ignore[attr-defined]
                elif hasattr(client, "projects") and hasattr(client.projects, "get_project"):
                    project_obj = client.projects.get_project(projects_project)  # type: ignore[attr-defined]
            except Exception as _proj_e:
                logger.debug("ai_projects: get_project failed: %s", repr(_proj_e))
                project_obj = None

            agents_svc = getattr(project_obj, "agents", None) if project_obj is not None else getattr(client, "agents", None)

            # Validate agent exists
            if agents_svc is not None:
                agent = agents_svc.get_agent(agent_id=agent_id)  # type: ignore[attr-defined]
            else:
                agent = getattr(client, "get_agent")(agent_id=agent_id)  # type: ignore[attr-defined]

            logger.info("ai_projects: got agent response (id=%s)", getattr(agent, "id", None))
            if not getattr(agent, "id", None):
                raise RuntimeError("Agent not found")

            # Try simple one-shot response using available surface
            text = ""
            if agents_svc is not None:
                try:
                    thread_payload = AgentThreadCreationOptions(
                        messages=[ThreadMessageOptions(role="user", content=prompt)]
                    ) if (AgentThreadCreationOptions and ThreadMessageOptions) else {
                        "messages": [{"role": "user", "content": prompt}]
                    }
                    logger.info("ai_projects: calling agents.create_thread_and_process_run on agent_id=%s", agent_id)
                    run = agents_svc.create_thread_and_process_run(  # type: ignore[attr-defined]
                        agent_id=agent_id,
                        thread=thread_payload,
                    )
                    # Collect all assistant messages from the completed thread
                    text = ""
                    try:
                        messages = agents_svc.messages.list(  # type: ignore[attr-defined]
                            thread_id=getattr(run, "thread_id", None),
                            order=(ListSortOrder.ASCENDING if ListSortOrder else None),
                        )
                        collected: List[str] = []
                        for msg in messages:
                            if getattr(msg, "role", "") != "assistant":
                                continue
                            # Prefer text_messages if available; otherwise parse generic content parts
                            try:
                                if hasattr(msg, "text_messages") and msg.text_messages:
                                    for t in msg.text_messages:
                                        val = getattr(getattr(t, "text", None), "value", "") or ""
                                        if val:
                                            if not collected or collected[-1] != val:
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
                                        if val:
                                            if not collected or collected[-1] != val:
                                                collected.append(val)
                            except Exception:
                                pass
                        if collected:
                            text = "\n".join(collected).strip()
                        if not text:
                            text = getattr(run, "output_text", None) or getattr(run, "content", None) or ""
                    except Exception as _e_list:
                        logger.debug("ai_projects: listing messages failed: %s", repr(_e_list))
                        text = getattr(run, "output_text", None) or getattr(run, "content", None) or ""
                except Exception as e:
                    logger.warning("ai_projects: create_thread_and_process_run path failed: %s", repr(e))
            
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
