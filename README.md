# COBOL Bridge MCP — read-only sidecar (SPEC)

**SPEC, not a live product.** See [`SPEC.md`](SPEC.md).

- Read-only sidecar. Never writes core / ledger / CICS.
- `cobolbridge.ai` HTTP **522** sits. This README does not attach the domain.
- No Starter / Pro / Enterprise pricing on this measurement surface.
- Not certified. Not partnered. Not a second GSPC board.
- Living board: `GET https://councilof.ai/api/gspc` (22 axis · 15 measured · 7 empty).

mcp-name: io.github.CSOAI-ORG/cobol-bridge-mcp

[![License](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![PyPI](https://img.shields.io/pypi/v/cobol-bridge-mcp)](https://pypi.org/project/cobol-bridge-mcp/)

MIT parser: COBOL source text in, heuristic metrics out. Optional MCP next to a workstation. Never an inside-bank install.

## Install (local / stdio)

```bash
pip install cobol-bridge-mcp
# or
uvx cobol-bridge-mcp
```

```json
{
  "mcpServers": {
    "cobol-bridge-mcp": {
      "command": "uvx",
      "args": ["cobol-bridge-mcp"]
    }
  }
}
```

Tools (read the source you already hold; they do not write production):

- `parse_cobol_program`
- `identify_business_rules`
- `estimate_migration_complexity`
- `plan_migration_phases`
- `generate_test_harness`

## Contract

Full contract: [`SPEC.md`](SPEC.md). Measurement, never certification. Do not stamp MEASURED. Do not claim 17 banks are clients.

## License

MIT © [CSOAI-ORG](https://github.com/CSOAI-ORG) / CSOAI Ltd (GB, Companies House 16939677)

<!-- mcp-name: io.github.CSOAI-ORG/cobol-bridge-mcp -->
