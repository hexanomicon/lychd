from __future__ import annotations

from collections.abc import Callable
from contextlib import nullcontext
from pathlib import Path
from unittest.mock import MagicMock

import pytest

import lychd.system.services.bind as bind_module
from lychd.system.binding_sites import (
    AttestedBindingSite,
    AttestedBindingSites,
)
from lychd.system.host_tools import TrustedExecutable
from lychd.system.readiness import BindingFoundation
from lychd.system.services.bind import (
    BindApplyError,
    BindingCommitState,
    BindingPlanDriftError,
    BindingRequirementError,
    BindPlan,
    BindRequest,
    BindUseCase,
)
from lychd.system.services.scribe import (
    BindingReconcilePlan,
    ScribeGenerationError,
    ScribeTransactionError,
    ScribeTransactionState,
)
from lychd.system.services.scribe.storage import PathStateIndeterminateError


def _tool(path: str, *, inode: int) -> TrustedExecutable:
    return TrustedExecutable(path=path, device=1, inode=inode)


def _site(path: str, *, inode: int) -> AttestedBindingSite:
    return AttestedBindingSite(path=Path(path), device=1, inode=inode)


def _foundation(
    *,
    podman: str = "/usr/bin/podman",
    podman_inode: int = 2,
    quadlet_site_inode: int = 4,
) -> BindingFoundation:
    return BindingFoundation(
        systemctl=_tool("/usr/bin/systemctl", inode=1),
        podman=_tool(podman, inode=podman_inode),
        quadlet_user_generator=_tool("/usr/libexec/podman/quadlet", inode=3),
        sites=AttestedBindingSites(
            quadlet=_site(
                "/home/operator/.config/containers/systemd",
                inode=quadlet_site_inode,
            ),
            systemd_user=_site(
                "/home/operator/.config/systemd/user",
                inode=5,
            ),
        ),
    )


def _request(
    *,
    required: tuple[str, ...] = ("operator-token",),
) -> BindRequest:
    return BindRequest.compile(
        manifests=(),
        plain_units={"lychd-reactor.path": "[Path]\n"},
        core_secret_factories={"lychd-core": lambda: "generated"},
        required_secret_names=required,
    )


def _use_case(
    *,
    scribe: MagicMock,
    secrets: MagicMock,
    systemd: MagicMock,
    foundation: BindingFoundation | None = None,
    observed_foundation: BindingFoundation | None = None,
) -> BindUseCase:
    expected = foundation or _foundation()
    return BindUseCase(
        scribe=scribe,
        secrets=secrets,
        systemd_factory=lambda: systemd,
        foundation=expected,
        foundation_probe=lambda: observed_foundation or expected,
        lock_factory=nullcontext,
    )


def test_plan_is_read_only_and_canonical() -> None:
    scribe = MagicMock()
    scribe.plan_reconcile_all.return_value = BindingReconcilePlan(
        changes=(),
        observed_generation="bindings-a",
        desired_generation="desired-a",
    )
    secrets = MagicMock()

    def exists(name: str) -> bool:
        return name == "operator-token"

    secrets.exists.side_effect = exists
    systemd = MagicMock()
    use_case = _use_case(scribe=scribe, secrets=secrets, systemd=systemd)

    plan = use_case.plan(_request())

    assert plan.observed_secrets == (
        ("lychd-core", False),
        ("operator-token", True),
    )
    assert plan.missing_core_secrets == ("lychd-core",)
    assert plan.missing_required_secrets == ()
    secrets.ensure_present.assert_not_called()
    scribe.reconcile_all.assert_not_called()
    systemd.daemon_reload.assert_not_called()


def test_apply_commits_in_order_once() -> None:
    events: list[str] = []
    binding_plan = BindingReconcilePlan(
        changes=(),
        observed_generation="bindings-a",
        desired_generation="desired-a",
    )
    scribe = MagicMock()
    scribe.plan_reconcile_all.return_value = binding_plan

    def reconcile(
        _manifests: object,
        *,
        plain_units: object,
        expected_generation: str | None,
        expected_desired_generation: str | None,
    ) -> str:
        del plain_units
        assert expected_generation == "bindings-a"
        assert expected_desired_generation == "desired-a"
        events.append("bindings")
        return "bindings-after"

    scribe.reconcile_all.side_effect = reconcile
    states: dict[str, bool] = {
        "lychd-core": False,
        "operator-token": True,
    }
    secrets = MagicMock()

    def exists(name: str) -> bool:
        return states[name]

    secrets.exists.side_effect = exists

    def ensure(name: str, value: str) -> bool:
        assert value == "generated"
        states[name] = True
        events.append("secret")
        return True

    secrets.ensure_present.side_effect = ensure
    systemd = MagicMock()

    def reload_systemd() -> None:
        events.append("reload")

    systemd.daemon_reload.side_effect = reload_systemd
    use_case = _use_case(scribe=scribe, secrets=secrets, systemd=systemd)
    request = _request()
    approved = use_case.plan(request)

    result = use_case.apply(request, approved)

    assert result.created_secrets == ("lychd-core",)
    assert result.binding_generation == "bindings-after"
    assert result.systemd_reloaded
    assert events == ["secret", "bindings", "reload"]
    assert scribe.plan_reconcile_all.call_count == 2
    scribe.reconcile_all.assert_called_once()
    assert scribe.reconcile_all.call_args.kwargs["expected_generation"] == "bindings-a"
    assert scribe.reconcile_all.call_args.kwargs["expected_desired_generation"] == "desired-a"
    systemd.daemon_reload.assert_called_once_with()


def test_apply_rejects_foundation_drift_before_effects() -> None:
    scribe = MagicMock()
    secrets = MagicMock()
    systemd = MagicMock()
    use_case = _use_case(
        scribe=scribe,
        secrets=secrets,
        systemd=systemd,
        observed_foundation=_foundation(podman="/opt/podman"),
    )
    scribe.plan_reconcile_all.return_value = BindingReconcilePlan(
        changes=(),
        observed_generation="bindings-a",
        desired_generation="desired-a",
    )
    secrets.exists.return_value = True
    approved = use_case.plan(_request(required=()))
    scribe.reset_mock()
    secrets.reset_mock()

    with pytest.raises(BindingPlanDriftError, match="host foundation changed"):
        use_case.apply(_request(required=()), approved)

    scribe.plan_reconcile_all.assert_not_called()
    secrets.exists.assert_not_called()
    scribe.reconcile_all.assert_not_called()
    systemd.daemon_reload.assert_not_called()


def test_apply_rejects_plan_from_another_bound_foundation() -> None:
    """A caller cannot splice intent approved for host B into host A's adapters."""
    expected = _foundation()
    scribe = MagicMock()
    scribe.plan_reconcile_all.return_value = BindingReconcilePlan(
        changes=(),
        observed_generation="bindings-a",
        desired_generation="desired-a",
    )
    secrets = MagicMock()
    secrets.exists.return_value = True
    systemd = MagicMock()
    use_case = _use_case(
        scribe=scribe,
        secrets=secrets,
        systemd=systemd,
        foundation=expected,
    )
    request = _request(required=())
    observed = use_case.plan(request)
    foreign_plan = BindPlan(
        foundation=_foundation(podman_inode=99),
        bindings=observed.bindings,
        observed_secrets=observed.observed_secrets,
        missing_core_secrets=observed.missing_core_secrets,
        missing_required_secrets=observed.missing_required_secrets,
    )
    scribe.reset_mock()
    secrets.reset_mock()

    with pytest.raises(
        BindingPlanDriftError,
        match="different host foundation",
    ):
        use_case.apply(request, foreign_plan)

    scribe.plan_reconcile_all.assert_not_called()
    secrets.exists.assert_not_called()
    secrets.ensure_present.assert_not_called()
    scribe.reconcile_all.assert_not_called()
    systemd.daemon_reload.assert_not_called()


def test_apply_rejects_binding_drift_before_secret_effects() -> None:
    scribe = MagicMock()
    scribe.plan_reconcile_all.return_value = BindingReconcilePlan(
        changes=(),
        observed_generation="bindings-b",
        desired_generation="desired-a",
    )
    secrets = MagicMock()
    systemd = MagicMock()
    use_case = _use_case(scribe=scribe, secrets=secrets, systemd=systemd)
    approved = BindPlan(
        foundation=_foundation(),
        bindings=BindingReconcilePlan(
            changes=(),
            observed_generation="bindings-a",
            desired_generation="desired-a",
        ),
        observed_secrets=(),
        missing_core_secrets=(),
        missing_required_secrets=(),
    )

    with pytest.raises(BindingPlanDriftError, match="Binding state changed"):
        use_case.apply(_request(required=()), approved)

    secrets.ensure_present.assert_not_called()
    scribe.reconcile_all.assert_not_called()
    systemd.daemon_reload.assert_not_called()


def test_apply_rejects_desired_byte_drift_before_secret_effects() -> None:
    """Equal dispositions and live state cannot conceal different desired bytes."""
    scribe = MagicMock()
    scribe.plan_reconcile_all.return_value = BindingReconcilePlan(
        changes=(),
        observed_generation="bindings-a",
        desired_generation="desired-b",
    )
    secrets = MagicMock()
    systemd = MagicMock()
    use_case = _use_case(scribe=scribe, secrets=secrets, systemd=systemd)
    approved = BindPlan(
        foundation=_foundation(),
        bindings=BindingReconcilePlan(
            changes=(),
            observed_generation="bindings-a",
            desired_generation="desired-a",
        ),
        observed_secrets=(),
        missing_core_secrets=(),
        missing_required_secrets=(),
    )

    with pytest.raises(BindingPlanDriftError, match="Binding state changed"):
        use_case.apply(_request(required=()), approved)

    secrets.ensure_present.assert_not_called()
    scribe.reconcile_all.assert_not_called()
    systemd.daemon_reload.assert_not_called()


def test_apply_rejects_secret_drift_before_effects() -> None:
    request = _request(required=())
    scribe = MagicMock()
    plan = BindingReconcilePlan(
        changes=(),
        observed_generation="bindings-a",
        desired_generation="desired-a",
    )
    scribe.plan_reconcile_all.return_value = plan
    secrets = MagicMock()
    secrets.exists.return_value = True
    systemd = MagicMock()
    use_case = _use_case(scribe=scribe, secrets=secrets, systemd=systemd)
    approved = BindPlan(
        foundation=_foundation(),
        bindings=plan,
        observed_secrets=(("lychd-core", False),),
        missing_core_secrets=("lychd-core",),
        missing_required_secrets=(),
    )

    with pytest.raises(BindingPlanDriftError, match="secret state changed"):
        use_case.apply(request, approved)

    secrets.ensure_present.assert_not_called()
    scribe.reconcile_all.assert_not_called()
    systemd.daemon_reload.assert_not_called()


def test_apply_rejects_missing_operator_secret_without_locking() -> None:
    scribe = MagicMock()
    secrets = MagicMock()
    systemd = MagicMock()
    use_case = _use_case(scribe=scribe, secrets=secrets, systemd=systemd)
    approved = BindPlan(
        foundation=_foundation(),
        bindings=BindingReconcilePlan(
            changes=(),
            observed_generation="bindings-a",
            desired_generation="desired-a",
        ),
        observed_secrets=(("operator-token", False),),
        missing_core_secrets=(),
        missing_required_secrets=("operator-token",),
    )

    with pytest.raises(BindingRequirementError, match="operator-token"):
        use_case.apply(_request(), approved)

    scribe.plan_reconcile_all.assert_not_called()
    secrets.ensure_present.assert_not_called()
    systemd.daemon_reload.assert_not_called()


def test_apply_reports_committed_bindings_when_reload_fails() -> None:
    """A terminal error preserves exact progress instead of hiding effects."""
    request = _request(required=())
    plan = BindingReconcilePlan(
        changes=(),
        observed_generation="bindings-a",
        desired_generation="desired-a",
    )
    scribe = MagicMock()
    scribe.plan_reconcile_all.return_value = plan
    scribe.reconcile_all.return_value = "bindings-after"
    present = {"lychd-core": False}
    secrets = MagicMock()

    def exists(name: str) -> bool:
        return present[name]

    secrets.exists.side_effect = exists

    def ensure(name: str, _value: str) -> bool:
        present[name] = True
        return True

    secrets.ensure_present.side_effect = ensure
    systemd = MagicMock()
    systemd.daemon_reload.side_effect = RuntimeError("manager unavailable")
    use_case = _use_case(scribe=scribe, secrets=secrets, systemd=systemd)
    approved = use_case.plan(request)

    with pytest.raises(BindApplyError, match="Bindings committed") as failure:
        use_case.apply(request, approved)

    assert failure.value.progress.created_secrets == ("lychd-core",)
    assert failure.value.progress.binding_commit_state is BindingCommitState.COMMITTED
    assert failure.value.progress.binding_generation == "bindings-after"
    assert not failure.value.progress.systemd_reloaded


def test_keyboard_interrupt_during_secret_commit_preserves_indeterminate_truth(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Cancellation keeps its native type while exposing possible secret residue."""
    request = _request(required=())
    plan = BindingReconcilePlan(
        changes=(),
        observed_generation="bindings-a",
        desired_generation="desired-a",
    )
    scribe = MagicMock()
    scribe.plan_reconcile_all.return_value = plan
    present = {"lychd-core": False}
    secrets = MagicMock()

    def exists(name: str) -> bool:
        return present[name]

    secrets.exists.side_effect = exists

    def interrupt_after_creation(name: str, _value: str) -> bool:
        present[name] = True
        raise KeyboardInterrupt

    secrets.ensure_present.side_effect = interrupt_after_creation
    systemd = MagicMock()
    observed_logger = MagicMock()
    monkeypatch.setattr(bind_module, "logger", observed_logger)
    use_case = _use_case(scribe=scribe, secrets=secrets, systemd=systemd)
    approved = use_case.plan(request)

    with pytest.raises(KeyboardInterrupt) as failure:
        use_case.apply(request, approved)

    assert present["lychd-core"]
    assert any("current core-secret operation is indeterminate" in note for note in failure.value.__notes__)
    partial = observed_logger.error.call_args
    assert partial.args == ("bind_apply_partial_failure",)
    assert partial.kwargs["phase"] == "core-secret"
    assert partial.kwargs["secret_reconciliation_indeterminate"] is True
    scribe.reconcile_all.assert_not_called()
    systemd.daemon_reload.assert_not_called()


def test_system_exit_after_binding_commit_preserves_committed_generation(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Terminal cancellation cannot erase the generation already on disk."""
    request = _request(required=())
    plan = BindingReconcilePlan(
        changes=(),
        observed_generation="bindings-a",
        desired_generation="desired-a",
    )
    scribe = MagicMock()
    scribe.plan_reconcile_all.return_value = plan
    scribe.reconcile_all.return_value = "bindings-after"
    secrets = MagicMock()
    secrets.exists.return_value = True
    systemd = MagicMock()
    systemd.daemon_reload.side_effect = SystemExit(130)
    observed_logger = MagicMock()
    monkeypatch.setattr(bind_module, "logger", observed_logger)
    use_case = _use_case(scribe=scribe, secrets=secrets, systemd=systemd)
    approved = use_case.plan(request)

    with pytest.raises(SystemExit) as failure:
        use_case.apply(request, approved)

    assert failure.value.code == 130
    assert any("binding generation committed: bindings-after" in note for note in failure.value.__notes__)
    partial = observed_logger.error.call_args
    assert partial.args == ("bind_apply_partial_failure",)
    assert partial.kwargs["phase"] == "systemd-reload"
    assert partial.kwargs["binding_generation"] == "bindings-after"
    scribe.reconcile_all.assert_called_once()


@pytest.mark.parametrize(
    ("signal_factory", "scribe_state", "progress_fact"),
    [
        (
            KeyboardInterrupt,
            ScribeTransactionState.ROLLED_BACK,
            "binding mutations rolled back cleanly",
        ),
        (
            lambda: SystemExit(130),
            ScribeTransactionState.INDETERMINATE,
            "binding commit state is indeterminate",
        ),
    ],
)
def test_scribe_wrapped_terminal_signal_keeps_native_cancellation_semantics(
    signal_factory: Callable[[], BaseException],
    scribe_state: ScribeTransactionState,
    progress_fact: str,
) -> None:
    """Scribe's classified rollback wrapper must not swallow Ctrl-C or exit."""
    request = _request(required=())
    plan = BindingReconcilePlan(
        changes=(),
        observed_generation="bindings-a",
        desired_generation="desired-a",
    )
    scribe = MagicMock()
    scribe.plan_reconcile_all.return_value = plan
    signal = signal_factory()

    def wrapped_interruption(*_args: object, **_kwargs: object) -> str:
        message = "commit interrupted"
        wrapped = ScribeTransactionError(message, state=scribe_state)
        wrapped.__cause__ = signal
        raise wrapped

    scribe.reconcile_all.side_effect = wrapped_interruption
    secrets = MagicMock()
    secrets.exists.return_value = True
    systemd = MagicMock()
    use_case = _use_case(scribe=scribe, secrets=secrets, systemd=systemd)
    approved = use_case.plan(request)

    with pytest.raises(type(signal)) as failure:
        use_case.apply(request, approved)

    assert failure.value is signal
    assert any(progress_fact in note for note in failure.value.__notes__)
    systemd.daemon_reload.assert_not_called()


@pytest.mark.parametrize("signal", [KeyboardInterrupt(), SystemExit(73)])
def test_nested_scribe_observation_terminal_keeps_native_cancellation_semantics(
    signal: BaseException,
) -> None:
    request = _request(required=())
    plan = BindingReconcilePlan(
        changes=(),
        observed_generation="bindings-a",
        desired_generation="desired-a",
    )
    scribe = MagicMock()
    scribe.plan_reconcile_all.return_value = plan
    nested = PathStateIndeterminateError(
        "observation interrupted",
        paths=frozenset({Path("/binding")}),
        cause=signal,
    )
    wrapped = ScribeTransactionError(
        "commit interrupted",
        state=ScribeTransactionState.INDETERMINATE,
        forward_error=nested,
    )
    wrapped.__cause__ = OSError("ordinary adapter wrapper")
    scribe.reconcile_all.side_effect = wrapped
    secrets = MagicMock()
    secrets.exists.return_value = True
    systemd = MagicMock()
    use_case = _use_case(scribe=scribe, secrets=secrets, systemd=systemd)
    approved = use_case.plan(request)

    with pytest.raises(type(signal)) as raised:
        use_case.apply(request, approved)

    assert raised.value is signal
    assert any("binding commit state is indeterminate" in note for note in signal.__notes__)
    systemd.daemon_reload.assert_not_called()


def test_scribe_cleanup_terminal_preserves_committed_generation_in_bind_progress() -> None:
    request = _request(required=())
    plan = BindingReconcilePlan(
        changes=(),
        observed_generation="bindings-a",
        desired_generation="desired-a",
    )
    scribe = MagicMock()
    scribe.plan_reconcile_all.return_value = plan
    terminal = KeyboardInterrupt()
    terminal.__cause__ = ScribeTransactionError(
        "cleanup interrupted",
        state=ScribeTransactionState.COMMITTED,
        generation="bindings-committed",
        cleanup_errors=(terminal,),
    )
    scribe.reconcile_all.side_effect = terminal
    secrets = MagicMock()
    secrets.exists.return_value = True
    systemd = MagicMock()
    use_case = _use_case(scribe=scribe, secrets=secrets, systemd=systemd)
    approved = use_case.plan(request)

    with pytest.raises(KeyboardInterrupt) as raised:
        use_case.apply(request, approved)

    assert raised.value is terminal
    assert any("binding generation committed: bindings-committed" in note for note in terminal.__notes__)
    systemd.daemon_reload.assert_not_called()


def test_apply_reports_post_secret_cas_drift_as_typed_progress() -> None:
    """CAS rejection after secret creation is no longer an effect-free drift."""
    request = _request(required=())
    plan = BindingReconcilePlan(
        changes=(),
        observed_generation="bindings-a",
        desired_generation="desired-a",
    )
    scribe = MagicMock()
    scribe.plan_reconcile_all.return_value = plan
    scribe.reconcile_all.side_effect = ScribeGenerationError("late drift")
    present = {"lychd-core": False}
    secrets = MagicMock()

    def exists(name: str) -> bool:
        return present[name]

    secrets.exists.side_effect = exists

    def ensure(name: str, _value: str) -> bool:
        present[name] = True
        return True

    secrets.ensure_present.side_effect = ensure
    systemd = MagicMock()
    use_case = _use_case(scribe=scribe, secrets=secrets, systemd=systemd)
    approved = use_case.plan(request)

    with pytest.raises(BindApplyError, match="changed during commit") as failure:
        use_case.apply(request, approved)

    assert failure.value.progress.created_secrets == ("lychd-core",)
    assert failure.value.progress.binding_commit_state is BindingCommitState.REJECTED
    assert failure.value.progress.binding_generation is None
    systemd.daemon_reload.assert_not_called()


@pytest.mark.parametrize(
    ("scribe_state", "binding_state", "message"),
    [
        (
            ScribeTransactionState.ROLLED_BACK,
            BindingCommitState.ROLLED_BACK,
            "rolled back",
        ),
        (
            ScribeTransactionState.INDETERMINATE,
            BindingCommitState.INDETERMINATE,
            "indeterminate",
        ),
    ],
)
def test_apply_preserves_scribe_failure_state_without_claiming_generation(
    scribe_state: ScribeTransactionState,
    binding_state: BindingCommitState,
    message: str,
) -> None:
    """Bind exposes Scribe's proof boundary rather than flattening failures."""
    request = _request(required=())
    plan = BindingReconcilePlan(
        changes=(),
        observed_generation="bindings-a",
        desired_generation="desired-a",
    )
    scribe = MagicMock()
    scribe.plan_reconcile_all.return_value = plan
    scribe.reconcile_all.side_effect = ScribeTransactionError(
        "commit failed",
        state=scribe_state,
    )
    secrets = MagicMock()
    secrets.exists.return_value = True
    systemd = MagicMock()
    use_case = _use_case(scribe=scribe, secrets=secrets, systemd=systemd)
    approved = use_case.plan(request)

    with pytest.raises(BindApplyError, match=message) as failure:
        use_case.apply(request, approved)

    assert failure.value.progress.binding_commit_state is binding_state
    assert failure.value.progress.binding_generation is None
    systemd.daemon_reload.assert_not_called()
