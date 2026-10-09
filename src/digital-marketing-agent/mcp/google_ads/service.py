"""Deterministic Google Ads emulator with no provider connection."""

# Implements: architecture/reference/components/dma-demand-search-lifecycle-and-advanced-solution-contract.md §7.3, §13
# Constitutional basis: C-001, C-041, C-059, C-063, ADR-020, ADR-026

from contracts.cde.foundation import DeterministicOwnerEmulator


class GoogleAdsEmulator(DeterministicOwnerEmulator):
    provider = "GOOGLE"
    operations = frozenset(
        {
            "paid_media.get_account_readiness",
            "paid_media.create_campaign",
            "paid_media.get_campaign_status",
            "paid_media.update_campaign",
            "paid_media.pause_campaign",
            "paid_media.get_spend",
            "paid_media.get_conversion_observations",
            "paid_media.upload_conversion",
        }
    )
