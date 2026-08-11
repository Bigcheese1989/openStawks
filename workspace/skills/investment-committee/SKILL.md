---
name: investment-committee
description: Rank researched equities and propose conservative target weights for a hypothetical model portfolio under fixed risk constraints.
---
# Investment committee

Use only the supplied research packages and current model-portfolio state.

Rules:
- No position may exceed the configured maximum position weight.
- Respect the configured minimum cash allocation.
- Prefer no action over weak action.
- Avoid concentration in multiple companies driven by the same unsupported thesis.
- A high quantitative screen rank does not override weak fundamentals, excessive valuation, or material unresolved risk.
- Explicitly include existing holdings in the target list when recommending a change; missing holdings are interpreted by deterministic code as unchanged.
- Do not output share quantities or instructions for the user's real brokerage account.
