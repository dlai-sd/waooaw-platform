# Implements: work-contracts/WC-172-safe-to-charge-real-customers.md WC172-R006
# Constitutional basis: C-038, C-059
"""GST arithmetic over integer paise: the tax split of a GST-inclusive amount, always summing exactly."""

from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any

from markup.package_engine import round_half_up_div

IST = timezone(timedelta(hours=5, minutes=30))


@dataclass(frozen=True)
class TaxSplit:
    taxable_paise: int
    cgst_paise: int
    sgst_paise: int
    igst_paise: int

    @property
    def total_paise(self) -> int:
        return self.taxable_paise + self.cgst_paise + self.sgst_paise + self.igst_paise


def split_inclusive(total_paise: int, rate_percent: int, intra_state: bool) -> TaxSplit:
    """Split a GST-inclusive amount. Taxable value is round(total * 100 / (100 + rate)); the tax is the rest, so the
    parts always add up to the amount paid. Intra-state tax is CGST and SGST (SGST takes the odd paisa); inter-state
    tax is IGST."""
    if total_paise <= 0 or rate_percent < 0:
        raise ValueError("a tax split needs a positive amount and a non-negative rate")
    taxable = round_half_up_div(total_paise * 100, 100 + rate_percent)
    tax = total_paise - taxable
    if intra_state:
        central = tax // 2
        return TaxSplit(taxable, central, tax - central, 0)
    return TaxSplit(taxable, 0, 0, tax)


def sum_splits(splits: Sequence[TaxSplit]) -> TaxSplit:
    return TaxSplit(
        sum(item.taxable_paise for item in splits),
        sum(item.cgst_paise for item in splits),
        sum(item.sgst_paise for item in splits),
        sum(item.igst_paise for item in splits),
    )


def fiscal_year_of(moment: datetime) -> str:
    """The Indian financial year (1 April to 31 March) of an instant, in IST, such as 2026-27."""
    local = moment.astimezone(IST)
    start = local.year if local.month >= 4 else local.year - 1
    return f"{start}-{(start + 1) % 100:02d}"


def document_number(prefix: str, series: str, fiscal_year: str, sequence_no: int) -> str:
    """WAOOAW/2026-27/000042 for invoices and WAOOAW/CN/2026-27/000042 for credit notes."""
    middle = "" if series == "INV" else f"{series}/"
    return f"{prefix}/{middle}{fiscal_year}/{sequence_no:06d}"


def digest_of(body: Mapping[str, Any]) -> str:
    """SHA-256 over the canonical JSON of a document body, so a stored document can be re-derived and compared."""
    canonical = json.dumps(body, sort_keys=True, separators=(",", ":"), ensure_ascii=False, default=str)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()
