"""Manual API rehearsal against disposable fixture objects, never official data."""

import json
import re
from typing import Any
from uuid import uuid4

from hoop.platform.artifacts import ArtifactError, PrivateArtifacts, Session
from hoop.platform.provenance import digest


def verify(session: Session, other: Session, unrelated_bucket: str) -> dict[str, Any]:
    if (
        other.settings.user_id == session.settings.user_id
        or not unrelated_bucket
        or unrelated_bucket == session.settings.bucket
        or re.fullmatch(r"[a-z0-9-]{1,63}", unrelated_bucket) is None
    ):
        raise ArtifactError("distinct_negative_test_identity_and_bucket_required")
    body = ("Baseline storage rehearsal " + uuid4().hex).encode()
    descriptor = PrivateArtifacts(session).put(body, kind="reports", format="txt")
    bucket = session.settings.bucket
    key = f"reports/{digest(body)[:2]}/{digest(body)}"
    path = f"/storage/v1/object/{bucket}/{key}"
    download = f"/storage/v1/object/authenticated/{bucket}/{key}"
    moved_hash = digest(b"moved-" + body)
    operations = {
        "replacement": ("PUT", path, b"different", {}),
        "upsert": ("POST", path, b"different", {"x-upsert": "true"}),
        "delete": (
            "DELETE",
            f"/storage/v1/object/{bucket}",
            json.dumps({"prefixes": [key]}).encode(),
            {},
        ),
        "move": (
            "POST",
            "/storage/v1/object/move",
            json.dumps(
                {
                    "bucketId": bucket,
                    "sourceKey": key,
                    "destinationKey": f"reports/{moved_hash[:2]}/{moved_hash}",
                }
            ).encode(),
            {},
        ),
        "bucket_admin": ("PUT", f"/storage/v1/bucket/{bucket}", b'{"public":false}', {}),
        "unrelated_bucket": (
            "POST",
            f"/storage/v1/object/{unrelated_bucket}/{key}",
            body,
            {"x-upsert": "false"},
        ),
        "private_api": (
            "GET",
            "/rest/v1/runs?select=run_id&limit=1",
            None,
            {"Accept-Profile": "platform"},
        ),
    }
    checks: dict[str, Any] = {"create_read_verified": True}
    for name, (method, url, data, headers) in operations.items():
        result = session.request(
            method, url, data, headers={"Content-Type": "application/json", **headers}
        )
        # 404 alone could mean a bad endpoint; only authorization-denial codes
        # count for mutation probes. API schema rejection can legitimately be 406.
        checks[name] = {
            "status": result.status,
            "denied": result.status in {401, 403}
            or (name == "private_api" and result.status == 406),
        }
    other_result = other.request("GET", download)
    anonymous = session.transport.request(
        "GET", session.settings.url + download, {"apikey": session.settings.key}, None
    )
    checks["other_identity_read"] = {
        "status": other_result.status,
        "denied": other_result.status in {401, 403, 404},
    }
    checks["anonymous_read"] = {
        "status": anonymous.status,
        "denied": anonymous.status in {401, 403, 404},
    }
    # Explicitly attempt create as both negative identities too.
    other_path = f"/storage/v1/object/{bucket}/models/{digest(body)[:2]}/{digest(body)}"
    anon_path = f"/storage/v1/object/{bucket}/features/{digest(body)[:2]}/{digest(body)}"
    other_write = other.request("POST", other_path, body, headers={"x-upsert": "false"})
    anon_write = session.transport.request(
        "POST",
        session.settings.url + anon_path,
        {"apikey": session.settings.key, "x-upsert": "false"},
        body,
    )
    checks["other_identity_create"] = {
        "status": other_write.status,
        "denied": other_write.status in {401, 403},
    }
    checks["anonymous_create"] = {
        "status": anon_write.status,
        "denied": anon_write.status in {401, 403},
    }
    final = session.request("GET", download)
    checks["original_bytes_preserved"] = final.status == 200 and final.body == body
    ok = all(value if isinstance(value, bool) else value["denied"] for value in checks.values())
    return {
        "verified": ok,
        "checks": checks,
        "fixture": descriptor,
        "note": "No cleanup by runtime; administrator maintenance is separate",
    }
