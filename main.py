from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from ticket_agent_graph import process_ticket_with_graph as process_ticket
from database import save_ticket
from database import get_connection


# =========================================================
# 1. INITIALIZE FASTAPI
# =========================================================

app = FastAPI(
    title="AI Support Ticket Triage Agent",
    description=(
        "LangGraph-based support ticket classification, "
        "risk assessment, knowledge retrieval and human review."
    ),
    version="2.0.0",
)


# =========================================================
# 2. ENABLE CORS
# =========================================================
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:5174",
        "http://127.0.0.1:5174",
        "https://support-ticket-agent.vercel.app",
        "https://support-ticket-agent-bkvnsri6w-hemant-mishra.vercel.app",
    ],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

# =========================================================
# 3. REQUEST MODELS
# =========================================================

class TicketRequest(BaseModel):
    ticket: str = Field(..., min_length=5)


class FollowUpRequest(BaseModel):
    ticket: str = Field(..., min_length=5)

    conversation_history: list[dict] = Field(
        default_factory=list
    )

    attempt_number: int = Field(
        default=1,
        ge=1,
        le=3,
    )


class BatchTestRequest(BaseModel):
    tickets: list[str] = Field(
        ...,
        min_length=1,
        max_length=10,
    )


# =========================================================
# 4. HOME ENDPOINT
# =========================================================

@app.get("/")
def home():
    return {
        "message": "AI Support Ticket Triage Agent is running!",
        "version": "2.0.0",
        "status": "healthy",
    }


# =========================================================
# 5. CREATE AND SAVE A SUPPORT TICKET
# =========================================================

@app.post("/tickets")
def create_ticket(request: TicketRequest):
    try:
        # Process ticket through LangGraph
        result = process_ticket(request.ticket)

        # Save the processed ticket to PostgreSQL
        ticket_id = save_ticket(result)

        # Return the saved ticket information
        return {
            "success": True,
            "ticket_id": ticket_id,
            "ticket": result.get(
                "ticket",
                request.ticket,
            ),
            "category": result.get("category"),
            "categories": result.get("categories", []),
            "sentiment": result.get("sentiment"),
            "risk_level": result.get("risk_level"),
            "priority": result.get("priority"),
            "action": result.get("action"),
            "needs_human_review": result.get(
                "needs_human_review",
                True,
            ),
            "reason": result.get("reason"),
            "draft_reply": result.get("draft_reply", ""),
            "sources": result.get("sources", []),
            "submitted_to_support_queue": True,
            "submission_message": (
                "Your support ticket has been saved "
                "to the support ticket queue."
            ),
        }

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Ticket processing or saving failed: {str(e)}",
        )


# =========================================================
# 6. FOLLOW-UP CONVERSATION ENDPOINT
# =========================================================

@app.post("/tickets/follow-up")
def ticket_follow_up(request: FollowUpRequest):
    try:
        # Build conversation text from previous messages
        history_lines = []

        for item in request.conversation_history:
            role = item.get("role", "student")
            content = item.get("content", "")

            if content:
                history_lines.append(
                    f"{role}: {content}"
                )

        # Include previous conversation in the ticket context
        complete_ticket = request.ticket

        if history_lines:
            complete_ticket += (
                "\n\nPrevious conversation:\n"
                + "\n".join(history_lines)
            )

        # Process the updated context through LangGraph
        result = process_ticket(
            complete_ticket,
            conversation_history=request.conversation_history,
            attempt_number=request.attempt_number,
        )

        # This endpoint does not create a new database ticket.
        # Final submission must happen through the submission flow.
        return {
            "success": True,
            "ticket": request.ticket,
            "category": result.get("category"),
            "categories": result.get("categories", []),
            "sentiment": result.get("sentiment"),
            "risk_level": result.get("risk_level"),
            "priority": result.get("priority"),
            "draft_reply": result.get("draft_reply", ""),
            "sources": result.get("sources", []),
            "needs_human_review": result.get(
                "needs_human_review",
                True,
            ),
            "action": result.get(
                "action",
                "HUMAN_REVIEW",
            ),
            "reason": result.get("reason", ""),
            "attempt_number": request.attempt_number,
            "submitted_to_support_queue": False,
            "submission_message": (
                "This is a follow-up response. "
                "The support ticket has not been newly submitted."
            ),
        }

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Follow-up processing failed: {str(e)}",
        )


# =========================================================
# 7. FETCH ALL TICKETS FOR ADMIN DASHBOARD
# =========================================================

@app.get("/tickets")
def get_tickets():
    try:
        query = """
            SELECT
                id,
                ticket_text,
                category,
                sentiment,
                risk_level,
                priority,
                action,
                needs_human_review,
                reason,
                draft_reply,
                sources,
                created_at
            FROM support_tickets
            ORDER BY created_at DESC;
        """

        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(query)
                rows = cur.fetchall()

        tickets = []

        for row in rows:
            tickets.append({
                "ticket_id": row[0],
                "ticket": row[1],
                "category": row[2],
                "sentiment": row[3],
                "risk_level": row[4],
                "priority": row[5],
                "action": row[6],
                "needs_human_review": row[7],
                "reason": row[8],
                "draft_reply": row[9],
                "sources": row[10],
                "created_at": (
                    row[11].isoformat()
                    if row[11]
                    else None
                ),
            })

        return {
            "total_tickets": len(tickets),
            "tickets": tickets,
        }

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Could not fetch tickets: {str(e)}",
        )


# =========================================================
# 8. TEST MULTIPLE TICKETS
# =========================================================

@app.post("/test-tickets")
def test_tickets(request: BatchTestRequest):
    results = []

    for index, ticket in enumerate(
        request.tickets,
        start=1,
    ):
        try:
            result = process_ticket(ticket)

            results.append({
                "test_id": index,
                "ticket": ticket,
                "category": result.get(
                    "category",
                    "unknown",
                ),
                "categories": result.get(
                    "categories",
                    [],
                ),
                "sentiment": result.get(
                    "sentiment",
                    "unknown",
                ),
                "risk_level": result.get(
                    "risk_level",
                    "unknown",
                ),
                "priority": result.get(
                    "priority",
                    "unknown",
                ),
                "action": result.get(
                    "action",
                    "HUMAN_REVIEW",
                ),
                "needs_human_review": result.get(
                    "needs_human_review",
                    True,
                ),
                "reason": result.get("reason", ""),
                "draft_reply": result.get(
                    "draft_reply",
                    "",
                ),
                "sources": result.get(
                    "sources",
                    [],
                ),
                "error": None,
            })

        except Exception as e:
            results.append({
                "test_id": index,
                "ticket": ticket,
                "error": str(e),
            })

    successful = sum(
        1 for item in results
        if item.get("error") is None
    )

    return {
        "total_tested": len(results),
        "successful": successful,
        "failed": len(results) - successful,
        "results": results,
    }