"""AI Shopping Agent API Endpoints v1.

Provides conversational shopping advice, structured product recommendations,
trade-off explanations, and clarification workflows for future frontend integration.
"""

from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field

from torob.agent.models import (
    ProposedAction,
    RecommendationResult,
    ShoppingConstraints,
    ShoppingIntent,
    ShoppingSession,
)
from torob.agent.orchestrator import ShoppingAgentOrchestrator
from torob.core.security import AuthContext, get_auth_context

router = APIRouter(prefix="/assistant", tags=["AI Shopping Assistant"])

# Singleton or instantiated orchestrator
orchestrator = ShoppingAgentOrchestrator()


class CreateSessionRequest(BaseModel):
    user_id: Optional[str] = None
    initial_message: Optional[str] = None


class SendMessageRequest(BaseModel):
    message: str = Field(min_length=1, max_length=1000, description="Customer shopping query or response")
    user_id: Optional[str] = None
    user_lat: Optional[float] = None
    user_lon: Optional[float] = None


class AgentInteractionResponse(BaseModel):
    session_id: str
    reply_text: str
    detected_intent: ShoppingIntent
    active_clarification: Optional[Dict[str, Any]] = None
    constraints: ShoppingConstraints
    recommendations: Optional[RecommendationResult] = None
    proposed_actions: List[ProposedAction] = Field(default_factory=list)


@router.post("/sessions", response_model=Dict[str, Any])
def create_shopping_session(
    body: Optional[CreateSessionRequest] = None,
    auth: AuthContext = Depends(get_auth_context),
):
    """Creates a new conversational shopping session."""
    user_id = (body.user_id if body else None) or auth.user_id
    session = orchestrator.get_or_create_session(user_id=user_id)

    initial_reply = None
    if body and body.initial_message:
        session, initial_reply = orchestrator.process_message(
            session_id=session.session_id,
            user_message=body.initial_message,
            user_id=user_id,
        )

    return {
        "session_id": session.session_id,
        "user_id": session.user_id,
        "created_at": session.created_at.isoformat(),
        "expires_at": session.expires_at.isoformat(),
        "initial_reply": initial_reply,
    }


@router.post("/sessions/{session_id}/messages", response_model=AgentInteractionResponse)
def send_assistant_message(
    session_id: str,
    body: SendMessageRequest,
    auth: AuthContext = Depends(get_auth_context),
):
    """Sends a message to the shopping agent and returns structured recommendations and grounded reply."""
    user_id = body.user_id or auth.user_id
    existing = orchestrator.session_repo.get_session(session_id)
    if not existing:
        raise HTTPException(status_code=404, detail="Shopping session not found or expired")

    if existing.user_id and user_id and existing.user_id != user_id and auth.role.value != "admin":
        raise HTTPException(status_code=403, detail="Unauthorized access to shopping session")

    session, reply_text = orchestrator.process_message(
        session_id=session_id,
        user_message=body.message,
        user_id=user_id or existing.user_id,
        user_lat=body.user_lat,
        user_lon=body.user_lon,
    )

    clarification_dict = None
    if session.clarification_state.active_clarification_question:
        clarification_dict = {
            "question": session.clarification_state.active_clarification_question,
            "options": session.clarification_state.clarification_options,
            "questions_asked": session.clarification_state.questions_asked_count,
            "budget": session.clarification_state.clarification_budget,
        }

    return AgentInteractionResponse(
        session_id=session.session_id,
        reply_text=reply_text,
        detected_intent=session.detected_intent,
        active_clarification=clarification_dict,
        constraints=session.constraints,
        recommendations=session.latest_recommendations,
        proposed_actions=session.proposed_actions,
    )


@router.get("/sessions/{session_id}", response_model=Dict[str, Any])
def get_shopping_session(
    session_id: str,
    auth: AuthContext = Depends(get_auth_context),
):
    """Retrieves full session history, constraints, and recommendations."""
    session = orchestrator.session_repo.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Shopping session not found or expired")

    if session.user_id and auth.user_id and session.user_id != auth.user_id and auth.role.value != "admin":
        raise HTTPException(status_code=403, detail="Unauthorized access to shopping session")

    return {
        "session_id": session.session_id,
        "user_id": session.user_id,
        "detected_intent": session.detected_intent.value,
        "constraints": session.constraints.model_dump(),
        "messages": [m.model_dump() for m in session.messages],
        "created_at": session.created_at.isoformat(),
        "updated_at": session.updated_at.isoformat(),
    }


@router.get("/sessions/{session_id}/recommendations")
def get_session_recommendations(
    session_id: str,
    auth: AuthContext = Depends(get_auth_context),
):
    """Retrieves the latest structured recommendations for the session."""
    session = orchestrator.session_repo.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Shopping session not found or expired")

    if session.user_id and auth.user_id and session.user_id != auth.user_id and auth.role.value != "admin":
        raise HTTPException(status_code=403, detail="Unauthorized access to shopping session")

    if not session.latest_recommendations:
        return {"recommendations": None, "message": "No recommendations generated yet for this session."}

    return session.latest_recommendations.model_dump()
