from __future__ import annotations

from contextlib import contextmanager
from dataclasses import dataclass
from types import MappingProxyType
from typing import TYPE_CHECKING, Any, Protocol, cast
from uuid import uuid4

from lychd.config.runes.extension import RuneConfigStore
from lychd.domain.animation.extension import PortalStore, SoulstoneStore
from lychd.domain.animation.transmute import TransmutationStore
from lychd.domain.oculus.models import MAX_PATTERNS, MAX_SOURCES, SourceSnapshot
from lychd.domain.oculus.runtime import RegisteredInspection, RegisteredObservation
from lychd.domain.weaver.inspection import InspectionContribution
from lychd.extensions.base import ExtensionStore
from lychd.extensions.delegation import DelegatedRuntimeStore

if TYPE_CHECKING:
    from collections.abc import Callable, Generator, Mapping

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


class ObservationRegistrationStore(Protocol):
    """Declare safe component/source metadata without registering any execution."""

    def add(self, snapshot: SourceSnapshot) -> None: ...


class InspectionRegistrationStore(Protocol):
    """Contribute an exact immutable score without a Workflow binding."""

    def add(self, contribution: InspectionContribution) -> None: ...


class ObservationStore(ExtensionStore):
    def __init__(self, *, current_registrant: Callable[[], str], generation: str) -> None:
        """Bind provenance and process generation independently of contributed data."""
        super().__init__()
        self._current_registrant = current_registrant
        self._generation = generation
        self._registrations: dict[str, RegisteredObservation] = {}

    @property
    def registrations(self) -> tuple[RegisteredObservation, ...]:
        return tuple(self._registrations.values())

    def add(self, snapshot: SourceSnapshot) -> None:
        self._require_mutable()
        snapshot = SourceSnapshot.model_validate_json(snapshot.model_dump_json())
        if snapshot.source_id == "native" or snapshot.source_id in self._registrations:
            msg = "Observation source identity is reserved or already registered."
            raise ValueError(msg)
        if (
            snapshot.activities
            or any(component.lifecycle not in {"configured", "unknown"} for component in snapshot.components)
            or len(self._registrations) >= MAX_SOURCES
        ):
            msg = "Registration accepts bounded declarations only, not runtime activity."
            raise ValueError(msg)
        snapshot = snapshot.model_copy(update={"generation": self._generation})
        self._registrations[snapshot.source_id] = RegisteredObservation(
            registrant_id=self._current_registrant(),
            snapshot=snapshot,
        )


class InspectionStore(ExtensionStore):
    def __init__(self, *, current_registrant: Callable[[], str], generation: str) -> None:
        """Create a sealed profile catalogue, separate from all executable registries."""
        super().__init__()
        self._current_registrant = current_registrant
        self._generation = generation
        self._registrations: dict[tuple[str, str, str, str, str], RegisteredInspection] = {}

    @property
    def registrations(self) -> tuple[RegisteredInspection, ...]:
        return tuple(self._registrations.values())

    def add(self, contribution: InspectionContribution) -> None:
        self._require_mutable()
        contribution = InspectionContribution.model_validate_json(contribution.model_dump_json())
        descriptor = contribution.descriptor
        identity = (
            contribution.source_id,
            contribution.profile_id,
            contribution.profile_revision,
            descriptor.pattern_id,
            descriptor.revision,
        )
        if contribution.source_id == "native" or identity in self._registrations:
            msg = "Inspection identity is reserved or already registered."
            raise ValueError(msg)
        if len(self._registrations) >= MAX_PATTERNS or any(
            item.descriptor.pattern_id == descriptor.pattern_id
            and item.descriptor.revision == descriptor.revision
            and item.descriptor != descriptor
            for item in self._registrations.values()
        ):
            msg = "Inspection catalogue limit or exact-revision conflict."
            raise ValueError(msg)
        self._registrations[identity] = RegisteredInspection(
            registrant_id=self._current_registrant(),
            source_id=contribution.source_id,
            generation=self._generation,
            profile_id=contribution.profile_id,
            profile_revision=contribution.profile_revision,
            descriptor=descriptor,
        )


@dataclass(frozen=True, slots=True)
class _ContributionStoreView:
    """Expose only registrant-bound contribution callables named by the host."""

    _calls: Mapping[str, Callable[..., Any]]

    def __getattr__(self, name: str) -> Any:
        try:
            return self._calls[name]
        except KeyError:
            raise AttributeError(name) from None


@dataclass(frozen=True, slots=True, init=False)
class ExtensionRegistrationContext:
    """Registrant-bound shaped surface passed to one extension's ``register`` shim."""

    runes: RuneRegistrationStore
    soulstones: SoulstoneRegistrationStore
    portals: PortalRegistrationStore
    transmutation: TransmutationRegistrationStore
    delegated_runtimes: DelegatedRuntimeRegistrationStore
    observations: ObservationRegistrationStore
    inspections: InspectionRegistrationStore

    def __init__(self, root: ExtensionContext, registrant_id: str) -> None:
        """Bind every shaped contribution store to ``registrant_id``."""

        def attributed(method: Callable[..., Any]) -> Callable[..., Any]:
            def invoke(*args: Any, **kwargs: Any) -> Any:
                with root.provenance(registrant_id):
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
        object.__setattr__(self, "observations", cast("ObservationRegistrationStore", bound(root.observations, "add")))
        object.__setattr__(self, "inspections", cast("InspectionRegistrationStore", bound(root.inspections, "add")))


class ExtensionContext:
    """Host-provided root of explicit extension registration stores."""

    def __init__(self) -> None:
        """Create the extension registration stores for one assembly pass."""
        self._current_registrant_id: str | None = None
        generation = uuid4().hex

        def current_registrant() -> str:
            return self.current_registrant_id

        self.runes = RuneConfigStore(current_registrant=current_registrant)
        self.soulstones = SoulstoneStore(self.runes, current_registrant=current_registrant)
        self.portals = PortalStore(self.runes, current_registrant=current_registrant)
        self.transmutation = TransmutationStore(current_registrant=current_registrant)
        self.delegated_runtimes = DelegatedRuntimeStore(
            current_registrant=current_registrant,
        )
        self.observations = ObservationStore(current_registrant=current_registrant, generation=generation)
        self.inspections = InspectionStore(current_registrant=current_registrant, generation=generation)

    def freeze(self) -> None:
        """Seal every contribution store after the single assembly pass."""
        for store in (
            self.runes,
            self.soulstones,
            self.portals,
            self.transmutation,
            self.delegated_runtimes,
            self.observations,
            self.inspections,
        ):
            store.freeze()

    def registration_view(self, registrant_id: str) -> ExtensionRegistrationContext:
        """Return the only root surface an extension registrant receives."""
        return ExtensionRegistrationContext(self, registrant_id)

    @contextmanager
    def provenance(self, registrant_id: str) -> Generator[None]:
        """Manager-only: attribute registrations inside the block to ``registrant_id``."""
        previous = self._current_registrant_id
        self._current_registrant_id = registrant_id
        try:
            yield
        finally:
            self._current_registrant_id = previous

    @property
    def current_registrant_id(self) -> str:
        """The Core or extension registrant whose contribution is being added.

        Raises:
            RuntimeError: If accessed outside a ``provenance`` block.

        """
        if self._current_registrant_id is None:
            msg = "current_registrant_id is only defined inside an ExtensionContext.provenance(...) block."
            raise RuntimeError(msg)
        return self._current_registrant_id
