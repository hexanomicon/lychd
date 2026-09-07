---
title: Provision
icon: material/cart-outline
---

# :material-cart-outline: Provision

An approved need is still several steps away from an order. Provision brings ordinary food, cleaning goods, toiletries, and other consumables into shared household custody, keeping each step separately reviewable.

## From need to result

`homestead.observe_shops@1` admits dated, attributed offers from Kaufland, Lidl, another merchant, a local market, or another eligible source. A shop profile is independently revocable. Public fetch, rendered observation, authentication, cart mutation, address disclosure, order submission, and payment remain separate powers.

`homestead.plan_provision@1` combines policy, stores, budget, offers, and any purpose-limited `FoodNeed@1` from [Eating](../wellbeing/eating.md). The need may carry quantities, exclusions, useful product traits, expiry, privacy class, and unresolved flags. It carries no diagnosis, journal, measurement, medication, genetics, movement history, or merchant instruction.

`homestead.build_cart@1` prepares the cart. Before `homestead.checkout@1` submits it once, it rechecks merchant, product, package, price, stock, fees, delivery, substitutions, recurring terms, disclosure, and worst-case budget. A material change returns to the Magus. Raw addresses, payment data, credentials, and one-time codes never enter prompts.

`ProvisionResult@1` reports what became available, unavailable, substituted, refused, or uncertain. It does not report eating, health, or adherence. Offers, plans, carts, orders, deliveries, and reconciliation retain independent revisions. Missing merchant acknowledgement leaves checkout or payment unknown and blocks retries until reconciliation establishes the effect. Restart cannot duplicate cart changes, orders, notifications, or delivery reconciliation.

Personal meal choice, preparation guidance, and eating out remain with Wellbeing; confirmed cooking becomes a stock transformation in [Stores](stores.md). [Scavenger](../scavenger/index.md) owns irregular, high-value, compatibility-heavy, property, and seller-negotiated acquisitions.

Return to [Homestead](index.md).
