from pathlib import Path
from lychd.config.runes.discovery import RuneSchemaDiscovery
from lychd.config.runes.writer import ConfigWriter
from lychd.system.constants import PATH_EXTENSIONS_DIR, PATH_RUNES_DIR

class CodexService:
    """Domain boundary for Codex management."""
    
    @staticmethod
    def inscribe(crypt_path: Path | None = None, runes_dir: Path | None = None) -> None:
        """
        The inscription ritual.
        Invokes CryptMachinery (via RuneSchemaDiscovery) to safely scan 
        duck-typed independent organs, discover their ExtensionSchemaProtocol 
        shapes, and forge their anchor TOML templates.
        """
        # 1. Discover all schemas (Built-in + External Crypt)
        discovery = RuneSchemaDiscovery(crypt_path=crypt_path)
        schemas = discovery.discover_classes()
        
        # 2. Write TOML templates and initialize anchors
        writer = ConfigWriter(runes_dir=runes_dir)
        writer.initialize_anchors(schemas)
        writer.inscribe_samples(schemas)
