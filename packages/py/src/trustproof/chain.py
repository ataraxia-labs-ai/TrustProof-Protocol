from __future__ import annotations

import copy
import hmac
import json
import re
from hashlib import sha256
from typing import Any

import jwt

GENESIS_PREV_HASH = "0" * 64
HEX_64_RE = re.compile(r"^[0-9a-fA-F]{64}$")


def normalize_hex(s: str) -> str:
    return s.lower()


def _is_hex64(value: Any) -> bool:
    return isinstance(value, str) and bool(HEX_64_RE.fullmatch(value))


def _error(code: str, message: str, index: int | None = None) -> dict[str, Any]:
    out: dict[str, Any] = {"code": code, "message": message}
    if index is not None:
        out["index"] = index
    return out


def canonical_json(obj: Any) -> str:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def sha256_hex(s: str) -> str:
    return sha256(s.encode("utf-8")).hexdigest()


def compute_canonical_event_material(claims: dict[str, Any]) -> str:
    return canonical_json(
        {
            "subject": claims["subject"],
            "action": claims["action"],
            "resource": claims["resource"],
            "policy": claims["policy"],
            "result": claims["result"],
            "hashes": claims["hashes"],
            "timestamp": claims["timestamp"],
            "jti": claims["jti"],
        }
    )


def compute_entry_hash(prev_hash_hex: str, canonical_event_material: str) -> str:
    if not _is_hex64(prev_hash_hex):
        raise ValueError("prev_hash_hex must be a 64-char hex string.")
    return sha256_hex(f"{normalize_hex(prev_hash_hex)}{canonical_event_material}")


def _extract_prev_entry_hash(prev_payload: Any, label: str) -> str:
    if not isinstance(prev_payload, dict):
        raise ValueError(f"{label} must decode to an object.")
    chain = prev_payload.get("chain")
    if not isinstance(chain, dict):
        raise ValueError(f"{label} is missing chain object.")
    prev_hash = chain.get("entry_hash")
    if not _is_hex64(prev_hash):
        raise ValueError(f"{label} chain.entry_hash must be a 64-char hex string.")
    return normalize_hex(prev_hash)


def append(
    prev: str | dict[str, Any] | None,
    next_claims: dict[str, Any],
    private_key_pem: str,
    kid: str | None = None,
) -> str:
    if prev is None:
        prev_hash = GENESIS_PREV_HASH
    elif isinstance(prev, str):
        untrusted_payload = jwt.decode(
            prev,
            options={
                "verify_signature": False,
                "verify_aud": False,
                "verify_iss": False,
                "verify_exp": False,
            },
        )
        prev_hash = _extract_prev_entry_hash(untrusted_payload, "Previous JWT payload")
    elif isinstance(prev, dict):
        prev_hash = _extract_prev_entry_hash(prev, "Previous claims")
    else:
        raise ValueError("prev must be None, a JWT string, or a claims dict.")

    if not isinstance(next_claims, dict):
        raise ValueError("next_claims must be a dict.")

    claims_to_sign = copy.deepcopy(next_claims)
    chain = claims_to_sign.get("chain")
    if not isinstance(chain, dict):
        chain = {}
    chain["prev_hash"] = prev_hash
    claims_to_sign["chain"] = chain

    canonical_event_material = compute_canonical_event_material(claims_to_sign)
    chain["entry_hash"] = compute_entry_hash(prev_hash, canonical_event_material)

    from .generate import generate

    return generate(claims_to_sign, private_key_pem, kid=kid)


def verify_chain(tokens: list[str], public_key_pem: str) -> dict[str, Any]:
    previous_entry_hash: str | None = None

    from .verify import verify

    for index, token in enumerate(tokens):
        proof_result = verify(token, public_key_pem)
        if not proof_result.get("ok"):
            return {
                "ok": False,
                "errors": [
                    _error(
                        "INVALID_PROOF",
                        "Proof signature/schema verification failed.",
                        index=index,
                    )
                ],
            }

        claims = proof_result.get("claims")
        if not isinstance(claims, dict):
            return {
                "ok": False,
                "errors": [_error("INVALID_PROOF", "Proof claims are missing.", index=index)],
            }

        chain = claims.get("chain")
        if not isinstance(chain, dict):
            return {
                "ok": False,
                "errors": [_error("INVALID_PROOF", "Proof chain is missing.", index=index)],
            }

        prev_hash = chain.get("prev_hash")
        entry_hash = chain.get("entry_hash")
        if not _is_hex64(prev_hash) or not _is_hex64(entry_hash):
            return {
                "ok": False,
                "errors": [
                    _error(
                        "INVALID_PROOF",
                        "Proof chain hashes must be 64-char hex strings.",
                        index=index,
                    )
                ],
            }

        prev_hash_norm = normalize_hex(prev_hash)
        entry_hash_norm = normalize_hex(entry_hash)

        canonical_event_material = compute_canonical_event_material(claims)
        recomputed_entry_hash = compute_entry_hash(prev_hash_norm, canonical_event_material)
        if not hmac.compare_digest(recomputed_entry_hash.lower(), entry_hash_norm):
            return {
                "ok": False,
                "errors": [
                    _error(
                        "CHAIN_ENTRY_HASH_MISMATCH",
                        "chain.entry_hash does not match recomputed entry hash.",
                        index=index,
                    )
                ],
            }

        if index == 0:
            if prev_hash_norm != GENESIS_PREV_HASH:
                return {
                    "ok": False,
                    "errors": [
                        _error(
                            "CHAIN_GENESIS_PREV_HASH_INVALID",
                            "Genesis proof chain.prev_hash must be 64 zeros.",
                            index=index,
                        )
                    ],
                }
        elif not hmac.compare_digest(prev_hash_norm, previous_entry_hash):
            return {
                "ok": False,
                "errors": [
                    _error(
                        "CHAIN_LINK_MISMATCH",
                        "chain.prev_hash does not match previous proof chain.entry_hash.",
                        index=index,
                    )
                ],
            }

        previous_entry_hash = entry_hash_norm

    return {"ok": True, "errors": []}
