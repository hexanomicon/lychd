from __future__ import annotations

from io import StringIO

from rich.console import Console

from lychd.cli import lifecycle_view
from lychd.cli.lifecycle_view import render_lifecycle_plan
from lychd.system.constants import (
    PATH_CODEX_ROOT,
    PATH_POSTGRESS_DATA_DIR,
    PATH_SYSTEMD_CONFIG_DIR,
    PATH_SYSTEMD_UNITS_DIR,
    PATH_SYSTEMD_USER_UNITS_DIR,
)
from lychd.system.services.lifecycle import (
    LifecycleAction,
    LifecycleDisposition,
    LifecyclePlan,
    LifecycleResourceKind,
)


def _render(plan: LifecyclePlan, *, verbose: bool = False) -> str:
    stream = StringIO()
    console = Console(file=stream, color_system=None, width=120)
    render_lifecycle_plan(plan=plan, console=console, verbose=verbose)
    return stream.getvalue()


def test_plan_uses_domain_and_path_trees_without_repetitive_reasons() -> None:
    root = PATH_CODEX_ROOT
    plan = LifecyclePlan(
        actions=(
            LifecycleAction(
                LifecycleDisposition.WOULD_CREATE,
                LifecycleResourceKind.DIRECTORY,
                str(root),
                "managed directory is absent",
            ),
            LifecycleAction(
                LifecycleDisposition.WOULD_CREATE,
                LifecycleResourceKind.FILE,
                str(root / "lychd.toml"),
                "generated file is absent with mode 0600",
            ),
            LifecycleAction(
                LifecycleDisposition.WOULD_CREATE,
                LifecycleResourceKind.DIRECTORY,
                str(root / "runes"),
                "managed directory is absent",
            ),
        )
    )

    output = _render(plan)
    verbose = _render(plan, verbose=True)

    assert "CODEX — ~/.config" in output
    assert "Shared XDG root for the Codex and Binding." not in output
    assert "Create 3" not in output
    assert "└── lychd" in output
    assert "LychD settings and typed Runes." not in output
    assert "Primary settings loaded before Rune documents." not in output
    assert "mode 0600" in output
    assert "managed directory is absent" not in output
    assert "WOULD CREATE" not in output
    assert "CODEX — ~/.config · Shared XDG root for the Codex and Binding." in verbose
    assert "└── lychd — LychD settings and typed Runes." in verbose
    assert "├── lychd.toml — Primary settings loaded before Rune documents." in verbose


def test_verbose_plan_adds_shared_anchors_without_generic_planner_reasons() -> None:
    plan = LifecyclePlan(
        actions=(
            LifecycleAction(
                LifecycleDisposition.PRESERVE,
                LifecycleResourceKind.DIRECTORY,
                str(PATH_SYSTEMD_CONFIG_DIR),
                "safe directory already exists",
            ),
            LifecycleAction(
                LifecycleDisposition.PRESERVE,
                LifecycleResourceKind.DIRECTORY,
                str(PATH_SYSTEMD_USER_UNITS_DIR),
                "safe directory already exists",
            ),
        )
    )

    compact = _render(plan)
    verbose = _render(plan, verbose=True)

    assert "systemd/user" in compact
    assert "Shared plain user-unit site" not in compact
    assert "Shared systemd user-configuration root" not in compact
    assert "systemd — Shared systemd user-configuration root" in verbose
    assert "└── user — Shared plain user-unit site" in verbose
    assert "present" in compact
    assert "safe directory already exists" not in verbose
    assert "SHARED 1 present" in compact
    assert "SHARED 2 present" in verbose


def test_external_mount_and_blocker_details_remain_visible_by_default() -> None:
    blocked = PATH_CODEX_ROOT / "unsafe"
    plan = LifecyclePlan(
        actions=(
            LifecycleAction(
                LifecycleDisposition.PRESERVE,
                LifecycleResourceKind.MOUNT,
                str(PATH_POSTGRESS_DATA_DIR),
                "pre-existing mount is outside initialization ownership",
            ),
            LifecycleAction(
                LifecycleDisposition.BLOCKED,
                LifecycleResourceKind.DIRECTORY,
                str(blocked),
                "symlink component is not trusted: /tmp/link",
            ),
        )
    )

    output = _render(plan)
    verbose = _render(plan, verbose=True)
    flattened = " ".join(output.split())

    assert "Live PostgreSQL data within the Phylactery" not in output
    assert "Live PostgreSQL data within the Phylactery" in verbose
    assert "external mount kept" in flattened
    assert "symlink component is not trusted: /tmp/link" in output
    assert "1 external mount" in output
    assert "1 blocked" in output


def test_path_color_implicitly_encodes_disposition() -> None:
    target = PATH_CODEX_ROOT / "lychd.toml"
    created = LifecycleAction(
        LifecycleDisposition.WOULD_CREATE,
        LifecycleResourceKind.FILE,
        str(target),
        "generated file is absent with mode 0600",
    )

    created_label = lifecycle_view._path_label(  # pyright: ignore[reportPrivateUsage]
        ["lychd.toml"],
        actions=(created,),
        path_descriptions={target: "Primary operator settings."},
    )
    styled_segments = [(created_label.plain[span.start : span.end], str(span.style)) for span in created_label.spans]

    assert styled_segments == [
        ("lychd.toml", "bold cyan"),
        (" — ", "dim"),
        ("Primary operator settings.", "white"),
        (" · ", "dim"),
        ("mode 0600", "dim"),
    ]

    existing = LifecycleAction(
        LifecycleDisposition.PRESERVE,
        LifecycleResourceKind.FILE,
        str(target),
        "generated file already matches",
    )
    existing_label = lifecycle_view._path_label(  # pyright: ignore[reportPrivateUsage]
        ["lychd.toml"],
        actions=(existing,),
        path_descriptions={target: "Primary operator settings."},
    )

    assert [(existing_label.plain[span.start : span.end], str(span.style)) for span in existing_label.spans] == [
        ("lychd.toml", "bold green"),
        (" — ", "dim"),
        ("Primary operator settings.", "white"),
    ]


def test_shared_anchor_color_is_distinct_from_its_lifecycle_state() -> None:
    created = LifecycleAction(
        LifecycleDisposition.WOULD_CREATE,
        LifecycleResourceKind.DIRECTORY,
        str(PATH_SYSTEMD_UNITS_DIR),
        "managed directory is absent",
    )

    label = lifecycle_view._path_label(  # pyright: ignore[reportPrivateUsage]
        ["containers", "systemd"],
        actions=(created,),
        path_descriptions={PATH_SYSTEMD_UNITS_DIR: "Shared Podman Quadlet directory."},
        shared_anchor=True,
    )
    styled_segments = [(label.plain[span.start : span.end], str(span.style)) for span in label.spans]

    assert styled_segments == [
        ("containers/systemd", "bold bright_blue"),
        (" — ", "dim"),
        ("Shared Podman Quadlet directory.", "white"),
        (" · ", "dim"),
        ("will create", "cyan"),
    ]
