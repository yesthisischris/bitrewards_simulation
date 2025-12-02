from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import List, Optional


class ContributionType(str, Enum):
    CORE_RESEARCH = "core_research"
    FUNDING = "funding"
    SUPPORTING = "supporting"


@dataclass
class Contribution:
    contribution_id: str
    project_id: Optional[str]
    owner_id: int
    contribution_type: ContributionType
    quality: float
    parents: List[str] = field(default_factory=list)


@dataclass
class UsageEvent:
    contribution_id: str
    gross_value: float
    fee_amount: float
