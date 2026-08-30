from __future__ import annotations

from contextlib import contextmanager
from dataclasses import dataclass
from types import MappingProxyType
from typing import TYPE_CHECKING, Any, Protocol, cast

from lychd.config.runes.extension import RuneConfigStore
from lychd.domain.animation.extension import PortalStore, SoulstoneStore
from lychd.domain.animation.transmute import TransmutationStore
from lychd.extensions.delegation import DelegatedRuntimeStore

if TYPE_CHECKING:
    from collections.abc import Callable, Iterator, Mapping

    from lychd.config.runes.base import RuneConfig
    from lychd.domain.animation.services.adapters.contracts import PortalDefinition, SoulstoneDefinition
    from lychd.domain.animation.transmute import QuadletContributor
    from lychd.extensions.delegation import DelegatedRuntimeDefinition


class RuneRegistrationStore(Protocol):
    """Extension-visible Rune contribution surface."""

    def add_schema(self, schema: type[RuneConfig]) -> None: ...


class SoulstoneRegistrationStore(Protocol):
    """Extension-visible Soulstone contribution surface."""

    def add(self, definition: SoulstoneDefinition) -> None: ...


class PortalRegistrationStore(Protocol):
    """Extension-visible Portal contribution surface."""

    def add(self, definition: PortalDefinition) -> None: ...


class TransmutationRegistrationStore(Protocol):
    """Extension-visible Quadlet contribution surface."""

    def add_contributor(self, contributor: QuadletContributor) -> None: ...


class DelegatedRuntimeRegistrationStore(Protocol):
    """Extension-visible delegated-runtime contribution surface."""

    def add(self, definition: DelegatedRuntimeDefinition) -> None: ...


@dataclass(frozen=True, slots=True)
class _ContributionStoreView:
    """Expose only provider-bound contribution callables named by the host."""

    _calls: Mapping[str, Callable[..., Any]]

    def __getattr__(self, name: str) -> Any:
        try:
            return self._calls[name]
        except KeyError:
            raise AttributeError(name) from None


@dataclass(frozen=True, slots=True, init=False)
class ExtensionRegistrationContext:
    """Provider-bound shaped surface passed to one extension's ``register`` shim."""

    runes: RuneRegistrationStore
    soulstones: SoulstoneRegistrationStore
    portals: PortalRegistrationStore
    transmutation: TransmutationRegistrationStore
    delegated_runtimes: DelegatedRuntimeRegistrationStore

    def __init__(self, root: ExtensionContext, provider_id: str) -> None:
        """Bind every shaped contribution store to ``provider_id``."""

        def attributed(method: Callable[..., Any]) -> Callable[..., Any]:
            def invoke(*args: Any, **kwargs: Any) -> Any:
                with root.provenance(provider_id):
                    return method(*args, **kwargs)

            return invoke

        def bound(store: Any, *methods: str) -> _ContributionStoreView:
            calls = {name: attributed(cast("Callable[..., Any]", getattr(store, name))) for name in methods}
            return _ContributionStoreView(_calls=MappingProxyType(calls))

        object.__setattr__(self, "runes", cast("RuneRegistrationStore", bound(root.runes, "add_schema")))
        object.__setattr__(
            self,
            "soulstones",
            cast("SoulstoneRegistrationStore", bound(root.soulstones, "add")),
        )
        object.__setattr__(self, "portals", cast("PortalRegistrationStore", bound(root.portals, "add")))
        object.__setattr__(
            self,
            "transmutation",
            cast("TransmutationRegistrationStore", bound(root.transmutation, "add_contributor")),
        )
        object.__setattr__(
            self,
            "delegated_runtimes",
            cast("DelegatedRuntimeRegistrationStore", bound(root.delegated_runtimes, "add")),
        )


class ExtensionContext:
    """Host-provided root of explicit extension registration stores."""

    def __init__(self) -> None:
        """Create the extension registration stores for one assembly pass."""
        self._current_extension_id: str | None = None

        def current_provider() -> str:
            return self._current_extension_id or "direct"

        self.runes = RuneConfigStore(current_provider=current_provider)
        self.soulstones = SoulstoneStore(self.runes, current_provider=current_provider)
        self.portals = PortalStore(self.runes, current_provider=current_provider)
        self.transmutation = TransmutationStore(current_provider=current_provider)
        self.delegated_runtimes = DelegatedRuntimeStore(
            current_provider=lambda: self.current_extension_id,
        )

    def freeze(self) -> None:
        """Seal every contribution store after the single assembly pass."""
        for store in (
            self.runes,
            self.soulstones,
            self.portals,
            self.transmutation,
            self.delegated_runtimes,
        ):
            store.freeze()

    def registration_view(self, extension_id: str) -> ExtensionRegistrationContext:
        """Return the only root surface an extension registrant receives."""
        return ExtensionRegistrationContext(self, extension_id)

    @contextmanager
    def provenance(self, extension_id: str) -> Iterator[None]:
        """Manager-only: attribute registrations inside the block to ``extension_id``."""
        previous = self._current_extension_id
        self._current_extension_id = extension_id
        try:
            yield
        finally:
            self._current_extension_id = previous

    @property
    def current_extension_id(self) -> str:
        """The extension whose ``register()`` is executing.

        Raises:
            RuntimeError: If accessed outside a ``provenance`` block.

        """
        if self._current_extension_id is None:
            msg = "current_extension_id is only defined inside an ExtensionContext.provenance(...) block."
            raise RuntimeError(msg)
        return self._current_extension_id
