import tomllib
from pathlib import Path
from lychd.system.constants import PATH_SYSTEMD_UNITS_DIR, PATH_RUNES_DIR

class InfrastructureService:
    """Domain boundary for physical manifestation (Quadlets & Targets)."""
    
    @staticmethod
    def transmute(runes_dir: Path | None = None, units_dir: Path | None = None) -> None:
        """
        The transmutation ritual.
        Takes validated Codex data and writes Podman Quadlet manifests 
        and Systemd Target units.
        Enforces Quadlet Physics: injects 'Conflicts=' into Targets.
        """
        runes_dir = runes_dir or PATH_RUNES_DIR
        units_dir = units_dir or PATH_SYSTEMD_UNITS_DIR
        
        # 1. Discover and parse all active Runes (Codex)
        toml_files = list(runes_dir.rglob("*.toml"))
        runes_metadata = []
        
        for toml_path in toml_files:
            try:
                with open(toml_path, "rb") as f:
                    data = tomllib.load(f)
                runes_metadata.append({
                    "path": toml_path,
                    "id": toml_path.stem,
                    "always_on": data.get("always_on", False)
                })
            except Exception:
                # In production, this would be logged and handled via validation
                continue
        
        # 2. Forge the Physical Constraints
        for rune in runes_metadata:
            coven_id = rune["id"]
            is_always_on = rune["always_on"]
            
            # A. The Coven Target (The Master Switch)
            # This is the meta-unit the Orchestrator flips to activate a coven.
            target_name = f"lychd-coven-{coven_id}.target"
            target_path = units_dir / target_name
            
            target_content = [
                "[Unit]",
                f"Description=LychD Coven Target: {coven_id}",
                f"Wants=lychd-{coven_id}.service",
                f"Before=lychd-{coven_id}.service",
            ]
            
            # THE QUADLET PHYSICS: Implicit Exclusivity (ADR 08 §3)
            # Non-always-on units conflict with all other non-always-on units.
            if not is_always_on:
                enemies = [f"lychd-coven-{other['id']}.target" 
                           for other in runes_metadata 
                           if other["id"] != coven_id and not other["always_on"]]
                if enemies:
                    target_content.append(f"Conflicts={' '.join(enemies)}")
            
            target_path.parent.mkdir(parents=True, exist_ok=True)
            target_path.write_text("\n".join(target_content) + "\n", encoding="utf-8")
            
            # B. The Quadlet Container Manifest
            container_path = units_dir / f"lychd-{coven_id}.container"
            container_content = [
                "[Unit]",
                f"Description=LychD Container: {coven_id}",
                f"PartOf={target_name}", # Lifecycle bound to the Target switch
                "",
                "[Container]",
                f"Image=ghcr.io/lychd/coven-{coven_id}:latest",
                "User=%U",
                "UserNS=keep-id", # Identity Symmetry (ADR 08 §7)
            ]
            
            container_path.write_text("\n".join(container_content) + "\n", encoding="utf-8")
