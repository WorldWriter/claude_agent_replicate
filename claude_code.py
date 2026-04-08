#!/usr/bin/env python3
"""Simplified Claude Code — A minimal Python replica of the Claude Code CLI.

Implements core architecture patterns discovered through source analysis:
- Agent loop: think → act → observe cycle with stop condition
- Tool system: 6 built-in tools + MCP external tools + parallel execution
- Context assembly: static/dynamic boundary for prompt caching
- Memory system: 4 types, Markdown frontmatter, MEMORY.md index
- Skill system: .claude/skills/*.md workflow templates

Usage:
    python claude_code.py chat "your question"
    python claude_code.py repl
    python claude_code.py remember "content" --type project --name "title"
    python claude_code.py memories [--query "keyword"]
"""
from __future__ import annotations

import argparse
import concurrent.futures
import datetime as dt
import fnmatch
import json
import os
import platform
import re
import subprocess
import sys
import textwrap
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
SYSTEM_PROMPT_DYNAMIC_BOUNDARY = "\n══════ SYSTEM_PROMPT_DYNAMIC_BOUNDARY ══════\n"
DEFAULT_MODEL = "claude-sonnet-4-20250514"
MAX_TURNS = 20
BASH_TIMEOUT = 120
MAX_TOOL_OUTPUT = 16000

# ---------------------------------------------------------------------------
# Tool base class
# ---------------------------------------------------------------------------

@dataclass
class ToolDef:
    """Anthropic API tool definition."""
    name: str
    description: str
    input_schema: Dict[str, Any]


class Tool:
    name: str
    description: str
    input_schema: Dict[str, Any]
    is_read_only: bool = True

    def execute(self, **kwargs) -> str:
        raise NotImplementedError

    def to_api_schema(self) -> Dict[str, Any]:
        return {"name": self.name, "description": self.description, "input_schema": self.input_schema}


# ---------------------------------------------------------------------------
# Built-in tools
# ---------------------------------------------------------------------------

class ReadTool(Tool):
    name = "Read"
    description = "Read a file. Returns numbered lines. Use offset/limit for large files."
    is_read_only = True
    input_schema = {
        "type": "object",
        "properties": {
            "file_path": {"type": "string", "description": "Absolute path to the file"},
            "offset": {"type": "integer", "description": "Line number to start from (0-based)", "default": 0},
            "limit": {"type": "integer", "description": "Max lines to read", "default": 2000},
        },
        "required": ["file_path"],
    }

    def execute(self, file_path: str, offset: int = 0, limit: int = 2000, **_) -> str:
        p = Path(file_path)
        if not p.exists():
            return f"Error: file not found: {file_path}"
        try:
            lines = p.read_text(encoding="utf-8", errors="replace").splitlines()
        except Exception as e:
            return f"Error reading file: {e}"
        selected = lines[offset : offset + limit]
        numbered = [f"{i + offset + 1}\t{line}" for i, line in enumerate(selected)]
        return "\n".join(numbered)


class WriteTool(Tool):
    name = "Write"
    description = "Write content to a file. Creates parent directories if needed."
    is_read_only = False
    input_schema = {
        "type": "object",
        "properties": {
            "file_path": {"type": "string", "description": "Absolute path to the file"},
            "content": {"type": "string", "description": "Content to write"},
        },
        "required": ["file_path", "content"],
    }

    def execute(self, file_path: str, content: str, **_) -> str:
        p = Path(file_path)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(content, encoding="utf-8")
        return f"Wrote {len(content)} bytes to {file_path}"


class EditTool(Tool):
    name = "Edit"
    description = "Replace exact string in a file. old_string must be unique unless replace_all=true."
    is_read_only = False
    input_schema = {
        "type": "object",
        "properties": {
            "file_path": {"type": "string", "description": "Absolute path to the file"},
            "old_string": {"type": "string", "description": "Exact text to find"},
            "new_string": {"type": "string", "description": "Replacement text"},
            "replace_all": {"type": "boolean", "description": "Replace all occurrences", "default": False},
        },
        "required": ["file_path", "old_string", "new_string"],
    }

    def execute(self, file_path: str, old_string: str, new_string: str, replace_all: bool = False, **_) -> str:
        p = Path(file_path)
        if not p.exists():
            return f"Error: file not found: {file_path}"
        text = p.read_text(encoding="utf-8")
        count = text.count(old_string)
        if count == 0:
            return "Error: old_string not found in file"
        if count > 1 and not replace_all:
            return f"Error: old_string found {count} times. Use replace_all=true or provide more context."
        if replace_all:
            result = text.replace(old_string, new_string)
        else:
            result = text.replace(old_string, new_string, 1)
        p.write_text(result, encoding="utf-8")
        return f"Replaced {count if replace_all else 1} occurrence(s) in {file_path}"


class BashTool(Tool):
    name = "Bash"
    description = "Execute a shell command. Returns stdout and stderr."
    is_read_only = False
    input_schema = {
        "type": "object",
        "properties": {
            "command": {"type": "string", "description": "Shell command to execute"},
            "timeout": {"type": "integer", "description": "Timeout in seconds", "default": BASH_TIMEOUT},
        },
        "required": ["command"],
    }

    def execute(self, command: str, timeout: int = BASH_TIMEOUT, **_) -> str:
        try:
            result = subprocess.run(
                command, shell=True, capture_output=True, text=True, timeout=timeout,
            )
            output = ""
            if result.stdout:
                output += result.stdout
            if result.stderr:
                output += f"\n[stderr]\n{result.stderr}"
            if result.returncode != 0:
                output += f"\n[exit code: {result.returncode}]"
            return output.strip()[:MAX_TOOL_OUTPUT] or "(no output)"
        except subprocess.TimeoutExpired:
            return f"Error: command timed out after {timeout}s"
        except Exception as e:
            return f"Error: {e}"


class GlobTool(Tool):
    name = "Glob"
    description = "Find files matching a glob pattern. Returns sorted file paths."
    is_read_only = True
    input_schema = {
        "type": "object",
        "properties": {
            "pattern": {"type": "string", "description": "Glob pattern (e.g. '**/*.py')"},
            "path": {"type": "string", "description": "Directory to search in (default: cwd)"},
        },
        "required": ["pattern"],
    }

    def execute(self, pattern: str, path: str = ".", **_) -> str:
        base = Path(path)
        if not base.is_dir():
            return f"Error: directory not found: {path}"
        matches = sorted(str(p) for p in base.glob(pattern) if p.is_file())
        if not matches:
            return "(no matches)"
        return "\n".join(matches[:200])


class GrepTool(Tool):
    name = "Grep"
    description = "Search file contents for a regex pattern. Returns matching lines with file paths and line numbers."
    is_read_only = True
    input_schema = {
        "type": "object",
        "properties": {
            "pattern": {"type": "string", "description": "Regex pattern to search for"},
            "path": {"type": "string", "description": "File or directory to search (default: cwd)"},
            "glob": {"type": "string", "description": "File glob filter (e.g. '*.py')"},
        },
        "required": ["pattern"],
    }

    def execute(self, pattern: str, path: str = ".", glob: str = "", **_) -> str:
        cmd = ["grep", "-rn", "-E", pattern]
        if glob:
            cmd.extend(["--include", glob])
        cmd.append(path)
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            output = result.stdout.strip()
            if not output:
                return "(no matches)"
            lines = output.splitlines()
            return "\n".join(lines[:100])
        except Exception as e:
            return f"Error: {e}"


BUILTIN_TOOLS: List[Tool] = [ReadTool(), WriteTool(), EditTool(), BashTool(), GlobTool(), GrepTool()]


# ---------------------------------------------------------------------------
# MCP Client (stdio transport)
# ---------------------------------------------------------------------------

class MCPTool(Tool):
    """Adapter: wraps an MCP server tool as a local Tool."""
    is_read_only = False  # conservative default

    def __init__(self, server_name: str, tool_name: str, description: str, schema: Dict, client: "MCPClient"):
        self.name = f"mcp__{server_name}__{tool_name}"
        self.description = description
        self.input_schema = schema
        self._client = client
        self._remote_name = tool_name

    def execute(self, **kwargs) -> str:
        return self._client.call_tool(self._remote_name, kwargs)


class MCPClient:
    """Minimal MCP client using JSON-RPC over stdio."""

    def __init__(self, server_name: str, command: str, args: List[str]):
        self.server_name = server_name
        self._req_id = 0
        try:
            self._proc = subprocess.Popen(
                [command] + args,
                stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            )
            self._initialize()
        except FileNotFoundError:
            raise RuntimeError(f"MCP server command not found: {command}")

    def _send(self, method: str, params: Dict | None = None) -> Any:
        self._req_id += 1
        msg = {"jsonrpc": "2.0", "id": self._req_id, "method": method}
        if params:
            msg["params"] = params
        data = json.dumps(msg) + "\n"
        self._proc.stdin.write(data.encode())
        self._proc.stdin.flush()
        line = self._proc.stdout.readline()
        if not line:
            raise RuntimeError(f"MCP server {self.server_name} closed connection")
        resp = json.loads(line)
        if "error" in resp:
            raise RuntimeError(f"MCP error: {resp['error']}")
        return resp.get("result")

    def _initialize(self):
        self._send("initialize", {
            "protocolVersion": "2024-11-05",
            "capabilities": {},
            "clientInfo": {"name": "simplified-claude-code", "version": "0.1"},
        })
        self._send("notifications/initialized")

    def list_tools(self) -> List[MCPTool]:
        result = self._send("tools/list")
        tools = []
        for t in result.get("tools", []):
            tools.append(MCPTool(
                server_name=self.server_name,
                tool_name=t["name"],
                description=t.get("description", ""),
                schema=t.get("inputSchema", {"type": "object", "properties": {}}),
                client=self,
            ))
        return tools

    def call_tool(self, tool_name: str, arguments: Dict) -> str:
        result = self._send("tools/call", {"name": tool_name, "arguments": arguments})
        if isinstance(result, dict):
            content = result.get("content", [])
            texts = [c.get("text", str(c)) for c in content if isinstance(c, dict)]
            return "\n".join(texts) if texts else json.dumps(result)
        return str(result)

    def close(self):
        try:
            self._proc.terminate()
            self._proc.wait(timeout=5)
        except Exception:
            self._proc.kill()


def load_mcp_servers(config_path: Path) -> List[MCPClient]:
    """Load MCP servers from .claude/mcp_servers.json."""
    if not config_path.exists():
        return []
    try:
        config = json.loads(config_path.read_text())
    except (json.JSONDecodeError, OSError):
        return []
    clients = []
    for name, spec in config.get("servers", {}).items():
        try:
            client = MCPClient(name, spec["command"], spec.get("args", []))
            clients.append(client)
        except Exception as e:
            print(f"[warn] Failed to connect MCP server '{name}': {e}", file=sys.stderr)
    return clients


# ---------------------------------------------------------------------------
# Tool parallel execution — partitionToolCalls
# ---------------------------------------------------------------------------

def partition_tool_calls(tool_calls: List[Dict], registry: Dict[str, Tool]) -> List[List[Dict]]:
    """Partition tool calls into batches: consecutive read-only tools run concurrently,
    non-read-only tools run one at a time (serial)."""
    batches: List[List[Dict]] = []
    current_ro_batch: List[Dict] = []
    for call in tool_calls:
        tool = registry.get(call["name"])
        is_ro = tool.is_read_only if tool else False
        if is_ro:
            current_ro_batch.append(call)
        else:
            if current_ro_batch:
                batches.append(current_ro_batch)
                current_ro_batch = []
            batches.append([call])
    if current_ro_batch:
        batches.append(current_ro_batch)
    return batches


def execute_batch(batch: List[Dict], registry: Dict[str, Tool]) -> List[Dict]:
    """Execute a batch of tool calls. If batch has multiple items, run concurrently."""
    def _run_one(call: Dict) -> Dict:
        tool = registry.get(call["name"])
        if not tool:
            content = f"Error: unknown tool '{call['name']}'"
        else:
            try:
                content = tool.execute(**call.get("input", {}))
            except Exception as e:
                content = f"Error executing {call['name']}: {e}"
        return {"type": "tool_result", "tool_use_id": call["id"], "content": content[:MAX_TOOL_OUTPUT]}

    if len(batch) == 1:
        return [_run_one(batch[0])]

    with concurrent.futures.ThreadPoolExecutor(max_workers=min(len(batch), 8)) as pool:
        futures = {pool.submit(_run_one, call): call for call in batch}
        results = []
        for future in concurrent.futures.as_completed(futures):
            results.append(future.result())
    return results


# ---------------------------------------------------------------------------
# Skill system
# ---------------------------------------------------------------------------

@dataclass
class Skill:
    name: str
    description: str
    allowed_tools: List[str]
    body: str
    source: Path


def _parse_frontmatter(text: str) -> tuple[Dict[str, Any], str]:
    """Parse YAML-like frontmatter from markdown."""
    if not text.startswith("---"):
        return {}, text
    end = text.find("---", 3)
    if end == -1:
        return {}, text
    fm_text = text[3:end].strip()
    body = text[end + 3:].strip()
    meta: Dict[str, Any] = {}
    for line in fm_text.splitlines():
        if ":" in line:
            key, _, val = line.partition(":")
            val = val.strip()
            # Parse simple list: [a, b, c]
            if val.startswith("[") and val.endswith("]"):
                val = [x.strip().strip("'\"") for x in val[1:-1].split(",")]
            meta[key.strip()] = val
    return meta, body


def load_skills(dirs: List[Path]) -> Dict[str, Skill]:
    """Load skills from directories. Earlier dirs have higher priority."""
    skills: Dict[str, Skill] = {}
    for d in reversed(dirs):  # reversed so earlier dirs override
        if not d.is_dir():
            continue
        for f in sorted(d.glob("*.md")):
            meta, body = _parse_frontmatter(f.read_text(encoding="utf-8", errors="replace"))
            name = meta.get("name", f.stem)
            if isinstance(name, list):
                name = name[0]
            skills[name] = Skill(
                name=name,
                description=meta.get("description", ""),
                allowed_tools=meta.get("allowed-tools", []),
                body=body,
                source=f,
            )
    return skills


# ---------------------------------------------------------------------------
# Memory system
# ---------------------------------------------------------------------------

MEMORY_TYPES = {"user", "feedback", "project", "reference"}


@dataclass
class MemoryEntry:
    name: str
    description: str
    mem_type: str
    content: str
    path: Path


class MemoryStore:
    """Markdown-file-based memory with MEMORY.md index."""

    def __init__(self, memory_dir: Path, index_path: Path):
        self.memory_dir = memory_dir
        self.index_path = index_path

    def remember(self, name: str, content: str, mem_type: str = "project", description: str = "") -> MemoryEntry:
        if mem_type not in MEMORY_TYPES:
            mem_type = "project"
        self.memory_dir.mkdir(parents=True, exist_ok=True)
        slug = re.sub(r"[^a-zA-Z0-9_\u4e00-\u9fff]+", "_", name).strip("_")[:60]
        filename = f"{mem_type}_{slug}.md"
        path = self.memory_dir / filename
        now = dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        desc = description or name
        md = f"---\nname: {name}\ndescription: {desc}\ntype: {mem_type}\ncreated_at: {now}\n---\n\n{content}\n"
        path.write_text(md, encoding="utf-8")
        self._update_index()
        return MemoryEntry(name=name, description=desc, mem_type=mem_type, content=content, path=path)

    def recall(self, query: str = "", limit: int = 5) -> List[MemoryEntry]:
        if not self.memory_dir.is_dir():
            return []
        entries = []
        for f in sorted(self.memory_dir.glob("*.md")):
            meta, body = _parse_frontmatter(f.read_text(encoding="utf-8", errors="replace"))
            entries.append(MemoryEntry(
                name=meta.get("name", f.stem),
                description=meta.get("description", ""),
                mem_type=meta.get("type", "project"),
                content=body,
                path=f,
            ))
        if not query:
            return entries[:limit]
        tokens = {t.lower() for t in re.findall(r"[a-zA-Z0-9_\u4e00-\u9fff]+", query) if len(t) > 1}
        scored = []
        for e in entries:
            text = f"{e.name} {e.description} {e.content}".lower()
            score = sum(text.count(t) for t in tokens)
            if score > 0:
                scored.append((score, e))
        scored.sort(key=lambda x: x[0], reverse=True)
        return [e for _, e in scored[:limit]]

    def _update_index(self):
        """Rebuild MEMORY.md index from memory directory."""
        if not self.memory_dir.is_dir():
            return
        lines = ["# Memory Index\n"]
        for f in sorted(self.memory_dir.glob("*.md")):
            meta, _ = _parse_frontmatter(f.read_text(encoding="utf-8", errors="replace"))
            name = meta.get("name", f.stem)
            desc = meta.get("description", "")
            rel = f.name
            lines.append(f"- [{name}](memory/{rel}) — {desc}")
        self.index_path.write_text("\n".join(lines) + "\n", encoding="utf-8")

    def load_index(self) -> str:
        if self.index_path.exists():
            return self.index_path.read_text(encoding="utf-8", errors="replace")
        return ""


# ---------------------------------------------------------------------------
# Context builder
# ---------------------------------------------------------------------------

class ContextBuilder:
    """Assembles system prompt with static/dynamic boundary."""

    def __init__(self, cwd: Path, context_files: List[Path] | None = None):
        self.cwd = cwd
        self.context_files = context_files or []

    def build(self, tools: List[Tool], memory_index: str) -> str:
        # --- Static section ---
        static_parts = [
            "# Identity\nYou are a simplified Claude Code agent. You help users with software engineering tasks using the tools available to you.",
            self._load_claude_md(),
            self._tool_summary(tools),
        ]

        # --- Dynamic section ---
        dynamic_parts = [
            self._environment_info(),
        ]
        if memory_index:
            dynamic_parts.append(f"# Memory\n{memory_index}")
        for cf in self.context_files:
            if cf.exists():
                dynamic_parts.append(f"# Context: {cf.name}\n{cf.read_text(encoding='utf-8', errors='replace')[:8000]}")

        return "\n\n".join(static_parts) + SYSTEM_PROMPT_DYNAMIC_BOUNDARY + "\n\n".join(dynamic_parts)

    def _load_claude_md(self) -> str:
        claude_md = self.cwd / "CLAUDE.md"
        if claude_md.exists():
            content = claude_md.read_text(encoding="utf-8", errors="replace")[:6000]
            return f"# Project Rules (CLAUDE.md)\n{content}"
        return ""

    def _tool_summary(self, tools: List[Tool]) -> str:
        lines = ["# Available Tools"]
        for t in tools:
            lines.append(f"- **{t.name}**: {t.description}")
        return "\n".join(lines)

    def _environment_info(self) -> str:
        git_status = ""
        try:
            r = subprocess.run(
                ["git", "status", "--short"], capture_output=True, text=True, timeout=5, cwd=str(self.cwd),
            )
            if r.returncode == 0:
                branch = subprocess.run(
                    ["git", "branch", "--show-current"], capture_output=True, text=True, timeout=5, cwd=str(self.cwd),
                ).stdout.strip()
                git_status = f"\nGit branch: {branch}\nGit status:\n{r.stdout.strip()[:1000]}"
        except Exception:
            pass
        return textwrap.dedent(f"""\
            # Environment
            - Working directory: {self.cwd}
            - Platform: {platform.system()} {platform.machine()}
            - Date: {dt.datetime.now().strftime('%Y-%m-%d %H:%M')}
            - Python: {platform.python_version()}{git_status}""")


# ---------------------------------------------------------------------------
# Agent loop
# ---------------------------------------------------------------------------

class AgentLoop:
    """Core agent loop: think → act → observe."""

    def __init__(
        self,
        tools: List[Tool],
        system_prompt: str,
        model: str = DEFAULT_MODEL,
        max_turns: int = MAX_TURNS,
    ):
        import anthropic
        self.client = anthropic.Anthropic()
        self.model = model
        self.max_turns = max_turns
        self.system_prompt = system_prompt
        self.registry: Dict[str, Tool] = {t.name: t for t in tools}
        self.api_tools = [t.to_api_schema() for t in tools]

    def run(self, user_message: str) -> str:
        """Run agent loop and return final assistant text."""
        messages = [{"role": "user", "content": user_message}]
        all_text: List[str] = []

        for turn in range(self.max_turns):
            response = self.client.messages.create(
                model=self.model,
                max_tokens=8192,
                system=self.system_prompt,
                tools=self.api_tools,
                messages=messages,
            )

            # Extract text and tool_use blocks
            text_parts = []
            tool_calls = []
            for block in response.content:
                if block.type == "text":
                    text_parts.append(block.text)
                elif block.type == "tool_use":
                    tool_calls.append({"id": block.id, "name": block.name, "input": block.input})

            if text_parts:
                text = "\n".join(text_parts)
                print(text)
                all_text.append(text)

            # No tool calls → done
            if not tool_calls:
                break

            # Append assistant message
            messages.append({"role": "assistant", "content": response.content})

            # Execute tools with partitioning
            batches = partition_tool_calls(tool_calls, self.registry)
            tool_results = []
            for batch in batches:
                batch_results = execute_batch(batch, self.registry)
                tool_results.extend(batch_results)

            # Print tool usage summary
            for call, result in zip(tool_calls, tool_results):
                content_preview = result["content"][:200]
                print(f"  [{call['name']}] {content_preview}{'...' if len(result['content']) > 200 else ''}")

            # Append tool results
            messages.append({
                "role": "user",
                "content": [
                    {"type": "tool_result", "tool_use_id": r["tool_use_id"], "content": r["content"]}
                    for r in tool_results
                ],
            })

            # Check stop reason
            if response.stop_reason == "end_turn":
                break
        else:
            print(f"\n[agent] Reached max turns ({self.max_turns})")

        return "\n".join(all_text)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def _resolve_paths(cwd: Path):
    claude_dir = cwd / ".claude"
    memory_dir = claude_dir / "memory"
    index_path = claude_dir / "MEMORY.md"
    skill_dirs = [claude_dir / "skills", Path.home() / ".claude" / "skills"]
    mcp_config = claude_dir / "mcp_servers.json"
    return claude_dir, memory_dir, index_path, skill_dirs, mcp_config


def cmd_chat(args: argparse.Namespace) -> None:
    cwd = Path.cwd()
    _, memory_dir, index_path, skill_dirs, mcp_config = _resolve_paths(cwd)

    memory_store = MemoryStore(memory_dir, index_path)
    context_files = [Path(p) for p in (args.context or [])]
    builder = ContextBuilder(cwd, context_files)

    # Collect all tools
    tools: List[Tool] = list(BUILTIN_TOOLS)

    # Load MCP tools
    mcp_clients = load_mcp_servers(mcp_config)
    for client in mcp_clients:
        try:
            tools.extend(client.list_tools())
        except Exception as e:
            print(f"[warn] MCP {client.server_name}: {e}", file=sys.stderr)

    system_prompt = builder.build(tools, memory_store.load_index())
    model = args.model if hasattr(args, "model") and args.model else DEFAULT_MODEL

    agent = AgentLoop(tools, system_prompt, model=model)
    agent.run(args.prompt)

    # Cleanup MCP
    for client in mcp_clients:
        client.close()


def cmd_repl(args: argparse.Namespace) -> None:
    cwd = Path.cwd()
    _, memory_dir, index_path, skill_dirs, mcp_config = _resolve_paths(cwd)

    memory_store = MemoryStore(memory_dir, index_path)
    context_files = [Path(p) for p in (args.context or [])]
    builder = ContextBuilder(cwd, context_files)
    skills = load_skills(skill_dirs)

    tools: List[Tool] = list(BUILTIN_TOOLS)
    mcp_clients = load_mcp_servers(mcp_config)
    for client in mcp_clients:
        try:
            tools.extend(client.list_tools())
        except Exception as e:
            print(f"[warn] MCP {client.server_name}: {e}", file=sys.stderr)

    model = args.model if hasattr(args, "model") and args.model else DEFAULT_MODEL

    # Skill listing
    if skills:
        print("Available skills: " + ", ".join(f"/{name}" for name in sorted(skills)))

    print("Type your message, /skill-name, or /exit to quit.\n")

    while True:
        try:
            user_input = input(">>> ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nBye!")
            break

        if not user_input:
            continue
        if user_input.lower() in ("/exit", "/quit"):
            print("Bye!")
            break

        # Check for skill invocation
        if user_input.startswith("/"):
            parts = user_input[1:].split(None, 1)
            skill_name = parts[0]
            skill_args = parts[1] if len(parts) > 1 else ""
            if skill_name in skills:
                skill = skills[skill_name]
                prompt = f"[Skill: {skill.name}]\n{skill.body}"
                if skill_args:
                    prompt += f"\n\nUser arguments: {skill_args}"
                user_input = prompt
                print(f"[skill] Executing /{skill.name}...")
            else:
                print(f"Unknown skill: /{skill_name}")
                continue

        system_prompt = builder.build(tools, memory_store.load_index())
        agent = AgentLoop(tools, system_prompt, model=model)
        agent.run(user_input)
        print()

    for client in mcp_clients:
        client.close()


def cmd_remember(args: argparse.Namespace) -> None:
    cwd = Path.cwd()
    _, memory_dir, index_path, _, _ = _resolve_paths(cwd)
    store = MemoryStore(memory_dir, index_path)
    entry = store.remember(args.name, args.text, mem_type=args.type)
    print(f"Stored memory [{entry.mem_type}] '{entry.name}' at {entry.path}")


def cmd_memories(args: argparse.Namespace) -> None:
    cwd = Path.cwd()
    _, memory_dir, index_path, _, _ = _resolve_paths(cwd)
    store = MemoryStore(memory_dir, index_path)
    entries = store.recall(args.query or "", limit=20)
    if not entries:
        print("No memories found.")
        return
    for e in entries:
        print(f"[{e.mem_type}] {e.name}")
        print(f"  {e.description}")
        preview = e.content[:150].replace("\n", " ")
        print(f"  {preview}{'...' if len(e.content) > 150 else ''}")
        print()


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Simplified Claude Code CLI")
    parser.add_argument("--model", default=DEFAULT_MODEL, help=f"Model to use (default: {DEFAULT_MODEL})")
    sub = parser.add_subparsers(dest="command", required=True)

    chat = sub.add_parser("chat", help="Run a single agent interaction")
    chat.add_argument("prompt", help="User message")
    chat.add_argument("--context", nargs="*", help="Extra context files to load")
    chat.set_defaults(func=cmd_chat)

    repl = sub.add_parser("repl", help="Interactive REPL with skill support")
    repl.add_argument("--context", nargs="*", help="Extra context files to load")
    repl.set_defaults(func=cmd_repl)

    remember = sub.add_parser("remember", help="Store a memory")
    remember.add_argument("text", help="Memory content")
    remember.add_argument("--name", required=True, help="Memory title")
    remember.add_argument("--type", default="project", choices=sorted(MEMORY_TYPES), help="Memory type")
    remember.set_defaults(func=cmd_remember)

    memories = sub.add_parser("memories", help="List/search stored memories")
    memories.add_argument("--query", default="", help="Filter by keyword")
    memories.set_defaults(func=cmd_memories)

    return parser


def main(argv: Sequence[str] | None = None) -> None:
    parser = build_parser()
    args = parser.parse_args(argv)
    args.func(args)


if __name__ == "__main__":
    main()
