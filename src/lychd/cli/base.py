"""Shared helpers for CLI commands."""

from __future__ import annotations

from collections.abc import Callable
from functools import wraps
from typing import TYPE_CHECKING

import click

if TYPE_CHECKING:
    from rich.console import Console


def get_console() -> Console:
    """Return a Rich console via lazy import.

    Why this exists:
    - Importing `rich` at module import time makes plain CLI bootstrap heavier.
    - Lazy import keeps `--help` and command discovery fast.
    """
    from rich.console import Console

    return Console()


def ritual_command(
    *, name: str, help_text: str, start_message: str
) -> Callable[[Callable[..., object]], click.Command]:
    """Build a Click command wrapper with shared UX and error policy.

    Chain this decorator enforces for every command:
    1. Print a consistent "ritual start" message.
    2. Execute the real command callback.
    3. If anything fails, render a consistent Rich error and convert to `click.Abort`.

    """

    def decorator[**P, R](func: Callable[P, R]) -> click.Command:
        # `**P` (inside `[]`) declares a type-level parameter pack (PEP 695), not runtime kwargs unpacking.
        # `Callable[P, R]` then uses that pack as "all params of func", while `R` is the return type.
        # More: https://docs.python.org/3/library/typing.html#typing.ParamSpec

        @click.command(name=name, help=help_text)
        @wraps(func)
        def wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
            # Lazy creation keeps command registration/help path lightweight.
            console = get_console()
            console.print(start_message)

            try:
                # Forward the same args/kwargs we received to the original callback.
                return func(*args, **kwargs)
            except Exception as e:
                # Normalize failures into one CLI-style abort path with readable output.
                console.print(f"\n[bold red]✖ Ritual Failed:[/][red] {e}[/]")
                raise click.Abort from e

        return wrapper

    return decorator
