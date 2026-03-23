"""TrustProof — Signed, verifiable action receipts for humans + AI agents."""

from .chain import append, verify_chain
from .generate import generate
from .mesh import (
    Issuer,
    IssuerRegistry,
    IssuerTrust,
    MeshLink,
    MeshVerification,
    MeshVerifier,
)
from .types import (
    ChainResult,
    ErrorInfo,
    ProtocolRefs,
    TrustProofClaims,
    VCProfile,
    VerifyResult,
)
from .verify import verify

__version__ = "0.2.0"

__all__ = [
    "__version__",
    "generate",
    "verify",
    "append",
    "verify_chain",
    "TrustProofClaims",
    "VerifyResult",
    "ChainResult",
    "ErrorInfo",
    "ProtocolRefs",
    "VCProfile",
    "Issuer",
    "IssuerRegistry",
    "IssuerTrust",
    "MeshLink",
    "MeshVerification",
    "MeshVerifier",
]
