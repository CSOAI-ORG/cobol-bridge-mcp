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

from mcp.server.fastmcp import FastMCP
from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional
import json
import re
from datetime import datetime, timedelta, timezone
from collections import defaultdict
import os as _os
import sys
import os

# --- Pydantic Models ---

class ParserResult(BaseModel):
    lines_of_code: int
    divisions_found: List[str]
    section_count: int
    paragraph_count: int
    paragraphs_sample: List[str]
    io_surfaces: Dict[str, Any]
    cyclomatic_complexity: int
    complexity_band: str
    tier: str
    branding: str = "Built by MEOK AI Labs | https://meok.ai"

class BusinessRule(BaseModel):
    condition: str
    then_clause: str = Field(..., alias="then")
    else_clause: Optional[str] = Field(None, alias="else")

class BusinessRulesResponse(BaseModel):
    rule_count: int
    rules: List[BusinessRule]
    note: str
    tier: str
    branding: str = "Built by MEOK AI Labs | https://meok.ai"

class MigrationEffort(BaseModel):
    target_stack: str
    loc: int
    cyclomatic_complexity: int
    paragraph_count: int
    io_surface_count: int
    embedded_sql_blocks: int
    cics_blocks: int
    complexity_factor: float
    estimated_effort_days: float
    estimated_effort_months: float
    team_size_recommendation: str
    risk_level: str
    tier: str
    branding: str = "Built by MEOK AI Labs | https://meok.ai"

class MigrationPhase(BaseModel):
    phase: int
    name: str
    duration_weeks: int
    deliverables: List[str]

class MigrationPlanResponse(BaseModel):
    phases: List[MigrationPhase]
    total_duration_weeks: int
    total_duration_months: float
    rule_of_thumb: str
    tier: str
    branding: str = "Built by MEOK AI Labs | https://meok.ai"

class TestHarnessResponse(BaseModel):
    target_stack: str
    harness_code: str
    tier: str
    branding: str = "Built by MEOK AI Labs | https://meok.ai"

# --- Parsing Logic ---

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
        if len(line) > 6 and line[6] in ("*", "/"): continue
        lines.append(line.upper())
    return "\n".join(lines)

def _count_paragraphs(src):
    proc_idx = src.upper().find("PROCEDURE DIVISION")
    if proc_idx < 0: return []
    proc = src[proc_idx:]
    skip = {"PROGRAM-ID", "AUTHOR", "DATE-WRITTEN", "INSTALLATION", "SECURITY", "ENVIRONMENT", "DATA", "WORKING-STORAGE", "FILE-CONTROL", "INPUT-OUTPUT", "FILE", "LINKAGE", "PROCEDURE", "CONFIGURATION", "SPECIAL-NAMES", "SOURCE-COMPUTER", "OBJECT-COMPUTER"}
    return [m.group(1) for m in PARAGRAPH_RE.finditer(proc) if m.group(1) not in skip]

def _cc(src):
    proc_idx = src.upper().find("PROCEDURE DIVISION")
    if proc_idx < 0: return 0
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

# --- Utils ---

_MEOK_API_KEY = _os.environ.get("MEOK_API_KEY", "")

try:
    from auth_middleware import check_access as _shared_check_access
    _AUTH_ENGINE_AVAILABLE = True
except ImportError:
    _AUTH_ENGINE_AVAILABLE = False
    def _shared_check_access(api_key: str = ""):
        if _MEOK_API_KEY and api_key and api_key == _MEOK_API_KEY:
            return True, "OK", "pro"
        return True, "OK, Pro at https://www.csoai.org/checkout", "free"

FREE_DAILY_LIMIT = 10
_usage = defaultdict(list)
STRIPE_PRO = "https://buy.stripe.com/7sY00l6WgbIK0ZTfL28k90Q"

def _rl(tier="free"):
    if tier in ("pro", "professional", "enterprise"): return None
    now = datetime.now(timezone.utc)
    cutoff = now - timedelta(days=1)
    _usage["anonymous"] = [t for t in _usage["anonymous"] if t > cutoff]
    if len(_usage["anonymous"]) >= FREE_DAILY_LIMIT:
        return f"Free tier limit ({FREE_DAILY_LIMIT}/day). Pro £79/mo: {STRIPE_PRO}"
    _usage["anonymous"].append(now)
    return None

# --- MCP Setup ---

mcp = FastMCP("COBOL Bridge", instructions="AI-assisted COBOL → modern stack bridge. Parse, extract, and plan migrations.")

@mcp.tool()
def parse_cobol_program(source_code: str, api_key: str = "") -> ParserResult:
    """Parse a COBOL source file and extract metrics."""
    allowed, msg, tier = _shared_check_access(api_key)
    if not allowed: return {"error": msg}
    if err := _rl(tier): return {"error": err}
    if not source_code or len(source_code.strip()) < 20: return {"error": "source_code too short"}

    src = _normalize_cobol(source_code)
    divisions_present = [d for d in DIVISIONS if d in src.upper()]
    paragraphs = _count_paragraphs(src)
    sections = [m.group(1) for m in SECTION_RE.finditer(src)]
    io = _io_surfaces(src)
    cc = _cc(src)

    return ParserResult(
        lines_of_code=len(source_code.split("\n")),
        divisions_found=divisions_present,
        section_count=len(sections),
        paragraph_count=len(paragraphs),
        paragraphs_sample=paragraphs[:20],
        io_surfaces=io,
        cyclomatic_complexity=cc,
        complexity_band="LOW" if cc < 10 else "MEDIUM" if cc < 25 else "HIGH" if cc < 50 else "VERY_HIGH",
        tier=tier
    )

@mcp.tool()
def identify_business_rules(source_code: str, max_rules: int = 10, api_key: str = "") -> BusinessRulesResponse:
    """Extract IF/EVALUATE business rules from COBOL source."""
    allowed, msg, tier = _shared_check_access(api_key)
    if not allowed: return {"error": msg}
    if err := _rl(tier): return {"error": err}
    if not source_code or len(source_code.strip()) < 20: return {"error": "source_code too short"}

    src = _normalize_cobol(source_code)
    proc_idx = src.upper().find("PROCEDURE DIVISION")
    rules = []
    if proc_idx >= 0:
        proc = src[proc_idx:proc_idx + 20000]
        if_pattern = re.compile(r'\bIF\s+(.+?)(?:\s+THEN)?\s+(.+?)(?:\bELSE\b\s+(.+?))?\s*(?:\bEND-IF\b|\.\s*$)', re.IGNORECASE | re.DOTALL)
        for m in if_pattern.finditer(proc):
            rules.append(BusinessRule(condition=m.group(1).strip()[:200], then=m.group(2).strip()[:200], **({"else": m.group(3).strip()[:200]} if m.group(3) else {})))
            if len(rules) >= max(1, min(50, max_rules)): break

    return BusinessRulesResponse(
        rule_count=len(rules),
        rules=rules,
        note="Heuristic extraction. Manual review recommended.",
        tier=tier
    )

@mcp.tool()
def estimate_migration_complexity(source_code: str, target_stack: str = "python", api_key: str = "") -> MigrationEffort:
    """Estimate migration effort to target stack."""
    allowed, msg, tier = _shared_check_access(api_key)
    if not allowed: return {"error": msg}
    if err := _rl(tier): return {"error": err}
    if not source_code or len(source_code.strip()) < 20: return {"error": "source_code too short"}

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

    return MigrationEffort(
        target_stack=target_stack,
        loc=loc,
        cyclomatic_complexity=cc,
        paragraph_count=paragraphs,
        io_surface_count=len(io["files"]),
        embedded_sql_blocks=io["embedded_sql_blocks"],
        cics_blocks=io["cics_blocks"],
        complexity_factor=round(complexity_factor, 2),
        estimated_effort_days=round(total, 1),
        estimated_effort_months=round(total / 21, 1),
        team_size_recommendation="1 developer" if total < 60 else "2 developers" if total < 200 else "3-5 person team + lead",
        risk_level="LOW" if cc < 10 and io["cics_blocks"] == 0 else "MEDIUM" if cc < 25 else "HIGH",
        tier=tier
    )

@mcp.tool()
def plan_migration_phases(loc: int = 0, complexity: int = 0, api_key: str = "") -> MigrationPlanResponse:
    """Generate a 4-phase migration plan."""
    allowed, msg, tier = _shared_check_access(api_key)
    if not allowed: return {"error": msg}

    phases = [
        MigrationPhase(phase=1, name="Discovery + parallel-run setup", duration_weeks=max(2, loc // 2000), deliverables=["Full COBOL inventory", "Business rule catalogue", "Test harness", "Target-stack architecture"]),
        MigrationPhase(phase=2, name="Translation", duration_weeks=max(4, loc // 500), deliverables=["Faithful semantic translation", "SQL → modern ORM", "CICS calls → modern transaction context", "Copybook → modern data structures"]),
        MigrationPhase(phase=3, name="Parallel run validation", duration_weeks=max(4, complexity // 5), deliverables=["Daily run against production-equivalent dataset", "Output equivalence check", "Performance regression check", "Edge-case discovery"]),
        MigrationPhase(phase=4, name="Cutover + decommission", duration_weeks=4, deliverables=["Switch live traffic", "Keep COBOL hot-standby (30d)", "Decommission COBOL infra", "Post-cutover reporting"]),
    ]
    total = sum(p.duration_weeks for p in phases)
    return MigrationPlanResponse(
        phases=phases,
        total_duration_weeks=total,
        total_duration_months=round(total / 4, 1),
        rule_of_thumb="Typical 100K LOC COBOL: 18-24 months / 3-5 dev team.",
        tier=tier
    )

@mcp.tool()
def generate_test_harness(source_code: str = "", target_stack: str = "python", api_key: str = "") -> TestHarnessResponse:
    """Generate skeleton test harness for parallel-run equivalence testing."""
    allowed, msg, tier = _shared_check_access(api_key)
    if not allowed: return {"error": msg}
    harness = '''import subprocess, json, hashlib\nfrom pathlib import Path\n\ndef run_cobol(input_file):\n    result = subprocess.run(["./cobol_binary", input_file], capture_output=True, text=True, timeout=300)\n    return result.stdout\n\ndef run_modern(input_file):\n    from modern_app import main as modern_main\n    return modern_main(input_file)\n\ndef diff_output(a, b):\n    return {"equal": hashlib.sha256(a.encode()).hexdigest() == hashlib.sha256(b.encode()).hexdigest()}\n\ndef run_parallel_test(test_cases_dir):\n    results = []\n    for tc in Path(test_cases_dir).glob("*.dat"):\n        cobol_out = run_cobol(str(tc))\n        modern_out = run_modern(str(tc))\n        results.append({"input": tc.name, **diff_output(cobol_out, modern_out)})\n    return results\n\nif __name__ == "__main__":\n    r = run_parallel_test("test_inputs/")\n    print(json.dumps(r, indent=2))'''
    return TestHarnessResponse(target_stack=target_stack, harness_code=harness, tier=tier)

if __name__ == "__main__":
    mcp.run()


# ── MEOK monetization layer (Stripe upgrade · PAYG · pricing) ──────────
# Free tier is zero-config. Upgrade to Pro (unlimited) or pay-as-you-go per call.
import os as _meok_os
MEOK_STRIPE_UPGRADE = "https://buy.stripe.com/00wfZjcgAeUW4c5cyQ8k90K"  # Pro (unlimited)
MEOK_PAYG_KEY = _meok_os.environ.get("MEOK_PAYG_KEY", "")  # set to enable PAYG (x402 / ~GBP0.05 per call)
MEOK_PRICING = "https://meok.ai/pricing"


def meok_upsell(tier: str = "free") -> dict:
    """Monetization options for free-tier callers: Pro upgrade, PAYG, or pricing page."""
    if tier != "free":
        return {}
    return {"upgrade_url": MEOK_STRIPE_UPGRADE,
            "payg_enabled": bool(MEOK_PAYG_KEY),
            "pricing": MEOK_PRICING}
