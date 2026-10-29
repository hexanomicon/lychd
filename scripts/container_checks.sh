#!/usr/bin/env bash
# Build and run the repository check image without mounting the checkout or HOME.
set -euo pipefail
umask 022

fail() { printf '%s\n' "$*" >&2; exit 2; }

build_only=0
if [[ ${1:-} == --build-only ]]; then
    build_only=1
    shift
fi
inside=0
if [[ ${1:-} == --inside ]]; then
    shift
    [[ -f /opt/lychd-test-image && ( -f /run/.containerenv || -f /.dockerenv ) ]] ||
        fail 'Core checks require the OCI test image and an observed container marker.'
    inside=1
fi

[[ $# -gt 0 ]] || set -- test
for target in "$@"; do
    case "$target" in
        lint|format-check|type-check|test|test-ci|test-config|test-containers|coverage|check|developer-fixture) ;;
        *) fail "Unsupported container check target: $target" ;;
    esac
done
if [[ "$inside" == 1 ]]; then
    export LYCHD_TEST_CONTAINER=1
    XDG_RUNTIME_DIR=$(mktemp -d /tmp/lychd-check-runtime.XXXXXX)
    export XDG_RUNTIME_DIR
    exec make --no-print-directory "$@"
fi
engine=${LYCHD_TEST_ENGINE:-podman}
case "$engine" in
    podman|docker) ;;
    *) fail 'LYCHD_TEST_ENGINE must be podman or docker.' ;;
esac
command -v "$engine" >/dev/null || fail "OCI check engine unavailable: $engine (no host fallback)."
command -v timeout >/dev/null || fail 'Core checks require the host timeout supervisor.'
python_version=${LYCHD_TEST_PYTHON:-3.15.0}
case "$python_version" in
    3.14.8|3.15.0) ;;
    *) fail 'LYCHD_TEST_PYTHON must match a reviewed CI lane: 3.14.8 or 3.15.0.' ;;
esac
root=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd -P)
context=$(mktemp -d "${TMPDIR:-/tmp}/lychd-check-context.XXXXXX")
cidfile="$context/container.id"
child_pid=
supervise() {
    local result=0
    "$@" &
    child_pid=$!
    wait "$child_pid" || result=$?
    child_pid=
    return "$result"
}
cleanup() {
    status=$?
    trap - EXIT
    trap '' INT TERM
    keep_context=0
    if [[ -n "$child_pid" ]]; then
        kill -TERM "$child_pid" 2>/dev/null || true
        for ((attempt = 0; attempt < 50; attempt++)); do
            kill -0 "$child_pid" 2>/dev/null || break
            sleep 0.1
        done
        kill -KILL "$child_pid" 2>/dev/null || true
        wait "$child_pid" 2>/dev/null || true
    fi
    if [[ -s "$cidfile" ]]; then
        container_id=$(< "$cidfile")
        if [[ "$container_id" =~ ^[a-f0-9]{64}$ ]]; then
            if ! timeout --signal=TERM --kill-after=5s 15s "$engine" rm --force "$container_id" >/dev/null; then
                printf '%s\n' "Cannot settle owned check container $container_id; reconcile $context." >&2
                keep_context=1
                [[ "$status" != 0 ]] || status=1
            fi
        else
            printf '%s\n' "Invalid check container identity; reconcile $context." >&2
            keep_context=1
            [[ "$status" != 0 ]] || status=1
        fi
    fi
    [[ "$keep_context" != 0 ]] || rm -rf -- "$context"
    exit "$status"
}
trap cleanup EXIT
trap 'exit 130' INT
trap 'exit 143' TERM

# Explicit roots only. In particular, .git, private .agents state, local envs,
# caches, dependency installs, and arbitrary untracked root files never cross.
inputs=(AGENTS.md CONTRIBUTING.md README.md ROADMAP.md LICENSE THIRD_PARTY_NOTICES.md
    Makefile Containerfile Containerfile.tests pyproject.toml uv.lock
    .containerignore .python-version .nvmrc zensical.toml
    .github .agents/scopes .agents/workflows clients docs examples scripts src tests)
tar -C "$root" --exclude=node_modules --exclude=.venv --exclude=.cache \
    --exclude=__pycache__ --exclude='*.pyc' --exclude=.gradle --exclude=build \
    --exclude=.svelte-kit --exclude=.pytest_cache --exclude=.ruff_cache \
    -cf - "${inputs[@]}" | tar -C "$context" -xf -
# Both engines see only this already-bounded context. Its production ignore
# file is retained as test data; the build uses a local empty ignore file.
: > "$context/.dockerignore"
cp -- "$context/.dockerignore" "$context/.containerignore.build"
image="localhost/lychd-checks:python-${python_version}"
build=("$engine" build --file "$context/Containerfile.tests"
    --build-arg "PYTHON_VERSION=$python_version" --tag "$image" --iidfile "$context/image.id")
if [[ "$engine" == podman ]]; then
    build+=(--ignorefile "$context/.containerignore.build"
        --memory 4g --cpu-period 100000 --cpu-quota 200000)
elif [[ ${DOCKER_BUILDKIT:-1} == 0 ]]; then
    build+=(--memory 4g --cpu-period 100000 --cpu-quota 200000)
else
    build+=(--resource memory=4g --resource cpu-period=100000 --resource cpu-quota=200000)
fi
supervise "${build[@]}" "$context"
image_id=$(< "$context/image.id")
[[ "$image_id" =~ ^(sha256:)?[a-f0-9]{64}$ ]] || fail 'OCI build did not return an exact image ID.'
if [[ "$build_only" == 1 ]]; then
    exit 0
fi

selection=()
# Forward selection only; never inherit credentials or the caller's whole env.
for name in N K M ARGS VERBOSE PYTEST_TARGETS PYTEST_BASE_ROOT PYTEST_BASETEMP \
    RUFF_TARGETS FORMAT_TARGETS TYPECHECK_TARGETS CONTAINER_TEST_TARGETS; do
    if [[ -v "$name" ]]; then
        selection+=(--env "$name")
    fi
done
needs_daemon=0
for target in "$@"; do
    [[ "$target" != test-containers ]] || needs_daemon=1
done
common_run=("$engine" run --cidfile "$cidfile" --label io.lychd.repository-check=1
    --memory 4g --cpus 2 --pids-limit 512 --cap-drop=ALL
    --security-opt=no-new-privileges --tmpfs /tmp:rw,nosuid,nodev,size=1g)
run=("${common_run[@]}" --network=none)
if [[ " $* " == *' developer-fixture '* ]]; then
    [[ $# == 1 ]] || fail 'developer-fixture must run as its own explicit invocation.'
    run=("${common_run[@]}" --publish 127.0.0.1:8000:8000)
fi
if [[ "$needs_daemon" == 1 ]]; then
    # This is explicit host-daemon authority for disposable PostgreSQL receipts,
    # confined to the test harness. It is never granted to the production Vessel.
    socket=${LYCHD_TEST_DAEMON_SOCKET:-}
    [[ -n "$socket" && "$socket" == /* && -S "$socket" ]] ||
        fail 'test-containers requires an explicit absolute LYCHD_TEST_DAEMON_SOCKET.'
    # The qualified socket profile uses Docker's host group mapping. Rootless
    # Podman's socket/user namespace mapping needs its own acceptance receipt.
    [[ "$engine" == docker ]] || fail 'test-containers currently requires the qualified Docker socket profile.'
    printf '%s\n' "Disposable database checks receive daemon authority via $socket." >&2
    run=("${common_run[@]}" --network=host --security-opt label=disable
        --mount "type=bind,src=$socket,dst=/var/run/docker.sock"
        --group-add "$(stat -c %g -- "$socket")"
        --env DOCKER_HOST=unix:///var/run/docker.sock
        --env TESTCONTAINERS_DOCKER_SOCKET_OVERRIDE="$socket"
        --env TESTCONTAINERS_HOST_OVERRIDE=127.0.0.1
        --env TESTCONTAINERS_CONNECTION_MODE=docker_host)
    for name in TESTCONTAINERS_RYUK_PRIVILEGED TESTCONTAINERS_RYUK_DISABLED; do
        if [[ -v "$name" ]]; then
            run+=(--env "$name")
        fi
    done
fi
if [[ " $* " == *' developer-fixture '* ]]; then
    supervise "${run[@]}" "${selection[@]}" "$image_id" "$@"
else
    supervise timeout --signal=TERM --kill-after=15s 1800s "${run[@]}" "${selection[@]}" "$image_id" "$@"
fi
