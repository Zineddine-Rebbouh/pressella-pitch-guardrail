from datetime import datetime, timezone
from enum import Enum
from typing import Any, Optional, Union
from uuid import UUID, uuid4
from pydantic import BaseModel, Field


class Channel(str, Enum):
    EMAIL = "email"
    SMS = "sms"
    WHATSAPP = "whatsapp"


class DraftStatus(str, Enum):
    PENDING_VERIFICATION = "pending_verification"
    VERIFIED_PASS = "verified_pass"
    VERIFIED_FAIL = "verified_fail"
    APPROVED = "approved"
    REJECTED = "rejected"


class HumanDecisionType(str, Enum):
    APPROVE = "approve"
    REJECT = "reject"


class EmailPitch(BaseModel):
    subject: str
    body: str


class FlaggedClaim(BaseModel):
    claim: str
    reason: str


class GuardrailVerdict(BaseModel):
    rule: str
    passed: bool
    reason: str
    flagged_claims: list[FlaggedClaim] = Field(default_factory=list)


class VerificationRound(BaseModel):
    verified_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    verdicts: list[GuardrailVerdict] = Field(default_factory=list)


class HumanDecision(BaseModel):
    decision: HumanDecisionType
    note: Optional[str] = None
    decided_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class Draft(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    channel: Channel
    prospect_profile: dict[str, Any]
    campaign_brief: dict[str, Any]
    generated_pitch: Union[EmailPitch, str]
    status: DraftStatus = DraftStatus.PENDING_VERIFICATION
    guardrail_verdicts: list[VerificationRound] = Field(default_factory=list)
    human_decision: Optional[HumanDecision] = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
