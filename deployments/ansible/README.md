# Tumbleweed host-floor candidate

Use the canonical [Tumbleweed runbook](../../docs/deployments/tumbleweed/index.md) for controller
setup, private inventory and variables, check/apply commands, limitations and host acceptance.
`host.yml` and `verify.yml` prepare and observe an already installed host. `source.yml` stages
one exact source CLI over direct runtime-user SSH, while the body is inactive. These assets
do not initialize, bind, start or update a running LychD application.
