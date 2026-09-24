"""Pure, bounded Phase 5A remote-analysis projection and response decoder."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from hashlib import sha256
import json
import re
from types import MappingProxyType
from typing import Any

from app.domain.email_analysis import (
    AnalysisCandidates, AnalysisDomainError, AnalysisInput, AnalyticalSignalCandidate,
    CommitmentCandidate, ContextMention, EvidenceCandidate, FactCandidate,
    InferenceCandidate, NextStepCandidate, ProposalCandidate, QuestionCandidate,
    SupportRef, TaskCandidate, classify_quote,
)


MAX_REQUEST_BYTES = 160_000
MAX_RESPONSE_BYTES = 160_000
MAX_ITEMS = 50
MAX_DEPTH = 12
MAX_TEXT = 4_000
SCHEMA_VERSION = 1

_SECRET_PATTERNS = (
    re.compile(r"-----BEGIN (?:[A-Z0-9 ]+ )?PRIVATE KEY-----", re.I),
    re.compile(r"\bBearer\s+[A-Za-z0-9._~+/=-]{12,}\b", re.I),
    re.compile(r"\b(?:api[_ -]?key|access[_ -]?token|refresh[_ -]?token|password|passwd|client[_ -]?secret)\s*[:=]\s*['\"]?\S{8,}", re.I),
)
_TOP = ("summary", "facts", "inferences", "proposals", "questions", "commitments",
        "tasks", "next_steps", "response_needed", "commercial_risk", "priority", "context_mentions")


class AISchemaError(ValueError):
    """Only a fixed, value-free code may escape this boundary."""

    def __init__(self, code: str):
        self.code = code
        super().__init__(code)


def _fail(code: str = "invalid_output") -> None:
    raise AISchemaError(code)


def _object(value: Any, keys: tuple[str, ...]) -> dict:
    if type(value) is not dict or set(value) != set(keys):
        _fail()
    return value


def _text(value: Any, maximum: int = MAX_TEXT, *, nullable: bool = False) -> str | None:
    if nullable and value is None:
        return None
    if type(value) is not str or not value or len(value) > maximum:
        _fail()
    return value


def _array(value: Any) -> list:
    if type(value) is not list or len(value) > MAX_ITEMS:
        _fail()
    return value


def _number(value: Any) -> int:
    if type(value) is not int or value < 0:
        _fail()
    return value


def _date(value: Any) -> datetime | None:
    if value is None:
        return None
    _text(value, 40)
    try:
        result = datetime.fromisoformat(value)
    except ValueError:
        _fail()
    if result.tzinfo is None or result.utcoffset() is None:
        _fail()
    return result.astimezone(timezone.utc)


def _bounded_json(value: Any, maximum: int, *, string_limit: int = MAX_TEXT) -> None:
    def walk(item: Any, depth: int) -> None:
        if depth > MAX_DEPTH:
            _fail()
        if type(item) is dict:
            if len(item) > MAX_ITEMS:
                _fail()
            for key, child in item.items():
                if type(key) is not str or len(key) > 100:
                    _fail()
                walk(child, depth + 1)
        elif type(item) in (list, tuple):
            if len(item) > MAX_ITEMS:
                _fail()
            for child in item:
                walk(child, depth + 1)
        elif type(item) is str:
            if len(item) > string_limit:
                _fail()
        elif item is not None and type(item) not in (bool, int):
            _fail()

    walk(value, 0)
    try:
        size = len(json.dumps(value, ensure_ascii=False, allow_nan=False,
                              separators=(",", ":")).encode("utf-8"))
    except (TypeError, ValueError, UnicodeError):
        _fail()
    if size > maximum:
        _fail("payload_too_large")


@dataclass(frozen=True, slots=True)
class RemoteProjection:
    payload: tuple[MappingProxyType, ...] = field(repr=False)
    _messages: tuple = field(repr=False)

    def remote_payload(self) -> list[dict]:
        return [{key: list(value) if key == "recipients" else value
                 for key, value in message.items()} for message in self.payload]


def project_analysis_input(analysis_input: AnalysisInput) -> RemoteProjection:
    if not isinstance(analysis_input, AnalysisInput):
        _fail("invalid_input")
    selected = analysis_input.selected_messages
    if not 1 <= len(selected) <= 7 or selected[0].role != "target" or any(
        item.role != "prior" for item in selected[1:]
    ) or sum(len(item.body_excerpt) for item in selected) > 30_000:
        _fail("invalid_input")
    payload = []
    for index, message in enumerate(selected):
        remote = {"message_alias": f"m{index}", "role": message.role,
                  "body_excerpt": message.body_excerpt}
        if message.sender is not None:
            remote["sender"] = message.sender
        if message.recipients:
            remote["recipients"] = message.recipients
        if message.subject is not None:
            remote["subject"] = message.subject
        if message.message_date is not None:
            date = message.message_date
            remote["message_date"] = (date.replace(tzinfo=timezone.utc) if date.tzinfo is None
                                      else date.astimezone(timezone.utc)).isoformat()
        if any(pattern.search(part) for part in (message.body_excerpt, message.sender or "",
                                                message.subject or "", *message.recipients)
               for pattern in _SECRET_PATTERNS):
            _fail("sensitive_content")
        payload.append(remote)
    _bounded_json(payload, MAX_REQUEST_BYTES, string_limit=30_000)
    return RemoteProjection(tuple(MappingProxyType(item) for item in payload), selected)


def _string(maximum: int = MAX_TEXT, *, nullable: bool = False) -> dict:
    base = {"type": "string", "maxLength": maximum}
    return {"anyOf": [base, {"type": "null"}]} if nullable else base


def _obj(properties: dict[str, dict]) -> dict:
    return {"type": "object", "properties": properties,
            "required": list(properties), "additionalProperties": False}


def _list(item: dict) -> dict:
    return {"type": "array", "items": item, "maxItems": MAX_ITEMS}


def _nullable(obj: dict) -> dict:
    return {"anyOf": [obj, {"type": "null"}]}


def response_schema() -> dict:
    """Local strict JSON Schema; provider support is a later verification gate."""
    integer = {"type": "integer", "minimum": 0}
    evidence = _obj({"message_alias": _string(2), "start_offset": integer,
                     "end_offset": integer, "exact_text": _string()})
    support = _obj({"kind": {"type": "string", "enum": ["fact", "inference", "proposal"]},
                    "index": integer})
    refs = _list(support)
    fact = _obj({"fact_type": _string(100), "value_reference": _string(255), "evidence": evidence})
    inference = _obj({"inference_type": _string(100), "value_reference": _string(255),
                      "support_refs": refs, "evidence": _nullable(evidence)})
    proposal = _obj({"proposal_type": _string(100), "value_reference": _string(255),
                     "support_refs": refs, "evidence": _nullable(evidence)})
    question = _obj({"question_text": _string(), "evidence": evidence})
    date = _string(40, nullable=True)
    commitment = _obj({"description": _string(255),
                       "responsible_party": {"type": "string", "enum": ["self", "counterparty", "unknown"]},
                       "date_certainty": {"type": "string", "enum": ["exact", "resolved_relative", "uncertain", "none"]},
                       "date_expression": _string(255, nullable=True), "resolved_due_at": date,
                       "evidence": evidence, "explicit_promise": {"type": "boolean"}})
    task = _obj({"title": _string(255), "due_at": date, "support_refs": refs})
    next_step = _obj({"description": _string(255), "target_at": date, "support_refs": refs})
    signal = _obj({"value": _string(20), "support_refs": refs,
                   "evidence": _nullable(evidence)})
    mention = _obj({"kind": {"type": "string", "enum": ["company", "contact", "work", "opportunity", "offer"]},
                    "text": _string(), "evidence": evidence})
    return _obj({"schema_version": {"type": "integer", "enum": [SCHEMA_VERSION]},
                 "summary": _string(4000, nullable=True), "facts": _list(fact),
                 "inferences": _list(inference), "proposals": _list(proposal),
                 "questions": _list(question), "commitments": _list(commitment),
                 "tasks": _list(task), "next_steps": _list(next_step),
                 "response_needed": _nullable(signal), "commercial_risk": _nullable(signal),
                 "priority": _nullable(signal), "context_mentions": _list(mention)})


def decode_analysis_response(value: Any, projection: RemoteProjection) -> AnalysisCandidates:
    if not isinstance(projection, RemoteProjection):
        _fail()
    _bounded_json(value, MAX_RESPONSE_BYTES)
    data = _object(value, ("schema_version", *_TOP))
    if type(data["schema_version"]) is not int or data["schema_version"] != SCHEMA_VERSION:
        _fail()
    messages = {f"m{i}": item for i, item in enumerate(projection._messages)}

    def evidence(raw: Any) -> EvidenceCandidate:
        item = _object(raw, ("message_alias", "start_offset", "end_offset", "exact_text"))
        alias = _text(item["message_alias"], 2)
        if alias not in messages:
            _fail()
        message = messages[alias]
        start, end = _number(item["start_offset"]), _number(item["end_offset"])
        exact = _text(item["exact_text"])
        if not start < end <= len(message.body_excerpt) or message.body_excerpt[start:end] != exact:
            _fail()
        return EvidenceCandidate(message.source_record_id, start, end,
                                 sha256(exact.encode("utf-8")).hexdigest(), exact)

    def optional_evidence(raw: Any) -> EvidenceCandidate | None:
        return None if raw is None else evidence(raw)

    def supports(raw: Any) -> tuple[SupportRef, ...]:
        result = []
        for item in _array(raw):
            item = _object(item, ("kind", "index"))
            result.append(SupportRef(_text(item["kind"], 20), _number(item["index"])))
        return tuple(result)

    def signal(raw: Any) -> AnalyticalSignalCandidate | None:
        if raw is None:
            return None
        item = _object(raw, ("value", "support_refs", "evidence"))
        return AnalyticalSignalCandidate(_text(item["value"], 20),
                                         supports(item["support_refs"]),
                                         optional_evidence(item["evidence"]))

    try:
        facts = tuple(FactCandidate(_text(item["fact_type"], 100),
                                    _text(item["value_reference"], 255), evidence(item["evidence"]))
                      for raw in _array(data["facts"])
                      for item in (_object(raw, ("fact_type", "value_reference", "evidence")),))
        inferences = tuple(InferenceCandidate(_text(item["inference_type"], 100),
                                               _text(item["value_reference"], 255),
                                               supports(item["support_refs"]), optional_evidence(item["evidence"]))
                           for raw in _array(data["inferences"])
                           for item in (_object(raw, ("inference_type", "value_reference", "support_refs", "evidence")),))
        proposals = tuple(ProposalCandidate(_text(item["proposal_type"], 100),
                                            _text(item["value_reference"], 255),
                                            supports(item["support_refs"]), optional_evidence(item["evidence"]))
                          for raw in _array(data["proposals"])
                          for item in (_object(raw, ("proposal_type", "value_reference", "support_refs", "evidence")),))
        questions = tuple(QuestionCandidate(_text(item["question_text"]), evidence(item["evidence"]),
                                             classify_quote(messages[item["evidence"]["message_alias"]].body_excerpt,
                                                            evidence(item["evidence"])))
                          for raw in _array(data["questions"])
                          for item in (_object(raw, ("question_text", "evidence")),))
        commitments = tuple(CommitmentCandidate(
            _text(item["description"], 255), _text(item["responsible_party"], 20),
            _text(item["date_certainty"], 20), _text(item["date_expression"], 255, nullable=True),
            _date(item["resolved_due_at"]), evidence(item["evidence"]), item["explicit_promise"])
            for raw in _array(data["commitments"])
            for item in (_object(raw, ("description", "responsible_party", "date_certainty",
                                     "date_expression", "resolved_due_at", "evidence", "explicit_promise")),))
        tasks = tuple(TaskCandidate(_text(item["title"], 255), _date(item["due_at"]),
                                    supports(item["support_refs"])) for raw in _array(data["tasks"])
                      for item in (_object(raw, ("title", "due_at", "support_refs")),))
        next_steps = tuple(NextStepCandidate(_text(item["description"], 255), _date(item["target_at"]),
                                             supports(item["support_refs"])) for raw in _array(data["next_steps"])
                           for item in (_object(raw, ("description", "target_at", "support_refs")),))
        mentions = tuple(ContextMention(_text(item["kind"], 20), _text(item["text"]),
                                        evidence(item["evidence"])) for raw in _array(data["context_mentions"])
                         for item in (_object(raw, ("kind", "text", "evidence")),))
        return AnalysisCandidates(_text(data["summary"], 4000, nullable=True), facts, inferences,
                                  proposals, questions, commitments, tasks, next_steps,
                                  signal(data["response_needed"]), signal(data["commercial_risk"]),
                                  signal(data["priority"]), mentions)
    except (AnalysisDomainError, KeyError, TypeError, ValueError, OverflowError, UnicodeError):
        _fail()
