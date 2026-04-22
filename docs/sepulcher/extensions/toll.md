---
title:  Toll
icon: material/cash-register
---

# :material-cash-register: The Toll: Extension of Economics

> _"Intelligence is energy, and energy has a cost. The Toll is the accountant of the Sepulcher, ensuring that the exchange of cognition for currency is precise, automated, and sovereign."_

**The Toll** is the Economic Extension of the LychD system. It is the implementation of **[ADR 41 (x402)](../../adr/41-x402.md)**—a middleware and toolset that enables the Daemon to transact value natively via the **x402 (Payment Required)** protocol.

It transforms the Lych from a cost center into an economic agent. It manages the **Tithe** (Resource Quotas) for internal users and facilitates **Settlement** (Crypto Payments) for external services and the Swarm.

## I. The Middleware (The Gate)

The Toll grafts a financial interceptor onto the **[Vessel](../vessel/index.md)**. This middleware can be applied globally or to specific high-value routes.

1. **The Challenge:** When a request hits a "Tolled Endpoint" (e.g., `/v1/chat/completions`), the middleware checks for a valid **[L402 Ticket](https://l402.org/)**.
2. **The Invoice:** If no ticket is present, the Toll returns `402 Payment Required`. The response includes a Lightning Network or Solana invoice for the exact compute cost of the request.
3. **The Settlement:** The client pays the invoice. The payment gateway returns a **Preimage** (Proof of Payment).
4. **The Access:** The client retries the request with the Preimage in the `Authorization` header. The Toll verifies it and allows the request to proceed.

## II. The Tithe (Internal Quotas)

For users within the **[Ward](./ward.md)** (Family/Guests), the Toll enforces resource discipline without requiring per-request payments.

- **The Ledger:** It maintains a balance of "Credits" for each Sigil in the **[Phylactery](../phylactery/index.md)**.
- **The Draw:** Every token generated and every second of GPU time consumes credits.
- **The Throttle:** If a user's balance hits zero, the Toll downgrades their priority via the **[Orchestrator](../../adr/23-orchestrator.md)** or blocks access until they provide an "Offering" (a payment to recharge their balance).

## III. Economic Dispatching (The Banker)

The Toll integrates with the **[Dispatcher](../../adr/22-dispatcher.md)** to optimize the "Cost of Truth."

- **Price Discovery:** Before a ritual begins, the Toll calculates the cost of local execution (Electricity/Opportunity Cost) vs. the cost of remote **[Portals](../animator/portal.md)**.
- **Arbitrage:**
    - _Scenario:_ The local GPU is busy.
    - _Logic:_ "It is cheaper to pay $0.01 to OpenRouter than to wait 5 minutes."
    - _Action:_ The Toll authorizes a micropayment from the System Wallet and routes the request to the cloud.

## IV. Symbiosis with The Legion

The Toll is the lifeblood of the **[Swarm (A2A)](./legion.md)**. It allows sovereign nodes to trade labor.

- **The Bid:** When a node subscribes to a workload pool, it posts its price.
- **The Payment:** When a task is completed, the requesting node pays the worker node directly via x402.
- **The Result:** A decentralized marketplace of compute where no central authority takes a cut.

## V. Security of the Vault

The Toll manages the **System Wallet**. This is a high-risk component protected by the **[Iron Pact of Sovereignty](../../adr/00-license.md)**.

- **Key Storage:** Private keys are encrypted at rest in the Crypt, accessible only to the Toll process.
- **Spending Limits:** The Magus can configure strict daily spending caps in the **[Codex](../codex.md)**. If the Lych attempts to spend more than the limit (e.g., due to a runaway loop), the Toll freezes the wallet and alerts the Magus.

!!! tip "Frictionless Portals"
    The Toll supports providers that implement native L402. This allows the Lych to use paid APIs without the Magus ever signing up for an account or entering a credit card. The machine simply pays for what it uses, packet by packet.
