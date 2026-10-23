"""Pure, bounded human projection of caller-owned private companion events."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any, Literal, cast
from unicodedata import category

type Language = Literal["sk", "cs", "en"]

_LABELS = {
    "unknown": ("neznáme", "neznámé", "unknown"),
    "none": ("žiadne", "žádné", "none"),
    "yes": ("áno", "ano", "yes"),
    "no": ("nie", "ne", "no"),
    "truncated": ("[skrátené]", "[zkráceno]", "[truncated]"),
    "setup_limits": (
        "Vybrané modely neoverujú mikrofón ani počúvanie.",
        "Vybrané modely neověřují mikrofon ani poslech.",
        "Selected models do not confirm that the microphone or listening works.",
    ),
    "setup": ("Vybrané nastavenie", "Vybrané nastavení", "Selected setup"),
    "language": ("jazyk vstupu", "jazyk vstupu", "input language"),
    "reply_language": ("jazyk reči", "jazyk řeči", "speech language"),
    "recognizer": ("rozpoznávač", "rozpoznávač", "recognizer"),
    "interpretation": ("výklad vybraný", "výklad vybrán", "interpretation selected"),
    "target": ("Vybraný cieľ", "Vybraný cíl", "Selected target"),
    "actor": ("Server hlási aktéra", "Server hlásí aktéra", "Server reports actor"),
    "queued": ("Vo fronte", "Ve frontě", "Queued"),
    "queue_waiting": ("vo fronte", "ve frontě", "queued"),
    "queue": ("Čakajúce vstupy", "Čekající vstupy", "Pending inputs"),
    "heard": ("Rozpoznané", "Rozpoznáno", "Recognized"),
    "microphone": ("vyžiadaný mikrofón", "vyžádaný mikrofon", "requested microphone"),
    "supplied": ("dodaný WAV", "dodaný WAV", "supplied WAV"),
    "reply": ("Hlasová odpoveď", "Hlasová odpověď", "Voice reply"),
    "waiting_audio": ("čaká na zvuk", "čeká na zvuk", "waiting for audio"),
    "recording_pending": ("záznam vyžiadaný", "záznam vyžádán", "recording requested"),
    "recording": ("prijíma audio", "přijímá audio", "receiving audio"),
    "finishing": ("ukončuje záznam", "ukončuje záznam", "finishing capture"),
    "reading_audio": ("číta dodaný zvuk", "čte dodaný zvuk", "reading supplied audio"),
    "transcribing": ("rozpoznáva", "rozpoznává", "recognizing"),
    "synthesizing": ("pripravuje hlas", "připravuje hlas", "preparing voice"),
    "generated": ("hlas pripravený", "hlas připraven", "voice prepared"),
    "player_pending": ("prehrávanie vyžiadané", "přehrávání vyžádáno", "playback requested"),
    "voice": ("Zvukový vstup", "Zvukový vstup", "Audio input"),
    "voice_refused": ("Zvukový vstup odmietnutý", "Zvukový vstup odmítnut", "Audio input refused"),
    "voice_unknown": (
        "Výsledok hlasového vstupu nepotvrdený",
        "Výsledek hlasového vstupu nepotvrzen",
        "Audio input outcome unconfirmed",
    ),
    "voice_evidence_failed": (
        "Uloženie dôkazu zvukového vstupu zlyhalo",
        "Uložení důkazu zvukového vstupu selhalo",
        "Audio input evidence retention failed",
    ),
    "capture_off": ("Záznam ukončený", "Záznam ukončen", "Recording finished"),
    "capture_unknown": (
        "Ukončenie záznamu nepotvrdené; zvuk vypnutý, text dostupný",
        "Ukončení záznamu nepotvrzeno; zvuk vypnut, text dostupný",
        "Recording stop unconfirmed; audio disabled, text available",
    ),
    "stop_requested": (
        "Zastavenie vyžiadané; potvrdenie ešte chýba",
        "Zastavení vyžádáno; potvrzení ještě chybí",
        "Stop requested; acknowledgement pending",
    ),
    "stop_applied": ("Server potvrdil zastavenie", "Server potvrdil zastavení", "Server acknowledged stop"),
    "stop_refused": ("Zastavenie odmietnuté", "Zastavení odmítnuto", "Stop refused"),
    "stop_cancelled": (
        "Zastavenie zrušené; zastavenie nepotvrdené",
        "Zastavení zrušeno; zastavení nepotvrzeno",
        "Stop cancelled; stop unconfirmed",
    ),
    "stop_unknown": (
        "Výsledok zastavenia nepotvrdený; neopakovať automaticky",
        "Výsledek zastavení nepotvrzen; neopakovat automaticky",
        "Stop outcome unconfirmed; no automatic replay",
    ),
    "result": ("Výsledok", "Výsledek", "Result"),
    "applied": ("použité", "použito", "applied"),
    "refused": ("odmietnuté", "odmítnuto", "refused"),
    "cancelled": ("zrušené", "zrušeno", "cancelled"),
    "expired": ("vypršané", "vypršelo", "expired"),
    "no_action": ("bez akcie", "bez akce", "no action"),
    "clarification": ("upresnenie", "upřesnění", "clarification"),
    "known": ("známe", "známé", "known"),
    "input_refused": ("Vstup alebo ovládanie odmietnuté", "Vstup nebo ovládání odmítnuto", "Input or control refused"),
    "failed": ("zlyhalo", "selhalo", "failed"),
    "not_attempted": ("neskúšané", "nezkoušeno", "not attempted"),
    "cancelled_server_work_unknown": (
        "zrušené; práca servera neznáma",
        "zrušeno; práce serveru neznámá",
        "cancelled; server work unknown",
    ),
    "player_exited": ("prehrávač skončil", "přehrávač skončil", "player finished"),
    "interrupted": ("prerušené", "přerušeno", "interrupted"),
    "settlement_unknown": ("ukončenie nepotvrdené", "ukončení nepotvrzeno", "settlement unknown"),
    "recorded": ("ponechané", "ponecháno", "retained"),
    "evidence": ("dôkaz", "důkaz", "evidence"),
    "playback": ("prehrávanie", "přehrávání", "playback"),
    "status": ("Miestny stav", "Místní stav", "Local status"),
    "opened": ("otvorené", "otevřeno", "open"),
    "closed": ("prijímanie zatvorené", "přijímání uzavřeno", "admission closed"),
    "stopping": ("zastavovanie", "zastavování", "stopping"),
    "fenced": ("vstup ohraničený", "vstup ohraničen", "fenced"),
    "audio_blocked": ("zvuk blokovaný", "zvuk blokován", "audio blocked"),
    "presentation_failed": ("výstup zlyhal", "výstup selhal", "presentation failed"),
    "result_evidence_failed": ("Uloženie výsledku zlyhalo", "Uložení výsledku selhalo", "Result retention failed"),
    "synthesis_failed": ("príprava hlasu zlyhala", "příprava hlasu selhala", "voice preparation failed"),
    "artifact_write_failed": ("uloženie zvuku zlyhalo", "uložení zvuku selhalo", "audio retention failed"),
    "playback_failed": ("prehrávanie zlyhalo", "přehrávání selhalo", "playback failed"),
    "playback_unsettled": (
        "ukončenie prehrávania nepotvrdené",
        "ukončení přehrávání nepotvrzeno",
        "playback stop unconfirmed",
    ),
    "pending_evidence": ("čakajúce dôkazy", "čekající důkazy", "pending evidence"),
    "current": ("Spracúvaný vstup", "Zpracovávaný vstup", "Current input"),
    "pending": ("Čakajúci vstup", "Čekající vstup", "Pending input"),
    "admission_pending": ("čaká na prijatie", "čeká na přijetí", "waiting for admission"),
    "response_pending": ("čaká na výsledok", "čeká na výsledek", "waiting for result"),
    "settling": ("dokončuje sa", "dokončuje se", "finishing"),
    "remaining": ("zostáva", "zbývá", "time left"),
    "deadline_passed": (
        "termín uplynul; dokončenie nepotvrdené",
        "termín uplynul; dokončení nepotvrzeno",
        "deadline passed; finish unconfirmed",
    ),
    "run_pending": ("ID Run zatiaľ neznáme", "ID Run zatím neznámé", "Run ID not yet known"),
    "timing": ("Časy na hostiteľovi", "Časy na hostiteli", "Host timings"),
    "timing_evidence_failed": ("uloženie časov zlyhalo", "uložení časů selhalo", "timing retention failed"),
    "elapsed": ("celkom miestne", "celkem místně", "local elapsed"),
    "audio_wait_ms": ("čakanie na zvuk", "čekání na zvuk", "audio wait"),
    "reply_audio_wait_ms": ("čakanie odpovede na zvuk", "čekání odpovědi na zvuk", "reply audio wait"),
    "capture_ms": ("záznam", "záznam", "capture"),
    "supplied_audio_read_ms": ("čítanie WAV", "čtení WAV", "WAV read"),
    "admission_ms": ("prijatie pokynu", "přijetí pokynu", "instruction admission"),
    "transcription_ms": ("prepis", "přepis", "transcription"),
    "native_wait_ms": ("fronta a výsledok", "fronta a výsledek", "queue and result"),
    "synthesis_ms": ("príprava hlasu", "příprava hlasu", "synthesis"),
    "playback_ms": ("prehrávač", "přehrávač", "player"),
    "returned": ("miestny návrat", "místní návrat", "local return"),
    "cancelled_local": ("miestne zrušené", "místně zrušeno", "locally cancelled"),
    "raised_local": ("miestna chyba", "místní chyba", "local error"),
    "local_retirement_unknown": (
        "miestne ukončené, práca neznáma",
        "místně ukončeno, práce neznámá",
        "locally retired, work unknown",
    ),
    "native_result_observed": ("výsledok prijatý", "výsledek přijat", "result observed"),
    "local_outcome_unavailable": ("výsledok nedostupný", "výsledek nedostupný", "result unavailable"),
    "languages": ("Vybrané jazyky", "Vybrané jazyky", "Selected languages"),
    "language_busy": (
        "Jazyk sa nezmenil; najprv dokonči alebo zastav hlasový pokyn a odpoveď.",
        "Jazyk se nezměnil; nejprve dokonči nebo zastav hlasový pokyn a odpověď.",
        "Language unchanged; finish or stop the voice input and reply first.",
    ),
}
_VOICE_PHASES = ("waiting_audio", "recording_pending", "recording", "finishing", "reading_audio", "transcribing")
_REPLY_PHASES = ("waiting_audio", "synthesizing", "generated", "player_pending")
_KINDS = ("applied", "refused", "cancelled", "expired", "unknown", "no_action", "clarification", "known")
_MAX_ITEMS = 16
_MAX_BMP_CODEPOINT = 0xFFFF


def _label(key: str, language: Language) -> str:
    return _LABELS[key][("sk", "cs", "en").index(language)]


def _literal(value: object, language: Language, *, limit: int = 80) -> str:
    if not isinstance(value, str):
        return _label("none" if value is None else "unknown", language)
    pieces: list[str] = []
    width = 0
    for character in value:
        code = ord(character)
        if character in {'"', "\\"}:
            escaped = "\\" + character
        elif not character.isprintable() or category(character).startswith("C"):
            escaped = f"\\u{code:04x}" if code <= _MAX_BMP_CODEPOINT else f"\\U{code:08x}"
        else:
            escaped = character
        if width + len(escaped) > limit:
            pieces.append(_label("truncated", language))
            break
        pieces.append(escaped)
        width += len(escaped)
    return "".join(pieces)


def _number(value: object, language: Language) -> str:
    return str(value) if type(value) is int and 0 <= value <= 10**15 else _label("unknown", language)


def _flag(value: object, language: Language) -> str:
    return _label("yes" if value is True else "no" if value is False else "unknown", language)


def _closed(value: object, allowed: tuple[str, ...], language: Language) -> str:
    return _label(value, language) if isinstance(value, str) and value in allowed else _label("unknown", language)


def _identity(event: Mapping[str, Any], language: Language) -> str:
    return f"[{_literal(event.get('request_id'), language)}]"


def _operation(operation: Mapping[str, Any], language: Language, *, reply: bool) -> str:
    prefix = _label("reply" if reply else "voice", language)
    phases = _REPLY_PHASES if reply else _VOICE_PHASES
    phase = _closed(operation.get("phase"), phases, language)
    source = _closed(operation.get("source"), ("microphone", "supplied", "reply"), language)
    suffix = "" if reply else f" ({source})"
    return f"{_identity(operation, language)} {prefix}: {phase}{suffix}."


def _setup(event: Mapping[str, Any], language: Language) -> str:
    fields = [
        f"{_label(key, language)}={_literal(event.get(key), language)}"
        for key in ("language", "reply_language", "recognizer")
    ]
    fields.append(f"{_label('interpretation', language)}={_flag(event.get('interpretation_selected'), language)}")
    commands = (
        "Príkazy: stav | čakaj | nasleduj ma | choď X Y Z | pozri X Y Z | blok X Y Z | povedz TEXT | stop",
        "Příkazy: stav | čekej | následuj mě | jdi X Y Z | podívej X Y Z | blok X Y Z | řekni TEXT | stop",
        "Commands: state | idle | follow me | goto X Y Z | look X Y Z | inspect X Y Z | say TEXT | stop",
    )[("sk", "cs", "en").index(language)]
    return (
        f"{_label('setup', language)}: {', '.join(fields)}.\n"
        f"{_label('target', language)}: {_literal(event.get('target_id'), language)}.\n"
        f"{_label('setup_limits', language)}\n"
        f"{commands}\n:record [1-15] | :wav ABS_PATH | :target UUID | :language [INPUT [REPLY]] | :status | :quit"
    )


def _command(command: Mapping[str, Any], language: Language, *, current: bool) -> str:
    phase = _closed(command.get("phase"), ("queued", "admission_pending", "response_pending", "settling"), language)
    if command.get("phase") == "queued":
        phase = _label("queue_waiting", language)
    run = command.get("run_id")
    run_label = f"Run {_literal(run, language)}" if isinstance(run, str) else _label("run_pending", language)
    remaining = command.get("remaining_ms")
    deadline = (
        _label("deadline_passed", language)
        if type(remaining) is int and remaining == 0
        else f"{_label('remaining', language)}: {_number(remaining, language)} ms"
    )
    return (
        f"{_label('current' if current else 'pending', language)} {_identity(command, language)}: "
        f"{phase}; {run_label}; {deadline}."
    )


def _status(event: Mapping[str, Any], language: Language) -> str:
    supplied = event.get("session")
    session: Mapping[str, Any] = cast("Mapping[str, Any]", supplied) if isinstance(supplied, Mapping) else {}
    flags = "; ".join(
        f"{_label(key, language)}={_flag(session.get(key), language)}"
        for key in ("opened", "closed", "stopping", "fenced")
    )
    lines = [f"{_label('status', language)}: {flags}."]
    current = session.get("current")
    lines.append(
        _command(cast("Mapping[str, Any]", current), language, current=True)
        if isinstance(current, Mapping)
        else f"{_label('current', language)}: {_label('none', language)}."
    )
    pending = session.get("pending")
    items = cast("list[Any] | tuple[Any, ...]", pending) if isinstance(pending, (list, tuple)) else ()
    lines.append(f"{_label('queue', language)}: {len(items)}/{_number(session.get('capacity'), language)}.")
    lines.extend(
        _command(cast("Mapping[str, Any]", item), language, current=False)
        for item in items[:_MAX_ITEMS]
        if isinstance(item, Mapping)
    )
    if len(items) > _MAX_ITEMS:
        lines.append(_label("truncated", language))
    voice = event.get("voice")
    lines.append(
        _operation(cast("Mapping[str, Any]", voice), language, reply=False)
        if isinstance(voice, Mapping)
        else f"{_label('voice', language)}: {_label('none', language)}."
    )
    replies = event.get("replies")
    operations = cast("list[Any] | tuple[Any, ...]", replies) if isinstance(replies, (tuple, list)) else ()
    lines.extend(
        _operation(cast("Mapping[str, Any]", item), language, reply=True)
        for item in operations[:_MAX_ITEMS]
        if isinstance(item, Mapping)
    )
    if len(operations) > _MAX_ITEMS:
        lines.append(_label("truncated", language))
    if event.get("stopping") is True and session.get("stopping") is not True:
        lines.append(_label("stop_requested", language) + ".")
    lines.extend(
        _label(key, language) + "." for key in ("audio_blocked", "presentation_failed") if event.get(key) is True
    )
    if session.get("pending_evidence"):
        lines.append(f"{_label('pending_evidence', language)}: {_number(session['pending_evidence'], language)}.")
    lines.append(f"{_label('target', language)}: {_literal(event.get('target_id'), language)}.")
    return "\n".join(lines)


def _audio(event: Mapping[str, Any], language: Language) -> str | None:
    kind = event.get("kind")
    if "voice_failure" in event and kind in ("refused", "unknown"):
        kind = "voice_unknown" if kind == "unknown" else "voice_refused"
    if kind in ("voice_stage", "reply_stage"):
        return _operation(event, language, reply=kind == "reply_stage")
    if kind in ("voice_refused", "voice_unknown", "voice_evidence_failed"):
        line = f"{_identity(event, language)} {_label(kind, language)}."
        supplied = event.get("feedback")
        if kind != "voice_evidence_failed" and isinstance(supplied, Mapping):
            feedback = cast("Mapping[str, Any]", supplied)
            if isinstance(feedback.get("text"), str):
                line += " " + _literal(feedback["text"], language, limit=240)
        return line
    if kind in ("reply_evidence", "speech_failed", "reply_evidence_failed"):
        reply = _closed(
            event.get("reply_status"),
            ("generated", "failed", "not_attempted", "cancelled_server_work_unknown"),
            language,
        )
        player = _closed(
            event.get("playback"),
            ("not_attempted", "player_exited", "interrupted", "failed", "settlement_unknown"),
            language,
        )
        evidence = _closed(event.get("evidence_status"), ("recorded", "failed"), language)
        failure = ""
        if event.get("reply_failure") is not None:
            failure = "; " + _closed(
                event["reply_failure"],
                ("synthesis_failed", "artifact_write_failed", "playback_failed", "playback_unsettled"),
                language,
            )
        return f"{_identity(event, language)} {_label('reply', language)}: {reply}{failure}; {_label('playback', language)}: {player}; {_label('evidence', language)}: {evidence}."
    capture = event.get("capture")
    if capture in ("off", "unknown"):
        return _label("capture_off" if capture == "off" else "capture_unknown", language) + "."
    return None


def _result(event: Mapping[str, Any], language: Language) -> str | None:
    kind = event.get("kind")
    feedback: Mapping[str, Any]
    if kind == "native_evidence_failed":
        return f"{_identity(event, language)} {_label('result_evidence_failed', language)}."
    if event.get("control") == "stop" or kind == "voice_stop_result":
        result = event.get("game_kind") if kind == "voice_stop_result" else kind
        disposition = result if result in ("applied", "refused", "cancelled", "unknown") else "unknown"
        line = f"{_identity(event, language)} {_label('stop_' + disposition, language)}."
        supplied_feedback = event.get("feedback")
        feedback = cast("Mapping[str, Any]", supplied_feedback) if isinstance(supplied_feedback, Mapping) else {}
        if isinstance(feedback.get("text"), str):
            line += " " + _literal(feedback["text"], language, limit=240)
        return line
    if kind in ("stop_requested", "stop_unknown"):
        return _label(kind, language) + "."
    supplied_feedback = event.get("feedback")
    feedback = cast("Mapping[str, Any]", supplied_feedback) if isinstance(supplied_feedback, Mapping) else {}
    if isinstance(feedback.get("text"), str):
        return f"{_identity(event, language)} {_label('result', language)} ({_closed(kind, _KINDS, language)}): {_literal(feedback['text'], language, limit=240)}"
    if kind == "refused":
        return f"{_identity(event, language)} {_label('input_refused', language)}."
    return None


def _input(event: Mapping[str, Any], language: Language) -> str | None:
    kind = event.get("kind")
    if kind == "heard":
        source = _closed(event.get("source"), ("microphone", "supplied"), language)
        return f'{_identity(event, language)} {_label("heard", language)} ({source}): "{_literal(event.get("text"), language, limit=240)}"'
    if kind == "queued":
        counts = ""
        if type(event.get("local_pending")) is int and type(event.get("local_capacity")) is int:
            counts = f"; {_label('queue', language)}={_number(event['local_pending'], language)}/{_number(event['local_capacity'], language)}"
        return f"{_identity(event, language)} {_label('queued', language)}{counts}."
    return None


def _binding(event: Mapping[str, Any], language: Language) -> str | None:
    kind = event.get("kind")
    supplied_server = event.get("server")
    if isinstance(supplied_server, Mapping):
        server = cast("Mapping[str, Any]", supplied_server)
        return f"{_label('actor', language)}: {_literal(server.get('actor_id'), language)}."
    if "target_id" in event and kind is None:
        return f"{_label('target', language)}: {_literal(event['target_id'], language)}."
    return None


def _timing(event: Mapping[str, Any], language: Language) -> str | None:
    if event.get("kind") not in ("voice_timing", "timing_evidence_failed"):
        return None
    supplied = event.get("stages")
    stages: Mapping[str, Any] = cast("Mapping[str, Any]", supplied) if isinstance(supplied, Mapping) else {}
    fields = [f"{_label('elapsed', language)}={_number(event.get('elapsed_ms'), language)} ms"]
    acquisition = "supplied_audio_read" if event.get("source") == "supplied" else "capture"
    for name in (
        "audio_wait",
        acquisition,
        "transcription",
        "admission",
        "native_wait",
        "reply_audio_wait",
        "synthesis",
        "playback",
    ):
        supplied_stage = stages.get(name)
        stage: Mapping[str, Any] = (
            cast("Mapping[str, Any]", supplied_stage) if isinstance(supplied_stage, Mapping) else {}
        )
        value = (
            _label("not_attempted", language)
            if stage.get("status") == "not_attempted"
            else _number(stage.get("duration_ms"), language)
            + " ms ("
            + _closed(
                stage.get("status"),
                ("returned", "cancelled_local", "raised_local", "local_retirement_unknown"),
                language,
            )
            + ")"
        )
        if name == "native_wait" and stage.get("status") != "not_attempted":
            value += (
                " ("
                + _closed(
                    event.get("native_end_basis"),
                    ("native_result_observed", "local_outcome_unavailable", "local_retirement_unknown"),
                    language,
                )
                + ")"
            )
        fields.append(f"{_label(name + '_ms', language)}={value}")
    if event.get("kind") == "timing_evidence_failed":
        fields.append(_label("timing_evidence_failed", language))
    return f"{_identity(event, language)} {_label('timing', language)}: {'; '.join(fields)}."


def format_companion_event(event: Mapping[str, Any], *, language: Language) -> str | None:
    """Project supplied event facts and private words as bounded literal text.

    The caller must use a literal-text renderer. This function does not interpret
    feedback, diagnostic prose, device readiness or outcomes.
    """
    if language not in ("sk", "cs", "en"):
        msg = "Human labels support sk, cs and en only."
        raise ValueError(msg)
    if event.get("ready") is True:
        return _setup(event, language)
    if event.get("kind") == "status":
        return _status(event, language)
    if event.get("kind") == "language_busy":
        return f"{_identity(event, language)} {_label('language_busy', language)}"
    if event.get("kind") == "language":
        fields: list[str] = []
        for key in ("language", "reply_language"):
            value = event.get(key)
            selected = (
                value if value in ("sk", "cs", "en") else _label("none" if value is None else "unknown", language)
            )
            fields.append(f"{_label(key, language)}={selected}")
        return f"{_identity(event, language)} {_label('languages', language)}: {'; '.join(fields)}."
    for formatter in (_timing, _input, _audio, _result, _binding):
        line = formatter(event, language)
        if line is not None:
            return line
    return None


__all__ = ("format_companion_event",)
