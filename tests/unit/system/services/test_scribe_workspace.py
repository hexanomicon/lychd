"""Compound-failure evidence for Scribe's descriptor-pinned workspaces."""

from __future__ import annotations

import os
import stat
from types import SimpleNamespace
from typing import TYPE_CHECKING

import pytest

from lychd.system.atomic_paths import rename_noreplace_at
from lychd.system.binding_sites import AttestedBindingSite, AttestedBindingSites
from lychd.system.descriptor_settlement import DescriptorSet, find_settlement_outcome
from lychd.system.interruptions import iter_exception_graph
from lychd.system.services.scribe.authority import BindingAuthority
from lychd.system.services.scribe.errors import (
    ScribeGenerationError,
    ScribeTransactionError,
    ScribeTransactionState,
)
from lychd.system.services.scribe.storage import PathStateIndeterminateError
from lychd.system.services.scribe.transaction import BindingTransaction
from lychd.system.services.scribe.workspace import (
    TransactionWorkspace,
    WorkspaceSettlementError,
)

if TYPE_CHECKING:
    from pathlib import Path


@pytest.mark.parametrize(
    "close_failure",
    [OSError("child close failed"), KeyboardInterrupt(), SystemExit(91)],
)
def test_create_settles_parent_and_child_after_attestation_failure(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    close_failure: BaseException,
) -> None:
    """An earlier child failure cannot skip either acquired descriptor close."""
    parent = tmp_path / "binding-site"
    parent.mkdir()
    primary = OSError("child attestation failed")
    real_close = os.close
    real_fstat = os.fstat
    fstat_calls = 0
    close_calls = 0

    def fail_child_attestation(descriptor: int) -> os.stat_result:
        nonlocal fstat_calls
        fstat_calls += 1
        if fstat_calls == 2:
            raise primary
        return real_fstat(descriptor)

    def close_then_fail(descriptor: int) -> None:
        nonlocal close_calls
        close_calls += 1
        real_close(descriptor)
        if close_calls == 1:
            raise close_failure

    monkeypatch.setattr(
        "lychd.system.services.scribe.workspace.os.fstat",
        fail_child_attestation,
    )
    monkeypatch.setattr(
        "lychd.system.descriptor_settlement.os.close",
        close_then_fail,
    )

    expected = WorkspaceSettlementError if isinstance(close_failure, Exception) else type(close_failure)
    with pytest.raises(expected) as raised:
        TransactionWorkspace.create(parent)

    graph = tuple(iter_exception_graph(raised.value))
    assert primary in graph
    assert close_failure in graph
    if isinstance(raised.value, WorkspaceSettlementError):
        assert raised.value.outcome == "workspace_retained"
        assert raised.value.outcome_verified
    else:
        assert raised.value is close_failure
    assert close_calls == 2
    assert len(tuple(parent.glob(".lychd-transaction-*"))) == 1


@pytest.mark.parametrize(
    "close_failure",
    [OSError("staged close failed"), KeyboardInterrupt(), SystemExit(93)],
)
def test_prepare_file_settles_close_and_exact_name_after_write_failure(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    close_failure: BaseException,
) -> None:
    """Staging rollback completes even when its descriptor close is a peer failure."""
    parent = tmp_path / "binding-site"
    parent.mkdir()
    workspace = TransactionWorkspace.create(parent)
    primary = OSError("staged chmod failed")
    real_close = os.close
    real_fstat = os.fstat
    injected = False

    def fail_chmod(_descriptor: int, _mode: int) -> None:
        raise primary

    def close_then_fail(descriptor: int) -> None:
        nonlocal injected
        is_regular = stat.S_ISREG(real_fstat(descriptor).st_mode)
        real_close(descriptor)
        if is_regular and not injected:
            injected = True
            raise close_failure

    monkeypatch.setattr(
        "lychd.system.services.scribe.workspace.os.fchmod",
        fail_chmod,
    )
    monkeypatch.setattr(
        "lychd.system.descriptor_settlement.os.close",
        close_then_fail,
    )

    expected = WorkspaceSettlementError if isinstance(close_failure, Exception) else type(close_failure)
    try:
        with pytest.raises(expected) as raised:
            workspace.prepare_file(
                b"prepared bytes",
                mode=0o600,
                prefix="new-",
            )

        graph = tuple(iter_exception_graph(raised.value))
        assert primary in graph
        assert close_failure in graph
        if isinstance(raised.value, WorkspaceSettlementError):
            assert raised.value.outcome == "rolled_back"
            assert raised.value.outcome_verified
        else:
            assert raised.value is close_failure
        assert injected
        assert workspace.owned_entries == {}
        assert tuple(workspace.path.iterdir()) == ()
    finally:
        workspace.close()


@pytest.mark.parametrize(
    "close_failure",
    [OSError("cleanup close failed"), KeyboardInterrupt(), SystemExit(95)],
)
def test_cleanup_settles_both_descriptors_after_exact_workspace_removal(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    close_failure: BaseException,
) -> None:
    """Final descriptor failures retain the already-proven removed outcome."""
    parent = tmp_path / "binding-site"
    parent.mkdir()
    workspace = TransactionWorkspace.create(parent)
    real_close = os.close
    close_calls = 0

    def close_then_fail(descriptor: int) -> None:
        nonlocal close_calls
        close_calls += 1
        real_close(descriptor)
        if close_calls == 1:
            raise close_failure

    monkeypatch.setattr(
        "lychd.system.descriptor_settlement.os.close",
        close_then_fail,
    )

    expected = WorkspaceSettlementError if isinstance(close_failure, Exception) else type(close_failure)
    with pytest.raises(expected) as raised:
        workspace.cleanup()

    assert close_failure in tuple(iter_exception_graph(raised.value))
    if not isinstance(close_failure, Exception):
        assert raised.value is close_failure
    settlement = find_settlement_outcome(raised.value)
    assert settlement is not None
    assert settlement.name == "removed"
    assert settlement.verified
    assert close_calls == 2
    assert not workspace.path.exists()
    assert workspace.parent_fd == -1
    assert workspace.directory_fd == -1


@pytest.mark.parametrize(
    "mkdir_failure",
    [OSError("mkdir return failed"), KeyboardInterrupt(), SystemExit(121)],
)
def test_workspace_mkdir_after_effect_retains_exact_unverified_path(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    mkdir_failure: BaseException,
) -> None:
    """A mkdir without a returned identity token cannot grant cleanup authority."""
    parent = tmp_path / "binding-site"
    parent.mkdir()
    real_mkdir = os.mkdir
    created_name = ""

    def create_then_raise(
        path: str | bytes | os.PathLike[str] | os.PathLike[bytes],
        mode: int = 0o777,
        *,
        dir_fd: int | None = None,
    ) -> None:
        nonlocal created_name
        real_mkdir(path, mode=mode, dir_fd=dir_fd)
        created_name = os.fsdecode(path)
        raise mkdir_failure

    monkeypatch.setattr(
        "lychd.system.services.scribe.workspace.os.mkdir",
        create_then_raise,
    )

    with pytest.raises(WorkspaceSettlementError) as raised:
        TransactionWorkspace.create(parent)

    recovery = parent / created_name
    assert mkdir_failure in tuple(iter_exception_graph(raised.value))
    assert raised.value.outcome == "recovery"
    assert not raised.value.outcome_verified
    assert raised.value.recovery_paths == (recovery,)
    assert recovery.is_dir()


@pytest.mark.parametrize(
    "open_failure",
    [OSError("open return failed"), KeyboardInterrupt(), SystemExit(123)],
)
def test_prepare_open_after_effect_retains_exact_unverified_child(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    open_failure: BaseException,
) -> None:
    """A create without a returned descriptor never adopts its pathname result."""
    parent = tmp_path / "binding-site"
    parent.mkdir()
    workspace = TransactionWorkspace.create(parent)
    real_open = os.open
    real_close = os.close
    created_name = ""

    def create_then_raise(
        path: str | bytes | os.PathLike[str] | os.PathLike[bytes],
        flags: int,
        mode: int = 0o777,
        *,
        dir_fd: int | None = None,
    ) -> int:
        nonlocal created_name
        if flags & os.O_CREAT and flags & os.O_EXCL:
            descriptor = real_open(path, flags, mode, dir_fd=dir_fd)
            real_close(descriptor)
            created_name = os.fsdecode(path)
            raise open_failure
        return real_open(path, flags, mode, dir_fd=dir_fd)

    monkeypatch.setattr(
        "lychd.system.services.scribe.workspace.os.open",
        create_then_raise,
    )

    try:
        with pytest.raises(WorkspaceSettlementError) as raised:
            workspace.prepare_file(
                b"prepared bytes",
                mode=0o600,
                prefix="new-",
            )

        recovery = workspace.path / created_name
        assert open_failure in tuple(iter_exception_graph(raised.value))
        assert raised.value.outcome == "recovery"
        assert not raised.value.outcome_verified
        assert raised.value.recovery_paths == (recovery,)
        assert recovery.is_file()
    finally:
        workspace.close()


@pytest.mark.parametrize("effect", ["complete", "none"])
@pytest.mark.parametrize(
    "rename_failure",
    [OSError("rename return failed"), KeyboardInterrupt(), SystemExit(125)],
)
def test_cleanup_rename_failure_classifies_both_workspace_names(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    effect: str,
    rename_failure: BaseException,
) -> None:
    """Workspace cleanup proves complete and no-effect rename outcomes."""
    parent = tmp_path / "binding-site"
    parent.mkdir()
    workspace = TransactionWorkspace.create(parent)
    real_rename = rename_noreplace_at

    def rename_then_raise(
        source_name: str,
        destination_name: str,
        *,
        source_dir_fd: int,
        destination_dir_fd: int,
    ) -> None:
        if effect == "complete":
            real_rename(
                source_name,
                destination_name,
                source_dir_fd=source_dir_fd,
                destination_dir_fd=destination_dir_fd,
            )
        raise rename_failure

    monkeypatch.setattr(
        "lychd.system.services.scribe.workspace_settlement.rename_noreplace_at",
        rename_then_raise,
    )

    expected = WorkspaceSettlementError if isinstance(rename_failure, Exception) else type(rename_failure)
    with pytest.raises(expected) as raised:
        workspace.cleanup()

    assert rename_failure in tuple(iter_exception_graph(raised.value))
    settlement = find_settlement_outcome(raised.value)
    assert settlement is not None
    if effect == "complete":
        assert settlement.name == "removed"
        assert settlement.verified
        assert not workspace.path.exists()
        assert tuple(parent.glob(".lychd-cleanup-*")) == ()
    else:
        assert settlement.name == "retained"
        assert settlement.verified
        assert workspace.path.is_dir()
        evidence = next(
            error for error in iter_exception_graph(raised.value) if isinstance(error, WorkspaceSettlementError)
        )
        assert workspace.path in evidence.recovery_paths


@pytest.mark.parametrize("indeterminate", [False, True])
@pytest.mark.parametrize(
    "fstat_failure",
    [OSError("fstat failed"), KeyboardInterrupt(), SystemExit(127)],
)
@pytest.mark.parametrize(
    "close_failure",
    [OSError("close failed"), KeyboardInterrupt(), SystemExit(129)],
)
def test_expected_site_attestation_settles_fstat_and_close_peers(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    indeterminate: bool,  # noqa: FBT001 - parametrized mode
    fstat_failure: BaseException,
    close_failure: BaseException,
) -> None:
    """Site attestation preserves its primary while settling every descriptor."""
    site = tmp_path / "binding-site"
    site.mkdir()
    metadata = site.stat()
    identity = AttestedBindingSite(
        path=site,
        device=metadata.st_dev,
        inode=metadata.st_ino,
    )
    transaction = BindingTransaction(
        BindingAuthority(site),
        expected_sites=AttestedBindingSites(
            quadlet=identity,
            systemd_user=identity,
        ),
    )
    real_fstat = os.fstat
    real_settle = DescriptorSet.settle
    failed = False

    def fail_first_fstat(descriptor: int) -> os.stat_result:
        nonlocal failed
        if not failed:
            failed = True
            raise fstat_failure
        return real_fstat(descriptor)

    def settle_then_fail(descriptors: DescriptorSet) -> tuple[BaseException, ...]:
        return (*real_settle(descriptors), close_failure)

    monkeypatch.setattr(
        "lychd.system.services.scribe.transaction.os.fstat",
        fail_first_fstat,
    )
    monkeypatch.setattr(
        "lychd.system.services.scribe.transaction.DescriptorSet.settle",
        settle_then_fail,
    )

    if indeterminate:
        expected: type[BaseException] = PathStateIndeterminateError
    elif not isinstance(fstat_failure, Exception):
        expected = type(fstat_failure)
    elif not isinstance(close_failure, Exception):
        expected = type(close_failure)
    else:
        expected = ScribeGenerationError
    require_sites = getattr(  # noqa: B009 - adversarial private boundary
        transaction,
        "_require_expected_sites_now",
    )
    with pytest.raises(expected) as raised:
        require_sites(indeterminate=indeterminate)

    graph = tuple(iter_exception_graph(raised.value))
    assert fstat_failure in graph
    assert close_failure in graph
    settlement = find_settlement_outcome(raised.value)
    assert settlement is not None
    assert settlement.name == ("indeterminate" if indeterminate else "unchanged")
    assert settlement.verified is not indeterminate


def test_cleanup_outcome_unions_operator_visible_recovery_paths(
    tmp_path: Path,
) -> None:
    """Outer Scribe evidence retains prior and workspace cleanup paths."""
    prior_path = tmp_path / "prior-recovery"
    cleanup_path = tmp_path / "cleanup-recovery"
    active = ScribeTransactionError(
        "active transaction failure",
        state=ScribeTransactionState.INDETERMINATE,
        recovery_paths=(prior_path,),
    )
    cleanup = WorkspaceSettlementError(
        "workspace cleanup failure",
        failures=(),
        outcome="recovery",
        verified=False,
        recovery_paths=(cleanup_path,),
    )
    classify = getattr(  # noqa: B009 - adversarial private boundary
        BindingTransaction,
        "_cleanup_outcome",
    )

    outcome = classify(
        active_error=active,
        committed_generation="",
        cleanup_errors=(cleanup,),
    )

    assert outcome is active
    assert outcome.cleanup_errors == (cleanup,)
    assert outcome.recovery_paths == (prior_path, cleanup_path)


@pytest.mark.parametrize("effect", ["complete", "none"])
@pytest.mark.parametrize(
    "rmdir_failure",
    [OSError("rmdir return failed"), KeyboardInterrupt(), SystemExit(131)],
)
def test_cleanup_rmdir_failure_classifies_exact_detached_name(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    effect: str,
    rmdir_failure: BaseException,
) -> None:
    """An exceptional rmdir is complete only when the detached inode is absent."""
    parent = tmp_path / "binding-site"
    parent.mkdir()
    workspace = TransactionWorkspace.create(parent)
    real_rmdir = os.rmdir

    def rmdir_then_raise(
        path: str | bytes | os.PathLike[str] | os.PathLike[bytes],
        *,
        dir_fd: int | None = None,
    ) -> None:
        if effect == "complete":
            real_rmdir(path, dir_fd=dir_fd)
        raise rmdir_failure

    monkeypatch.setattr(
        "lychd.system.services.scribe.workspace.os.rmdir",
        rmdir_then_raise,
    )

    expected = WorkspaceSettlementError if isinstance(rmdir_failure, Exception) else type(rmdir_failure)
    with pytest.raises(expected) as raised:
        workspace.cleanup()

    assert rmdir_failure in tuple(iter_exception_graph(raised.value))
    settlement = find_settlement_outcome(raised.value)
    assert settlement is not None
    if effect == "complete":
        assert settlement.name == "removed"
        assert settlement.verified
        assert tuple(parent.glob(".lychd-cleanup-*")) == ()
    else:
        recoveries = tuple(parent.glob(".lychd-cleanup-*"))
        assert len(recoveries) == 1
        assert settlement.name == "retained"
        assert settlement.verified
        evidence = next(
            error
            for error in iter_exception_graph(raised.value)
            if isinstance(error, WorkspaceSettlementError) and recoveries[0] in error.recovery_paths
        )
        assert evidence.outcome == "retained"


@pytest.mark.parametrize("effect", ["complete", "none"])
@pytest.mark.parametrize(
    "rename_failure",
    [OSError("entry rename failed"), KeyboardInterrupt(), SystemExit(133)],
)
def test_child_quarantine_failure_retains_verified_workspace_truth(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    effect: str,
    rename_failure: BaseException,
) -> None:
    """Child detachment classifies both names before root cleanup can proceed."""
    parent = tmp_path / "binding-site"
    parent.mkdir()
    workspace = TransactionWorkspace.create(parent)
    staged = workspace.prepare_file(b"owned", mode=0o600, prefix="new-")
    real_rename = rename_noreplace_at

    def rename_then_raise(
        source_name: str,
        destination_name: str,
        *,
        source_dir_fd: int,
        destination_dir_fd: int,
    ) -> None:
        if destination_name.startswith(".entry-cleanup-"):
            if effect == "complete":
                real_rename(
                    source_name,
                    destination_name,
                    source_dir_fd=source_dir_fd,
                    destination_dir_fd=destination_dir_fd,
                )
            raise rename_failure
        real_rename(
            source_name,
            destination_name,
            source_dir_fd=source_dir_fd,
            destination_dir_fd=destination_dir_fd,
        )

    monkeypatch.setattr(
        "lychd.system.services.scribe.workspace_settlement.rename_noreplace_at",
        rename_then_raise,
    )

    expected = WorkspaceSettlementError if isinstance(rename_failure, Exception) else type(rename_failure)
    with pytest.raises(expected) as raised:
        workspace.cleanup()

    assert rename_failure in tuple(iter_exception_graph(raised.value))
    settlement = find_settlement_outcome(raised.value)
    assert settlement is not None
    assert settlement.name == "retained"
    assert settlement.verified
    assert workspace.path.is_dir()
    if effect == "complete":
        assert not staged.path.display.exists()
        assert tuple(workspace.path.glob(".entry-cleanup-*")) == ()
        evidence = next(
            error
            for error in iter_exception_graph(raised.value)
            if isinstance(error, WorkspaceSettlementError) and error.outcome == "retained"
        )
        assert evidence.recovery_paths == (workspace.path,)
    else:
        assert staged.path.display.read_bytes() == b"owned"


@pytest.mark.parametrize("effect", ["complete", "none"])
@pytest.mark.parametrize(
    "unlink_failure",
    [OSError("entry unlink failed"), KeyboardInterrupt(), SystemExit(135)],
)
def test_child_unlink_failure_retains_exact_random_name_when_needed(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    effect: str,
    unlink_failure: BaseException,
) -> None:
    """Child unlink reports absence or the exact random recovery leaf."""
    parent = tmp_path / "binding-site"
    parent.mkdir()
    workspace = TransactionWorkspace.create(parent)
    workspace.prepare_file(b"owned", mode=0o600, prefix="new-")
    real_unlink = os.unlink

    def unlink_then_raise(
        path: str | bytes | os.PathLike[str] | os.PathLike[bytes],
        *,
        dir_fd: int | None = None,
    ) -> None:
        if os.fsdecode(path).startswith(".entry-cleanup-"):
            if effect == "complete":
                real_unlink(path, dir_fd=dir_fd)
            raise unlink_failure
        real_unlink(path, dir_fd=dir_fd)

    monkeypatch.setattr(
        "lychd.system.services.scribe.workspace.os.unlink",
        unlink_then_raise,
    )

    expected = (
        WorkspaceSettlementError if effect == "none" or isinstance(unlink_failure, Exception) else type(unlink_failure)
    )
    with pytest.raises(expected) as raised:
        workspace.cleanup()

    assert unlink_failure in tuple(iter_exception_graph(raised.value))
    recoveries = tuple(workspace.path.glob(".entry-cleanup-*"))
    if effect == "complete":
        assert recoveries == ()
    else:
        assert len(recoveries) == 1
        evidence = next(
            error
            for error in iter_exception_graph(raised.value)
            if isinstance(error, WorkspaceSettlementError) and recoveries[0] in error.recovery_paths
        )
        assert not evidence.outcome_verified


@pytest.mark.parametrize("effect", ["complete", "none"])
@pytest.mark.parametrize(
    "restore_failure",
    [OSError("root restore failed"), KeyboardInterrupt(), SystemExit(137)],
)
def test_foreign_workspace_restore_failure_requires_captured_target_identity(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    effect: str,
    restore_failure: BaseException,
) -> None:
    """Foreign root restoration surfaces no-effect and proves complete by inode."""
    parent = tmp_path / "binding-site"
    parent.mkdir()
    workspace = TransactionWorkspace.create(parent)
    relocated = workspace.path.with_name(f"{workspace.path.name}-relocated")
    workspace.path.rename(relocated)
    cleanup_name = ".lychd-cleanup-foreign"
    cleanup_path = parent / cleanup_name
    cleanup_path.mkdir()
    (cleanup_path / "marker").write_text("foreign", encoding="utf-8")
    real_rename = rename_noreplace_at

    def restore_then_raise(
        source_name: str,
        destination_name: str,
        *,
        source_dir_fd: int,
        destination_dir_fd: int,
    ) -> None:
        if effect == "complete":
            real_rename(
                source_name,
                destination_name,
                source_dir_fd=source_dir_fd,
                destination_dir_fd=destination_dir_fd,
            )
        raise restore_failure

    monkeypatch.setattr(
        "lychd.system.services.scribe.workspace_settlement.rename_noreplace_at",
        restore_then_raise,
    )
    restore = getattr(  # noqa: B009 - adversarial private boundary
        workspace,
        "_restore_foreign_cleanup_name",
    )
    expected = (
        WorkspaceSettlementError
        if effect == "none" or isinstance(restore_failure, Exception)
        else type(restore_failure)
    )
    try:
        with pytest.raises(expected) as raised:
            restore(cleanup_name)

        assert restore_failure in tuple(iter_exception_graph(raised.value))
        settlement = find_settlement_outcome(raised.value)
        assert settlement is not None
        if effect == "complete":
            assert settlement.name == "foreign_restored"
            assert settlement.verified
            assert (workspace.path / "marker").read_text(encoding="utf-8") == "foreign"
            assert not cleanup_path.exists()
        else:
            assert settlement.name == "recovery"
            assert not settlement.verified
            assert (cleanup_path / "marker").read_text(encoding="utf-8") == "foreign"
    finally:
        workspace.close()


@pytest.mark.parametrize("effect", ["complete", "none"])
@pytest.mark.parametrize(
    "restore_failure",
    [OSError("child restore failed"), KeyboardInterrupt(), SystemExit(139)],
)
def test_foreign_child_restore_failure_requires_captured_target_identity(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    effect: str,
    restore_failure: BaseException,
) -> None:
    """Foreign child restoration never infers completion from source absence."""
    parent = tmp_path / "binding-site"
    parent.mkdir()
    workspace = TransactionWorkspace.create(parent)
    cleanup_name = ".entry-cleanup-foreign"
    original_name = "original"
    cleanup_path = workspace.path / cleanup_name
    cleanup_path.write_bytes(b"foreign")
    workspace.recovery_names.add(cleanup_name)
    real_rename = rename_noreplace_at

    def restore_then_raise(
        source_name: str,
        destination_name: str,
        *,
        source_dir_fd: int,
        destination_dir_fd: int,
    ) -> None:
        if effect == "complete":
            real_rename(
                source_name,
                destination_name,
                source_dir_fd=source_dir_fd,
                destination_dir_fd=destination_dir_fd,
            )
        raise restore_failure

    monkeypatch.setattr(
        "lychd.system.services.scribe.workspace_settlement.rename_noreplace_at",
        restore_then_raise,
    )
    restore = getattr(  # noqa: B009 - adversarial private boundary
        workspace,
        "_restore_foreign_entry",
    )
    expected = (
        WorkspaceSettlementError
        if effect == "none" or isinstance(restore_failure, Exception)
        else type(restore_failure)
    )
    try:
        with pytest.raises(expected) as raised:
            restore(cleanup_name, original_name)

        assert restore_failure in tuple(iter_exception_graph(raised.value))
        settlement = find_settlement_outcome(raised.value)
        assert settlement is not None
        if effect == "complete":
            assert settlement.name == "foreign_restored"
            assert settlement.verified
            assert (workspace.path / original_name).read_bytes() == b"foreign"
            assert not cleanup_path.exists()
        else:
            assert settlement.name == "recovery"
            assert not settlement.verified
            assert cleanup_path.read_bytes() == b"foreign"
    finally:
        workspace.close()


def test_multi_workspace_disposal_unions_exact_recovery_paths(
    tmp_path: Path,
) -> None:
    """Scribe exposes every retained workspace and foreign child together."""
    workspaces: dict[Path, TransactionWorkspace] = {}
    expected_paths: list[Path] = []
    for index in range(2):
        parent = tmp_path / f"binding-site-{index}"
        parent.mkdir()
        workspace = TransactionWorkspace.create(parent)
        child = workspace.path / "foreign-child"
        child.write_bytes(b"foreign")
        workspaces[parent] = workspace
        expected_paths.extend((workspace.path, child))
    prepared = SimpleNamespace(workspaces=workspaces)
    dispose = getattr(  # noqa: B009 - adversarial private boundary
        BindingTransaction,
        "_dispose_workspaces",
    )
    classify = getattr(  # noqa: B009 - adversarial private boundary
        BindingTransaction,
        "_cleanup_outcome",
    )

    cleanup_errors = dispose(prepared, retain=False)
    outcome = classify(
        active_error=None,
        committed_generation="committed-generation",
        cleanup_errors=cleanup_errors,
    )

    assert len(cleanup_errors) == 2
    assert outcome.state is ScribeTransactionState.COMMITTED
    assert outcome.generation == "committed-generation"
    assert outcome.recovery_paths == tuple(expected_paths)


def test_workspace_restore_source_disappearance_does_not_prove_target_identity(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """An unrelated public directory cannot satisfy foreign restore settlement."""
    parent = tmp_path / "binding-site"
    parent.mkdir()
    workspace = TransactionWorkspace.create(parent)
    workspace.path.rename(workspace.path.with_name("relocated-workspace"))
    cleanup_name = ".lychd-cleanup-foreign"
    cleanup_path = parent / cleanup_name
    cleanup_path.mkdir()
    primary = OSError("restore returned failure")

    def lose_source_and_create_unrelated(
        source_name: str,
        destination_name: str,
        *,
        source_dir_fd: int,
        destination_dir_fd: int,
    ) -> None:
        os.rmdir(source_name, dir_fd=source_dir_fd)
        os.mkdir(destination_name, dir_fd=destination_dir_fd)
        raise primary

    monkeypatch.setattr(
        "lychd.system.services.scribe.workspace_settlement.rename_noreplace_at",
        lose_source_and_create_unrelated,
    )
    restore = getattr(  # noqa: B009 - adversarial private boundary
        workspace,
        "_restore_foreign_cleanup_name",
    )
    try:
        with pytest.raises(WorkspaceSettlementError) as raised:
            restore(cleanup_name)

        assert primary in tuple(iter_exception_graph(raised.value))
        assert raised.value.outcome == "recovery"
        assert not raised.value.outcome_verified
        assert workspace.path in raised.value.recovery_paths
        assert workspace.path.is_dir()
        assert not cleanup_path.exists()
    finally:
        workspace.close()


def test_child_restore_source_disappearance_does_not_prove_target_identity(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """An unrelated target file cannot satisfy foreign child restoration."""
    parent = tmp_path / "binding-site"
    parent.mkdir()
    workspace = TransactionWorkspace.create(parent)
    cleanup_name = ".entry-cleanup-foreign"
    original_name = "original"
    cleanup_path = workspace.path / cleanup_name
    cleanup_path.write_bytes(b"foreign")
    primary = OSError("restore returned failure")

    def lose_source_and_create_unrelated(
        source_name: str,
        destination_name: str,
        *,
        source_dir_fd: int,
        destination_dir_fd: int,
    ) -> None:
        os.unlink(source_name, dir_fd=source_dir_fd)
        descriptor = os.open(
            destination_name,
            os.O_WRONLY | os.O_CREAT | os.O_EXCL,
            0o600,
            dir_fd=destination_dir_fd,
        )
        try:
            os.write(descriptor, b"unrelated")
        finally:
            os.close(descriptor)
        raise primary

    monkeypatch.setattr(
        "lychd.system.services.scribe.workspace_settlement.rename_noreplace_at",
        lose_source_and_create_unrelated,
    )
    restore = getattr(  # noqa: B009 - adversarial private boundary
        workspace,
        "_restore_foreign_entry",
    )
    try:
        with pytest.raises(WorkspaceSettlementError) as raised:
            restore(cleanup_name, original_name)

        assert primary in tuple(iter_exception_graph(raised.value))
        assert raised.value.outcome == "recovery"
        assert not raised.value.outcome_verified
        assert workspace.path / original_name in raised.value.recovery_paths
        assert (workspace.path / original_name).read_bytes() == b"unrelated"
        assert not cleanup_path.exists()
    finally:
        workspace.close()


@pytest.mark.parametrize(
    "unlink_failure",
    [OSError("unlink return failed"), KeyboardInterrupt(), SystemExit(141)],
)
def test_prepare_failure_with_verified_child_removal_is_exact_rollback(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    unlink_failure: BaseException,
) -> None:
    """A child cleanup peer cannot turn proven staging rollback into recovery."""
    parent = tmp_path / "binding-site"
    parent.mkdir()
    workspace = TransactionWorkspace.create(parent)
    primary = OSError("staged chmod failed")
    real_unlink = os.unlink

    def fail_chmod(_descriptor: int, _mode: int) -> None:
        raise primary

    def unlink_then_raise(
        path: str | bytes | os.PathLike[str] | os.PathLike[bytes],
        *,
        dir_fd: int | None = None,
    ) -> None:
        real_unlink(path, dir_fd=dir_fd)
        if os.fsdecode(path).startswith(".entry-cleanup-"):
            raise unlink_failure

    monkeypatch.setattr(
        "lychd.system.services.scribe.workspace.os.fchmod",
        fail_chmod,
    )
    monkeypatch.setattr(
        "lychd.system.services.scribe.workspace.os.unlink",
        unlink_then_raise,
    )

    expected = WorkspaceSettlementError if isinstance(unlink_failure, Exception) else type(unlink_failure)
    try:
        with pytest.raises(expected) as raised:
            workspace.prepare_file(
                b"prepared bytes",
                mode=0o600,
                prefix="new-",
            )

        graph = tuple(iter_exception_graph(raised.value))
        assert primary in graph
        assert unlink_failure in graph
        settlement = find_settlement_outcome(raised.value)
        assert settlement is not None
        assert settlement.name == "rolled_back"
        assert settlement.verified
        evidence = next(
            error for error in graph if isinstance(error, WorkspaceSettlementError) and error.outcome == "rolled_back"
        )
        assert evidence.recovery_paths == ()
        assert workspace.owned_entries == {}
        assert tuple(workspace.path.iterdir()) == ()
    finally:
        workspace.close()


def test_cleanup_recovery_unions_relocated_root_with_foreign_cleanup_leaf(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Rmdir drift retains both the exact pinned root and collided random leaf."""
    parent = tmp_path / "binding-site"
    parent.mkdir()
    workspace = TransactionWorkspace.create(parent)
    primary = OSError("rmdir returned failure")
    real_rename = rename_noreplace_at
    relocated = parent / ".lychd-relocated-exact-workspace"

    def relocate_then_replace(
        path: str | bytes | os.PathLike[str] | os.PathLike[bytes],
        *,
        dir_fd: int | None = None,
    ) -> None:
        cleanup_name = os.fsdecode(path)
        if dir_fd is None:
            raise AssertionError
        real_rename(
            cleanup_name,
            relocated.name,
            source_dir_fd=dir_fd,
            destination_dir_fd=dir_fd,
        )
        os.mkdir(cleanup_name, dir_fd=dir_fd)
        raise primary

    monkeypatch.setattr(
        "lychd.system.services.scribe.workspace.os.rmdir",
        relocate_then_replace,
    )

    with pytest.raises(WorkspaceSettlementError) as raised:
        workspace.cleanup()

    cleanup_paths = tuple(parent.glob(".lychd-cleanup-*"))
    assert len(cleanup_paths) == 1
    assert primary in tuple(iter_exception_graph(raised.value))
    assert raised.value.outcome == "recovery"
    assert not raised.value.outcome_verified
    assert relocated in raised.value.recovery_paths
    assert cleanup_paths[0] in raised.value.recovery_paths
    assert relocated.is_dir()
    assert cleanup_paths[0].is_dir()
    assert workspace.parent_fd == -1
    assert workspace.directory_fd == -1


@pytest.mark.parametrize(
    "observation_failure",
    [OSError("recovery observation failed"), KeyboardInterrupt(), SystemExit(143)],
)
@pytest.mark.parametrize(
    "close_failure",
    [OSError("descriptor close failed"), KeyboardInterrupt(), SystemExit(145)],
)
def test_close_observation_failure_cannot_skip_descriptor_settlement(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    observation_failure: BaseException,
    close_failure: BaseException,
) -> None:
    """Recovery observation is a peer after descriptor ownership is captured."""
    parent = tmp_path / "binding-site"
    parent.mkdir()
    workspace = TransactionWorkspace.create(parent)
    real_close = os.close
    close_calls = 0

    def fail_recovery_observation(
        _workspace: TransactionWorkspace,
        _active_name: str,
        *,
        parent_fd: int | None = None,
        directory_fd: int | None = None,
    ) -> tuple[Path, ...]:
        del parent_fd, directory_fd
        raise observation_failure

    def close_then_fail(descriptor: int) -> None:
        nonlocal close_calls
        close_calls += 1
        real_close(descriptor)
        if close_calls == 1:
            raise close_failure

    monkeypatch.setattr(
        TransactionWorkspace,
        "_retained_paths",
        fail_recovery_observation,
    )
    monkeypatch.setattr(
        "lychd.system.descriptor_settlement.os.close",
        close_then_fail,
    )

    if not isinstance(observation_failure, Exception):
        expected: type[BaseException] = type(observation_failure)
    elif not isinstance(close_failure, Exception):
        expected = type(close_failure)
    else:
        expected = WorkspaceSettlementError
    with pytest.raises(expected) as raised:
        workspace.close()

    graph = tuple(iter_exception_graph(raised.value))
    assert observation_failure in graph
    assert close_failure in graph
    settlement = find_settlement_outcome(raised.value)
    assert settlement is not None
    assert settlement.name == "ownership_released"
    assert settlement.verified
    assert close_calls == 2
    assert workspace.parent_fd == -1
    assert workspace.directory_fd == -1


@pytest.mark.parametrize(
    "observation_failure",
    [OSError("cleanup observation failed"), KeyboardInterrupt(), SystemExit(149)],
)
@pytest.mark.parametrize(
    "close_failure",
    [OSError("cleanup close failed"), KeyboardInterrupt(), SystemExit(151)],
)
def test_cleanup_secondary_observation_failure_still_settles_both_descriptors(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    observation_failure: BaseException,
    close_failure: BaseException,
) -> None:
    """A recovery-observation peer cannot escape cleanup before final close."""
    parent = tmp_path / "binding-site"
    parent.mkdir()
    workspace = TransactionWorkspace.create(parent)
    primary = OSError("entry enumeration failed")
    real_close = os.close
    close_calls = 0

    def fail_entry_cleanup(_workspace: TransactionWorkspace) -> bool:
        raise primary

    def fail_recovery_observation(
        _workspace: TransactionWorkspace,
        _active_name: str,
        *,
        parent_fd: int | None = None,
        directory_fd: int | None = None,
    ) -> tuple[Path, ...]:
        del parent_fd, directory_fd
        raise observation_failure

    def close_then_fail(descriptor: int) -> None:
        nonlocal close_calls
        close_calls += 1
        real_close(descriptor)
        if close_calls == 1:
            raise close_failure

    monkeypatch.setattr(
        TransactionWorkspace,
        "_unlink_pinned_entries",
        fail_entry_cleanup,
    )
    monkeypatch.setattr(
        TransactionWorkspace,
        "_retained_paths",
        fail_recovery_observation,
    )
    monkeypatch.setattr(
        "lychd.system.descriptor_settlement.os.close",
        close_then_fail,
    )

    with pytest.raises(WorkspaceSettlementError) as raised:
        workspace.cleanup()

    graph = tuple(iter_exception_graph(raised.value))
    assert primary in graph
    assert observation_failure in graph
    assert close_failure in graph
    assert raised.value.outcome == "recovery"
    assert not raised.value.outcome_verified
    assert close_calls == 2
    assert workspace.parent_fd == -1
    assert workspace.directory_fd == -1


@pytest.mark.parametrize(
    "observation_type",
    [OSError, KeyboardInterrupt, SystemExit],
)
@pytest.mark.parametrize(
    "fallback_type",
    [OSError, KeyboardInterrupt, SystemExit],
)
def test_close_compound_recovery_observation_failure_closes_real_fds(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    observation_type: type[BaseException],
    fallback_type: type[BaseException],
) -> None:
    """Even both failed recovery observations cannot escape before real close."""
    parent = tmp_path / "binding-site"
    parent.mkdir()
    workspace = TransactionWorkspace.create(parent)
    parent_fd = workspace.parent_fd
    directory_fd = workspace.directory_fd
    observation_failure = observation_type("primary recovery observation failed")
    fallback_failure = fallback_type("fallback recovery observation failed")

    def fail_recovery_observation(
        _workspace: TransactionWorkspace,
        _active_name: str,
        *,
        parent_fd: int | None = None,
        directory_fd: int | None = None,
    ) -> tuple[Path, ...]:
        del parent_fd, directory_fd
        raise observation_failure

    def fail_fallback_observation(
        _workspace: TransactionWorkspace,
        *,
        descriptor: int | None = None,
    ) -> Path:
        del descriptor
        raise fallback_failure

    monkeypatch.setattr(
        TransactionWorkspace,
        "_retained_paths",
        fail_recovery_observation,
    )
    monkeypatch.setattr(
        TransactionWorkspace,
        "recovery_path",
        fail_fallback_observation,
    )

    if not isinstance(observation_failure, Exception):
        expected: type[BaseException] = type(observation_failure)
    elif not isinstance(fallback_failure, Exception):
        expected = type(fallback_failure)
    else:
        expected = WorkspaceSettlementError
    with pytest.raises(expected) as raised:
        workspace.close()

    graph = tuple(iter_exception_graph(raised.value))
    assert observation_failure in graph
    assert fallback_failure in graph
    evidence = next(
        error
        for error in graph
        if isinstance(error, WorkspaceSettlementError) and error.outcome == "ownership_released"
    )
    assert evidence.outcome_verified
    assert workspace.path in evidence.recovery_paths
    assert workspace.parent_fd == -1
    assert workspace.directory_fd == -1
    with pytest.raises(OSError, match="Bad file descriptor"):
        os.fstat(parent_fd)
    with pytest.raises(OSError, match="Bad file descriptor"):
        os.fstat(directory_fd)


@pytest.mark.parametrize(
    "observation_type",
    [OSError, KeyboardInterrupt, SystemExit],
)
@pytest.mark.parametrize(
    "fallback_type",
    [OSError, KeyboardInterrupt, SystemExit],
)
def test_cleanup_compound_recovery_observation_failure_always_reaches_close(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    observation_type: type[BaseException],
    fallback_type: type[BaseException],
) -> None:
    """Cleanup preserves both observation peers and closes both real fds."""
    parent = tmp_path / "binding-site"
    parent.mkdir()
    workspace = TransactionWorkspace.create(parent)
    parent_fd = workspace.parent_fd
    directory_fd = workspace.directory_fd
    primary = OSError("entry cleanup failed")
    observation_failure = observation_type("primary recovery observation failed")
    fallback_failure = fallback_type("fallback recovery observation failed")

    def fail_entry_cleanup(_workspace: TransactionWorkspace) -> bool:
        raise primary

    def fail_recovery_observation(
        _workspace: TransactionWorkspace,
        _active_name: str,
        *,
        parent_fd: int | None = None,
        directory_fd: int | None = None,
    ) -> tuple[Path, ...]:
        del parent_fd, directory_fd
        raise observation_failure

    def fail_fallback_observation(
        _workspace: TransactionWorkspace,
        *,
        descriptor: int | None = None,
    ) -> Path:
        del descriptor
        raise fallback_failure

    monkeypatch.setattr(
        TransactionWorkspace,
        "_unlink_pinned_entries",
        fail_entry_cleanup,
    )
    monkeypatch.setattr(
        TransactionWorkspace,
        "_retained_paths",
        fail_recovery_observation,
    )
    monkeypatch.setattr(
        TransactionWorkspace,
        "recovery_path",
        fail_fallback_observation,
    )

    with pytest.raises(WorkspaceSettlementError) as raised:
        workspace.cleanup()

    graph = tuple(iter_exception_graph(raised.value))
    assert primary in graph
    assert observation_failure in graph
    assert fallback_failure in graph
    assert raised.value.outcome == "recovery"
    assert not raised.value.outcome_verified
    assert workspace.path in raised.value.recovery_paths
    assert workspace.parent_fd == -1
    assert workspace.directory_fd == -1
    with pytest.raises(OSError, match="Bad file descriptor"):
        os.fstat(parent_fd)
    with pytest.raises(OSError, match="Bad file descriptor"):
        os.fstat(directory_fd)
