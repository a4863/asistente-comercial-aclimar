"""Pure, deterministic canonical email threading."""

from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
import re
from typing import Literal

NORMALIZATION_VERSION = 1
ALGORITHM_VERSION = 1
_HEADER_LIMIT = 32768
_TOKEN_LIMIT = 998
_ATOM = r"[A-Za-z0-9!#$%&'*+/=?^_`{|}~-]+"
_LABEL = r"[A-Za-z0-9](?:[A-Za-z0-9-]{0,61}[A-Za-z0-9])?"
_ID = re.compile(rf"{_ATOM}(?:\.{_ATOM})*@{_LABEL}(?:\.{_LABEL})*", re.ASCII)
_SPLIT = re.compile(r"[ \t]+")
_PREFIX = re.compile(r"^(?:re|fw|fwd|rv|r|enc)\s*:\s*", re.IGNORECASE)
_HEX = re.compile(r"[0-9a-f]{64}", re.ASCII)


@dataclass(frozen=True, slots=True)
class EmailThreadInput:
    account_scope: str
    source_record_id: int
    message_id: str | None
    in_reply_to: str | None
    references: str | None
    subject: str | None
    source_revision: str


@dataclass(frozen=True, slots=True)
class TokenObservation:
    ordinal: int
    parse_status: Literal["valid", "malformed"]
    canonical_token: str | None
    token_digest: str


@dataclass(frozen=True, slots=True)
class HeaderParse:
    field_state: Literal["missing", "valid", "malformed", "over_limit", "multiple"]
    observations: tuple[TokenObservation, ...]


@dataclass(frozen=True, slots=True)
class ParsedEvidence:
    account_scope: str
    source_record_id: int
    header_kind: str
    ordinal: int
    parse_status: str
    canonical_token: str | None
    token_digest: str
    normalization_version: int
    source_revision: str


@dataclass(frozen=True, slots=True)
class EvidenceDecision:
    evidence_index: int
    outcome: str
    target_source_record_id: int | None


@dataclass(frozen=True, slots=True)
class AcceptedEdge:
    source_record_id: int
    target_source_record_id: int
    kind: Literal["direct_parent", "ancestor"]
    evidence_index: int


@dataclass(frozen=True, slots=True)
class SubjectDiagnostic:
    source_record_id: int
    normalized_subject: str | None


@dataclass(frozen=True, slots=True)
class ThreadingResult:
    account_scope: str
    reconstruction_key: str
    evidence: tuple[ParsedEvidence, ...]
    decisions: tuple[EvidenceDecision, ...]
    edges: tuple[AcceptedEdge, ...]
    components: tuple[tuple[int, ...], ...]
    subjects: tuple[SubjectDiagnostic, ...]


def _digest(domain: str, *fields: str | int | bytes | None) -> str:
    payload = domain.encode("utf-8")
    for field in fields:
        if field is None:
            payload += b"-1:"
        else:
            data = field if isinstance(field, bytes) else str(field).encode("utf-8")
            payload += str(len(data)).encode("ascii") + b":" + data
    return sha256(payload).hexdigest()


def _malformed(kind: str, ordinal: int, raw: str) -> TokenObservation:
    data = raw.encode("utf-8")
    return TokenObservation(ordinal, "malformed", None,
        _digest("3d2/malformed/v1", kind, ordinal, len(data), data[:_TOKEN_LIMIT]))


def _token(kind: str, ordinal: int, raw: str) -> TokenObservation:
    token = raw.strip(" \t")
    if token.startswith("<") and token.endswith(">"):
        token = token[1:-1]
    if len(token) <= _TOKEN_LIMIT and _ID.fullmatch(token):
        canonical = token.lower()
        return TokenObservation(ordinal, "valid", canonical, sha256(canonical.encode("utf-8")).hexdigest())
    return _malformed(kind, ordinal, raw)


def _parse(kind: str, value: str | None) -> HeaderParse:
    if value is None:
        return HeaderParse("missing", ())
    if not isinstance(value, str):
        raise ValueError(f"{kind} must be a string or None")
    if len(value.encode("utf-8")) > _HEADER_LIMIT:
        return HeaderParse("over_limit", (_malformed(kind, 0, value),))
    stripped = value.strip(" \t")
    if not stripped:
        return HeaderParse("malformed", (_malformed(kind, 0, value),))
    if kind == "message_id":
        observation = _token(kind, 0, value)
        return HeaderParse(observation.parse_status, (observation,))
    spans = _SPLIT.split(stripped)
    limit = 100 if kind == "references" else len(spans)
    observations = tuple(_token(kind, i, span) for i, span in enumerate(spans[:limit]))
    if kind == "references" and len(spans) > 100:
        start = list(re.finditer(r"[^ \t]+", stripped))[100].start()
        return HeaderParse("over_limit", observations + (_malformed(kind, 100, stripped[start:]),))
    if any(obs.parse_status == "malformed" for obs in observations):
        state = "malformed"
    elif kind == "in_reply_to" and len(observations) > 1:
        state = "multiple"
    else:
        state = "valid"
    return HeaderParse(state, observations)


def parse_message_id(value: str | None) -> HeaderParse:
    return _parse("message_id", value)


def parse_in_reply_to(value: str | None) -> HeaderParse:
    return _parse("in_reply_to", value)


def parse_references(value: str | None) -> HeaderParse:
    return _parse("references", value)


def normalize_subject(value: str | None) -> str | None:
    if value is None:
        return None
    if not isinstance(value, str):
        raise ValueError("subject must be a string or None")
    if len(value.encode("utf-8")) > _HEADER_LIMIT:
        return None
    normalized = " ".join(value.split())
    while match := _PREFIX.match(normalized):
        normalized = normalized[match.end():]
    return " ".join(normalized.split()).casefold()


def calculate_source_revision(message: EmailThreadInput) -> str:
    if not isinstance(message, EmailThreadInput):
        raise ValueError("message must be EmailThreadInput")
    if not isinstance(message.source_record_id, int) or isinstance(message.source_record_id, bool) or message.source_record_id <= 0:
        raise ValueError("source_record_id must be positive")
    for header in (message.message_id, message.in_reply_to, message.references):
        if header is not None and not isinstance(header, str):
            raise ValueError("ID headers must be strings or None")
    return _digest("3d1/source-revision/v1", message.source_record_id, message.message_id, message.in_reply_to, message.references)


def _validated(account_scope: str, messages: tuple[EmailThreadInput, ...]) -> tuple[EmailThreadInput, ...]:
    if not isinstance(account_scope, str) or not account_scope or len(account_scope) > 100:
        raise ValueError("invalid account_scope")
    if not isinstance(messages, tuple):
        raise ValueError("messages must be a tuple")
    seen: set[int] = set()
    for message in messages:
        expected = calculate_source_revision(message)
        if message.account_scope != account_scope:
            raise ValueError("mixed account scopes")
        if message.source_record_id in seen:
            raise ValueError("duplicate source_record_id")
        seen.add(message.source_record_id)
        if message.subject is not None and not isinstance(message.subject, str):
            raise ValueError("subject must be a string or None")
        if not isinstance(message.source_revision, str) or not _HEX.fullmatch(message.source_revision):
            raise ValueError("invalid source_revision")
        if message.source_revision != expected:
            raise ValueError("source_revision mismatch")
    return tuple(sorted(messages, key=lambda message: message.source_record_id))


def _key(account_scope: str, messages: tuple[EmailThreadInput, ...]) -> str:
    fields: list[str | int] = [account_scope, ALGORITHM_VERSION, len(messages)]
    for message in messages:
        fields.extend((message.source_record_id, message.source_revision))
    return _digest("3d2/reconstruction/v1", *fields)


def calculate_reconstruction_key(account_scope: str, messages: tuple[EmailThreadInput, ...]) -> str:
    return _key(account_scope, _validated(account_scope, messages))


def _cycles(links: dict[int, tuple[int, str, int]]) -> set[int]:
    visited: set[int] = set()
    cycles: set[int] = set()
    for start in sorted(links):
        if start in visited:
            continue
        path: list[int] = []
        positions: dict[int, int] = {}
        node = start
        while node in links and node not in visited and node not in positions:
            positions[node] = len(path)
            path.append(node)
            node = links[node][0]
        if node in positions:
            cycles.update(path[positions[node]:])
        visited.update(path)
    return cycles


def _reachable(start: int, goal: int, links: dict[int, tuple[int, str, int]], omitted: int) -> bool:
    seen: set[int] = set()
    node = start
    while node not in seen:
        if node == goal:
            return True
        seen.add(node)
        if node == omitted or node not in links:
            return False
        node = links[node][0]
    return False


def reconstruct_threads(account_scope: str, messages: tuple[EmailThreadInput, ...]) -> ThreadingResult:
    ordered = _validated(account_scope, messages)
    parsed: dict[int, dict[str, HeaderParse]] = {}
    evidence: list[ParsedEvidence] = []
    indices: dict[tuple[int, str, int], int] = {}
    identities: dict[str, list[int]] = {}
    for message in ordered:
        headers = {"message_id": parse_message_id(message.message_id),
                   "in_reply_to": parse_in_reply_to(message.in_reply_to),
                   "references": parse_references(message.references)}
        source = message.source_record_id
        parsed[source] = headers
        own = headers["message_id"]
        if own.field_state == "valid":
            token = own.observations[0].canonical_token
            assert token is not None
            identities.setdefault(token, []).append(source)
        for kind, header in headers.items():
            for observation in header.observations:
                index = len(evidence)
                indices[(source, kind, observation.ordinal)] = index
                evidence.append(ParsedEvidence(account_scope, source, kind, observation.ordinal,
                    observation.parse_status, observation.canonical_token, observation.token_digest,
                    NORMALIZATION_VERSION, message.source_revision))

    outcomes: list[str] = []
    targets: list[int | None] = [None] * len(evidence)
    for item in evidence:
        if item.parse_status == "malformed":
            outcomes.append("malformed")
        elif item.header_kind == "message_id":
            outcomes.append("identity_observed")
        else:
            matches = identities.get(item.canonical_token or "", ())
            outcomes.append("unresolved_external" if not matches else "duplicate_target" if len(matches) > 1 else "not_linking")

    provisional: dict[int, tuple[int, str, int]] = {}
    both_local: dict[int, tuple[int, int, int, int]] = {}
    for message in ordered:
        source = message.source_record_id
        irt, refs = parsed[source]["in_reply_to"], parsed[source]["references"]
        if irt.field_state == "multiple":
            for observation in irt.observations:
                outcomes[indices[(source, "in_reply_to", observation.ordinal)]] = "multiple_in_reply_to"
        elif irt.field_state == "malformed":
            for observation in irt.observations:
                if observation.parse_status == "valid":
                    outcomes[indices[(source, "in_reply_to", observation.ordinal)]] = "not_linking"
        blocked = irt.field_state in ("malformed", "multiple", "over_limit")
        direct: tuple[int, int] | None = None
        if irt.field_state == "valid":
            observation = irt.observations[0]
            matches = identities.get(observation.canonical_token or "", ())
            index = indices[(source, "in_reply_to", observation.ordinal)]
            if len(matches) == 1:
                if matches[0] == source:
                    outcomes[index] = "self_link"
                    blocked = True
                else:
                    direct = (matches[0], index)
            elif len(matches) > 1:
                blocked = True
        ancestor: tuple[int, int] | None = None
        if refs.field_state == "valid":
            for observation in reversed(refs.observations):
                matches = identities.get(observation.canonical_token or "", ())
                if len(matches) == 1:
                    index = indices[(source, "references", observation.ordinal)]
                    if matches[0] == source:
                        outcomes[index] = "self_link"
                        blocked = True
                    else:
                        ancestor = (matches[0], index)
                    break
        if blocked:
            continue
        if direct is not None:
            provisional[source] = (direct[0], "direct_parent", direct[1])
            if ancestor is not None:
                both_local[source] = (direct[0], direct[1], ancestor[0], ancestor[1])
        elif ancestor is not None:
            provisional[source] = (ancestor[0], "ancestor", ancestor[1])

    rejected: dict[int, str] = {}
    while True:
        active = {source: link for source, link in provisional.items() if source not in rejected}
        conflicts = {source for source, (direct, _, ancestor, _) in both_local.items()
                     if source in active and not _reachable(direct, ancestor, active, source)}
        for source in conflicts:
            rejected[source] = "conflict"
        active = {source: link for source, link in active.items() if source not in conflicts}
        cycles = _cycles(active)
        for source in cycles:
            rejected[source] = "cycle_rejected"
        if not conflicts and not cycles:
            break

    edges: list[AcceptedEdge] = []
    for source, (target, kind, index) in sorted(provisional.items()):
        if source in rejected:
            outcomes[index] = rejected[source]
            if rejected[source] == "conflict" and source in both_local:
                outcomes[both_local[source][3]] = "conflict"
            continue
        outcomes[index] = "accepted_direct_parent" if kind == "direct_parent" else "accepted_ancestor"
        targets[index] = target
        edges.append(AcceptedEdge(source, target, kind, index))
    edges.sort(key=lambda edge: (edge.source_record_id, edge.target_source_record_id, edge.kind))

    parent = {message.source_record_id: message.source_record_id for message in ordered}
    def root(node: int) -> int:
        while parent[node] != node:
            parent[node] = parent[parent[node]]
            node = parent[node]
        return node
    for edge in edges:
        left, right = root(edge.source_record_id), root(edge.target_source_record_id)
        if left != right:
            parent[max(left, right)] = min(left, right)
    groups: dict[int, list[int]] = {}
    for source in parent:
        groups.setdefault(root(source), []).append(source)
    components = tuple(sorted((tuple(sorted(group)) for group in groups.values()), key=lambda group: group[0]))
    return ThreadingResult(account_scope, _key(account_scope, ordered), tuple(evidence),
        tuple(EvidenceDecision(i, outcome, targets[i]) for i, outcome in enumerate(outcomes)),
        tuple(edges), components,
        tuple(SubjectDiagnostic(message.source_record_id, normalize_subject(message.subject)) for message in ordered))
