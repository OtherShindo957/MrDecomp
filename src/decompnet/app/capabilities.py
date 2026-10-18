"""Conservative pipeline capabilities, separate from binary recognition and host OS."""
from __future__ import annotations

MODES = [
    {"id": "native", "name": "Native PC Port", "status": "planned", "available": False,
     "target": "linux-amd64", "reason": "No playable native runtime pipeline is implemented yet."},
    {"id": "decompilation", "name": "Decompilation", "status": "supported", "available": True,
     "target": "original", "reason": "Matching source reconstruction; requires the appropriate compiler and game setup."},
    {"id": "recompilation", "name": "Static Recompilation", "status": "planned", "available": False,
     "target": "linux-amd64", "reason": "Game recompilation is not implemented. Use the separate RV32I experiment to translate small supported test programs."},
    {"id": "web", "name": "Web Port", "status": "planned", "available": False,
     "target": "wasm", "reason": "No browser runtime or verified WebAssembly build pipeline is implemented yet."},
]
_EXISTING = {"n64": ("Nintendo 64", "MIPS", "supported"),
             "gc": ("GameCube", "PowerPC", "supported"), "wii": ("Wii", "PowerPC", "supported"),
             "psx": ("PlayStation", "MIPS", "experimental"), "ps2": ("PlayStation 2", "MIPS", "experimental"),
             "gba": ("Game Boy Advance", "ARM", "experimental"), "nds": ("Nintendo DS", "ARM", "experimental")}
_PLANNED = ["NES", "SNES", "Wii U", "Game Boy / Color", "Nintendo 3DS", "Nintendo Switch",
            "PSP", "PlayStation Vita", "PlayStation 3", "PlayStation 4", "PlayStation 5",
            "Xbox", "Xbox 360", "Xbox One", "Xbox Series X/S", "Windows PC", "Sega", "DOS", "Linux", "Arcade"]


def registry() -> dict:
    platforms = [{"id": key, "name": name, "architecture": cpu, "status": status,
                  "modes": {m["id"]: status if m["id"] == "decompilation" else "planned" for m in MODES}}
                 for key, (name, cpu, status) in _EXISTING.items()]
    platforms += [{"id": name.lower().replace(" ", "-"), "name": name, "architecture": None,
                   "status": "planned", "modes": {m["id"]: "planned" for m in MODES}} for name in _PLANNED]
    platforms.append({"id": "rv32-test", "name": "RV32I test programs", "architecture": "RISC-V subset",
                      "status": "experimental", "modes": {"recompilation": "experimental", "decompilation": "unsupported", "native": "unsupported", "web": "unsupported"}})
    return {"modes": [dict(m) for m in MODES], "platforms": platforms}


def require_mode(mode: str) -> None:
    for entry in MODES:
        if entry["id"] == mode:
            if not entry["available"]:
                raise ValueError(entry["reason"])
            return
    raise ValueError(f"Unknown project mode: {mode}")
