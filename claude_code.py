#!/usr/bin/env python3
"""Simplified Claude Code CLI inspired by the exposed TypeScript source.

This script mirrors the high-level architecture documented in README_old.md
and docs/*.md by implementing the following concepts:
- Context builder with static/dynamic sections split by a boundary marker
- Minimal tool registry (ReadFile / SearchFile / MemoryNote) with metadata
- Memory store that persists Markdown-style facts per type (user/project/etc.)
- Doc indexer that surfaces relevant research notes for each query
- Agent loop that assembles a system prompt, derives a short plan, and emits
  human-readable responses without needing a remote LLM
"""
from __future__ import annotations

import argparse
import dataclasses
import datetime as dt
import json
import os
import re
import textwrap
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterable, List, Sequence

REPO_ROOT = Path(__file__).resolve().parent
DOCS_DIR = REPO_ROOT / "docs"
CLAUDE_DOC = REPO_ROOT / "CLAUDE.md"
README_DOC = REPO_ROOT / "README.md"
SYSTEM_PROMPT_DYNAMIC_BOUNDARY = "__SYSTEM_PROMPT_DYNAMIC_BOUNDARY__"
DEFAULT_MEMORY_PATH = REPO_ROOT / ".claude_memory.json"


# --------------------------------------------------------------------------------------
# Utility helpers
# --------------------------------------------------------------------------------------
def read_text(path: Path, limit: int | None = None) -> str:
    """Read UTF-8 text with safe defaults."""
    data = path.read_text(encoding="utf-8")
    if limit is not None:
        return data[:limit]
    return data


def clamp_lines(text: str, limit: int) -> str:
    lines = text.splitlines()
    if len(lines) <= limit:
        return text
    return "\n".join(lines[:limit]) + "\n..."


# --------------------------------------------------------------------------------------
# Memory Store
# --------------------------------------------------------------------------------------
@dataclass
class MemoryEntry:
    text: str
    mem_type: str
    created_at: str


class MemoryStore:
    """Very small persistence layer that mimics memdir/memoryTypes.ts."""

    def __init__(self, path: Path = DEFAULT_MEMORY_PATH) -> None:
        self.path = path
        self._data: Dict[str, List[MemoryEntry]] = {"user": [], "project": [], "reference": [], "feedback": []}
        self._load()

    def _load(self) -> None:
        if not self.path.exists():
            return
        try:
            raw = json.loads(self.path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            return
        for mem_type, entries in raw.items():
            bucket = self._data.setdefault(mem_type, [])
            for entry in entries:
                bucket.append(MemoryEntry(**entry))

    def _flush(self) -> None:
        payload = {key: [dataclasses.asdict(entry) for entry in entries] for key, entries in self._data.items()}
        try:
            self.path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
        except OSError:
            # read-only environments can ignore persistence failures
            pass

    def remember(self, text: str, mem_type: str = "project") -> MemoryEntry:
        entry = MemoryEntry(text=text, mem_type=mem_type, created_at=dt.datetime.utcnow().isoformat() + "Z")
        self._data.setdefault(mem_type, []).append(entry)
        self._data[mem_type] = self._data[mem_type][-25:]
        self._flush()
        return entry

    def recall(self, query: str, limit: int = 3) -> List[MemoryEntry]:
        tokens = {token for token in re.findall(r"[a-zA-Z0-9_]+", query.lower()) if len(token) > 3}
        scored: List[tuple[int, MemoryEntry]] = []
        for entries in self._data.values():
            for entry in entries:
                text_lower = entry.text.lower()
                score = sum(text_lower.count(token) for token in tokens) if tokens else 1
                if score:
                    scored.append((score, entry))
        scored.sort(key=lambda item: item[0], reverse=True)
        return [entry for _, entry in scored[:limit]]


# --------------------------------------------------------------------------------------
# Tools
# --------------------------------------------------------------------------------------
@dataclass
class ToolResult:
    name: str
    content: str
    metadata: Dict[str, str] | None = None


class Tool:
    name: str
    description: str
    is_concurrency_safe: bool

    def __init__(self, name: str, description: str, is_concurrency_safe: bool = True) -> None:
        self.name = name
        self.description = description
        self.is_concurrency_safe = is_concurrency_safe

    def run(self, **kwargs) -> ToolResult:
        raise NotImplementedError


class FileReadTool(Tool):
    def __init__(self, repo_root: Path) -> None:
        super().__init__("ReadFile", "Read repository files with path safeguards.")
        self.repo_root = repo_root

    def run(self, path: str, limit: int = 4000) -> ToolResult:
        target = (self.repo_root / path).resolve()
        target.relative_to(self.repo_root)
        data = read_text(target, limit=limit)
        return ToolResult(self.name, data, {"path": str(target)})


class SearchTool(Tool):
    def __init__(self, file_reader: FileReadTool) -> None:
        super().__init__("SearchFile", "Search for literal matches within a file.")
        self.file_reader = file_reader

    def run(self, path: str, query: str, max_matches: int = 5) -> ToolResult:
        content = self.file_reader.run(path, limit=20000).content
        matches: List[str] = []
        for lineno, line in enumerate(content.splitlines(), 1):
            if query.lower() in line.lower():
                matches.append(f"{lineno:>4}: {line.strip()}")
            if len(matches) >= max_matches:
                break
        result = "\n".join(matches) if matches else "(no matches)"
        return ToolResult(self.name, result, {"path": str((self.file_reader.repo_root / path).resolve())})


class MemoryNoteTool(Tool):
    def __init__(self, store: MemoryStore) -> None:
        super().__init__("MemoryNote", "Persist a short memory entry in the local store.", is_concurrency_safe=False)
        self.store = store

    def run(self, text: str, mem_type: str = "project") -> ToolResult:
        entry = self.store.remember(text, mem_type=mem_type)
        return ToolResult(self.name, f"stored: {entry.text}", {"mem_type": mem_type, "timestamp": entry.created_at})


# --------------------------------------------------------------------------------------
# Document index
# --------------------------------------------------------------------------------------
@dataclass
class DocHit:
    path: Path
    score: int
    snippet: str


class DocIndex:
    def __init__(self, docs_dir: Path) -> None:
        self.docs: List[tuple[Path, str, str]] = []
        for path in sorted(docs_dir.rglob("*.md")):
            text = read_text(path)
            self.docs.append((path, text, text.lower()))

    def search(self, query: str, limit: int = 3) -> List[DocHit]:
        tokens = [token for token in re.findall(r"[a-zA-Z0-9_]+", query.lower()) if len(token) > 3]
        if not tokens:
            tokens = query.lower().split()
        scored: List[tuple[int, Path, str]] = []
        for path, text, text_lower in self.docs:
            score = sum(text_lower.count(token) for token in tokens)
            if score:
                snippet = self._extract_snippet(text, tokens[0])
                scored.append((score, path, snippet))
        scored.sort(key=lambda item: item[0], reverse=True)
        hits = [DocHit(path=item[1], score=item[0], snippet=item[2]) for item in scored[:limit]]
        return hits

    @staticmethod
    def _extract_snippet(text: str, token: str) -> str:
        token_lower = token.lower()
        for line in text.splitlines():
            if token_lower in line.lower():
                return line.strip()
        return clamp_lines(text, 3)


# --------------------------------------------------------------------------------------
# Context builder
# --------------------------------------------------------------------------------------
class ContextBuilder:
    def __init__(self, repo_root: Path) -> None:
        self.repo_root = repo_root
        self.identity = "Claude Code Research Archive Assistant"
        self.rules = clamp_lines(read_text(CLAUDE_DOC), 60) if CLAUDE_DOC.exists() else ""
        self.repo_summary = clamp_lines(read_text(README_DOC), 40) if README_DOC.exists() else ""

    def build(self, request: str, tools: Sequence[Tool], memories: Sequence[MemoryEntry]) -> str:
        sections = [
            "# Identity", self.identity,
            "# Behavioral Guardrails", self.rules,
            f"# Repository Summary\n{self.repo_summary}",
            "# Tool Registry",
            "\n".join(f"- {tool.name}: {tool.description}" for tool in tools),
            SYSTEM_PROMPT_DYNAMIC_BOUNDARY,
            "# Dynamic Context",
            f"Current Request: {request}",
        ]
        if memories:
            rendered = "\n".join(f"- ({entry.mem_type}) {entry.text}" for entry in memories)
            sections.append("# Retrieved Memories")
            sections.append(rendered)
        sections.append(f"# Timestamp\n{dt.datetime.utcnow().isoformat()}Z")
        return "\n\n".join(sections)


# --------------------------------------------------------------------------------------
# Agent
# --------------------------------------------------------------------------------------
@dataclass
class AgentResponse:
    system_prompt: str
    plan: List[str]
    doc_hits: List[DocHit]
    memories: List[MemoryEntry]
    text: str


class SimplifiedAgent:
    def __init__(self, context_builder: ContextBuilder, doc_index: DocIndex, tools: Sequence[Tool], memory_store: MemoryStore) -> None:
        self.context_builder = context_builder
        self.doc_index = doc_index
        self.tools = list(tools)
        self.memory_store = memory_store

    def run(self, request: str) -> AgentResponse:
        memories = self.memory_store.recall(request)
        system_prompt = self.context_builder.build(request, self.tools, memories)
        plan = self._draft_plan(request)
        doc_hits = self.doc_index.search(request)
        summary = self._render_summary(request, plan, doc_hits, memories)
        return AgentResponse(system_prompt=system_prompt, plan=plan, doc_hits=doc_hits, memories=memories, text=summary)

    @staticmethod
    def _draft_plan(request: str) -> List[str]:
        return [
            f"Clarify objectives for: {request}",
            "Identify relevant research notes and source files",
            "Outline concrete next actions or tool calls"
        ]

    def _render_summary(self, request: str, plan: Sequence[str], doc_hits: Sequence[DocHit], memories: Sequence[MemoryEntry]) -> str:
        doc_lines = [f"- {hit.path.name} (score {hit.score}): {hit.snippet}" for hit in doc_hits] or ["- No related docs found"]
        memory_lines = [f"- ({entry.mem_type}) {entry.text}" for entry in memories] or ["- No stored memories matched"]
        plan_lines = [f"{idx+1}. {step}" for idx, step in enumerate(plan)]
        return textwrap.dedent(
            f"""
            ## Request
            {request}

            ## Plan
            {os.linesep.join(plan_lines)}

            ## Relevant Docs
            {os.linesep.join(doc_lines)}

            ## Memory Notes
            {os.linesep.join(memory_lines)}
            """
        ).strip()


# --------------------------------------------------------------------------------------
# CLI Entrypoint
# --------------------------------------------------------------------------------------
def build_agent() -> SimplifiedAgent:
    memory_store = MemoryStore()
    file_reader = FileReadTool(REPO_ROOT)
    tools: List[Tool] = [file_reader, SearchTool(file_reader), MemoryNoteTool(memory_store)]
    context_builder = ContextBuilder(REPO_ROOT)
    doc_index = DocIndex(DOCS_DIR)
    return SimplifiedAgent(context_builder, doc_index, tools, memory_store)


def cmd_chat(agent: SimplifiedAgent, args: argparse.Namespace) -> None:
    response = agent.run(args.prompt)
    print("=== SYSTEM PROMPT ===")
    print(response.system_prompt)
    print("\n=== AGENT RESPONSE ===")
    print(response.text)
    if args.show_docs:
        for hit in response.doc_hits:
            print(f"\n--- {hit.path} (score {hit.score}) ---\n{clamp_lines(read_text(hit.path), 120)}")


def cmd_remember(agent: SimplifiedAgent, args: argparse.Namespace) -> None:
    result = agent.memory_store.remember(args.text, mem_type=args.type)
    print(f"Stored memory in bucket '{result.mem_type}' at {result.created_at}")


def cmd_show_memory(agent: SimplifiedAgent, args: argparse.Namespace) -> None:
    hits = agent.memory_store.recall(args.query or "", limit=10)
    for entry in hits:
        print(f"[{entry.mem_type}] {entry.created_at} -> {entry.text}")


def cmd_list_tools(agent: SimplifiedAgent, args: argparse.Namespace) -> None:
    for tool in agent.tools:
        print(f"- {tool.name} (safe={tool.is_concurrency_safe}): {tool.description}")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Simplified Claude Code CLI")
    subparsers = parser.add_subparsers(dest="command", required=True)

    chat = subparsers.add_parser("chat", help="Run the simplified agent loop")
    chat.add_argument("prompt", help="User request or task description")
    chat.add_argument("--show-docs", action="store_true", help="Dump matched doc bodies")
    chat.set_defaults(func=cmd_chat)

    remember = subparsers.add_parser("remember", help="Store a new memory note")
    remember.add_argument("text", help="Memory content")
    remember.add_argument("--type", default="project", help="Memory bucket")
    remember.set_defaults(func=cmd_remember)

    show_memory = subparsers.add_parser("memories", help="Show stored memories")
    show_memory.add_argument("--query", default="", help="Filter memories by keyword")
    show_memory.set_defaults(func=cmd_show_memory)

    list_tools = subparsers.add_parser("tools", help="List registered tools")
    list_tools.set_defaults(func=cmd_list_tools)

    return parser


def main(argv: Sequence[str] | None = None) -> None:
    parser = build_parser()
    args = parser.parse_args(argv)
    agent = build_agent()
    args.func(agent, args)


if __name__ == "__main__":
    main()
