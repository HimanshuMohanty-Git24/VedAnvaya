# Rigveda semantic pilot cost

The completed pilot used `CODEX_DIRECT` inside Codex/Luna. Python did not invoke an
LLM API, and this run has no vendor token accounting or API billing.

| measure | result |
|---|---:|
| pilot EvidencePackets | 508 |
| batches | 22 |
| API requests | 0 |
| direct API cost | $0 |
| recorded input tokens | 0 — no API usage object exists |
| recorded output tokens | 0 — no API usage object exists |

The run manifest records `api_invocation: false`, `extraction_runtime: CODEX_DIRECT`,
`model: gpt-5.6-luna`, and `total_cost_usd: 0`. No projected full-corpus cost is
reported because there was no API workload from which to extrapolate.

This is a workload report, not a claim that local Codex reasoning has a vendor price of
zero. Any future separately authorized vendor-backed run must record its own actual
provider usage and cost.
