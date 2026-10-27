"""Bridge one saved SOURCE-001 observation without replaying a live request."""

from pathlib import Path
from typing import Any
from urllib.parse import urlsplit
from uuid import NAMESPACE_URL, uuid5

import psycopg

from hoop.platform.artifacts import ArtifactError, PrivateArtifacts, retain
from hoop.platform.evidence import EvidenceError, register, safe_summary
from hoop.platform.provenance import digest, parse_time


def persist_observation(
    conn: psycopg.Connection[Any],
    store: PrivateArtifacts,
    report: dict[str, Any],
    archive: Path,
    *,
    run_id: str,
    failure_directory: Path,
) -> dict[str, Any]:
    observation = str(report["observation_id"])
    check_id = str(uuid5(NAMESPACE_URL, "baseline:source-check:v2:" + run_id + ":" + observation))
    if report.get("requested_at") is None:
        raise EvidenceError("No request was made; record an incomplete run event instead")
    parsed = urlsplit(report["request_url"])
    if (
        parsed.scheme != "https"
        or parsed.hostname not in {"stats.nba.com", "cdn.nba.com"}
        or parsed.username
        or parsed.password
        or parsed.fragment
    ):
        raise EvidenceError("Unsupported saved request identity")
    # The approved probe already validates query keys. Keep the same safe URL
    # check when importing an externally edited report.
    from hoop.domains.nba.sources.policy import ProbeRequest

    ProbeRequest(
        report["capability"],
        report["request_url"],
        report["environment"],
        report["request_context"],
    )
    summary = safe_summary(
        {
            "request_url": report["request_url"],
            "request_context": report["request_context"],
            "parser_version": report["parser_version"],
            "bridge_version": "nba-source-persist-v2",
            "capability": report["capability"],
            "policy": report["policy"],
            "original_outcome": report["outcome"],
            "provenance": "archived_observation_rehearsal",
            "observation_id": observation,
        }
    )
    raw_id = None
    state = (
        "accepted"
        if report["outcome"] == "verified_sample"
        else ("transport_failure" if report.get("received_at") is None else "invalid")
    )
    try:
        if report.get("raw_path") is not None:
            path = (archive / report["raw_path"]).resolve()
            if not path.is_relative_to((archive / "raw").resolve()):
                raise EvidenceError("Saved raw path escapes archive")
            body = path.read_bytes()
            if digest(body) != report["raw_sha256"]:
                raise EvidenceError("Saved raw checksum mismatch")
            try:
                artifact = retain(
                    conn,
                    store,
                    body,
                    kind="raw",
                    format="source",
                    manifest={"parser_version": report["parser_version"]},
                )
                raw_id = artifact["artifact_id"]
            except ArtifactError:
                state = "storage_failure"
                summary["retention_reason"] = "storage_failure"
        record = {
            "check_id": check_id,
            "run_id": run_id,
            "source_id": str(parsed.hostname),
            "adapter_version": report["parser_version"],
            "state": state,
            "requested_at": parse_time(report["requested_at"]),
            "received_at": parse_time(report["received_at"]) if report.get("received_at") else None,
            "validated_at": parse_time(report["validated_at"]) if state == "accepted" else None,
            "source_published_at": parse_time(report["source_publication_time"])
            if report.get("source_publication_time")
            else None,
            "raw_artifact_id": raw_id,
            "http_status": report.get("http_status"),
            "record_count": report.get("record_count"),
            "validation_summary": summary,
        }
        return register(conn, "source_checks", record)
    except (EvidenceError, psycopg.Error, OSError):
        failure_directory.mkdir(parents=True, exist_ok=True)
        failure = {
            "run_id": run_id,
            "check_id": check_id,
            "reason_code": "evidence_persistence_failed",
            "durable_recording_confirmed": False,
        }
        # A new report preserves each failed attempt without exposing server text.
        from uuid import uuid4

        with (failure_directory / f"{uuid4().hex}.json").open("x", encoding="utf-8") as stream:
            import json

            json.dump(failure, stream, sort_keys=True)
        raise EvidenceError(
            "Evidence persistence failed; sanitized local report retained"
        ) from None
