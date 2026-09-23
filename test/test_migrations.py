from alembic.config import Config
from alembic import command
import pytest
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.exc import IntegrityError
from uuid import uuid4

from app.persistence.models import Base


PHASE2B_TABLES = {
    "task",
    "commitment",
    "question",
    "next_step",
    "alert",
    "follow_up_preference",
    "follow_up_preference_history",
    "action_proposal",
    "approval_decision",
    "execution_result",
    "operational_evidence_link",
}
PHASE3A_TABLES = {
    "email_message",
    "imap_message_location",
    "email_attachment_metadata",
}
PHASE3D1_TABLES = {
    "thread_evidence", "thread_evidence_decision", "thread_membership_change",
    "thread_lineage_operation", "thread_lineage_edge",
}
PHASE4_TABLES = {
    "analysis_run", "analysis_source_evidence", "analysis_derivation_link",
    "analysis_summary", "analysis_operational_link",
}


def _config(isolated_tmp_path):
    cfg = Config("alembic.ini")
    cfg.set_main_option("sqlalchemy.url", f"sqlite:///{isolated_tmp_path / 'test.db'}")
    return cfg


def test_upgrade_empty_database(isolated_tmp_path):
    cfg = _config(isolated_tmp_path)
    command.upgrade(cfg, "head")
    engine = create_engine(cfg.get_main_option("sqlalchemy.url"))
    try:
        tables = set(inspect(engine).get_table_names())
        assert "source_record" in tables
        assert PHASE2B_TABLES <= tables
        assert PHASE3A_TABLES <= tables
        assert PHASE3D1_TABLES <= tables
        assert {"account_scope", "stable_key", "legacy_status"} <= {
            column["name"] for column in inspect(engine).get_columns("conversation")
        }

        command.downgrade(cfg, "0004")
        assert PHASE3D1_TABLES.isdisjoint(inspect(engine).get_table_names())
        command.upgrade(cfg, "head")
        assert PHASE3D1_TABLES <= set(inspect(engine).get_table_names())

        command.downgrade(cfg, "0003")
        tables_after_downgrade = set(inspect(engine).get_table_names())
        assert "source_record" in tables_after_downgrade
        assert PHASE2B_TABLES <= tables_after_downgrade
        assert PHASE3A_TABLES.isdisjoint(tables_after_downgrade)

        command.upgrade(cfg, "head")
        tables_after_reupgrade = set(inspect(engine).get_table_names())
        assert PHASE2B_TABLES <= tables_after_reupgrade
        assert PHASE3A_TABLES <= tables_after_reupgrade
    finally:
        engine.dispose()


def _legacy_source(connection, scope, *, source_type="email_message", email=True):
    result = connection.execute(text("""
        INSERT INTO source_record
        (created_at, source_type, source_system_scope, ingested_at, retention_state, manual_entry, provenance)
        VALUES ('2026-01-01', :source_type, :scope, '2026-01-01', 'active', 0, 'test')
    """), {"source_type": source_type, "scope": scope})
    source_id = result.lastrowid
    if email:
        connection.execute(text("""
            INSERT INTO email_message
            (created_at, source_record_id, content_truncated, provenance)
            VALUES ('2026-01-01', :source_id, 0, 'test')
        """), {"source_id": source_id})
    return source_id


def _legacy_conversation(connection, members, *, superseded=False):
    result = connection.execute(text("""
        INSERT INTO conversation (created_at, provenance, superseded_at)
        VALUES ('2026-01-01', 'old', :superseded)
    """), {"superseded": "2026-02-01" if superseded else None})
    conversation_id = result.lastrowid
    for source_id in members:
        connection.execute(text("""
            INSERT INTO conversation_membership
            (created_at, conversation_id, source_record_id, evidence_type, evidence_reference)
            VALUES ('2026-01-01', :conversation_id, :source_id, 'old-proof', 'legacy-ref')
        """), {"conversation_id": conversation_id, "source_id": source_id})
    return conversation_id


def test_phase3d1_legacy_classification_history_and_downgrade_guard(isolated_tmp_path):
    cfg = _config(isolated_tmp_path)
    command.upgrade(cfg, "0004")
    engine = create_engine(cfg.get_main_option("sqlalchemy.url"))
    with engine.begin() as connection:
        valid = _legacy_conversation(connection, [_legacy_source(connection, "imap:one")])
        orphan = _legacy_conversation(connection, [])
        mixed = _legacy_conversation(connection, [
            _legacy_source(connection, "imap:one"), _legacy_source(connection, "imap:two")])
        non_email = _legacy_conversation(connection, [
            _legacy_source(connection, "manual", source_type="manual_note", email=False)])
        missing_email = _legacy_conversation(connection, [_legacy_source(connection, "imap:one", email=False)])
        empty_scope = _legacy_conversation(connection, [_legacy_source(connection, "")])
        superseded = _legacy_conversation(connection, [_legacy_source(connection, "imap:one")], superseded=True)
    engine.dispose()

    command.upgrade(cfg, "head")
    engine = create_engine(cfg.get_main_option("sqlalchemy.url"))
    with engine.connect() as connection:
        rows = {row.id: row for row in connection.execute(text(
            "SELECT id, account_scope, stable_key, legacy_status FROM conversation"
        )).all()}
        assert rows[valid].account_scope == "imap:one"
        assert rows[valid].legacy_status == "resolved"
        for identifier in (orphan, mixed, non_email, missing_email, empty_scope, superseded):
            assert rows[identifier].account_scope is None
            assert rows[identifier].legacy_status == "legacy_unresolved"
        assert len({row.stable_key for row in rows.values()}) == len(rows)
        assert all(len(row.stable_key) == 36 for row in rows.values())
        membership_count = connection.execute(text("SELECT count(*) FROM conversation_membership")).scalar_one()
        baseline_count = connection.execute(text("""
            SELECT count(*) FROM thread_membership_change
            WHERE reason='legacy_assignment_baseline' AND old_conversation_id IS NULL
              AND evidence_decision_id IS NULL AND reconstruction_key IS NULL
        """)).scalar_one()
        assert baseline_count == membership_count == 7
        assert connection.execute(text("SELECT count(*) FROM conversation_membership WHERE evidence_type='old-proof' AND evidence_reference='legacy-ref'")).scalar_one() == 7
        assert connection.execute(text("SELECT count(*) FROM thread_membership_change WHERE account_scope IS NULL")).scalar_one() == 6
        indexes = {entry["name"] for entry in inspect(engine).get_indexes("thread_evidence")}
        assert {"ix_thread_evidence_scope_token_kind", "ix_thread_evidence_source_revision"} <= indexes
        checks = {entry["name"] for entry in inspect(engine).get_check_constraints("thread_evidence")}
        assert "ck_thread_evidence_token_shape" in checks
    engine.dispose()

    with pytest.raises(RuntimeError, match="downgrade refused"):
        command.downgrade(cfg, "0004")
    engine = create_engine(cfg.get_main_option("sqlalchemy.url"))
    try:
        with engine.connect() as connection:
            assert connection.execute(text("SELECT count(*) FROM thread_membership_change")).scalar_one() == 7
            assert connection.execute(text("SELECT version_num FROM alembic_version")).scalar_one() == "0005"
    finally:
        engine.dispose()


def _lineage_rows(connection):
    operations = tuple(tuple(row) for row in connection.execute(text("""
        SELECT id, created_at, account_scope, kind, reconstruction_key, replay_key, provenance
        FROM thread_lineage_operation ORDER BY id
    """)))
    edges = tuple(tuple(row) for row in connection.execute(text("""
        SELECT id, created_at, operation_id, predecessor_conversation_id, successor_conversation_id
        FROM thread_lineage_edge ORDER BY id
    """)))
    return operations, edges


def _lineage_conversations(connection, count):
    result = []
    for _ in range(count):
        row = connection.execute(text("""
            INSERT INTO conversation
            (created_at, provenance, account_scope, stable_key, legacy_status)
            VALUES ('2026-01-01', 'test', 'imap:one', :stable_key, 'resolved')
        """), {"stable_key": str(uuid4())})
        result.append(row.lastrowid)
    return result


def _lineage_operation(connection, kind, key, predecessor_ids, successor_ids):
    row = connection.execute(text("""
        INSERT INTO thread_lineage_operation
        (created_at, account_scope, kind, reconstruction_key, replay_key, provenance)
        VALUES ('2026-01-01', 'imap:one', :kind, :reconstruction_key, :replay_key, 'test')
    """), {"kind": kind, "reconstruction_key": "d" * 64, "replay_key": key * 64})
    for predecessor_id in predecessor_ids:
        for successor_id in successor_ids:
            connection.execute(text("""
                INSERT INTO thread_lineage_edge
                (created_at, operation_id, predecessor_conversation_id, successor_conversation_id)
                VALUES ('2026-01-01', :operation_id, :predecessor_id, :successor_id)
            """), {"operation_id": row.lastrowid, "predecessor_id": predecessor_id,
                   "successor_id": successor_id})
    return row.lastrowid


def test_phase3d3a_lineage_migration_roundtrip_preserves_rows(isolated_tmp_path):
    cfg = _config(isolated_tmp_path)
    command.upgrade(cfg, "0005")
    engine = create_engine(cfg.get_main_option("sqlalchemy.url"))
    with engine.begin() as connection:
        ids = _lineage_conversations(connection, 10)
        _lineage_operation(connection, "merge", "a", ids[:2], [ids[2]])
        _lineage_operation(connection, "split", "b", [ids[3]], ids[4:6])
        _lineage_operation(connection, "repartition", "c", ids[6:8], ids[8:10])
        before = _lineage_rows(connection)
    engine.dispose()

    for target in ("0006", "0005", "0006"):
        if target == "0006":
            command.upgrade(cfg, target)
        else:
            command.downgrade(cfg, target)
        engine = create_engine(cfg.get_main_option("sqlalchemy.url"))
        try:
            with engine.connect() as connection:
                assert _lineage_rows(connection) == before
                assert connection.exec_driver_sql("PRAGMA foreign_key_check").fetchall() == []
                assert connection.execute(text("SELECT version_num FROM alembic_version")).scalar_one() == target
            inspector = inspect(engine)
            assert "ck_thread_lineage_operation_kind" in {
                item["name"] for item in inspector.get_check_constraints("thread_lineage_operation")}
            assert "ix_thread_lineage_operation_scope_time" in {
                item["name"] for item in inspector.get_indexes("thread_lineage_operation")}
            assert {"ix_thread_lineage_edge_predecessor", "ix_thread_lineage_edge_successor"} <= {
                item["name"] for item in inspector.get_indexes("thread_lineage_edge")}
        finally:
            engine.dispose()


def test_phase3d3a_downgrade_refuses_correction_without_data_loss(isolated_tmp_path):
    cfg = _config(isolated_tmp_path)
    command.upgrade(cfg, "0006")
    engine = create_engine(cfg.get_main_option("sqlalchemy.url"))
    with engine.begin() as connection:
        first, second = _lineage_conversations(connection, 2)
        _lineage_operation(connection, "correction", "a", [first], [second])
        before = _lineage_rows(connection)
    engine.dispose()

    with pytest.raises(RuntimeError, match="downgrade refused"):
        command.downgrade(cfg, "0005")
    engine = create_engine(cfg.get_main_option("sqlalchemy.url"))
    try:
        with engine.connect() as connection:
            assert _lineage_rows(connection) == before
            assert connection.execute(text("SELECT version_num FROM alembic_version")).scalar_one() == "0006"
            assert connection.exec_driver_sql("PRAGMA foreign_key_check").fetchall() == []
    finally:
        engine.dispose()


def _phase4_schema(engine):
    inspector = inspect(engine)
    result = {}
    for table in PHASE4_TABLES | {"commitment"}:
        result[table] = {
            "columns": {row["name"]: (str(row["type"]), row["nullable"], row["primary_key"])
                        for row in inspector.get_columns(table)},
            "checks": {row["name"]: " ".join(row["sqltext"].split())
                       for row in inspector.get_check_constraints(table) if row["name"]},
            "uniques": {tuple(row["column_names"])
                        for row in inspector.get_unique_constraints(table)},
            "indexes": {(row["name"], tuple(row["column_names"]), row["unique"],
                         row["dialect_options"].get("sqlite_where") is not None)
                        for row in inspector.get_indexes(table)},
            "fks": {(tuple(row["constrained_columns"]), row["referred_table"],
                     row["options"].get("ondelete"))
                    for row in inspector.get_foreign_keys(table)},
        }
    return result


def _phase4_parent(connection):
    source_id = connection.execute(text(
        "INSERT INTO source_record (created_at, source_type, source_system_scope, "
        "ingested_at, retention_state, manual_entry, provenance) "
        "VALUES ('2026-01-01', 'email_message', 'imap:one', '2026-01-01', "
        "'active', 0, 'test')"
    )).lastrowid
    conversation_id = connection.execute(text(
        "INSERT INTO conversation (created_at, provenance, account_scope, stable_key, legacy_status) "
        "VALUES ('2026-01-01', 'test', 'imap:one', :key, 'resolved')"
    ), {"key": str(uuid4())}).lastrowid
    return source_id, conversation_id


def _phase4_run(connection, source_id, conversation_id, **overrides):
    fields = dict(created_at="2026-01-01", updated_at="2026-01-01", account_scope="imap:one",
                  target_source_record_id=source_id, conversation_id=conversation_id,
                  run_version=1, input_digest="a" * 64, contract_version=1, policy_version=1,
                  request_mode="manual", status="reserved", failure_code=None, completed_at=None,
                  supersedes_run_id=None)
    fields.update(overrides)
    columns = ", ".join(fields)
    parameters = ", ".join(f":{name}" for name in fields)
    return connection.execute(text(f"INSERT INTO analysis_run ({columns}) VALUES ({parameters})"), fields).lastrowid


def _reject_sql(connection, sql, parameters):
    with pytest.raises(IntegrityError):
        with connection.begin_nested():
            connection.execute(text(sql) if isinstance(sql, str) else sql, parameters)


def test_phase4a2_upgrade_parity_legacy_and_roundtrip(isolated_tmp_path):
    cfg = _config(isolated_tmp_path)
    command.upgrade(cfg, "0006")
    engine = create_engine(cfg.get_main_option("sqlalchemy.url"))
    with engine.begin() as connection:
        legacy_id = connection.execute(text(
            "INSERT INTO commitment (created_at, description, state, due_at, "
            "resolution_reference, provenance) VALUES ('2026-01-01', 'legacy', 'confirmed', "
            "'2026-02-01', 'resolution', 'test')"
        )).lastrowid
        original = connection.execute(text("SELECT * FROM commitment WHERE id=:id"), {"id": legacy_id}).mappings().one()
    engine.dispose()

    command.upgrade(cfg, "0007")
    engine = create_engine(cfg.get_main_option("sqlalchemy.url"))
    reference = create_engine("sqlite://")
    try:
        Base.metadata.create_all(reference)
        migrated = _phase4_schema(engine)
        mapped = _phase4_schema(reference)
        for table in PHASE4_TABLES:
            assert migrated[table] == mapped[table]
        assert migrated["commitment"]["columns"] == mapped["commitment"]["columns"]
        assert migrated["commitment"]["indexes"] == mapped["commitment"]["indexes"]
        assert {name: expression for name, expression in migrated["commitment"]["checks"].items()
                if name.startswith("ck_commitment_") and name != "ck_commitment_state"} == {
                    name: expression for name, expression in mapped["commitment"]["checks"].items()
                    if name.startswith("ck_commitment_")
                }
        with engine.connect() as connection:
            current = connection.execute(text("SELECT * FROM commitment WHERE id=:id"), {"id": legacy_id}).mappings().one()
            assert {key: current[key] for key in original.keys()} == dict(original)
            assert all(current[key] is None for key in ("responsible_party", "date_certainty", "date_expression"))
            assert connection.exec_driver_sql("PRAGMA foreign_key_check").fetchall() == []
    finally:
        engine.dispose()
        reference.dispose()

    command.downgrade(cfg, "0006")
    engine = create_engine(cfg.get_main_option("sqlalchemy.url"))
    try:
        assert PHASE4_TABLES.isdisjoint(inspect(engine).get_table_names())
        assert {column["name"] for column in inspect(engine).get_columns("commitment")} == set(original)
        assert "ix_commitment_due_state" in {index["name"] for index in inspect(engine).get_indexes("commitment")}
        with engine.connect() as connection:
            assert dict(connection.execute(text("SELECT * FROM commitment WHERE id=:id"), {"id": legacy_id}).mappings().one()) == dict(original)
            assert connection.exec_driver_sql("PRAGMA foreign_key_check").fetchall() == []
    finally:
        engine.dispose()
    command.upgrade(cfg, "0007")
    engine = create_engine(cfg.get_main_option("sqlalchemy.url"))
    try:
        assert PHASE4_TABLES <= set(inspect(engine).get_table_names())
        with engine.connect() as connection:
            assert connection.execute(text("SELECT version_num FROM alembic_version")).scalar_one() == "0007"
    finally:
        engine.dispose()


def test_phase4a2_commitment_checks_and_run_lifecycle(isolated_tmp_path):
    cfg = _config(isolated_tmp_path)
    command.upgrade(cfg, "0007")
    engine = create_engine(cfg.get_main_option("sqlalchemy.url"))
    try:
        with engine.begin() as connection:
            connection.exec_driver_sql("PRAGMA foreign_keys=ON")
            due = "2026-02-01"
            base = dict(created_at="2026-01-01", description="promise", state="detected",
                        due_at=due, responsible_party="self", date_certainty="exact",
                        date_expression=None, provenance="test")
            statement = text(
                "INSERT INTO commitment (created_at, description, state, due_at, "
                "responsible_party, date_certainty, date_expression, provenance) "
                "VALUES (:created_at, :description, :state, :due_at, :responsible_party, "
                ":date_certainty, :date_expression, :provenance)"
            )
            connection.execute(statement, base)
            connection.execute(statement, base | {"date_certainty": "resolved_relative", "date_expression": "tomorrow"})
            connection.execute(statement, base | {"date_certainty": "uncertain", "due_at": None})
            connection.execute(statement, base | {"date_certainty": "none", "due_at": None})
            for changes in (
                {"responsible_party": "other"}, {"date_certainty": "invalid"},
                {"date_certainty": "exact", "due_at": None},
                {"date_certainty": "resolved_relative", "date_expression": None},
                {"date_certainty": "uncertain", "due_at": due},
                {"date_certainty": "none", "due_at": due},
            ):
                _reject_sql(connection, statement, base | changes)

            source_id, conversation_id = _phase4_parent(connection)
            run_id = _phase4_run(connection, source_id, conversation_id)
            _reject_sql(connection, text(
                "UPDATE analysis_run SET status='completed' WHERE id=:id"
            ), {"id": run_id})
            _reject_sql(connection, text(
                "UPDATE analysis_run SET status='failed_retryable' WHERE id=:id"
            ), {"id": run_id})
            connection.execute(text(
                "UPDATE analysis_run SET status='completed', completed_at='2026-01-02' WHERE id=:id"
            ), {"id": run_id})
            _reject_sql(connection, text(
                "UPDATE analysis_run SET failure_code='provider_failure' WHERE id=:id"
            ), {"id": run_id})
            assert connection.exec_driver_sql("PRAGMA foreign_key_check").fetchall() == []
    finally:
        engine.dispose()


def test_phase4a2_child_constraints_and_restrict(isolated_tmp_path):
    cfg = _config(isolated_tmp_path)
    command.upgrade(cfg, "0007")
    engine = create_engine(cfg.get_main_option("sqlalchemy.url"))
    try:
        with engine.begin() as connection:
            connection.exec_driver_sql("PRAGMA foreign_keys=ON")
            source_id, conversation_id = _phase4_parent(connection)
            run_id = _phase4_run(connection, source_id, conversation_id)
            evidence = dict(created_at="2026-01-01", analysis_run_id=run_id,
                            source_record_id=source_id, start_offset=0, end_offset=2,
                            body_digest="b" * 64, span_digest="c" * 64, quote_state="new")
            evidence_sql = text(
                "INSERT INTO analysis_source_evidence (created_at, analysis_run_id, source_record_id, "
                "start_offset, end_offset, body_digest, span_digest, quote_state) VALUES "
                "(:created_at, :analysis_run_id, :source_record_id, :start_offset, :end_offset, "
                ":body_digest, :span_digest, :quote_state)"
            )
            evidence_id = connection.execute(evidence_sql, evidence).lastrowid
            for change in ({"end_offset": 0}, {"quote_state": "invalid"}, {"span_digest": "bad"}, {}):
                _reject_sql(connection, evidence_sql, evidence | change)
            fact_id = connection.execute(text(
                "INSERT INTO extracted_fact (created_at, fact_type, value_reference, provenance) "
                "VALUES ('2026-01-01', 'question', '?', 'test')"
            )).lastrowid
            link_sql = text(
                "INSERT INTO analysis_derivation_link (created_at, analysis_run_id, extracted_fact_id, "
                "inference_id, evidence_id) VALUES ('2026-01-01', :run_id, :fact_id, :inference_id, :evidence_id)"
            )
            link_id = connection.execute(link_sql, {"run_id": run_id, "fact_id": fact_id,
                                                    "inference_id": None, "evidence_id": evidence_id}).lastrowid
            _reject_sql(connection, link_sql, {"run_id": run_id, "fact_id": None,
                                               "inference_id": None, "evidence_id": evidence_id})
            _reject_sql(connection, link_sql, {"run_id": run_id, "fact_id": fact_id,
                                               "inference_id": None, "evidence_id": evidence_id})
            summary_sql = text(
                "INSERT INTO analysis_summary (created_at, analysis_run_id, summary_text, summary_digest) "
                "VALUES ('2026-01-01', :run_id, :summary, :digest)"
            )
            _reject_sql(connection, summary_sql, {"run_id": run_id, "summary": "", "digest": "d" * 64})
            _reject_sql(connection, summary_sql, {"run_id": run_id, "summary": "x" * 4001, "digest": "d" * 64})
            connection.execute(summary_sql, {"run_id": run_id, "summary": "derived", "digest": "d" * 64})
            question_id = connection.execute(text(
                "INSERT INTO question (created_at, question_text, state, provenance) "
                "VALUES ('2026-01-01', '?', 'detected', 'test')"
            )).lastrowid
            op_sql = text(
                "INSERT INTO analysis_operational_link (created_at, analysis_run_id, derivation_link_id, "
                "operational_type, question_id) VALUES ('2026-01-01', :run_id, :link_id, :kind, :question_id)"
            )
            connection.execute(op_sql, {"run_id": run_id, "link_id": link_id,
                                        "kind": "question", "question_id": question_id})
            _reject_sql(connection, op_sql, {"run_id": run_id, "link_id": link_id,
                                         "kind": "task", "question_id": question_id})
            _reject_sql(connection, op_sql, {"run_id": run_id, "link_id": link_id,
                                         "kind": "question", "question_id": question_id})
            _reject_sql(connection, text("DELETE FROM analysis_run WHERE id=:id"), {"id": run_id})
            assert connection.exec_driver_sql("PRAGMA foreign_key_check").fetchall() == []
    finally:
        engine.dispose()


@pytest.mark.parametrize("kind", ["analysis_run", "analysis_source_evidence", "analysis_derivation_link", "analysis_summary", "analysis_operational_link", "commitment"])
def test_phase4a2_downgrade_refuses_all_data_without_loss(isolated_tmp_path, kind):
    cfg = _config(isolated_tmp_path)
    command.upgrade(cfg, "0007")
    engine = create_engine(cfg.get_main_option("sqlalchemy.url"))
    with engine.begin() as connection:
        connection.exec_driver_sql("PRAGMA foreign_keys=ON")
        source_id, conversation_id = _phase4_parent(connection)
        if kind == "commitment":
            connection.execute(text(
                "INSERT INTO commitment (created_at, description, state, provenance, "
                "responsible_party, date_certainty) VALUES "
                "('2026-01-01', 'promise', 'detected', 'test', 'self', 'none')"
            ))
        elif kind == "analysis_run":
            _phase4_run(connection, source_id, conversation_id)
        else:
            # With FK enforcement, a child necessarily has an AnalysisRun parent.
            run_id = _phase4_run(connection, source_id, conversation_id)
            if kind == "analysis_source_evidence":
                connection.execute(text(
                    "INSERT INTO analysis_source_evidence (created_at, analysis_run_id, source_record_id, "
                    "start_offset, end_offset, body_digest, span_digest, quote_state) VALUES "
                    "('2026-01-01', :run_id, :source_id, 0, 1, :digest, :digest, 'new')"
                ), {"run_id": run_id, "source_id": source_id, "digest": "a" * 64})
            elif kind == "analysis_summary":
                connection.execute(text(
                    "INSERT INTO analysis_summary (created_at, analysis_run_id, summary_text, summary_digest) "
                    "VALUES ('2026-01-01', :run_id, 'derived', :digest)"
                ), {"run_id": run_id, "digest": "a" * 64})
            else:
                fact_id = connection.execute(text(
                    "INSERT INTO extracted_fact (created_at, fact_type, value_reference, provenance) "
                    "VALUES ('2026-01-01', 'question', '?', 'test')"
                )).lastrowid
                link_id = connection.execute(text(
                    "INSERT INTO analysis_derivation_link (created_at, analysis_run_id, extracted_fact_id) "
                    "VALUES ('2026-01-01', :run_id, :fact_id)"
                ), {"run_id": run_id, "fact_id": fact_id}).lastrowid
                if kind == "analysis_operational_link":
                    question_id = connection.execute(text(
                        "INSERT INTO question (created_at, question_text, state, provenance) "
                        "VALUES ('2026-01-01', '?', 'detected', 'test')"
                    )).lastrowid
                    connection.execute(text(
                        "INSERT INTO analysis_operational_link (created_at, analysis_run_id, "
                        "derivation_link_id, operational_type, question_id) VALUES "
                        "('2026-01-01', :run_id, :link_id, 'question', :question_id)"
                    ), {"run_id": run_id, "link_id": link_id, "question_id": question_id})
        before = {table: connection.execute(text(f"SELECT count(*) FROM {table}")).scalar_one()
                  for table in PHASE4_TABLES | {"commitment"}}
    engine.dispose()
    with pytest.raises(RuntimeError, match="downgrade refused"):
        command.downgrade(cfg, "0006")
    engine = create_engine(cfg.get_main_option("sqlalchemy.url"))
    try:
        assert PHASE4_TABLES <= set(inspect(engine).get_table_names())
        with engine.connect() as connection:
            assert {table: connection.execute(text(f"SELECT count(*) FROM {table}")).scalar_one()
                    for table in before} == before
            assert connection.execute(text("SELECT version_num FROM alembic_version")).scalar_one() == "0007"
            assert connection.exec_driver_sql("PRAGMA foreign_key_check").fetchall() == []
    finally:
        engine.dispose()


def test_phase4a2_upgrade_failure_rolls_back_schema(isolated_tmp_path, monkeypatch):
    from alembic.operations import Operations

    cfg = _config(isolated_tmp_path)
    command.upgrade(cfg, "0006")
    original = Operations.create_table

    def fail_after_first(self, table_name, *args, **kwargs):
        if table_name == "analysis_source_evidence":
            raise RuntimeError("synthetic migration failure")
        return original(self, table_name, *args, **kwargs)

    with monkeypatch.context() as patcher:
        patcher.setattr(Operations, "create_table", fail_after_first)
        with pytest.raises(RuntimeError, match="synthetic migration failure"):
            command.upgrade(cfg, "0007")
    engine = create_engine(cfg.get_main_option("sqlalchemy.url"))
    try:
        assert PHASE4_TABLES.isdisjoint(inspect(engine).get_table_names())
        with engine.connect() as connection:
            assert connection.execute(text("SELECT version_num FROM alembic_version")).scalar_one() == "0006"
            assert connection.exec_driver_sql("PRAGMA foreign_key_check").fetchall() == []
    finally:
        engine.dispose()
