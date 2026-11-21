# Implements: work-contracts/WC-136-common-agent-workbench-spend-accounts-and-pricing-engine.md C1-04
# Constitutional basis: C-059, C-048, C-049, C-063
"""Protocol policy (STOP and START behaviour) read from the visitor content catalogue.

The product and the simulation judge read the same ``protocol`` object, so the judge cannot disagree with the
product about whether a STOP is acknowledged (architecture package section 6.6, WC136-R004).
"""

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_CONTENT_PATH = REPOSITORY_ROOT / "src/business-platform/Catalog/Visitor/waooaw-demo.v1.json"
FIXED_REF_PREFIX = "fixed."


class PolicyError(ValueError):
    pass


@dataclass(frozen=True)
class ProtocolPolicy:
    version: str
    fingerprint: str
    stop_acknowledges: bool
    stop_acknowledgement: str
    maximum_acknowledgements_per_stop: int
    stop_channels: tuple[str, ...]
    start_requires_consent: bool
    start_notice: str


def _object(value: Any, where: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise PolicyError(f"{where} must be an object")
    return value


def _flag(data: dict[str, Any], key: str, where: str) -> bool:
    value = data.get(key)
    if not isinstance(value, bool):
        raise PolicyError(f"{where}.{key} must be true or false")
    return value


def _fixed_text(content: dict[str, Any], ref: Any, where: str) -> str:
    """Resolves a ``fixed.<name>`` reference to its non-empty text."""
    if not isinstance(ref, str) or not ref.startswith(FIXED_REF_PREFIX):
        raise PolicyError(f"{where} must reference a fixed text such as '{FIXED_REF_PREFIX}stopAcknowledged'")
    fixed = content.get("fixed")
    text = fixed.get(ref[len(FIXED_REF_PREFIX) :]) if isinstance(fixed, dict) else None
    if not isinstance(text, str) or not text.strip():
        raise PolicyError(f"{where} '{ref}' does not resolve to a non-empty fixed text")
    return text


def parse_protocol_policy(content: Any) -> ProtocolPolicy:
    """Validates the ``protocol`` object of a content catalogue; any gap fails closed with ``PolicyError``."""
    root = _object(content, "content catalogue")
    if "protocol" not in root:
        raise PolicyError("content catalogue has no 'protocol' object")
    protocol = _object(root["protocol"], "protocol")
    version = protocol.get("version")
    if not isinstance(version, str) or not version.strip():
        raise PolicyError("protocol.version must be a non-empty string")
    stop = _object(protocol.get("stop"), "protocol.stop")
    start = _object(protocol.get("start"), "protocol.start")
    acknowledges = _flag(stop, "acknowledge", "protocol.stop")
    acknowledgement = _fixed_text(root, stop.get("acknowledgementRef"), "protocol.stop.acknowledgementRef")
    maximum = stop.get("maximumAcknowledgementsPerStop")
    if isinstance(maximum, bool) or maximum != 1:
        raise PolicyError("protocol.stop.maximumAcknowledgementsPerStop must be 1")
    channels = stop.get("channels")
    if not isinstance(channels, list) or not channels or not all(isinstance(c, str) and c.strip() for c in channels):
        raise PolicyError("protocol.stop.channels must be a non-empty list of channel names")
    requires_consent = _flag(start, "consentRequiredAgain", "protocol.start")
    notice = _fixed_text(root, start.get("noticeRef"), "protocol.start.noticeRef")
    canonical = json.dumps(
        {"protocol": protocol, "stopAcknowledgement": acknowledgement, "startNotice": notice},
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    )
    return ProtocolPolicy(
        version=version,
        fingerprint=hashlib.sha256(canonical.encode("utf-8")).hexdigest()[:16],
        stop_acknowledges=acknowledges,
        stop_acknowledgement=acknowledgement,
        maximum_acknowledgements_per_stop=1,
        stop_channels=tuple(channels),
        start_requires_consent=requires_consent,
        start_notice=notice,
    )


def load_protocol_policy(path: str | Path | None = None) -> ProtocolPolicy:
    """Reads the protocol policy from the content JSON (default: the demo catalogue the product serves)."""
    source = Path(path) if path else DEFAULT_CONTENT_PATH
    try:
        content = json.loads(source.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise PolicyError(f"cannot read content catalogue {source}: {type(exc).__name__}") from exc
    return parse_protocol_policy(content)
