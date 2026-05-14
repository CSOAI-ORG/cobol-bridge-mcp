#!/usr/bin/env python3
"""
COBOL Bridge MCP Server
========================
By MEOK AI Labs | https://meok.ai

AI-assisted COBOL → modern stack bridge. Real parser + business-rule
extraction + cyclomatic-complexity-aware migration planning. For banks,
insurers, and government legacy mainframes.

Install: pip install cobol-bridge-mcp
Domain: cobolbridge.ai
"""

import json
import re
import sys
import os
from datetime import datetime, timedelta, timezone
from typing import Optional
from collections import defaultdict
from mcp.server.fastmcp import FastMCP

import os as _os

_MEOK_API_KEY = _os.environ.get("MEOK_API_KEY", "")

try:
    sys.path.insert(0, os.path.expanduser("~/clawd/meok-labs-engine/shared"))
    from auth_middleware import check_access as _shared_check_access
    _AUTH_ENGINE_AVAILABLE = True
except ImportError:
    _AUTH_ENGINE_AVAILABLE = False

    def _shared_check_access(api_key: str = ""):
        if _MEOK_API_KEY and api_key and api_key == _MEOK_API_KEY:
            return True, "OK", "pro"
        if _MEOK_API_KEY and api_key and api_key != _MEOK_API_KEY:
            return False, "Invalid API key. Get one at https://meok.ai/api-keys", "free"
        return True, "OK", "free"


def check_access(api_key: str = ""):
    return _shared_check_access(api_key)


FREE_DAILY_LIMIT = 10
_usage = defaultdict(list)
STRIPE_PRO = "https://buy.stripe.com/14A4gB3K4eUWgYR56o8k836"


def _rl(tier="free"):
    if tier in ("pro", "professional", "enterprise"):
        return None
    now = datetime.now(timezone.utc)
    cutoff = now - timedelta(days=1)
    _usage["anonymous"] = [t for t in _usage["anonymous"] if t > cutoff]
    if len(_usage["anonymous"]) >= FREE_DAILY_LIMIT:
        return f"Free tier limit ({FREE_DAILY_LIMIT}/day). Pro £79/mo: {STRIPE_PRO}"
    _usage["anonymous"].append(now)
    return None


# ── Real COBOL parsing ─────────────────────────────────────────────────

DIVISIONS = ["IDENTIFICATION DIVISION", "ENVIRONMENT DIVISION", "DATA DIVISION", "PROCEDURE DIVISION"]
PARAGRAPH_RE = re.compile(r'^\s{0,7}([A-Z0-9][A-Z0-9-]*)\s*\.\s*$', re.MULTILINE)
SECTION_RE = re.compile(r'^\s{0,7}([A-Z0-9][A-Z0-9-]*)\s+SECTION\s*\.\s*$', re.MULTILINE)
FILE_IO_RE = re.compile(r'\b(OPEN|CLOSE|READ|WRITE|REWRITE|DELETE|START)\s+([A-Z][A-Z0-9-]*)\b', re.IGNORECASE)
COPY_RE = re.compile(r'\bCOPY\s+([A-Z][A-Z0-9-]*)', re.IGNORECASE)
SQL_RE = re.compile(r'\bEXEC\s+SQL\s+([\s\S]*?)END-EXEC', re.IGNORECASE)
CICS_RE = re.compile(r'\bEXEC\s+CICS\s+([\s\S]*?)END-EXEC', re.IGNORECASE)
IF_RE = re.compile(r'\bIF\s+', re.IGNORECASE)
EVALUATE_RE = re.compile(r'\bEVALUATE\s+', re.IGNORECASE)


def _normalize_cobol(src):
    lines = []
    for line in src.split("\n"):
        if len(line) > 6 and line[6] in ("*", "/"):
            continue
        lines.append(line.upper())
    return "\n".join(lines)


def _count_paragraphs(src):
    proc_idx = src.upper().find("PROCEDURE DIVISION")
    if proc_idx < 0:
        return []
    proc = src[proc_idx:]
    skip = {"PROGRAM-ID", "AUTHOR", "DATE-WRITTEN", "INSTALLATION", "SECURITY",
            "ENVIRONMENT", "DATA", "WORKING-STORAGE", "FILE-CONTROL",
            "INPUT-OUTPUT", "FILE", "LINKAGE", "PROCEDURE", "CONFIGURATION",
            "SPECIAL-NAMES", "SOURCE-COMPUTER", "OBJECT-COMPUTER"}
    return [m.group(1) for m in PARAGRAPH_RE.finditer(proc) if m.group(1) not in skip]


def _cc(src):
    proc_idx = src.upper().find("PROCEDURE DIVISION")
    if proc_idx < 0:
        return 0
    proc = src[proc_idx:].upper()
    return 1 + len(IF_RE.findall(proc)) + len(EVALUATE_RE.findall(proc)) + len(re.findall(r'\bWHEN\b', proc)) + len(re.findall(r'\bUNTIL\b', proc))


def _io_surfaces(src):
    files = defaultdict(list)
    for m in FILE_IO_RE.finditer(src):
        files[m.group(2)].append(m.group(1).upper())
    return {
        "files": {f: list(set(ops)) for f, ops in files.items()},
        "embedded_sql_blocks": len(SQL_RE.findall(src)),
        "cics_blocks": len(CICS_RE.findall(src)),
        "copybooks": list({m.group(1) for m in COPY_RE.finditer(src)}),
    }


mcp = FastMCP("COBOL Bridge", instructions=(
    "By MEOK AI Labs — AI-assisted COBOL → modern stack bridge. Parse COBOL source, "
    "extract business rules, plan migration with cyclomatic-complexity-aware effort estimates. "
    "For banks, insurers, and government legacy mainframes. "
    "Free tier: 10/day. Pro tier (£79/mo): unlimited."
))


@mcp.tool()
def parse_cobol_program(source_code: str, api_key: str = "") -> str:
    """Parse a COBOL source file. Extract divisions, paragraphs, file IO, SQL/CICS, copybooks, complexity."""
    allowed, msg, tier = check_access(api_key)
    if not allowed:
        return json.dumps({"error": msg, "upgrade_url": STRIPE_PRO})
    if err := _rl(tier):
        return json.dumps({"error": err, "upgrade_url": STRIPE_PRO})
    if not source_code or len(source_code.strip()) < 20:
        return json.dumps({"error": "source_code too short"})

    src = _normalize_cobol(source_code)
    divisions_present = [d for d in DIVISIONS if d in src.upper()]
    paragraphs = _count_paragraphs(src)
    sections = [m.group(1) for m in SECTION_RE.finditer(src)]
    io = _io_surfaces(src)
    cc = _cc(src)

    return json.dumps({
        "lines_of_code": len(source_code.split("\n")),
        "divisions_found": divisions_present,
        "section_count": len(sections),
        "paragraph_count": len(paragraphs),
        "paragraphs_sample": paragraphs[:20],
        "io_surfaces": io,
        "cyclomatic_complexity": cc,
        "complexity_band": "LOW" if cc < 10 else "MEDIUM" if cc < 25 else "HIGH" if cc < 50 else "VERY_HIGH",
        "tier": tier,
    }, indent=2)


@mcp.tool()
def identify_business_rules(source_code: str, max_rules: int = 10, api_key: str = "") -> str:
    """Extract IF/EVALUATE business rules from COBOL PROCEDURE DIVISION."""
    allowed, msg, tier = check_access(api_key)
    if not allowed:
        return json.dumps({"error": msg, "upgrade_url": STRIPE_PRO})
    if err := _rl(tier):
        return json.dumps({"error": err, "upgrade_url": STRIPE_PRO})
    if not source_code or len(source_code.strip()) < 20:
        return json.dumps({"error": "source_code too short"})

    src = _normalize_cobol(source_code)
    proc_idx = src.upper().find("PROCEDURE DIVISION")
    rules = []
    if proc_idx >= 0:
        proc = src[proc_idx:proc_idx + 20000]
        if_pattern = re.compile(
            r'\bIF\s+(.+?)(?:\s+THEN)?\s+(.+?)(?:\bELSE\b\s+(.+?))?\s*(?:\bEND-IF\b|\.\s*$)',
            re.IGNORECASE | re.DOTALL,
        )
        for m in if_pattern.finditer(proc):
            rules.append({
                "condition": m.group(1).strip()[:200],
                "then": (m.group(2) or "").strip()[:200],
                "else": (m.group(3) or "").strip()[:200],
            })
            if len(rules) >= max(1, min(50, max_rules)):
                break

    return json.dumps({
        "rule_count": len(rules),
        "rules": rules,
        "note": "Heuristic extraction. Manual review recommended for production migration.",
        "tier": tier,
    }, indent=2)


@mcp.tool()
def estimate_migration_complexity(source_code: str, target_stack: str = "python", api_key: str = "") -> str:
    """Estimate migration effort to target stack (python/java/go/rust/dotnet)."""
    allowed, msg, tier = check_access(api_key)
    if not allowed:
        return json.dumps({"error": msg, "upgrade_url": STRIPE_PRO})
    if err := _rl(tier):
        return json.dumps({"error": err, "upgrade_url": STRIPE_PRO})
    if not source_code or len(source_code.strip()) < 20:
        return json.dumps({"error": "source_code too short"})

    src = _normalize_cobol(source_code)
    loc = len(source_code.split("\n"))
    cc = _cc(src)
    io = _io_surfaces(src)
    paragraphs = len(_count_paragraphs(src))

    base_days = loc / 5
    complexity_factor = 2.5 if cc > 50 else 1.8 if cc > 25 else 1.3 if cc > 10 else 1.0
    sql_factor = 1.0 + 0.3 * min(io["embedded_sql_blocks"], 10) / 10
    cics_factor = 1.0 + 0.5 * min(io["cics_blocks"], 10) / 10
    total = base_days * complexity_factor * sql_factor * cics_factor

    return json.dumps({
        "target_stack": target_stack,
        "loc": loc,
        "cyclomatic_complexity": cc,
        "paragraph_count": paragraphs,
        "io_surface_count": len(io["files"]),
        "embedded_sql_blocks": io["embedded_sql_blocks"],
        "cics_blocks": io["cics_blocks"],
        "complexity_factor": round(complexity_factor, 2),
        "estimated_effort_days": round(total, 1),
        "estimated_effort_months": round(total / 21, 1),
        "team_size_recommendation": (
            "1 developer" if total < 60 else "2 developers" if total < 200 else "3-5 person team + lead"
        ),
        "risk_level": "LOW" if cc < 10 and io["cics_blocks"] == 0 else "MEDIUM" if cc < 25 else "HIGH",
        "tier": tier,
    }, indent=2)


@mcp.tool()
def plan_migration_phases(loc: int = 0, complexity: int = 0, api_key: str = "") -> str:
    """Generate a 4-phase migration plan based on LOC + complexity."""
    allowed, msg, tier = check_access(api_key)
    if not allowed:
        return json.dumps({"error": msg, "upgrade_url": STRIPE_PRO})

    phases = [
        {"phase": 1, "name": "Discovery + parallel-run setup",
         "duration_weeks": max(2, loc // 2000),
         "deliverables": ["Full COBOL inventory + dependency graph",
                          "Business rule catalogue (extracted via this MCP)",
                          "Test harness with golden inputs/outputs",
                          "Target-stack architecture skeleton"]},
        {"phase": 2, "name": "Translation",
         "duration_weeks": max(4, loc // 500),
         "deliverables": ["Faithful semantic translation per paragraph",
                          "EXEC SQL → modern ORM / SQL driver",
                          "CICS calls → modern transaction context",
                          "Copybook → modern data structure equivalents"]},
        {"phase": 3, "name": "Parallel run validation",
         "duration_weeks": max(4, complexity // 5),
         "deliverables": ["Daily run against production-equivalent dataset",
                          "Output equivalence check against COBOL baseline",
                          "Performance regression check",
                          "Edge-case discovery (typically 5-15% of dataset)"]},
        {"phase": 4, "name": "Cutover + decommission",
         "duration_weeks": 4,
         "deliverables": ["Switch live traffic to modern stack",
                          "Keep COBOL hot-standby for 30 days",
                          "Decommission COBOL infrastructure",
                          "Post-cutover performance + cost reporting"]},
    ]
    total = sum(p["duration_weeks"] for p in phases)
    return json.dumps({
        "phases": phases,
        "total_duration_weeks": total,
        "total_duration_months": round(total / 4, 1),
        "rule_of_thumb": "Typical 100K LOC COBOL: 18-24 months / 3-5 dev team. Aggressive replatform: 9-12 months.",
        "tier": tier,
    }, indent=2)


@mcp.tool()
def generate_test_harness(source_code: str = "", target_stack: str = "python", api_key: str = "") -> str:
    """Generate skeleton test harness for parallel-run equivalence testing."""
    allowed, msg, tier = check_access(api_key)
    if not allowed:
        return json.dumps({"error": msg, "upgrade_url": STRIPE_PRO})

    harness = '''import subprocess, json, hashlib
from pathlib import Path

def run_cobol(input_file):
    """Run the original COBOL binary with input_file."""
    result = subprocess.run(["./cobol_binary", input_file],
        capture_output=True, text=True, timeout=300)
    return result.stdout

def run_modern(input_file):
    """Run the modern translation."""
    from modern_app import main as modern_main
    return modern_main(input_file)

def diff_output(a, b):
    return {"equal": hashlib.sha256(a.encode()).hexdigest() == hashlib.sha256(b.encode()).hexdigest()}

def run_parallel_test(test_cases_dir):
    results = []
    for tc in Path(test_cases_dir).glob("*.dat"):
        cobol_out = run_cobol(str(tc))
        modern_out = run_modern(str(tc))
        results.append({"input": tc.name, **diff_output(cobol_out, modern_out)})
    return results

if __name__ == "__main__":
    r = run_parallel_test("test_inputs/")
    print(json.dumps(r, indent=2))
'''

    return json.dumps({
        "target_stack": target_stack,
        "harness_code": harness,
        "tier": tier,
    }, indent=2)


def main():
    mcp.run()


if __name__ == "__main__":
    main()
