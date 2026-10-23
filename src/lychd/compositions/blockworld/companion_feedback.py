"""Bounded SK/CZ/EN presentation of correlated companion receipts, without effect inference."""

from __future__ import annotations

from math import ceil
from typing import Protocol

from lychd.compositions.blockworld.companion import BridgeState, CompanionReason, CompanionRequest, CompanionResult
from lychd.compositions.blockworld.companion_intent import CompanionInstruction

LANGUAGES = ("sk", "cs", "en")
MAX_FEEDBACK_CHARS = 200

_OUTCOMES = {
    "no_action": ("Žiadnu hernú akciu nevykonám.", "Žádnou herní akci neprovedu.", "I will take no game action."),
    "clarification": (
        "Prosím, upresni jeden pokyn.",
        "Prosím, upřesni jeden pokyn.",
        "Please clarify one instruction.",
    ),
    "applied": ("Príkaz bol použitý.", "Příkaz byl použit.", "The command was applied."),
    "refused": ("Príkaz sa nevykonal.", "Příkaz se neprovedl.", "The command was not applied."),
    "expired": (
        "Príkaz vypršal pred vykonaním.",
        "Příkaz vypršel před provedením.",
        "The command expired before execution.",
    ),
    "unknown": (
        "Výsledok nie je potvrdený. Príkaz neopakujem.",
        "Výsledek není potvrzený. Příkaz neopakuji.",
        "The result is unconfirmed. I will not repeat it.",
    ),
}
_MODES = {
    "idle": ("čakám", "čekám", "waiting"),
    "look": ("riadim pohľad", "řídím pohled", "controlling gaze"),
    "goto": ("riadim presun", "řídím přesun", "controlling movement"),
    "follow": ("riadim nasledovanie", "řídím následování", "controlling follow"),
    "stopped": ("riadenie je zastavené", "řízení je zastavené", "controller stopped"),
}
_ACTIONS = {
    "look": ("Pokyn na pohľad bol použitý.", "Pokyn k pohledu byl použit.", "The gaze instruction was applied."),
    "idle": ("Pokyn na čakanie bol použitý.", "Pokyn k čekání byl použit.", "The waiting instruction was applied."),
    "goto": (
        "Pokyn na presun bol použitý. Príchod do cieľa nie je potvrdený.",
        "Pokyn k přesunu byl použit. Příchod do cíle není potvrzený.",
        "The movement instruction was applied. Arrival is unconfirmed.",
    ),
    "follow": (
        "Pokyn na nasledovanie bol použitý. Pohyb ešte nie je overený.",
        "Pokyn k následování byl použit. Pohyb ještě není ověřený.",
        "The follow instruction was applied. Movement is not yet verified.",
    ),
    "say": (
        "Správa bola odoslaná do herného chatu.",
        "Zpráva byla odeslána do herního chatu.",
        "The message was sent to game chat.",
    ),
}
_REASONS = {
    "time_not_authorized": (
        "Zmena herných hodín nie je povolená v tejto relácii.",
        "Změna herních hodin není povolena v této relaci.",
        "Game clock changes are not authorized in this session.",
    ),
    "weather_not_authorized": (
        "Zmena počasia na serveri nie je povolená v tejto relácii.",
        "Změna počasí na serveru není povolena v této relaci.",
        "Server weather changes are not authorized in this session.",
    ),
    "bounds": (
        "Pokyn prekračuje miestne hranice alebo vzdialenosť. Použi povolený priestor a kratšiu vzdialenosť.",
        "Pokyn překračuje místní hranice nebo vzdálenost. Použij povolený prostor a kratší vzdálenost.",
        "The instruction exceeds local bounds or distance limits. Use the allowed area and a shorter distance.",
    ),
    "actor_unavailable": (
        "NPC je v pozorovaní nedostupné. Skontroluj ho pred novým pokynom.",
        "NPC je v pozorování nedostupné. Zkontroluj ho před novým pokynem.",
        "The NPC is unavailable in the observation. Check it before a new instruction.",
    ),
    "target_unavailable": (
        "Cieľ nasledovania nie je dostupný v pozorovaní. Skontroluj vybraného hráča.",
        "Cíl následování není dostupný v pozorování. Zkontroluj vybraného hráče.",
        "The follow target is unavailable in the observation. Check the selected player.",
    ),
    "target_distant": (
        "Cieľ nasledovania je príliš ďaleko. Priblíž sa v povolenom priestore.",
        "Cíl následování je příliš daleko. Přibliž se v povoleném prostoru.",
        "The follow target is too far away. Move closer within the allowed area.",
    ),
    "target_unbound": (
        "Pri zachytení nebol vybraný hráč. Vyber cieľ a zadaj nový pokyn na nasledovanie.",
        "Při zachycení nebyl vybrán hráč. Vyber cíl a zadej nový pokyn k následování.",
        "No player was bound at capture. Select a target and give a new follow instruction.",
    ),
    "interpretation_budget_exhausted": (
        "Rozpočet výkladu pokynov je vyčerpaný. Použi presný príkaz, napríklad stav.",
        "Rozpočet výkladu pokynů je vyčerpán. Použij přesný příkaz, například stav.",
        "The interpretation budget is exhausted. Use an exact command such as state.",
    ),
    "interpretation_unavailable": (
        "Miestny výklad pokynu je nedostupný. Použi presný príkaz, napríklad stav.",
        "Místní výklad pokynu je nedostupný. Použij přesný příkaz, například stav.",
        "Local interpretation is unavailable. Use an exact command such as state.",
    ),
    "interpretation_response_refused": (
        "Odpoveď výkladu neprešla kontrolou. Použi presný príkaz, napríklad stav.",
        "Odpověď výkladu neprošla kontrolou. Použij přesný příkaz, například stav.",
        "The interpretation response failed validation. Use an exact command such as state.",
    ),
    "cancelled_before_execution": (
        "Príkaz bol zrušený pred vykonaním. Po dokončení zastavenia môžeš zadať nový pokyn.",
        "Příkaz byl zrušen před provedením. Po dokončení zastavení můžeš zadat nový pokyn.",
        "The command was cancelled before execution. After stop settles, you can give a new instruction.",
    ),
    "expired_before_execution": (
        "Príkaz vypršal vo fronte pred vykonaním. Zadaj nový pokyn.",
        "Příkaz vypršel ve frontě před provedením. Zadej nový pokyn.",
        "The command expired in the queue before execution. Give a new instruction.",
    ),
}
_REASON_KINDS: dict[str, str] = dict.fromkeys(
    (
        "weather_not_authorized",
        "time_not_authorized",
        "bounds",
        "actor_unavailable",
        "target_unavailable",
        "target_distant",
        "interpretation_budget_exhausted",
        "interpretation_unavailable",
        "interpretation_response_refused",
    ),
    "refused",
)
_REASON_KINDS.update(
    target_unbound="clarification", cancelled_before_execution="cancelled", expired_before_execution="expired"
)

_VOICE_FAILURES = {
    "input_unavailable": (
        "Hlasový vstup teraz nemožno prijať. Skontroluj miestny stav; môžeš použiť text.",
        "Hlasový vstup teď nelze přijmout. Zkontroluj místní stav; můžeš použít text.",
        "Voice input cannot be accepted now. Check local status; you can use text.",
    ),
    "capture_failed": (
        "Nahrávka zlyhala; nahrávanie je ukončené. Skontroluj zvukový vstup a začni novú nahrávku alebo použi text.",
        "Nahrávka selhala; nahrávání je ukončeno. Zkontroluj zvukový vstup a začni novou nahrávku nebo použij text.",
        "Recording failed and the recorder retired. Check audio input and start a fresh recording or use text.",
    ),
    "audio_unsettled": (
        "Ukončenie zvuku nie je potvrdené; ďalší zvuk je vypnutý. Použi text a skontroluj miestny stav.",
        "Ukončení zvuku není potvrzeno; další zvuk je vypnutý. Použij text a zkontroluj místní stav.",
        "Audio retirement is unconfirmed; further audio is disabled. Use text and check local status.",
    ),
    "audio_read_failed": (
        "Dodaný zvuk sa nepodarilo načítať. Skontroluj súkromný WAV súbor alebo použi text.",
        "Dodaný zvuk se nepodařilo načíst. Zkontroluj soukromý WAV soubor nebo použij text.",
        "Supplied audio could not be read. Check the private WAV file or use text.",
    ),
    "source_retention_failed": (
        "Zvuk sa nepodarilo uložiť. Skontroluj súkromné úložisko pred novým vstupom alebo použi text.",
        "Zvuk se nepodařilo uložit. Zkontroluj soukromé úložiště před novým vstupem nebo použij text.",
        "Input audio could not be retained. Check private storage before fresh input or use text.",
    ),
    "transcription_failed": (
        "Prepis sa nepodaril. Skontroluj vybranú hlasovú službu alebo použi presný textový príkaz.",
        "Přepis se nepodařil. Zkontroluj vybranou hlasovou službu nebo použij přesný textový příkaz.",
        "Transcription did not complete. Check the selected speech service or use an exact text command.",
    ),
    "transcript_retention_failed": (
        "Prepis sa nepodarilo uložiť. Skontroluj súkromné úložisko pred novým vstupom alebo použi text.",
        "Přepis se nepodařilo uložit. Zkontroluj soukromé úložiště před novým vstupem nebo použij text.",
        "The transcript could not be retained. Check private storage before fresh input or use text.",
    ),
    "instruction_refused": (
        "Hlasový pokyn nebol prijatý. Použi podporovaný presný príkaz v konzole alebo zadaj nový vstup.",
        "Hlasový pokyn nebyl přijat. Použij podporovaný přesný příkaz v konzoli nebo zadej nový vstup.",
        "The voice instruction was not accepted. Use a supported exact command in the console or give fresh input.",
    ),
    "admission_unknown": (
        "Prijatie pokynu nie je potvrdené. Neopakujem ho; over aktuálny stav príkazom stav.",
        "Přijetí pokynu není potvrzeno. Neopakuji ho; ověř aktuální stav příkazem stav.",
        "Instruction admission is unconfirmed. I will not repeat it; check current state with state.",
    ),
    "stop_unconfirmed": (
        "Výsledok zastavenia nie je potvrdený. Stop automaticky neopakujem; skontroluj stav.",
        "Výsledek zastavení není potvrzený. Stop automaticky neopakuji; zkontroluj stav.",
        "The stop outcome is unconfirmed. I will not repeat stop automatically; check state.",
    ),
}


class FeedbackDisposition(Protocol):
    """The host's correlated cause, including a queue outcome with no native Run."""

    @property
    def request_id(self) -> str: ...

    @property
    def kind(self) -> str: ...

    @property
    def reason(self) -> CompanionReason | None: ...


def _language(language: str) -> int:
    if language not in LANGUAGES:
        msg = "Replies support sk, cs and en only."
        raise ValueError(msg)
    return LANGUAGES.index(language)


def reply_text(kind: str, language: str) -> str:
    """Retain uncertainty for interruption and unfamiliar dispositions."""
    return _OUTCOMES.get(kind, _OUTCOMES["unknown"])[_language(language)]


def voice_failure_text(failure: str, language: str) -> str:
    """Describe a host-owned failed voice boundary, never a provider diagnosis or game result."""
    return _VOICE_FAILURES.get(failure, _VOICE_FAILURES["admission_unknown"])[_language(language)]


def feedback_text(
    request: CompanionRequest | CompanionInstruction,
    result: CompanionResult | None,
    *,
    kind: str,
    language: str,
    outcome: FeedbackDisposition | None = None,
    at_ms: int | None = None,
) -> str:
    """Use only correlated host dispositions, reasons and closed observation fields.

    Remote diagnostic prose, player names, UUIDs and chat contents never enter
    synthesized feedback. State is a reported snapshot, not a claim of live pose.
    at_ms is the caller's formatting time, never a new authorization or observation.
    """
    index = _language(language)
    conflicted = outcome is not None and (
        outcome.request_id != request.request_id
        or outcome.kind != kind
        or (
            result is not None
            and (result.request_id, result.kind, result.reason) != (outcome.request_id, outcome.kind, outcome.reason)
        )
    )
    if conflicted or kind != "applied":
        return (
            reply_text("unknown", language)
            if conflicted
            else _unloaded_feedback(request, result, kind=kind, language=language, index=index)
            or _reason_feedback(request.request_id, result, outcome, kind, index)
            or reply_text(kind, language)
        )
    if result is None or result.request_id != request.request_id or result.kind != kind:
        return reply_text("unknown", language)
    if isinstance(request, CompanionInstruction):
        text = (
            _state_feedback(result.observation, language=language, index=index)
            if result.observation is not None
            else reply_text(kind, language)
        )
        return _controller_limit(text, result, index=index, at_ms=at_ms)
    if request.action.kind in {"inspect", "weather", "time"}:
        presenter = {"inspect": _cell_feedback, "weather": _weather_feedback, "time": _clock_feedback}[
            request.action.kind
        ]
        return presenter(request, result, language=language, index=index)
    if request.action.kind == "state":
        return (
            reply_text("unknown", language)
            if result.observation is None
            else _state_feedback(result.observation, language=language, index=index)
        )
    text = _ACTIONS[request.action.kind][index]
    return text if request.action.kind == "say" else _controller_limit(text, result, index=index, at_ms=at_ms)


def _clock_feedback(request: CompanionRequest, result: CompanionResult, *, language: str, index: int) -> str:
    clock, action = result.clock, request.action
    if action.kind != "time" or clock is None or (clock.scope, clock.requested_mode) != (action.scope, action.mode):
        return reply_text("unknown", language)
    name = {"day": ("deň", "den", "day"), "night": ("noc", "noc", "night")}[clock.mode][index]
    enabled = ("áno", "ano", "yes")[index]
    disabled = ("nie", "ne", "no")[index]
    advance, pause = (enabled if clock.time_advancing else disabled), (enabled if clock.paused else disabled)
    cycles = f"{clock.before_cycle} → {clock.after_cycle}"
    text = (
        (
            f"Hodiny: najbližší {name}. Herný deň {cycles}; +{clock.delta_ticks} tickov. "
            f"Plynutie: {advance}; pauza: {pause}; tempo {clock.rate:.3g}."
        ),
        (
            f"Hodiny: nejbližší {name}. Herní den {cycles}; +{clock.delta_ticks} ticků. "
            f"Plynutí: {advance}; pauza: {pause}; tempo {clock.rate:.3g}."
        ),
        (
            f"Clock: next/equal {name}. Game day {cycles}; +{clock.delta_ticks} ticks. "
            f"Advancing: {advance}; paused: {pause}; rate {clock.rate:.3g}."
        ),
    )[index]
    return text if len(text) <= MAX_FEEDBACK_CHARS else reply_text("unknown", language)


def _weather_feedback(request: CompanionRequest, result: CompanionResult, *, language: str, index: int) -> str:
    weather, action = result.weather, request.action
    if (
        action.kind != "weather"
        or weather is None
        or (weather.mode, weather.scope, weather.duration_ticks) != (action.mode, action.scope, action.duration_ticks)
    ):
        return reply_text("unknown", language)
    name = {"clear": ("jasno", "jasno", "clear"), "rain": ("dážď", "déšť", "rain")}[weather.mode][index]
    return (
        f"Počasie servera nastavené: {name}. Časovač 600 herných tickov; potom prirodzený cyklus.",
        f"Počasí serveru nastaveno: {name}. Časovač 600 herních ticků; poté přirozený cyklus.",
        f"Server weather set to {name}. Timer: 600 game ticks; natural cycling follows.",
    )[index]


def _unloaded_feedback(
    request: CompanionRequest | CompanionInstruction,
    result: CompanionResult | None,
    *,
    kind: str,
    language: str,
    index: int,
) -> str | None:
    if (
        kind == "refused"
        and isinstance(request, CompanionRequest)
        and request.action.kind == "inspect"
        and result is not None
        and (result.request_id, result.kind) == (request.request_id, kind)
        and result.cell is not None
        and not result.cell.available
    ):
        return _cell_feedback(request, result, language=language, index=index)
    return None


def _cell_feedback(request: CompanionRequest, result: CompanionResult, *, language: str, index: int) -> str:
    """Present only the exact requested cell; retain a complete state when it exceeds display bounds."""
    cell, action = result.cell, request.action
    if action.kind != "inspect" or cell is None or cell.position != (action.x, action.y, action.z):
        return reply_text("unknown", language)
    x, y, z = cell.position
    if cell.available != (result.kind == "applied"):
        return reply_text("unknown", language)
    if not cell.available:
        return (
            f"Bunka X {x}, Y {y}, Z {z} nie je načítaná. Ďalší chunk nenačítavam.",
            f"Buňka X {x}, Y {y}, Z {z} není načtená. Další chunk nenačítám.",
            f"Cell X {x}, Y {y}, Z {z} is not loaded. I will not load another chunk.",
        )[index]
    if cell.block is None:
        return reply_text("unknown", language)
    properties = ",".join(f"{key}={value}" for key, value in sorted(cell.properties.items()))
    state = cell.block + (f"[{properties}]" if properties else "")
    text = (
        f"Pozorovaný blok X {x}, Y {y}, Z {z}: {state}.",
        f"Pozorovaný blok X {x}, Y {y}, Z {z}: {state}.",
        f"Observed block X {x}, Y {y}, Z {z}: {state}.",
    )[index]
    return (
        text
        if len(text) <= MAX_FEEDBACK_CHARS
        else (
            "Blok bol prečítaný; úplný stav je v súkromnom zázname.",
            "Blok byl přečten; úplný stav je v soukromém záznamu.",
            "The block was read; its complete state is in the private record.",
        )[index]
    )


def _controller_limit(text: str, result: CompanionResult, *, index: int, at_ms: int | None) -> str:
    """Describe only the host's finite outgoing window, never current controller state."""
    deadline = result.controller_expires_at_ms
    if type(deadline) is not int or deadline <= 0:
        return text
    remaining = deadline - at_ms if type(at_ms) is int and at_ms >= 0 else None
    if remaining is not None and remaining <= 0:
        suffix = (
            " Povolený čas uplynul; aktuálny stav over pokynom stav.",
            " Povolený čas uplynul; aktuální stav ověř příkazem stav.",
            " The authorized window elapsed; check current state with state.",
        )[index]
    elif remaining is not None and remaining <= 60_000:  # noqa: PLR2004 - the controller's maximum lease
        seconds = ceil(remaining / 1000)
        suffix = (
            f" Riadenie najviac {seconds} s; môže skončiť skôr. Aktuálny stav: stav.",
            f" Řízení nejvýše {seconds} s; může skončit dřív. Aktuální stav: stav.",
            f" Control for at most {seconds} s; it may end sooner. Check current state with state.",
        )[index]
    else:
        suffix = (
            " Riadenie je časovo obmedzené. Aktuálny stav: stav.",
            " Řízení je časově omezené. Aktuální stav: stav.",
            " Control is time limited. Check current state with state.",
        )[index]
    combined = text + suffix
    return combined if len(combined) <= MAX_FEEDBACK_CHARS else text


def _reason_feedback(
    request_id: str, result: CompanionResult | None, outcome: FeedbackDisposition | None, kind: str, index: int
) -> str | None:
    if any(
        disposition is not None and (disposition.request_id != request_id or disposition.kind != kind)
        for disposition in (result, outcome)
    ):
        return None
    reason = result.reason if result is not None else outcome.reason if outcome is not None else None
    return _REASONS[reason][index] if isinstance(reason, str) and _REASON_KINDS.get(reason) == kind else None


def _state_feedback(state: BridgeState, *, language: str, index: int) -> str:
    if state.mode == "unavailable":
        return (
            "Server hlási nedostupné NPC.",
            "Server hlásí nedostupné NPC.",
            "The server reported an unavailable NPC.",
        )[index]
    if state.position is None:
        return reply_text("unknown", language)
    coordinates = tuple(f"{axis:.1f}" for axis in state.position)
    if any(len(value) > 16 for value in coordinates):  # noqa: PLR2004 - finite display width, not a world-authority bound
        return reply_text("unknown", language)
    x, y, z = coordinates
    mode = _MODES[state.mode][index]
    text = (
        f"Pozorovaný stav: {mode}. Poloha X {x}, Y {y}, Z {z}.",
        f"Pozorovaný stav: {mode}. Poloha X {x}, Y {y}, Z {z}.",
        f"Reported state: {mode}. Position X {x}, Y {y}, Z {z}.",
    )[index]
    return text if len(text) <= MAX_FEEDBACK_CHARS else reply_text("unknown", language)
