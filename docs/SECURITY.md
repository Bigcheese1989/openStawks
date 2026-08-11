# Security boundary

This project intentionally contains no broker integration.

The OpenClaw `stock-analyst` agent is configured with an explicit allowlist of `web_search`, `web_fetch`, and `read`, and an explicit denylist covering shell/process execution, filesystem mutation, browser automation, messaging, cron, gateway configuration, and skill modification. The deterministic daily scheduler is an operator-authored OpenClaw command cron job; it is not created or modified by the model-facing agent.

The model portfolio lives only in the project's SQLite database. It is a simulation and is not synchronized with any real brokerage account.

Do not add IBKR, Alpaca, broker OAuth, trading API keys, banking credentials, or brokerage session cookies to this Raspberry Pi. If execution is ever added later, it should be a separate system with a separate security review and explicit human approval.

The model can still produce incorrect research. Source links in each PDF are provided so material claims can be checked against primary evidence.
