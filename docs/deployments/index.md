---
title: Deployments
icon: material/server
---

# Deployment experiments

These guides prepare an operator-controlled Linux host and separate that work from LychD's
application initialization, generated service body, and recovery. They do not establish a
working application merely because a playbook finishes.

- [Tumbleweed VPS](tumbleweed/index.md): a headless, mutable host prepared with repeatable
  Ansible operations; qualify one pilot before adding hosts.

[State of Work](../state-of-the-work.md#systemd-podman-embodiment) owns the delivery boundary.
Keep private inventories, keys, host settings, backup repositories and observations outside
the checkout.
