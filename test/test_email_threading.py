"""Synthetic contract tests for the pure 3D2 threading engine."""

from dataclasses import FrozenInstanceError, fields
from hashlib import sha256
import ast
from pathlib import Path

import pytest

from app.domain.email_threading import (
    ALGORITHM_VERSION, NORMALIZATION_VERSION, EmailThreadInput,
    calculate_reconstruction_key, calculate_source_revision, normalize_subject,
    parse_in_reply_to, parse_message_id, parse_references, reconstruct_threads,
)


def message(source, own=None, irt=None, refs=None, subject=None, scope="account"):
    provisional = EmailThreadInput(scope, source, own, irt, refs, subject, "")
    return EmailThreadInput(scope, source, own, irt, refs, subject,
                            calculate_source_revision(provisional))


def outcomes(result, source, kind):
    return [(e.ordinal, d.outcome, d.target_source_record_id)
            for e, d in zip(result.evidence, result.decisions)
            if e.source_record_id == source and e.header_kind == kind]


@pytest.mark.parametrize("token,canonical", [
    (" A@EXAMPLE ", "a@example"), ("\t<FOO.Bar+tag@A-b.C>\t", "foo.bar+tag@a-b.c"),
    ("x@y", "x@y"), ("!#$%&'*+/=?^_`{|}~-@d", "!#$%&'*+/=?^_`{|}~-@d"),
    ("a" * 996 + "@d", "a" * 996 + "@d"),
])
def test_valid_message_id(token, canonical):
    parsed = parse_message_id(token)
    assert parsed.field_state == "valid"
    assert parsed.observations[0].canonical_token == canonical
    assert parsed.observations[0].token_digest == sha256(canonical.encode()).hexdigest()


@pytest.mark.parametrize("token", [
    "a..b@d", ".a@d", "a.@d", "a@-d", "a@d-", "a@d..x", "a@d.",
    "a@" + "x" * 64, "a@d@e", '"a"@d', "a@[d]", "(x)a@d", "a@d(comment)",
    "<a@d", "a@d>", "<<a@d>>", "prose <a@d>", "a@d extra",
    "a@d\r\n", "a@d,", "a\\b@d", "ü@d", "a@d <b@d>",
    "a" * 997 + "@d",
])
def test_invalid_message_id(token):
    parsed = parse_message_id(token)
    assert parsed.field_state == "malformed"
    assert parsed.observations[0].canonical_token is None
    assert token not in repr(parsed)


def test_header_boundaries_and_missing_empty():
    assert parse_message_id(None).field_state == "missing"
    assert parse_message_id(None).observations == ()
    assert parse_message_id(" \t").field_state == "malformed"
    assert parse_in_reply_to(None).field_state == "missing"
    assert parse_in_reply_to(" ").field_state == "malformed"
    assert parse_references(None).field_state == "missing"
    assert parse_references("").field_state == "malformed"
    # The byte limit applies before syntax; a valid-length raw header may still be malformed.
    assert parse_message_id("a" * 32768).field_state == "malformed"
    assert parse_message_id("a" * 32769).field_state == "over_limit"
    assert parse_message_id("é" * 16384).field_state == "malformed"
    assert parse_message_id("é" * 16385).field_state == "over_limit"
    overflow = parse_message_id("SECRET" * 6000)
    assert "SECRET" not in repr(overflow)
    assert len(overflow.observations[0].token_digest) == 64


def test_list_scanner_and_limits():
    parsed = parse_references("<A@D> bad <B@D>")
    assert parsed.field_state == "malformed"
    assert [(o.ordinal, o.parse_status) for o in parsed.observations] == [
        (0, "valid"), (1, "malformed"), (2, "valid")]
    assert parse_references("<a@d><b@d>").field_state == "malformed"
    assert parse_in_reply_to("<a@d>").field_state == "valid"
    assert parse_in_reply_to("a@d b@d").field_state == "multiple"
    assert parse_in_reply_to("a@d bad").field_state == "malformed"
    hundred = " ".join(f"x{i}@d" for i in range(100))
    assert len(parse_references(hundred).observations) == 100
    over = parse_references(hundred + " x100@d")
    assert over.field_state == "over_limit"
    assert len(over.observations) == 101
    assert over.observations[-1].ordinal == 100
    assert over.observations[-1].parse_status == "malformed"


def test_direct_and_references_fallback_with_support():
    corpus = (message(1, "ROOT@D"), message(2, "child@d", "<root@d>"),
              message(3, "third@d", "external@d", "root@d absent@d child@d"))
    result = reconstruct_threads("account", corpus)
    assert result.components == ((1, 2, 3),)
    assert [(e.source_record_id, e.target_source_record_id, e.kind) for e in result.edges] == [
        (2, 1, "direct_parent"), (3, 2, "ancestor")]
    assert outcomes(result, 2, "in_reply_to") == [(0, "accepted_direct_parent", 1)]
    assert outcomes(result, 3, "references") == [
        (0, "not_linking", None), (1, "unresolved_external", None), (2, "accepted_ancestor", 2)]
    for edge in result.edges:
        decision = result.decisions[edge.evidence_index]
        assert decision.target_source_record_id == edge.target_source_record_id
        assert decision.outcome == "accepted_direct_parent" if edge.kind == "direct_parent" else decision.outcome == "accepted_ancestor"


def test_duplicate_self_and_blocking_fields():
    corpus = (message(1, "dup@d"), message(2, "DUP@D"), message(3, "root@d"),
              message(4, "x@d", "dup@d", "root@d"),
              message(5, "y@d", "y@d", "root@d"),
              message(6, "z@d", "root@d bad", "root@d"),
              message(7, "w@d", "root@d dup@d", "root@d"),
              message(8, "v@d", None, "root@d bad"))
    result = reconstruct_threads("account", corpus)
    assert result.edges == ()
    assert outcomes(result, 4, "in_reply_to") == [(0, "duplicate_target", None)]
    assert outcomes(result, 5, "in_reply_to") == [(0, "self_link", None)]
    assert outcomes(result, 6, "in_reply_to") == [(0, "not_linking", None), (1, "malformed", None)]
    assert outcomes(result, 7, "in_reply_to") == [
        (0, "multiple_in_reply_to", None), (1, "multiple_in_reply_to", None)]
    assert outcomes(result, 8, "references") == [(0, "not_linking", None), (1, "malformed", None)]
    assert len(result.components) == 8


def test_references_overflow_does_not_link_from_prefix():
    refs = "root@d " + " ".join(f"outside{i}@d" for i in range(100))
    result = reconstruct_threads("account", (message(1, "root@d"), message(2, "x@d", refs=refs)))
    assert result.components == ((1,), (2,))
    assert len(outcomes(result, 2, "references")) == 101


def test_conflict_bridge_and_incoming_to_blocked_source():
    corpus = (message(1, "one@d"), message(2, "two@d"),
              message(3, "bridge@d", "one@d", "two@d"),
              message(4, "follower@d", "bridge@d"))
    result = reconstruct_threads("account", corpus)
    assert result.components == ((1,), (2,), (3, 4))
    assert outcomes(result, 3, "in_reply_to") == [(0, "conflict", None)]
    assert outcomes(result, 3, "references") == [(0, "conflict", None)]
    assert [(edge.source_record_id, edge.target_source_record_id) for edge in result.edges] == [(4, 3)]


def test_conflict_rechecked_after_cycle_removal():
    # 1 -> 2 -> 3 -> 1 is a cycle. 4's References target (3) appears
    # reachable from its IRT target (2) before the cycle is removed, but
    # its own direct link cannot be used to prove compatibility.
    corpus = (message(1, "a@d", "b@d"), message(2, "b@d", "c@d"),
              message(3, "c@d", "a@d"),
              message(4, "d@d", "b@d", "c@d"))
    result = reconstruct_threads("account", corpus)
    assert result.components == ((1,), (2,), (3,), (4,))
    assert outcomes(result, 4, "in_reply_to") == [(0, "conflict", None)]
    assert outcomes(result, 4, "references") == [(0, "conflict", None)]


def test_compatible_ancestor_and_directed_cycle():
    compatible = reconstruct_threads("account", (
        message(1, "root@d"), message(2, "parent@d", "root@d"),
        message(3, "child@d", "parent@d", "root@d")))
    assert compatible.components == ((1, 2, 3),)
    assert outcomes(compatible, 3, "references") == [(0, "not_linking", None)]
    cycle = reconstruct_threads("account", (
        message(1, "a@d", "b@d"), message(2, "b@d", "a@d"),
        message(3, "c@d", "a@d")))
    assert cycle.components == ((1, 3), (2,))
    assert outcomes(cycle, 1, "in_reply_to") == [(0, "cycle_rejected", None)]
    assert outcomes(cycle, 2, "in_reply_to") == [(0, "cycle_rejected", None)]


def test_simultaneous_conflicts_cycles_and_permutation():
    corpus = (message(1, "a@d", "b@d"), message(2, "b@d", "a@d"),
              message(3, "c@d", "a@d", "outside@d"),
              message(4, "d@d", "a@d"), message(5, "e@d"))
    first = reconstruct_threads("account", corpus)
    assert reconstruct_threads("account", tuple(reversed(corpus))) == first
    assert first.components == ((1, 3, 4), (2,), (5,))
    assert outcomes(first, 3, "in_reply_to") == [(0, "accepted_direct_parent", 1)]


def test_late_root_and_shared_external_not_a_component():
    pair = (message(2, "a@d", "root@d"), message(3, "b@d", "root@d"))
    before = reconstruct_threads("account", pair)
    assert before.components == ((2,), (3,))
    after = reconstruct_threads("account", pair + (message(1, "root@d"),))
    assert after.components == ((1, 2, 3),)
    assert after.reconstruction_key != before.reconstruction_key


@pytest.mark.parametrize("subject,expected", [
    (None, None), (" \t ", ""), ("Re: x", "x"), ("Fw: x", "x"),
    ("Fwd: x", "x"), ("RV: x", "x"), ("R: x", "x"), ("Enc: x", "x"),
    ("Re: Fwd : Subject", "subject"),
    ("Re: [EXTERNAL] Fwd: Subject", "[external] fwd: subject"),
    ("  Re :\t  RV :  Hi  There  ", "hi there"),
])
def test_subject_normalization(subject, expected):
    assert normalize_subject(subject) == expected


def test_subject_excluded_from_topology_and_key():
    first = reconstruct_threads("account", (message(1, "a@d", subject="Same"),
                                            message(2, "b@d", "a@d", subject="Same")))
    second = reconstruct_threads("account", (message(1, "a@d", subject="Different"),
                                             message(2, "b@d", "a@d", subject="Another")))
    assert first.components == second.components == ((1, 2),)
    assert first.edges == second.edges
    assert first.reconstruction_key == second.reconstruction_key
    assert first.subjects != second.subjects
    assert normalize_subject("x" * 32769) is None


def test_fingerprints_and_input_validation():
    sample = message(4, "<A@D>", None, "z@d")
    payload = b"3d1/source-revision/v1" + b"1:4" + b"5:<A@D>" + b"-1:" + b"3:z@d"
    assert sample.source_revision == sha256(payload).hexdigest()
    assert ALGORITHM_VERSION == NORMALIZATION_VERSION == 1
    assert calculate_reconstruction_key("account", (sample,)) == reconstruct_threads("account", (sample,)).reconstruction_key
    empty = reconstruct_threads("account", ())
    assert empty.components == empty.edges == empty.evidence == empty.decisions == empty.subjects == ()
    assert empty.reconstruction_key == sha256(b"3d2/reconstruction/v1" + b"7:account" + b"1:1" + b"1:0").hexdigest()
    for account, corpus in [("", ()), ("x" * 101, ()), ("account", (sample, sample)),
                            ("account", (EmailThreadInput("account", 0, None, None, None, None, "0" * 64),)),
                            ("account", (message(1, scope="other"),)),
                            ("account", (EmailThreadInput("account", 1, "x@d", None, None, None, "0" * 64),))]:
        with pytest.raises(ValueError):
            reconstruct_threads(account, corpus)


def test_immutable_contract_and_stdlib_only():
    result = reconstruct_threads("account", (message(1, "a@d"),))
    with pytest.raises(FrozenInstanceError):
        result.account_scope = "other"
    assert not hasattr(result, "__dict__")
    assert all(isinstance(getattr(result, field.name), tuple) for field in fields(result)
               if field.name in {"evidence", "decisions", "edges", "components", "subjects"})
    module_path = Path(__file__).parents[1] / "app" / "domain" / "email_threading.py"
    imports = [node for node in ast.walk(ast.parse(module_path.read_text(encoding="utf-8")))
               if isinstance(node, (ast.Import, ast.ImportFrom))]
    assert {node.module if isinstance(node, ast.ImportFrom) else alias.name.split(".")[0]
            for node in imports for alias in node.names} <= {
        "__future__", "dataclasses", "hashlib", "re", "typing"}
