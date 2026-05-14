# COBOL Bridge (Legacy Modernization) MCP

[![PyPI](https://img.shields.io/pypi/v/cobol-bridge-mcp)](https://pypi.org/project/cobol-bridge-mcp/)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![MEOK AI Labs](https://img.shields.io/badge/MEOK_AI_Labs-governance--mcp-purple)](https://meok.ai)

AI-assisted COBOL → modern stack bridge. Parse COBOL programs, map to Python/Java/Go, generate test harnesses, plan migration. For banks, insurers, and government legacy mainframes.

## Install

```bash
pip install cobol-bridge-mcp
```

## Tools

| Tool | Purpose |
|------|---------|
| `parse_cobol_program` | Parse COBOL source — extract paragraphs, divisions, file IO |
| `identify_business_rules` | Extract business rules from procedure division logic |
| `plan_migration` | Generate phased migration plan COBOL → target stack |
| `generate_test_harness` | Generate equivalence test harness for parallel run |
| `estimate_complexity` | Estimate migration effort (cyclomatic complexity + IO surfaces) |

## Pairs with

- `meok-attestation-api` — POST results to https://meok-attestation-api.vercel.app/sign for cryptographically signed compliance certs
- `meok-attestation-verify` — public verification of any MEOK-signed cert
- Other MEOK governance MCPs via SOV3 `mcp_bridge_call`

## Pricing

- **Free**: 10 calls/day. No API key required.
- **Pro** £79/mo: unlimited + signed attestations. [Subscribe](https://buy.stripe.com/14A4gB3K4eUWgYR56o8k836)
- **Enterprise** £1,499/mo: white-label + on-premise + SLA. hello@meok.ai

## Status

Scaffold v1.0.0 ships the MCP framework + 5 tool stubs. v1.1.0 will add real regulation data ingestion.

If your team needs this MCP fully-loaded faster, ping hello@meok.ai for sponsored development.

## License

MIT © MEOK AI Labs

<!-- mcp-name: io.github.CSOAI-ORG/cobol-bridge-mcp -->
