#!/usr/bin/env bash
# Qualify real Scout DNS/TLS and current authority inside a dedicated OCI adapter.
set -euo pipefail
umask 077
fail() { printf '%s\n' "$*" >&2; exit 2; }

if [[ ${1:-} == --inside-setup || ${1:-} == --inside ]]; then
    [[ $# == 1 && -f /opt/lychd-test-image && -f /opt/lychd-scout-qualification &&
        ( -f /run/.containerenv || -f /.dockerenv ) ]] || fail 'The observed Scout qualification image is required.'
    if [[ $1 == --inside-setup ]]; then
        [[ $(id -u) == 0 ]] || fail 'Only namespace setup starts as container root.'
        ip link set lo up
        ip addr add 93.184.216.34/32 dev lo
        exec setpriv --reuid=1000 --regid=1000 --clear-groups \
            --inh-caps=-all --ambient-caps=-all --bounding-set=-all --no-new-privs \
            bash /work/scripts/container_scout_qualification.sh --inside
    fi
    export LYCHD_TEST_CONTAINER=1 UV_OFFLINE=1 UV_NO_SYNC=1 PYTHONDONTWRITEBYTECODE=1
    export UV_CACHE_DIR=/qualification/uv-cache
    export XDG_RUNTIME_DIR=/qualification/runtime
    mkdir "$XDG_RUNTIME_DIR"
    # Export only actual sanitized receipts, including failed occurrences. Never
    # export basetemps: they contain ephemeral TLS private keys and worker probes.
    export_receipts() {
        local result=$?
        trap - EXIT
        python - <<'PY' || result=1
from pathlib import Path
for phase in ("static", "fetch", "authority"):
    receipts = sorted({path.resolve(strict=True) for path in (Path("/qualification") / phase).glob("*/receipt.json")})
    if len(receipts) > 1:
        raise SystemExit("Ambiguous qualification receipt")
    if receipts:
        (Path("/qualification/export") / f"{phase}-receipt.json").write_bytes(receipts[0].read_bytes())
PY
        exit "$result"
    }
    trap export_receipts EXIT
    python -I -S scripts/scout_qualification.py --observe-inside
    LYCHD_REQUIRE_SCOUT_EXTRACTION_PROOF=1 LYCHD_SCOUT_EXTRACTION_PROFILE=/opt/scout-runtime.json \
        make test M=container N=0 ARGS='-p no:cacheprovider' \
        PYTEST_TARGETS=tests/integration/test_scout_extraction_runtime.py::test_scout_extraction_host_boundary \
        PYTEST_BASETEMP=/qualification/static
    LYCHD_REQUIRE_SCOUT_FETCH_PROOF=1 LYCHD_SCOUT_EXTRACTION_PROFILE=/opt/scout-runtime.json \
        make test M=container N=0 ARGS='-p no:cacheprovider' \
        PYTEST_TARGETS=tests/integration/test_scout_fetch_runtime.py::test_scout_fetch_isolated_dns_tls_passage \
        PYTEST_BASETEMP=/qualification/fetch
    LYCHD_REQUIRE_SCOUT_AUTHORITY_PROOF=1 \
        make test M=container N=0 ARGS='-p no:cacheprovider' \
        PYTEST_TARGETS=tests/integration/test_scout_authority_runtime.py::test_current_authority_isolated_network_passage \
        PYTEST_BASETEMP=/qualification/authority
    exit 0
fi

build_only=0
if [[ ${1:-} == --build-only ]]; then
    build_only=1
    shift
fi
[[ $# == 0 ]] || fail 'No arbitrary test, command, or runtime selection is accepted.'
case ${LYCHD_SCOUT_QUALIFICATION_PROFILE:-} in
    trusted-scout-c2|trusted-scout-ci-c1) ;;
    *) fail 'Explicit supported LYCHD_SCOUT_QUALIFICATION_PROFILE admission is required.' ;;
esac
[[ $(uname -m) == x86_64 ]] || fail 'This explicit seccomp/runtime profile supports Linux x86-64 only.'
[[ ${LYCHD_TEST_ENGINE:-docker} == docker ]] || fail 'This qualification adapter currently requires Docker.'
for tool in docker curl sha256sum timeout python3; do
    command -v "$tool" >/dev/null || fail "Required qualification tool unavailable: $tool (no host test fallback)."
done
root=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd -P)
output=${LYCHD_SCOUT_QUALIFICATION_OUTPUT:-}
[[ -n "$output" && "$output" == /* && -d "$output" ]] || fail 'Set LYCHD_SCOUT_QUALIFICATION_OUTPUT to an existing absolute artifact directory outside the checkout.'
output=$(realpath -e -- "$output")
[[ "$output/" != "$root/"* ]] || fail 'Raw qualification artifacts must remain outside the checkout.'
run_dir=$(mktemp -d "$output/scout-qualification.XXXXXX")
context="$run_dir/context"
mkdir "$context" "$run_dir/raw"
python3 -I -S "$root/scripts/scout_qualification.py" --preflight-engine >"$run_dir/engine-preflight.json"
export DOCKER_HOST=${DOCKER_HOST:-unix:///var/run/docker.sock}
child_pid=
control_active=0
supervise() {
    local result=0
    "$@" <&0 &
    child_pid=$!
    wait "$child_pid" || result=$?
    child_pid=
    return "$result"
}
cleanup() {
    status=$?
    trap - EXIT
    trap '' INT TERM
    if [[ -n "$child_pid" ]]; then
        kill -TERM "$child_pid" 2>/dev/null || true
        grace=50
        [[ "$control_active" == 0 ]] || grace=1200
        for ((attempt = 0; attempt < grace; attempt++)); do
            kill -0 "$child_pid" 2>/dev/null || break
            sleep 0.1
        done
        kill -KILL "$child_pid" 2>/dev/null || true
        wait "$child_pid" 2>/dev/null || true
    fi
    # The API controller owns durable identities, bounded export and removal.
    rm -rf -- "$context"
    printf '%s\n' "Scout qualification evidence: $run_dir (exit $status)"
    exit "$status"
}
trap cleanup EXIT
trap 'exit 130' INT
trap 'exit 143' TERM

# Match the ordinary check harness's explicit public input closure. No .git,
# private agent state, host environments, caches, HOME, or daemon mounts cross.
inputs=(AGENTS.md CONTRIBUTING.md README.md ROADMAP.md LICENSE THIRD_PARTY_NOTICES.md
    Makefile Containerfile Containerfile.tests Containerfile.scout-qualification pyproject.toml uv.lock
    .containerignore .python-version .nvmrc zensical.toml
    .github .agents/scopes .agents/workflows clients docs examples scripts src tests)
tar -C "$root" --exclude=node_modules --exclude=.venv --exclude=.cache \
    --exclude=__pycache__ --exclude='*.pyc' --exclude=.gradle --exclude=build \
    --exclude=.svelte-kit --exclude=.pytest_cache --exclude=.ruff_cache \
    -cf - "${inputs[@]}" | tar -C "$context" -xf -
# The artifact root stays private. Its copied public build inputs must be
# readable by setup's capability-free root and the ordinary test user alike.
chmod -R a+rX "$context"
: > "$context/.dockerignore"
cp -- "$context/.dockerignore" "$context/.containerignore.build"
find "$context" -type f -print0 | sort -z | xargs -0 sha256sum >"$run_dir/source-manifest.sha256"
base_image="localhost/lychd-scout-checks:${run_dir##*.}"
supervise timeout --signal=TERM --kill-after=15s 900s docker build \
    --resource memory=4g --resource cpu-period=100000 --resource cpu-quota=200000 \
    --file "$context/Containerfile.tests" --tag "$base_image" \
    --iidfile "$run_dir/base-image.id" "$context" >"$run_dir/base-build.log" 2>&1
base_image_id=$(< "$run_dir/base-image.id")
[[ "$base_image_id" =~ ^sha256:[a-f0-9]{64}$ ]] || fail 'Core check build did not return an exact image ID.'
[[ $(docker image inspect "$base_image" --format '{{.Id}}') == "$base_image_id" ]] ||
    fail 'Owned base image tag changed before adapter build.'
supervise timeout --signal=TERM --kill-after=15s 300s docker build \
    --resource memory=4g --resource cpu-period=100000 --resource cpu-quota=200000 \
    --file "$context/Containerfile.scout-qualification" --build-arg "CHECK_IMAGE=$base_image" \
    --iidfile "$run_dir/image.id" "$context" >"$run_dir/adapter-build.log" 2>&1
image_id=$(< "$run_dir/image.id")
[[ "$image_id" =~ ^sha256:[a-f0-9]{64}$ ]] || fail 'Qualification build did not return an exact image ID.'
[[ $(docker image inspect "$base_image" --format '{{.Id}}') == "$base_image_id" ]] ||
    fail 'Owned base image tag changed during adapter build.'
docker image inspect "$base_image_id" "$image_id" >"$run_dir/images.json"
python3 -I -S - "$run_dir/images.json" "$base_image_id" "$image_id" <<'PY'
import json, sys
base, adapter = json.load(open(sys.argv[1]))
assert base["Id"] == sys.argv[2] and adapter["Id"] == sys.argv[3]
layers = base["RootFS"]["Layers"]
assert layers and len(adapter["RootFS"]["Layers"]) > len(layers)
assert adapter["RootFS"]["Layers"][:len(layers)] == layers, "Adapter did not retain the exact base layers"
PY
if [[ "$build_only" == 1 ]]; then
    exit 0
fi

# Official Apache-2.0 Moby default profile, fetched immutably rather than vendored.
# Preserve its deny-by-default policy and every existing rule; only the exact
# namespace clone/unshare and mount calls used by Scout's fixed bwrap argv differ.
curl --fail --silent --show-error --location --max-time 30 \
    https://raw.githubusercontent.com/moby/profiles/4b8214fc4971e06172938a1f1554ccff6647ee80/seccomp/default.json \
    --output "$run_dir/default-seccomp.json"
printf '%s  %s\n' 6416b47770785a41ac59073cdc77d9fe98517df2799dc83ef207e622de3053f6 "$run_dir/default-seccomp.json" | sha256sum --check
# This is host JSON metadata transformation, never host Core/test execution.
python3 -I -S -c '
import json, sys
profile = json.load(sys.stdin)
assert profile["defaultAction"] == "SCMP_ACT_ERRNO"
profile["syscalls"].extend([
    {"names": ["clone"], "action": "SCMP_ACT_ALLOW", "args": [{"index": 0, "value": 2080505873, "op": "SCMP_CMP_EQ"}]},
    {"names": ["unshare"], "action": "SCMP_ACT_ALLOW", "args": [{"index": 0, "value": 268435456, "op": "SCMP_CMP_EQ"}]},
    {"names": ["mount", "umount2", "pivot_root"], "action": "SCMP_ACT_ALLOW"},
])
print(json.dumps(profile, indent=2))
' <"$run_dir/default-seccomp.json" >"$run_dir/scout-seccomp.json"
sha256sum "$run_dir/default-seccomp.json" "$run_dir/scout-seccomp.json" >"$run_dir/seccomp.sha256"
control_active=1
supervise python3 -I -S "$root/scripts/scout_qualification.py" "$image_id" "$run_dir" "$run_dir/scout-seccomp.json"
control_active=0
