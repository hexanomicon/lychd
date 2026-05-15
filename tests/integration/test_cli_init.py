import os
from pathlib import Path
from click.testing import CliRunner
import pytest
from lychd.interface.cli.main import cli

def test_cli_init_discovers_external_extension(tmp_path):
    """
    The Integration Crucible: 
    Verifies that 'lychd init' can discover a duck-typed extension in the Crypt
    and write its corresponding TOML template in the Codex.
    """
    # 1. Setup Mock Substrate (ADR 13 Layout)
    xdg_config = tmp_path / "config"
    xdg_data = tmp_path / "data"
    
    runes_dir = xdg_config / "lychd" / "runes"
    extensions_dir = xdg_data / "lychd" / "extensions"
    
    runes_dir.mkdir(parents=True)
    extensions_dir.mkdir(parents=True)
    
    # 2. Write Dummy Extension (Pillar III: The ABC Trap Avoidance)
    # This class implements RuneConfigProtocol but does NOT inherit from lychd.RuneConfig.
    # It MUST inherit from pydantic.BaseModel so the ConfigWriter can read its fields.
    dummy_code = """
from pydantic import BaseModel, Field
from typing import ClassVar

class DummyOrgan(BaseModel):
    # RuneConfigProtocol implementation
    relative_path: ClassVar[str] = "animator/dummy"
    singleton: ClassVar[bool] = True
    
    # Actual configuration fields
    power_level: int = Field(default=9000, description="The metabolic output of the organ.")
    is_evil: bool = Field(default=True, description="Whether the organ seeks world domination.")
"""
    dummy_file = extensions_dir / "dummy_organ.py"
    dummy_file.write_text(dummy_code)
    
    # 3. Execution via CliRunner
    runner = CliRunner()
    # We pass the paths explicitly to the command for deterministic testing
    result = runner.invoke(cli, ["init", "--crypt-path", str(extensions_dir), "--runes-dir", str(runes_dir)])
    
    # 4. Assertions
    assert result.exit_code == 0
    assert "Summoning the CryptMachinery..." in result.output
    assert "Codex inscribed successfully." in result.output
    
    # Verify the physical TOML was written to the correct anchor
    expected_toml = runes_dir / "animator" / "dummy" / "dummyorgan.toml"
    assert expected_toml.exists(), f"Expected TOML not found at {expected_toml}"
    
    toml_content = expected_toml.read_text()
    # ConfigWriter comments out optional fields (those with defaults)
    # and uses type-based placeholders (e.g., 0 for int, false for bool)
    assert "# power_level = 0" in toml_content
    assert "# is_evil = false" in toml_content
    assert "# The metabolic output of the organ." in toml_content
    assert "# default: 9000" in toml_content

if __name__ == "__main__":
    pytest.main([__file__])
