"""Fixed, bounded presentation of retained Horizon outcomes; no effect inference."""

from __future__ import annotations

from collections.abc import Mapping

REPLY_LANGUAGES = ("sk", "cs", "en")
MAX_FEEDBACK_CHARS = 200

# No diagnostic payload is interpolated into operator-facing or synthesized text.
_WORDING = {
    "refused": (
        "Pokyn bol odmietnutý. Presné podporované frázy nájdeš v návode.",
        "Pokyn byl odmítnut. Přesné podporované fráze najdeš v návodu.",
        "Instruction refused. The guide lists the supported phrases.",
    ),
    "client_observed": (
        "Herný klient oznámil výsledok. Podrobnosti sú v zázname.",
        "Herní klient oznámil výsledek. Podrobnosti jsou v záznamu.",
        "The game client reported the result. Details are in the record.",
    ),
    "outcome_unknown": (
        "Účinok je neznámy. Práca sa zastavila; akciu neopakuj. Skontroluj súkromný záznam.",
        "Účinek je neznámý. Práce se zastavila; akci neopakuj. Zkontroluj soukromý záznam.",
        "The effect is unknown. Work stopped; do not repeat the action. Inspect the private record.",
    ),
    "client_error": (
        "Herný klient oznámil chybu. Pred ďalšou akciou skontroluj súkromný záznam.",
        "Herní klient oznámil chybu. Před další akcí zkontroluj soukromý záznam.",
        "The game client reported an error. Inspect the private record before any further action.",
    ),
    "idle_started": (
        "Čakanie sa začalo.",
        "Čekání začalo.",
        "Waiting started.",
    ),
    "follow_started": (
        "Nasledovanie sa začalo.",
        "Následování začalo.",
        "Following started.",
    ),
    "build_started": (
        "Schválený stavebný plán som prijal.",
        "Schválený stavební plán byl přijat.",
        "The build plan was accepted.",
    ),
    "stopped": (
        "Relácia sa zastavila. Pred ďalšou akciou skontroluj zaznamenané účinky.",
        "Relace se zastavila. Před další akcí zkontroluj zaznamenané účinky.",
        "The session stopped. Inspect retained effects before another action.",
    ),
    "unknown": (
        "Výsledok sa nepodarilo zaradiť. Akciu neopakuj; skontroluj súkromný záznam.",
        "Výsledek se nepodařilo zařadit. Akci neopakuj; zkontroluj soukromý záznam.",
        "The result could not be classified. Do not repeat the action; inspect the private record.",
    ),
    "synthesis_failed": (
        "Hlasovú odpoveď sa nepodarilo vytvoriť. Výsledok hry zostáva v zázname; akciu neopakuj.",
        "Hlasovou odpověď se nepodařilo vytvořit. Výsledek hry zůstává v záznamu; akci neopakuj.",
        "The voice reply could not be generated. The game result is retained; do not repeat the action.",
    ),
    "playback_failed": (
        "Hlasovú odpoveď sa nepodarilo prehrať. Výsledok hry je uložený.",
        "Hlasovou odpověď se nepodařilo přehrát. Výsledek hry je uložený.",
        "The voice reply could not be played. The game result is retained.",
    ),
    "playback_unsettled": (
        "Ukončenie prehrávača sa nepodarilo potvrdiť. Hlasová relácia je zablokovaná.",
        "Ukončení přehrávače se nepodařilo potvrdit. Hlasová relace je zablokovaná.",
        "Player retirement could not be confirmed. The voice session is blocked.",
    ),
}


def feedback_text(result: Mapping[str, object], language: str) -> str:
    """Describe only the actual disposition, never provider prose or inferred progress."""
    if language not in REPLY_LANGUAGES:
        msg = "Feedback language must be sk, cs or en."
        raise ValueError(msg)
    kind = result.get("kind")
    key = kind if isinstance(kind, str) and kind in _WORDING else "unknown"
    if kind == "behavior_started":
        behavior = result.get("behavior")
        key = f"{behavior}_started" if behavior in ("idle", "follow") else "unknown"
    return _WORDING[key][REPLY_LANGUAGES.index(language)]
