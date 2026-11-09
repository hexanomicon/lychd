#!/usr/bin/env bash
# Offline source checks only. Never contacts or provisions an inventory host.
set -euo pipefail

LYCHD_CHECK_TOOLS=${1:?Usage: deployments/check.sh /absolute/controller/environment}
[[ $LYCHD_CHECK_TOOLS == /* ]] || { echo 'Use an absolute tooling environment path.' >&2; exit 2; }
LYCHD_CHECK_ROOT=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd -P)
LYCHD_CHECK_SCRATCH=$(mktemp -d /tmp/lychd-deployment-checks.XXXXXX)
trap 'rm -rf -- "$LYCHD_CHECK_SCRATCH"' EXIT
export ANSIBLE_HOME="$LYCHD_CHECK_SCRATCH/ansible"
export PYTHONDONTWRITEBYTECODE=1
cd "$LYCHD_CHECK_ROOT"

"$LYCHD_CHECK_TOOLS/bin/python" -m unittest discover -s deployments/ansible/tests
"$LYCHD_CHECK_TOOLS/bin/python" -m unittest discover -s deployments/autoyast/tests
"$LYCHD_CHECK_TOOLS/bin/python" -m unittest discover -s deployments/access -p 'test_*.py'
"$LYCHD_CHECK_TOOLS/bin/ruff" check deployments
"$LYCHD_CHECK_TOOLS/bin/ruff" format --check deployments

cd deployments/ansible
for playbook in host verify source deploy app-verify server admin access access-verify access-revoke workstation workstation-verify; do
    inventory=inventory.example.yml
    [[ $playbook != workstation* ]] || inventory=inventory.workstation.example.yml
    "$LYCHD_CHECK_TOOLS/bin/ansible-playbook" -i "$inventory" --syntax-check "playbooks/$playbook.yml"
    "$LYCHD_CHECK_TOOLS/bin/ansible-playbook" -i "$inventory" --list-hosts "playbooks/$playbook.yml" > "$LYCHD_CHECK_SCRATCH/hosts.txt"
    count=$(sed -n 's/.*hosts (\([0-9][0-9]*\)):.*/\1/p' "$LYCHD_CHECK_SCRATCH/hosts.txt" | sort -u)
    [[ $count == 1 ]] || { echo "Expected one example host per play: $playbook" >&2; exit 1; }
done
