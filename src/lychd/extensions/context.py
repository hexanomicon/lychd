from typing import Protocol, runtime_checkable
from litestar import Router, Controller

@runtime_checkable
class ExtensionContext(Protocol):
    """
    The host-provided registration surface for boot-time extension grafting.
    This is the Extension Context, not the whole Extension Protocol.
    """
    
    def add_router(self, router: Router) -> None:
        """
        Enforces the Unbound Routing Law.
        Accepts fully formed unbound Router objects to graft onto the Vessel.
        Rejects @app.get bindings.
        """
        ...
        
    def add_controller(self, controller: type[Controller]) -> None:
        """
        Enforces the Unbound Routing Law.
        Accepts standalone Controller classes.
        """
        ...
