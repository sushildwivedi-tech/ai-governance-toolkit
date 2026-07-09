from __future__ import annotations

import pytest
from pathlib import Path

FIXTURES_DIR = Path(__file__).parent / "fixtures"


@pytest.mark.parametrize("filename,expected_fw", [
    ("sample_anthropic_agent.py", "anthropic_claude"),
    ("sample_langchain_agent.py", "langchain"),
    ("sample_langgraph_agent.py", "langgraph"),
    ("sample_crewai_agent.py", "crewai"),
])
def test_framework_detection(filename, expected_fw):
    from governance_toolkit.scanner.detector import scan_file
    results = scan_file(FIXTURES_DIR / filename)
    assert len(results) >= 1
    frameworks = {r.framework for r in results}
    assert expected_fw in frameworks


def test_no_false_positives():
    from governance_toolkit.scanner.detector import scan_file
    results = scan_file(FIXTURES_DIR / "sample_no_agent.py")
    assert results == []


def test_claude_model_extracted():
    from governance_toolkit.scanner.detector import scan_file
    results = scan_file(FIXTURES_DIR / "sample_anthropic_agent.py")
    claude_results = [r for r in results if r.framework == "anthropic_claude"]
    assert len(claude_results) >= 1
    assert claude_results[0].model == "claude-opus-4-5"


def test_tools_extracted_from_langchain():
    from governance_toolkit.scanner.detector import scan_file
    results = scan_file(FIXTURES_DIR / "sample_langchain_agent.py")
    assert len(results) >= 1
    all_tools = [t for r in results for t in r.tools]
    assert "search_web" in all_tools
    assert "calculator" in all_tools


def test_agent_id_is_deterministic():
    from governance_toolkit.scanner.detector import scan_file
    r1 = scan_file(FIXTURES_DIR / "sample_anthropic_agent.py")
    r2 = scan_file(FIXTURES_DIR / "sample_anthropic_agent.py")
    assert len(r1) > 0
    claude1 = next(r for r in r1 if r.framework == "anthropic_claude")
    claude2 = next(r for r in r2 if r.framework == "anthropic_claude")
    assert claude1.agent_id == claude2.agent_id


def test_scan_directory_finds_expected_frameworks():
    from governance_toolkit.scanner.detector import scan_directory
    results = scan_directory(FIXTURES_DIR)
    frameworks = {r.framework for r in results}
    assert "anthropic_claude" in frameworks
    assert "langchain" in frameworks
    assert "langgraph" in frameworks
    assert "crewai" in frameworks


def test_scan_skips_pycache(tmp_path):
    from governance_toolkit.scanner.detector import scan_directory
    pycache = tmp_path / "__pycache__"
    pycache.mkdir()
    (pycache / "agent.py").write_text("import anthropic\nclient = anthropic.Anthropic()")
    results = scan_directory(tmp_path)
    assert results == []


def test_large_file_skipped(tmp_path):
    from governance_toolkit.scanner.detector import scan_file
    big = tmp_path / "big_agent.py"
    big.write_text("import anthropic\n" + "# " + "x" * (1024 * 1024 + 100))
    results = scan_file(big)
    assert results == []


def test_syntax_error_file_does_not_crash(tmp_path):
    from governance_toolkit.scanner.detector import scan_file
    broken = tmp_path / "broken.py"
    broken.write_text("import anthropic\nclient = anthropic.Anthropic(\ndef broken syntax here")
    results = scan_file(broken)
    assert isinstance(results, list)


def test_fingerprint_has_required_fields():
    from governance_toolkit.scanner.detector import scan_file
    results = scan_file(FIXTURES_DIR / "sample_anthropic_agent.py")
    claude = next(r for r in results if r.framework == "anthropic_claude")
    assert claude.agent_id
    assert claude.name
    assert claude.file_path
    assert claude.line_number > 0
    assert claude.framework == "anthropic_claude"
    assert claude.scan_timestamp is not None


def test_to_dict_serializable():
    import json
    from governance_toolkit.scanner.detector import scan_file
    results = scan_file(FIXTURES_DIR / "sample_anthropic_agent.py")
    for r in results:
        d = r.to_dict()
        json.dumps(d, default=str)


def test_to_agent_create_maps_correctly():
    from governance_toolkit.scanner.detector import scan_file
    from governance_toolkit.registry.schemas import AgentCreate
    results = scan_file(FIXTURES_DIR / "sample_anthropic_agent.py")
    claude = next(r for r in results if r.framework == "anthropic_claude")
    data = claude.to_agent_create()
    ac = AgentCreate(**data)
    assert ac.framework == "anthropic_claude"
    assert ac.name == claude.name
