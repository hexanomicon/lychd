from typing import Any
from pydantic import BaseModel

from lychd.extensions.protocols import (
    AnimatorProtocol,
    CapabilityProtocol,
    ReasoningCapability,
    SensoryCapability,
    EmbeddingCapability,
    MindBundle,
)

class HardwareTransitionRequired(Exception):
    """
    Raised when a requested capability is not currently loaded in VRAM.
    
    This exception acts as the metaphysical trigger for the Stasis Protocol 
    (The Long Sleep). When raised, it instructs the Agent Graph to freeze its 
    execution and serialize its state. The Orchestrator intercepts this signal 
    and physically invokes `Animator.activate_capability()` to perform the 
    LlamaSwap (or full Coven restart). Once the hardware is warm (`is_active=True`),
    the Graph rehydrates.
    """
    def __init__(self, capability: CapabilityProtocol, animator: AnimatorProtocol) -> None:
        super().__init__(f"Hardware transition required for capability: {capability.identifier}")
        self.capability = capability
        self.animator = animator

class Dispatcher:
    """
    The Semantic Cortex of LychD.
    
    Resolves abstract cognitive intents into concrete MindBundles,
    and manages the Animator Handshake to trigger the Stasis Protocol
    when physical limits (finite VRAM) require a model swap.
    """
    
    def __init__(self, animators: list[AnimatorProtocol] | None = None) -> None:
        """
        :param animators: Internal registry of active and inactive Animators.
        """
        self.animators: list[AnimatorProtocol] = animators or []
        
    def resolve_intent(self, intent_type: str) -> tuple[AnimatorProtocol, CapabilityProtocol]:
        """
        Scans registered Animators for a Capability matching the abstract intent.
        
        :param intent_type: The abstract intent (e.g., "reasoning", "vision", "embedding").
        :return: A tuple of the Animator and the matched Capability.
        :raises ValueError: If no animator can fulfill the intent.
        """
        for animator in self.animators:
            # Assuming a cached synchronous list for the Dispatcher's rapid resolution path.
            # In production, this would read from the registry synchronized by the Orchestrator.
            # We use an internal stub method `_get_cached_capabilities` for the example.
            capabilities = getattr(animator, "_cached_capabilities", [])
            for capability in capabilities:
                if intent_type == "reasoning" and isinstance(capability, ReasoningCapability):
                    return animator, capability
                elif intent_type == "vision" and isinstance(capability, SensoryCapability):
                    return animator, capability
                elif intent_type == "embedding" and isinstance(capability, EmbeddingCapability):
                    return animator, capability
                    
        raise ValueError(f"No registered Animator can fulfill intent: {intent_type}")

    def request_mind_bundle(self, capability: CapabilityProtocol, animator: AnimatorProtocol) -> MindBundle:
        """
        The Stasis Protocol Handshake.
        
        Evaluates the physical state of the requested capability.
        - If `is_active=True` or `is_static=True`, the capability is ready and a MindBundle is returned.
        - If `is_active=False` and `is_static=False`, the capability is supported but not in VRAM.
          This method MUST raise `HardwareTransitionRequired`.
        
        :param capability: The requested CapabilityProtocol.
        :param animator: The AnimatorProtocol providing the capability.
        :return: The assembled MindBundle ready for Agent execution.
        :raises HardwareTransitionRequired: If the capability is cold and must be swapped.
        """
        if not capability.is_static and not capability.is_active:
            raise HardwareTransitionRequired(capability, animator)
            
        capabilities_to_grant = [capability]
        
        # Perform Modality Zip if a text model lacks native vision
        if isinstance(capability, ReasoningCapability):
            zipped_tools = self._modality_zip(capability)
            capabilities_to_grant.extend(zipped_tools)
            
        return MindBundle(
            animator=animator,
            capabilities=capabilities_to_grant,
            limits={"max_tokens": 4096, "tier": "local_priority"}  # Placeholder policy from The Toll
        )
        
    def _modality_zip(self, reasoning_cap: ReasoningCapability) -> list[CapabilityProtocol]:
        """
        The Modality Zip.
        
        If a ReasoningCapability (Text LLM) is handed an image but lacks native 
        multimodal support, the Dispatcher resolves a SensoryCapability (Vision OCR) 
        and injects it as a Deferred Tool into the MindBundle.
        
        When the Agent uses this tool, the graph calls `request_mind_bundle` for the 
        SensoryCapability, which may raise `HardwareTransitionRequired` and sleep 
        the text model to make room for the vision model.
        
        :param reasoning_cap: The primary text capability.
        :return: A list of supplementary SensoryCapabilities to inject as tools.
        """
        # Stub logic: Assume we check if the `reasoning_cap` natively supports vision.
        # If it doesn't, we attempt to find a vision capability to map as a tool.
        try:
            _, vision_cap = self.resolve_intent("vision")
            return [vision_cap]
        except ValueError:
            # If no vision capability exists in the system at all, return empty.
            return []
