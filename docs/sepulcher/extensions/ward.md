---
title:  Ward
icon: material/shield-account-outline
---

# :material-shield-account-outline: The Ward: Extension of Authority

> _"A sovereign mind must have boundaries. The Ward is the circle of salt that defines who may speak to the Daemon and what powers they may wield. It transforms a single-user tool into a multi-tenant citadel."_

**The Ward** is the IAM (Identity and Access Management) Extension of the LychD system. It is the implementation of **[ADR 38 (IAM)](../../adr/38-iam.md)**—the security layer that enforces authentication and scoped authorization across the **[Vessel](../vessel/index.md)**.

While **[The Veil](./veil.md)** secures the perimeter, The Ward secures the soul. It ensures that family members, automated peers, and external APIs can interact with the Lich without gaining the omnipotence of the Magus.

## I. The Sigil (Identity)

In the philosophy of the Ward, a user is not a "User"; they are a bearer of a **Sigil**. A Sigil is a cryptographic token (API Key or JWT) bound to a specific identity in the **[Phylactery](../phylactery/index.md)**.

- **The Master Sigil:** Created during the **[Summoning](../../summoning.md)**. It possesses the `*` (Universal) scope, granting total dominion over the Sepulcher.
- **Guest Sigils:** Created by the Master for specific entities. Each is bound to a restrictive list of **Scopes**.
    - `chat.read`: Can read history but not speak.
    - `chat.write`: Can interact with Agents.
    - `system.admin`: Can trigger **[Evolution](../../adr/18-evolution.md)**.

## II. The Middleware (Enforcement)

The Ward grafts itself onto the **[Vessel's](../vessel/index.md)** request lifecycle as a global middleware.

1. **Extraction:** It intercepts every HTTP and WebSocket request, extracting the Sigil from the `Authorization` header or `X-Lych-Sigil` token.
2. **Validation:** It verifies the cryptographic signature against the system's secret.
3. **Scope Check:** Before the request reaches an endpoint, the Ward verifies that the Sigil possesses the required scope for that specific route handler.
4. **Rejection:** If the check fails, the Ward returns `403 Forbidden` instantly, preventing the unprivileged entity from touching the core logic.

```python
# Usage in an Extension Router
@get("/admin/restart", guards=[RequiresScope("system.admin")])
async def restart_system() -> Response:
    ...
```

## III. Capability Gating (The Dispatcher's Filter)

The Ward extends its protection into the cognitive realm via the **[Dispatcher](../../adr/22-dispatcher.md)**.

- **The Filter:** When an **[Agent](../../adr/20-agents.md)** is summoned, the Ward inspects the active Sigil.
- **The Mask:** It physically removes sensitive tools from the Agent's arsenal if the user lacks the scope.
    - _Example:_ A Guest user asks "Delete all files." The Agent cannot even _attempt_ this, because the `file_system.delete` tool was filtered out of its context before the LLM was even invoked.

## IV. Symbiosis with The Veil

The Ward and **[The Veil](./veil.md)** work in tandem to secure the threshold.

- **Public Shielding:** The Veil is configured to reject any request to `/api/*` that does not carry a valid Sigil format, stopping DDoS attacks at the edge.
- **Inner Circle Bypass:** Traffic originating from the **[Tether (VPN)](./tether.md)** is often granted a "Trusted Context," allowing the Master to bypass explicit login rituals when connecting from a bonded device.

## V. Management (The Rituals)

The Ward exposes CLI commands via **[The CLI](../../adr/19-cli.md)** for Sigil management.

- `lychd ward mint <name> --scopes "chat.*,vision.*"`: Generates a new API Key.
- `lychd ward revoke <name>`: Instantly banishes a Sigil, terminating all active sessions.
- `lychd ward audit`: Displays a log of which Sigils accessed which resources, sourced from the **[Oculus](./oculus.md)** traces.
