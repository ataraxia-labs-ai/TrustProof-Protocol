from __future__ import annotations

import hmac
import re
from typing import Any

import jwt
from jwt import InvalidTokenError

from .chain import canonical_json, sha256_hex

HEX_64_RE = re.compile(r"^[0-9a-fA-F]{64}$")
REQUIRED_FIELDS = (
    "subject",
    "action",
    "resource",
    "policy",
    "result",
    "hashes",
    "timestamp",
    "jti",
    "chain",
)


def _is_hex64(value: Any) -> bool:
    return isinstance(value, str) and bool(HEX_64_RE.fullmatch(value))


def _error(code: str, message: str, details: Any | None = None) -> dict[str, Any]:
    out: dict[str, Any] = {"code": code, "message": message}
    if details is not None:
        out["details"] = details
    return out


def _validate_claims_minimal(claims: Any) -> list[dict[str, Any]]:
    errors: list[dict[str, Any]] = []
    if not isinstance(claims, dict):
        return [_error("INVALID_SCHEMA", "Claims payload must be a JSON object.")]

    missing_fields = [field for field in REQUIRED_FIELDS if field not in claims]
    if missing_fields:
        errors.append(
            _error(
                "INVALID_SCHEMA",
                "Claims payload is missing required fields.",
                {"missing_fields": missing_fields},
            )
        )

    jti = claims.get("jti")
    if not isinstance(jti, str) or not jti.strip():
        errors.append(_error("MISSING_JTI", "Claims payload must include a non-empty jti."))

    hashes = claims.get("hashes")
    if not isinstance(hashes, dict):
        errors.append(_error("INVALID_SCHEMA", "claims.hashes must be an object."))
    else:
        if not _is_hex64(hashes.get("input_hash")):
            errors.append(
                _error("INVALID_SCHEMA", "claims.hashes.input_hash must be a 64-char hex string.")
            )
        if not _is_hex64(hashes.get("output_hash")):
            errors.append(
                _error(
                    "INVALID_SCHEMA", "claims.hashes.output_hash must be a 64-char hex string."
                )
            )

    chain = claims.get("chain")
    if not isinstance(chain, dict):
        errors.append(_error("INVALID_SCHEMA", "claims.chain must be an object."))
    else:
        if not _is_hex64(chain.get("prev_hash")):
            errors.append(
                _error("INVALID_SCHEMA", "claims.chain.prev_hash must be a 64-char hex string.")
            )
        if not _is_hex64(chain.get("entry_hash")):
            errors.append(
                _error("INVALID_SCHEMA", "claims.chain.entry_hash must be a 64-char hex string.")
            )

    return errors


def verify(
    token: str,
    public_key_pem: str,
    expected_input: dict[str, Any] | None = None,
    expected_output: dict[str, Any] | None = None,
) -> dict[str, Any]:
    try:
        claims = jwt.decode(
            token,
            public_key_pem,
            algorithms=["EdDSA"],
            options={"verify_aud": False, "verify_iss": False},
        )
    except InvalidTokenError as exc:
        return {
            "ok": False,
            "errors": [_error("INVALID_SIGNATURE", "JWT signature verification failed.", str(exc))],
        }

    errors = _validate_claims_minimal(claims)

    if expected_input is not None and isinstance(claims, dict):
        hashes_obj = claims.get("hashes")
        actual_input_hash = hashes_obj.get("input_hash") if isinstance(hashes_obj, dict) else None
        expected_input_hash = sha256_hex(canonical_json(expected_input))
        if not isinstance(actual_input_hash, str) or (
            not hmac.compare_digest(actual_input_hash.lower(), expected_input_hash.lower())
        ):
            errors.append(
                _error(
                    "INPUT_HASH_MISMATCH",
                    "Computed input hash does not match claims.hashes.input_hash.",
                    {"expected_hash": expected_input_hash, "actual_hash": actual_input_hash},
                )
            )

    if expected_output is not None and isinstance(claims, dict):
        hashes_obj = claims.get("hashes")
        actual_output_hash = (
            hashes_obj.get("output_hash") if isinstance(hashes_obj, dict) else None
        )
        expected_output_hash = sha256_hex(canonical_json(expected_output))
        if not isinstance(actual_output_hash, str) or (
            not hmac.compare_digest(actual_output_hash.lower(), expected_output_hash.lower())
        ):
            errors.append(
                _error(
                    "OUTPUT_HASH_MISMATCH",
                    "Computed output hash does not match claims.hashes.output_hash.",
                    {"expected_hash": expected_output_hash, "actual_hash": actual_output_hash},
                )
            )

    if errors:
        return {"ok": False, "claims": claims, "errors": errors}

    return {"ok": True, "claims": claims, "errors": []}
