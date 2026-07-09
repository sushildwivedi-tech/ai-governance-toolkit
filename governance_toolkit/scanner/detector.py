from __future__ import annotations

import ast
import re
import subprocess
from collections import Counter
from datetime import datetime
from pathlib import Path
from typing import List, Optional

from .fingerprint import AgentFingerprint, make_agent_id

PREFILTER_PATTERN = re.compile(
    r"\b(anthropic|langchain|langgraph|crewai|autogpt|AutoGPT)\b",
    re.IGNORECASE,
)

MODEL_PATTERN = re.compile(r"""model\s*=\s*["'](claude-[a-zA-Z0-9\-\.]+)["']""")

FRAMEWORK_PATTERNS: dict[str, list[str]] = {
    "anthropic_claude": [
        r"import\s+anthropic",
        r"from\s+anthropic[\s\.\,]",
        r"Anthropic\s*\(",
        r"AsyncAnthropic\s*\(",
        r"anthropic\.Anthropic",
        r"""model=["']claude-""",
        r"ANTHROPIC_API_KEY",
        r"anthropic_api_key",
        r"from\s+langchain_anthropic",
    ],
    "langgraph": [
        r"from\s+langgraph[\._]",
        r"import\s+langgraph",
        r"StateGraph\s*\(",
        r"\.add_node\s*\(",
        r"\.set_entry_point\s*\(",
    ],
    "langchain": [
        r"from\s+langchain[\._]",
        r"import\s+langchain",
        r"AgentExecutor\s*\(",
        r"create_react_agent\s*\(",
        r"create_tool_calling_agent\s*\(",
        r"@tool\b",
        r"ChatAnthropic\s*\(",
        r"ChatOpenAI\s*\(",
        r"from\s+langchain_core",
    ],
    "crewai": [
        r"from\s+crewai\b",
        r"import\s+crewai",
        r"from\s+crewai_tools",
        r"Crew\s*\(",
        r"Process\.sequential",
        r"Process\.hierarchical",
    ],
    "autogpt": [
        r"import\s+autogpt",
        r"from\s+autogpt[\._]",
        r"AutoGPT\s*\(",
        r"auto_gpt",
    ],
}

COMPILED_PATTERNS: dict[str, list[re.Pattern]] = {
    fw: [re.compile(p) for p in patterns]
    for fw, patterns in FRAMEWORK_PATTERNS.items()
}

FRAMEWORK_MODULE_PREFIXES: dict[str, list[str]] = {
    "anthropic_claude": ["anthropic", "langchain_anthropic"],
    "langgraph": ["langgraph"],
    "langchain": ["langchain", "langchain_core", "langchain_community", "langchain_openai"],
    "crewai": ["crewai", "crewai_tools"],
    "autogpt": ["autogpt"],
}

AGENT_BASE_CLASSES = {"Agent", "BaseAgent", "BaseSingleActionAgent", "BaseChatAgent"}
AGENT_CONSTRUCTOR_NAMES = {
    "AgentExecutor", "Crew", "StateGraph", "create_react_agent",
    "create_tool_calling_agent", "create_openai_tools_agent",
}
CHAT_MODEL_CONSTRUCTORS = {
    "ChatAnthropic", "ChatOpenAI", "ChatGoogleGenerativeAI",
    "ChatMistralAI", "Anthropic", "AsyncAnthropic",
}

DEFAULT_SKIP_DIRS = {
    "__pycache__", ".git", ".venv", "venv", "env",
    "node_modules", "dist", "build", ".tox", "site-packages",
    ".eggs", ".mypy_cache", ".pytest_cache",
}
MAX_FILE_SIZE = 1 * 1024 * 1024  # 1MB


def _classify_import(module: str) -> Optional[str]:
    for fw, prefixes in FRAMEWORK_MODULE_PREFIXES.items():
        for prefix in prefixes:
            if module == prefix or module.startswith(prefix + "."):
                return fw
    return None


def _get_name(node: ast.expr) -> Optional[str]:
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        return node.attr
    return None


def _get_call_name(node: ast.Call) -> str:
    if isinstance(node.func, ast.Name):
        return node.func.id
    if isinstance(node.func, ast.Attribute):
        return node.func.attr
    return ""


class AgentVisitor(ast.NodeVisitor):
    def __init__(self):
        self.frameworks: set[str] = set()
        self.imports: list[str] = []
        self.models: list[str] = []
        self.tools: list[str] = []
        self.agent_var_names: list[str] = []
        self.class_names: list[str] = []
        self.first_line: dict[str, int] = {}

    def visit_Import(self, node: ast.Import):
        for alias in node.names:
            self.imports.append(alias.name)
            fw = _classify_import(alias.name)
            if fw:
                self.frameworks.add(fw)
                self.first_line.setdefault(fw, node.lineno)
        self.generic_visit(node)

    def visit_ImportFrom(self, node: ast.ImportFrom):
        if node.module:
            self.imports.append(node.module)
            fw = _classify_import(node.module)
            if fw:
                self.frameworks.add(fw)
                self.first_line.setdefault(fw, node.lineno)
        self.generic_visit(node)

    def visit_FunctionDef(self, node: ast.FunctionDef):
        for dec in node.decorator_list:
            if isinstance(dec, ast.Name) and dec.id in ("tool", "Tool"):
                self.tools.append(node.name)
            elif isinstance(dec, ast.Attribute) and dec.attr in ("tool",):
                self.tools.append(node.name)
        self.generic_visit(node)

    visit_AsyncFunctionDef = visit_FunctionDef

    def visit_ClassDef(self, node: ast.ClassDef):
        for base in node.bases:
            name = _get_name(base)
            if name in AGENT_BASE_CLASSES:
                self.class_names.append(node.name)
        self.generic_visit(node)

    def visit_Call(self, node: ast.Call):
        func_name = _get_call_name(node)

        if func_name in ("create", "stream") or (
            isinstance(node.func, ast.Attribute) and node.func.attr in ("create", "stream")
        ):
            for kw in node.keywords:
                if kw.arg == "model" and isinstance(kw.value, ast.Constant):
                    self.models.append(str(kw.value.value))

        if func_name in CHAT_MODEL_CONSTRUCTORS:
            for kw in node.keywords:
                if kw.arg == "model" and isinstance(kw.value, ast.Constant):
                    self.models.append(str(kw.value.value))

        if func_name in AGENT_CONSTRUCTOR_NAMES:
            for kw in node.keywords:
                if kw.arg == "tools" and isinstance(kw.value, ast.List):
                    for elt in kw.value.elts:
                        tool_name = _get_name(elt)
                        if tool_name:
                            self.tools.append(tool_name)

        self.generic_visit(node)

    def visit_Assign(self, node: ast.Assign):
        if isinstance(node.value, ast.Call):
            func_name = _get_call_name(node.value)
            if func_name in AGENT_CONSTRUCTOR_NAMES:
                for target in node.targets:
                    if isinstance(target, ast.Name):
                        self.agent_var_names.append(target.id)
        self.generic_visit(node)


def _detect_frameworks_regex(content: str) -> dict[str, int]:
    found: dict[str, int] = {}
    lines = content.splitlines()
    for fw, patterns in COMPILED_PATTERNS.items():
        for i, line in enumerate(lines, 1):
            for pat in patterns:
                if pat.search(line):
                    found.setdefault(fw, i)
                    break
            if fw in found:
                break
    return found


def _extract_owner(file_path: Path) -> Optional[str]:
    try:
        result = subprocess.run(
            ["git", "blame", "--porcelain", str(file_path)],
            capture_output=True,
            text=True,
            timeout=5,
            cwd=str(file_path.parent),
        )
        if result.returncode != 0:
            return None
        emails = re.findall(r"^author-mail <([^>]+)>", result.stdout, re.MULTILINE)
        if not emails:
            return None
        return Counter(emails).most_common(1)[0][0]
    except (subprocess.TimeoutExpired, FileNotFoundError, OSError):
        return None


def _infer_name(visitor: AgentVisitor, file_path: Path) -> str:
    if visitor.class_names:
        return visitor.class_names[0]
    if visitor.agent_var_names:
        return visitor.agent_var_names[0]
    if visitor.tools:
        return visitor.tools[0] + "_agent"
    return file_path.stem


def _extract_evidence(content: str, frameworks: set[str]) -> list[str]:
    evidence = []
    lines = content.splitlines()
    for i, line in enumerate(lines, 1):
        stripped = line.strip()
        if not stripped:
            continue
        for fw in frameworks:
            for pat in COMPILED_PATTERNS.get(fw, []):
                if pat.search(line):
                    evidence.append(f"line {i}: {stripped[:120]}")
                    break
    return evidence[:10]


def scan_file(path: Path) -> list[AgentFingerprint]:
    try:
        if path.stat().st_size > MAX_FILE_SIZE:
            return []
        content = path.read_text(encoding="utf-8", errors="ignore")
    except OSError:
        return []

    if not PREFILTER_PATTERN.search(content):
        return []

    results: list[AgentFingerprint] = []
    owner = _extract_owner(path)

    try:
        tree = ast.parse(content, filename=str(path))
        visitor = AgentVisitor()
        visitor.visit(tree)
        frameworks = visitor.frameworks

        if not frameworks:
            regex_hits = _detect_frameworks_regex(content)
            if not regex_hits:
                return []
            frameworks = set(regex_hits.keys())
            for fw in frameworks:
                visitor.first_line.setdefault(fw, regex_hits[fw])

        models_from_regex = MODEL_PATTERN.findall(content)
        all_models = visitor.models + [m for m in models_from_regex if m not in visitor.models]

        for fw in frameworks:
            line_no = visitor.first_line.get(fw, 1)
            agent_id = make_agent_id(str(path), fw, line_no)
            name = _infer_name(visitor, path)
            model = all_models[0] if all_models else None
            evidence = _extract_evidence(content, {fw})

            results.append(AgentFingerprint(
                agent_id=agent_id,
                name=name,
                file_path=str(path),
                line_number=line_no,
                framework=fw,
                model=model,
                tools=list(dict.fromkeys(visitor.tools)),
                owner=owner,
                evidence=evidence,
                scan_timestamp=datetime.utcnow(),
            ))

    except SyntaxError:
        regex_hits = _detect_frameworks_regex(content)
        if not regex_hits:
            return []
        models_from_regex = MODEL_PATTERN.findall(content)
        for fw, line_no in regex_hits.items():
            agent_id = make_agent_id(str(path), fw, line_no)
            results.append(AgentFingerprint(
                agent_id=agent_id,
                name=path.stem,
                file_path=str(path),
                line_number=line_no,
                framework=fw,
                model=models_from_regex[0] if models_from_regex else None,
                tools=[],
                owner=owner,
                evidence=_extract_evidence(content, {fw}),
                scan_timestamp=datetime.utcnow(),
            ))

    return results


def scan_notebook(path: Path) -> list[AgentFingerprint]:
    import json
    try:
        nb = json.loads(path.read_text(encoding="utf-8", errors="ignore"))
    except (OSError, json.JSONDecodeError):
        return []

    combined = ""
    for cell in nb.get("cells", []):
        if cell.get("cell_type") == "code":
            combined += "".join(cell.get("source", [])) + "\n"

    if not combined.strip():
        return []

    tmp_path = path.with_suffix(".py")
    results = []
    try:
        tmp_path.write_text(combined, encoding="utf-8")
        raw = scan_file(tmp_path)
        for fp in raw:
            results.append(AgentFingerprint(
                agent_id=make_agent_id(str(path) + "#notebook", fp.framework, fp.line_number),
                name=fp.name,
                file_path=str(path) + "#notebook",
                line_number=fp.line_number,
                framework=fp.framework,
                model=fp.model,
                tools=fp.tools,
                owner=fp.owner,
                evidence=fp.evidence,
                scan_timestamp=fp.scan_timestamp,
            ))
    finally:
        if tmp_path.exists():
            tmp_path.unlink()

    return results


def scan_directory(
    root: Path,
    exclude_patterns: Optional[list[str]] = None,
) -> list[AgentFingerprint]:
    seen: set[Path] = set()
    results: list[AgentFingerprint] = []

    for p in sorted(root.rglob("*")):
        if p.suffix not in (".py", ".ipynb"):
            continue
        if any(part in DEFAULT_SKIP_DIRS for part in p.parts):
            continue
        if exclude_patterns:
            if any(p.match(pat) for pat in exclude_patterns):
                continue

        canonical = p.resolve()
        if canonical in seen:
            continue
        seen.add(canonical)

        if p.suffix == ".ipynb":
            results.extend(scan_notebook(p))
        else:
            results.extend(scan_file(p))

    return results
