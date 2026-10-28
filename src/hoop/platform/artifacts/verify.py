"""Manual API rehearsal against disposable fixture objects, never official data."""

import base64
import json
import re
from collections.abc import Callable
from typing import Any
from uuid import uuid4

from hoop.platform.artifacts import (
    ArtifactError,
    PrivateArtifacts,
    Response,
    Session,
    is_storage_error,
)
from hoop.platform.provenance import digest


def _denied(response: Response, *, concealed_read: bool = False) -> bool:
    return (
        response.status in {401, 403}
        or is_storage_error(response, code="AccessDenied", status=403)
        or (
            concealed_read
            and (response.status == 404 or is_storage_error(response, code="NoSuchKey", status=404))
        )
    )


def verify(
    session: Session,
    other: Session,
    unrelated_bucket: str,
    *,
    policies: Callable[[], dict[str, Any]] | None = None,
) -> dict[str, Any]:
    if (
        other.settings.user_id == session.settings.user_id
        or not unrelated_bucket
        or unrelated_bucket == session.settings.bucket
        or re.fullmatch(r"[a-z0-9-]{1,63}", unrelated_bucket) is None
    ):
        raise ArtifactError("distinct_negative_test_identity_and_bucket_required")
    policy_before = policies() if policies else None
    if policies:
        session.authenticate()
        # This diagnoses the role of a token returned by the trusted Auth API;
        # the Storage service still validates its signature on every request.
        try:
            payload = session.access.split(".")[1]
            claims = json.loads(base64.urlsafe_b64decode(payload + "=" * (-len(payload) % 4)))
        except (ValueError, IndexError):
            raise ArtifactError("api_role_claim_not_verified") from None
        if (
            not isinstance(claims, dict)
            or claims.get("role") != "authenticated"
            or claims.get("sub") != session.settings.user_id
        ):
            raise ArtifactError("api_role_claim_not_verified")
    body = ("Baseline storage rehearsal " + uuid4().hex).encode()
    descriptor = PrivateArtifacts(session).put(body, kind="reports", format="txt")
    bucket = session.settings.bucket
    key = f"reports/{digest(body)[:2]}/{digest(body)}"
    path = f"/storage/v1/object/{bucket}/{key}"
    download = f"/storage/v1/object/authenticated/{bucket}/{key}"
    moved_hash = digest(b"moved-" + body)
    destination = f"/storage/v1/object/authenticated/{bucket}/reports/{moved_hash[:2]}/{moved_hash}"
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
    mutation_bytes_verified = True
    for name, (method, url, data, headers) in operations.items():
        before = session.request("GET", download) if policies and name != "private_api" else None
        destination_before = (
            session.request("GET", destination) if policies and name == "move" else None
        )
        result = session.request(
            method, url, data, headers={"Content-Type": "application/json", **headers}
        )
        after = session.request("GET", download) if policies and name != "private_api" else None
        # 404 alone could mean a bad endpoint; only authorization-denial codes
        # count for mutation probes. API schema rejection can legitimately be 406.
        checks[name] = {
            "status": result.status,
            "denied": _denied(result) or (name == "private_api" and result.status == 406),
        }
        if policies and name != "private_api":
            mutation_bytes_verified = mutation_bytes_verified and (
                before is not None
                and before.status == 200
                and before.body == body
                and after is not None
                and after.status == 200
                and after.body == body
            )
        if policies and name in {"delete", "move", "bucket_admin"}:
            unchanged = (
                before is not None
                and before.status == 200
                and before.body == body
                and after is not None
                and after.status == 200
                and after.body == body
            )
            prevented = False
            if name == "delete" and result.status == 200:
                try:
                    prevented = json.loads(result.body) == []
                except ValueError:
                    pass
            elif name == "move":
                destination_after = session.request("GET", destination)

                def absent(response: Response) -> bool:
                    return response.status == 404 or is_storage_error(
                        response, code="NoSuchKey", status=404
                    )

                prevented = (
                    is_storage_error(result, code="NoSuchKey", status=404)
                    and destination_before is not None
                    and absent(destination_before)
                    and absent(destination_after)
                )
            elif name == "bucket_admin":
                prevented = is_storage_error(result, code="NoSuchBucket", status=404)
            checks[name]["original_bytes_unchanged"] = unchanged
            checks[name]["prevention_verified"] = unchanged and prevented
    other_result = other.request("GET", download)
    anonymous = session.transport.request(
        "GET", session.settings.url + download, {"apikey": session.settings.key}, None
    )
    checks["other_identity_read"] = {
        "status": other_result.status,
        "denied": _denied(other_result, concealed_read=True),
    }
    checks["anonymous_read"] = {
        "status": anonymous.status,
        "denied": _denied(anonymous, concealed_read=True),
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
        "denied": _denied(other_write),
    }
    checks["anonymous_create"] = {
        "status": anon_write.status,
        "denied": _denied(anon_write),
    }
    final = session.request("GET", download)
    checks["original_bytes_preserved"] = final.status == 200 and final.body == body
    policy_after = policies() if policies else None
    if policies:
        checks["mutation_bytes_verified"] = mutation_bytes_verified
        checks["policy_stable"] = policy_before == policy_after and bool(
            policy_before and policy_before.get("verified")
        )
    ok = all(
        value
        if isinstance(value, bool)
        else value["denied"] or value.get("prevention_verified", False)
        for value in checks.values()
    )
    return {
        "verified": ok,
        "policy_evidence": policy_after,
        "checks": checks,
        "fixture": descriptor,
        "note": "No cleanup by runtime; administrator maintenance is separate",
    }
