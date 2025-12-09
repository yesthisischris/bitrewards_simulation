from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import List, Optional


class ContributionType(str, Enum):
    CORE_RESEARCH = "core_research"
    FUNDING = "funding"
    SUPPORTING = "supporting"


class EdgeType(str, Enum):
    DERIVATIVE = "derivative"
    FUNDING = "funding"
    SUPPORTING = "supporting"
    OTHER = "other"


class HonorSealStatus(str, Enum):
    NONE = "none"
    HONEST = "honest"
    FAKE = "fake"
    DISHONORED = "dishonored"


@dataclass
class Contribution:
    contribution_id: str
    project_id: Optional[str]
    owner_id: int
    contribution_type: ContributionType
    quality: float
    parents: List[str] = field(default_factory=list)
    true_parents: List[str] = field(default_factory=list)
    funding_raised: float = 0.0
    royalty_percent: Optional[float] = None
    usage_count: int = 0
    lockup_remaining_steps: int = 0
    is_performance_verified: bool = False
    kind: Optional[str] = None
    accrued_royalty_value: float = 0.0
    honor_seal_status: HonorSealStatus = HonorSealStatus.NONE
    honor_seal_mint_step: Optional[int] = None


@dataclass
class UsageEvent:
    contribution_id: str
    gross_value: float
    fee_amount: float


@dataclass
class TreasuryState:
    balance: float = 0.0
    cumulative_inflows: float = 0.0
    cumulative_outflows: float = 0.0
