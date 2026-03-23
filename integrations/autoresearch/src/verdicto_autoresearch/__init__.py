"""verdicto-autoresearch — Cryptographic audit trails for autonomous AI research."""

from .callback import ExperimentCallback
from .config import AutoresearchConfig
from .program_md import generate_program_md_snippet

__version__ = "0.1.0"

__all__ = [
    "__version__",
    "ExperimentCallback",
    "AutoresearchConfig",
    "generate_program_md_snippet",
]
