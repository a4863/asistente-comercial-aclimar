"""Synthetic, offline checks for the Phase 5A disclosure boundary."""

from datetime import datetime, timezone
from hashlib import sha256
import copy

import pytest

from app.domain.email_analysis import AnalysisInput, SelectedMessage
from app.integrations.ai_schema import (
    AISchemaError, MAX_REQUEST_BYTES, decode_analysis_response,
    project_analysis_input, response_schema,
)


def _input(body="Need a quote?", priors=(), *, sender=None, recipients=()):
    messages = [SelectedMessage(101, "target", body, sha256(body.encode()).hexdigest(),
                                sender, recipients, "Commercial offer", datetime(2026, 9, 24, tzinfo=timezone.utc))]
    for index, prior in enumerate(priors):
        messages.append(SelectedMessage(102 + index, "prior", prior,
                                        sha256(prior.encode()).hexdigest(), None, (), None, None))
    return AnalysisInput("imap:synthetic", 101, 1, 1, tuple(messages), "a" * 64)


def _evidence(alias="m0", text="Need a quote?", start=0):
    return {"message_alias": alias, "start_offset": start,
            "end_offset": start + len(text), "exact_text": text}


def _empty():
    return {"schema_version": 1, "summary": None, "facts": [], "inferences": [],
            "proposals": [], "questions": [], "commitments": [], "tasks": [],
            "next_steps": [], "response_needed": None, "commercial_risk": None,
            "priority": None, "context_mentions": []}


def test_projection_allowlist_aliases_and_immutable_local_map():
    projection = project_analysis_input(_input(priors=("", "Earlier"), sender="a@example.test",
                                         recipients=("b@example.test",)))
    remote = projection.remote_payload()
    assert [item["message_alias"] for item in remote] == ["m0", "m1", "m2"]
    assert set(remote[0]) == {"message_alias", "role", "body_excerpt", "sender", "recipients", "subject", "message_date"}
    assert remote[0]["recipients"] == ["b@example.test"]
    assert remote[1]["body_excerpt"] == ""
    assert remote[0]["role"] == "target" and remote[1]["role"] == "prior"
    assert "101" not in str(remote) and "imap:synthetic" not in str(remote)
    assert "a" * 64 not in str(remote)
    remote[0]["body_excerpt"] = "changed"
    assert projection.remote_payload()[0]["body_excerpt"] == "Need a quote?"
    assert "Need a quote?" not in repr(projection) and "101" not in repr(projection)
    assert project_analysis_input(_input()).remote_payload()[0]["message_alias"] == "m0"


def test_six_priors_and_inherited_limit():
    projection = project_analysis_input(_input("x" * 30_000, priors=("",) * 6))
    assert len(projection.remote_payload()) == 7
    with pytest.raises(Exception):
        _input("x" * 30_001)
    with pytest.raises(Exception):
        _input(priors=("",) * 7)


def test_utf8_request_byte_overflow(monkeypatch):
    import app.integrations.ai_schema as schema
    monkeypatch.setattr(schema, "MAX_REQUEST_BYTES", 100)
    with pytest.raises(AISchemaError, match="payload_too_large"):
        project_analysis_input(_input("á" * 50))
    assert MAX_REQUEST_BYTES > 30_000


@pytest.mark.parametrize("secret", [
    "-----BEGIN PRIVATE KEY-----\nFAKEONLY\n-----END PRIVATE KEY-----",
    "Authorization: Bearer abcdefghijklmnop12345",
    "password = SyntheticLongValue123",
    "api_key: synthetic_key_12345",
])
def test_sensitive_preflight_has_value_free_error(secret):
    with pytest.raises(AISchemaError) as caught:
        project_analysis_input(_input("Please quote. " + secret))
    assert caught.value.code == "sensitive_content"
    assert secret not in str(caught.value) and secret not in repr(caught.value)


def test_benign_commercial_lookalikes_accepted():
    remote = project_analysis_input(_input("Quote 12345, bearer of the offer; token price 7 EUR.")).remote_payload()
    assert remote[0]["body_excerpt"].startswith("Quote")


def test_schema_strict_recursively_and_no_action_capability():
    schema = response_schema()
    def visit(value):
        if isinstance(value, dict):
            if value.get("type") == "object":
                assert value["additionalProperties"] is False
                assert set(value["required"]) == set(value["properties"])
            assert not set(value) & {"tools", "actions", "function_call"}
            for child in value.values():
                visit(child)
        elif isinstance(value, list):
            for child in value:
                visit(child)
    visit(schema)


def test_schema_enums_match_existing_domain_rules_without_new_keywords():
    schema = response_schema()
    properties = schema["properties"]

    def support_kinds(field):
        item = properties[field]["items"] if field in ("inferences", "proposals", "tasks", "next_steps") else properties[field]["anyOf"][0]
        return item["properties"]["support_refs"]["items"]["properties"]["kind"]["enum"]

    assert support_kinds("inferences") == ["fact"]
    assert support_kinds("proposals") == ["fact", "inference"]
    assert support_kinds("tasks") == support_kinds("next_steps") == ["fact", "inference", "proposal"]
    for field, values in (
        ("response_needed", ["yes", "no", "uncertain"]),
        ("commercial_risk", ["none", "low", "medium", "high", "unknown"]),
        ("priority", ["low", "normal", "high", "urgent"]),
    ):
        assert support_kinds(field) == ["fact"]
        nullable = properties[field]["anyOf"]
        assert nullable[1] == {"type": "null"}
        assert nullable[0]["properties"]["value"] == {
            "type": "string", "maxLength": 20, "enum": values,
        }
    assert properties["schema_version"] == {"type": "integer", "enum": [1]}
    assert properties["facts"]["maxItems"] == 50
    assert properties["facts"]["items"]["properties"]["fact_type"]["maxLength"] == 100
    assert properties["tasks"]["items"]["properties"]["support_refs"]["items"]["properties"]["index"] == {
        "type": "integer", "minimum": 0,
    }

    allowed = {"type", "maxLength", "maxItems", "minimum", "enum", "anyOf", "items",
               "properties", "required", "additionalProperties"}

    def check_keywords(node):
        assert set(node) <= allowed
        for key, value in node.items():
            if key == "properties":
                for child in value.values():
                    check_keywords(child)
            elif key == "items":
                check_keywords(value)
            elif key == "anyOf":
                for child in value:
                    check_keywords(child)

    check_keywords(schema)


def test_schema_support_fragments_are_independent():
    properties = response_schema()["properties"]

    def kinds(field):
        item = properties[field]["items"] if field in ("inferences", "proposals", "tasks", "next_steps") else properties[field]["anyOf"][0]
        return item["properties"]["support_refs"]["items"]["properties"]["kind"]["enum"]

    kinds("inferences").append("proposal")
    assert kinds("proposals") == ["fact", "inference"]
    assert kinds("tasks") == kinds("next_steps") == ["fact", "inference", "proposal"]
    kinds("response_needed").append("proposal")
    assert kinds("commercial_risk") == kinds("priority") == ["fact"]
    inference_ref = properties["inferences"]["items"]["properties"]["support_refs"]["items"]
    task_ref = properties["tasks"]["items"]["properties"]["support_refs"]["items"]
    inference_ref["properties"]["index"]["minimum"] = 1
    assert task_ref["properties"]["index"]["minimum"] == 0


def test_full_candidate_graph_and_local_evidence_mapping():
    projection = project_analysis_input(_input())
    raw = _empty()
    evidence = _evidence()
    fact_ref = {"kind": "fact", "index": 0}
    inference_ref = {"kind": "inference", "index": 0}
    proposal_ref = {"kind": "proposal", "index": 0}
    raw.update({
        "summary": "Quote requested",
        "facts": [{"fact_type": "request", "value_reference": "quote", "evidence": evidence}],
        "inferences": [{"inference_type": "interest", "value_reference": "commercial",
                        "support_refs": [fact_ref], "evidence": None}],
        "proposals": [{"proposal_type": "reply", "value_reference": "respond",
                       "support_refs": [fact_ref, inference_ref], "evidence": None}],
        "questions": [{"question_text": "Need a quote?", "evidence": evidence}],
        "commitments": [{"description": "Send offer", "responsible_party": "unknown",
                         "date_certainty": "none", "date_expression": None,
                         "resolved_due_at": None, "evidence": evidence, "explicit_promise": False}],
        "tasks": [{"title": "Review request", "due_at": None, "support_refs": [proposal_ref]}],
        "next_steps": [{"description": "Prepare reply", "target_at": None,
                        "support_refs": [fact_ref]}],
        "response_needed": {"value": "yes", "support_refs": [fact_ref], "evidence": None},
        "commercial_risk": {"value": "unknown", "support_refs": [fact_ref], "evidence": None},
        "priority": {"value": "normal", "support_refs": [fact_ref], "evidence": None},
        "context_mentions": [{"kind": "company", "text": "Acme", "evidence": evidence}],
    })
    result = decode_analysis_response(raw, projection)
    assert result.facts[0].evidence.source_record_id == 101
    assert result.facts[0].evidence.span_digest == sha256(b"Need a quote?").hexdigest()
    assert result.questions[0].quote_state == "new"
    assert len(result.tasks) == len(result.next_steps) == 1


def test_minimal_and_evidence_backed_fact_remain_valid():
    projection = project_analysis_input(_input())
    assert decode_analysis_response(_empty(), projection).facts == ()
    raw = _empty()
    raw["facts"] = [{"fact_type": "request", "value_reference": "quote",
                     "evidence": _evidence()}]
    result = decode_analysis_response(raw, projection)
    assert result.facts[0].evidence.exact_text == "Need a quote?"


@pytest.mark.parametrize("change", [
    lambda r: r.update(extra="no"),
    lambda r: r.update(schema_version=True),
    lambda r: r.update(facts=[{"fact_type": "x", "value_reference": "y", "evidence": _evidence("m9")}]),
    lambda r: r.update(facts=[{"fact_type": "x", "value_reference": "y", "evidence": _evidence(text="Wrong") }]),
    lambda r: r.update(facts=[{"fact_type": "x", "value_reference": "y", "evidence": _evidence(start=True)}]),
    lambda r: r.update(facts=[{"fact_type": "x", "value_reference": "y", "evidence": _evidence(start=20)}]),
    lambda r: r.update(questions=[{"question_text": "Mismatch", "evidence": _evidence()}]),
    lambda r: r.update(tasks=[{"title": "x", "due_at": "yesterday", "support_refs": []}]),
    lambda r: r.update(tasks=[{"title": "x", "due_at": None, "support_refs": [{"kind": "action", "index": 0}]}]),
    lambda r: r.update(tasks=[{"title": "x", "due_at": None, "support_refs": [{"kind": "fact", "index": 9}]}]),
    lambda r: r.update(facts=[{"fact_type": "x" * 101, "value_reference": "y", "evidence": _evidence()}]),
    lambda r: r.update(facts=[{"fact_type": "x", "value_reference": "y", "evidence": {**_evidence(), "extra": 1}}]),
    lambda r: r.update(response_needed={"value": "maybe", "support_refs": [], "evidence": _evidence()}),
    lambda r: r.update(commitments=[{"description": "Send offer", "responsible_party": "unknown",
                                      "date_certainty": "exact", "date_expression": None,
                                      "resolved_due_at": None, "evidence": _evidence(),
                                      "explicit_promise": False}]),
    lambda r: r.update(facts=[{"fact_type": "request", "value_reference": "quote",
                               "evidence": _evidence()}],
                       tasks=[{"title": "Follow up", "due_at": "2026-09-29T12:00:00",
                               "support_refs": [{"kind": "fact", "index": 0}]}]),
    lambda r: r.update(facts=[{}] * 51),
])
def test_invalid_outputs_fail_closed(change):
    raw = copy.deepcopy(_empty())
    change(raw)
    with pytest.raises(AISchemaError) as caught:
        decode_analysis_response(raw, project_analysis_input(_input()))
    assert caught.value.code in {"invalid_output", "payload_too_large"}


def test_duplicate_support_and_quoted_question():
    projection = project_analysis_input(_input("> Need a quote?"))
    raw = _empty()
    raw["questions"] = [{"question_text": "Need a quote?", "evidence": _evidence(text="Need a quote?", start=2)}]
    assert decode_analysis_response(raw, projection).questions[0].quote_state == "quoted"
    raw = _empty()
    raw["facts"] = [{"fact_type": "x", "value_reference": "y", "evidence": _evidence()}]
    raw["inferences"] = [{"inference_type": "x", "value_reference": "y", "evidence": None,
                          "support_refs": [{"kind": "fact", "index": 0}] * 2}]
    with pytest.raises(AISchemaError):
        decode_analysis_response(raw, project_analysis_input(_input()))
