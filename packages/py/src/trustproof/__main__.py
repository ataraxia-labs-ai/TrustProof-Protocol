from __future__ import annotations

import argparse
import base64
import json
import sys
from pathlib import Path
from typing import Any

from .verify import verify as verify_token


def _decode_base64url_to_utf8(value: str) -> str:
    normalized = value.replace("-", "+").replace("_", "/")
    padding = "=" * ((4 - (len(normalized) % 4)) % 4)
    return base64.b64decode(f"{normalized}{padding}").decode("utf-8")


def _decode_jwt_payload_untrusted(token: str) -> dict[str, Any]:
    parts = token.split(".")
    if len(parts) != 3:
        raise ValueError("Token must be compact JWS (three dot-separated segments).")

    payload_json = _decode_base64url_to_utf8(parts[1])
    payload = json.loads(payload_json)
    if not isinstance(payload, dict):
        raise ValueError("JWT payload must decode to a JSON object.")
    return payload


def _load_public_key_pem(pubkey_arg: str) -> str:
    if "BEGIN PUBLIC KEY" in pubkey_arg:
        return pubkey_arg

    path = Path(pubkey_arg)
    if path.exists() and path.is_file():
        return path.read_text(encoding="utf-8")

    return _decode_base64url_to_utf8(pubkey_arg)


def _format_verify_summary(claims: Any) -> str:
    if not isinstance(claims, dict):
        return "✅ Verified"

    subject = claims.get("subject") if isinstance(claims.get("subject"), dict) else {}
    resource = claims.get("resource") if isinstance(claims.get("resource"), dict) else {}
    result = claims.get("result") if isinstance(claims.get("result"), dict) else {}
    hashes = claims.get("hashes") if isinstance(claims.get("hashes"), dict) else {}
    chain = claims.get("chain") if isinstance(claims.get("chain"), dict) else {}

    subject_type = subject.get("type", "unknown")
    subject_id = subject.get("id", "unknown")
    action = claims.get("action", "unknown")
    decision = result.get("decision", "unknown")
    resource_type = resource.get("type", "unknown")
    resource_id = resource.get("id", "unknown")
    timestamp = claims.get("timestamp", "unknown")
    jti = claims.get("jti", "unknown")

    return "\n".join(
        [
            "✅ Verified",
            f"Subject: {subject_type}:{subject_id}",
            f"Action: {action}",
            f"Decision: {decision}",
            f"Resource: {resource_type}:{resource_id}",
            f"Timestamp: {timestamp}",
            f"JTI: {jti}",
            f"Hashes: input={_short_hash(hashes.get('input_hash'))} output={_short_hash(hashes.get('output_hash'))}",
            f"Chain: prev={_short_hash(chain.get('prev_hash'))} entry={_short_hash(chain.get('entry_hash'))}",
        ]
    )


def _short_hash(value: Any) -> str:
    if not isinstance(value, str) or not value:
        return "unknown"
    return f"{value[:6]}…"


def _format_not_verified(errors: list[dict[str, Any]]) -> str:
    lines = ["❌ Not Verified"]
    for error in errors:
        code = error.get("code", "UNKNOWN_ERROR")
        message = error.get("message", "Unknown verification error.")
        lines.append(f"{code}: {message}")
    return "\n".join(lines)


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="trustproof",
        description="TrustProof CLI — Signed, verifiable action receipts for AI agents.",
    )
    subparsers = parser.add_subparsers(dest="command")

    verify_parser = subparsers.add_parser("verify", help="Verify a signed TrustProof JWT")
    verify_parser.add_argument("jwt", help="JWT token")
    verify_parser.add_argument("--pubkey", required=True, help="Public key PEM, base64 PEM, or path")
    verify_parser.add_argument("--json", action="store_true", help="Emit machine-readable JSON")

    inspect_parser = subparsers.add_parser("inspect", help="Inspect JWT payload without verification")
    inspect_parser.add_argument("jwt", help="JWT token")
    inspect_parser.add_argument("--json", action="store_true", help="Emit machine-readable JSON")

    subparsers.add_parser("version", help="Print version")
    subparsers.add_parser("schema", help="Print the TrustProof JSON Schema to stdout")

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)

    if not args.command:
        parser.print_help()
        return 0

    if args.command == "version":
        from . import __version__

        print(f"trustproof {__version__}")
        return 0

    if args.command == "schema":
        schema_path = Path(__file__).resolve().parent.parent.parent.parent / "spec" / "trustproof.schema.json"
        if not schema_path.exists():
            # Fallback: try relative to installed package (won't have spec/)
            print('{"error": "Schema file not found. Install from source to access schema."}', file=sys.stderr)
            return 1
        print(schema_path.read_text(encoding="utf-8"), end="")
        return 0

    if args.command == "inspect":
        try:
            payload = _decode_jwt_payload_untrusted(args.jwt)
        except Exception as exc:  # noqa: BLE001
            if args.json:
                print(
                    json.dumps(
                        {"error": str(exc)},
                        ensure_ascii=False,
                        separators=(",", ":"),
                    )
                )
            else:
                print(f"FAIL\n{exc}", file=sys.stderr)
            return 1

        if args.json:
            print(json.dumps(payload, ensure_ascii=False, separators=(",", ":")))
        else:
            print(json.dumps(payload, ensure_ascii=False, indent=2))
        return 0

    if args.command == "verify":
        try:
            public_key_pem = _load_public_key_pem(args.pubkey)
        except Exception as exc:  # noqa: BLE001
            result = {
                "ok": False,
                "errors": [{"code": "PUBKEY_LOAD_ERROR", "message": str(exc)}],
            }
            if args.json:
                print(json.dumps(result, ensure_ascii=False, separators=(",", ":")))
            else:
                print(_format_not_verified(result["errors"]), file=sys.stderr)
            return 1

        result = verify_token(args.jwt, public_key_pem)

        if args.json:
            print(json.dumps(result, ensure_ascii=False, separators=(",", ":")))
        elif result.get("ok"):
            print(_format_verify_summary(result.get("claims")))
        else:
            print(_format_not_verified(result.get("errors", [])), file=sys.stderr)

        return 0 if result.get("ok") else 1

    parser.print_help()
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
