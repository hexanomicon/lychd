from __future__ import annotations

from typing import ClassVar
from pydantic import BaseModel, Field

# THE SCHEMA (The Codex Paradox Resolution)
# This implements ExtensionSchemaProtocol via duck-typing.
class VllmRuneConfig(BaseModel):
    """
    Configuration schema for vLLM Animator instances.
    Maps Soulstone TOMLs to physical bridge parameters.
    """
    # Schema attributes for the Extension Protocol discovery branch
    relative_path: ClassVar[str] = "animator/soulstones"
    singleton: ClassVar[bool] = False 
    
    # Configuration Fields
    base_url: str = Field(
        default="http://localhost:8000",
        description="The internal network URL of the vLLM Coven (Container)."
    )
    api_key: str = Field(
        default="vllm-local-auth",
        description="The access token required by the vLLM instance."
    )
