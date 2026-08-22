from typing import Any, Literal, Optional

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel

from app.guardrails.banned_phrases import check_banned_phrases
from app.guardrails.channel_format import check_channel_format
from app.guardrails.llm_judge import check_llm_judge
from app.guardrails.pii import check_pii
from app.guardrails.unsubstantiated_claims import check_unsubstantiated_claims
from app.models.draft import (
    Channel,
    Draft,
    DraftStatus,
    HumanDecision,
    HumanDecisionType,
    VerificationRound,
)
from app.repository import DEFAULT_DB_PATH, get_draft, save_draft
from app.services.generator import GenerationError, generate_pitch

router = APIRouter(tags=["drafts"])


def get_db_path() -> str:
    """Returns the database file path to use for requests.

    Dynamic indirection function so tests can patch get_db_path to redirect to temporary SQLite databases.
    """
    return DEFAULT_DB_PATH


class CreateDraftRequest(BaseModel):
    prospect_profile: dict[str, Any]
    campaign_brief: dict[str, Any]
    channel: Channel


class RecordDecisionRequest(BaseModel):
    decision: Literal["approve", "reject"]
    note: Optional[str] = None


@router.post("/drafts", response_model=Draft, status_code=status.HTTP_201_CREATED)
def create_draft(req: CreateDraftRequest):
    """POST /drafts: Generates pitch message and creates a pending_verification draft."""
    try:
        pitch = generate_pitch(req.prospect_profile, req.campaign_brief, req.channel)
    except GenerationError as e:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Generation failed: {str(e)}",
        )

    draft = Draft(
        channel=req.channel,
        prospect_profile=req.prospect_profile,
        campaign_brief=req.campaign_brief,
        generated_pitch=pitch,
        status=DraftStatus.PENDING_VERIFICATION,
        guardrail_verdicts=[],
    )
    db_path = get_db_path()
    save_draft(draft, db_path=db_path)
    return draft


@router.post("/drafts/{id}/verify", response_model=Draft)
def verify_draft(id: str):
    """POST /drafts/{id}/verify: Runs all 5 guardrail rules and appends a VerificationRound."""
    db_path = get_db_path()
    draft = get_draft(id, db_path=db_path)
    if draft is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Draft not found",
        )

    # Run ALL FIVE guardrail rules unconditionally (no short-circuiting)
    verdict_1 = check_pii(draft)
    verdict_2 = check_banned_phrases(draft)
    verdict_3 = check_channel_format(draft)
    verdict_4 = check_unsubstantiated_claims(draft)
    verdict_5 = check_llm_judge(draft)

    verdicts = [verdict_1, verdict_2, verdict_3, verdict_4, verdict_5]
    all_passed = all(v.passed for v in verdicts)

    new_round = VerificationRound(verdicts=verdicts)
    draft.guardrail_verdicts.append(new_round)

    if all_passed:
        draft.status = DraftStatus.VERIFIED_PASS
    else:
        draft.status = DraftStatus.VERIFIED_FAIL

    save_draft(draft, db_path=db_path)
    return draft


@router.get("/drafts/{id}", response_model=Draft)
def retrieve_draft(id: str):
    """GET /drafts/{id}: Retrieves draft record by ID."""
    db_path = get_db_path()
    draft = get_draft(id, db_path=db_path)
    if draft is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Draft not found",
        )
    return draft


@router.post("/drafts/{id}/decision", response_model=Draft)
def record_decision(id: str, req: RecordDecisionRequest):
    """POST /drafts/{id}/decision: Records human reviewer approval/rejection decision."""
    db_path = get_db_path()
    draft = get_draft(id, db_path=db_path)
    if draft is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Draft not found",
        )

    if draft.status == DraftStatus.PENDING_VERIFICATION:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Cannot record decision on unverified draft (pending_verification status)",
        )

    if draft.human_decision is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Decision already recorded — re-verify to make a new decision.",
        )

    decision_type = (
        HumanDecisionType.APPROVE
        if req.decision == "approve"
        else HumanDecisionType.REJECT
    )
    draft.human_decision = HumanDecision(
        decision=decision_type,
        note=req.note,
    )

    if req.decision == "approve":
        draft.status = DraftStatus.APPROVED
    else:
        draft.status = DraftStatus.REJECTED

    save_draft(draft, db_path=db_path)
    return draft
