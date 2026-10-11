from typing import TypedDict, Any

from langgraph.graph import StateGraph, START, END

from ticket_agent import (
    classify_ticket_details,
    detect_student_risk,
    vector_store,
    should_escalate,
    llm,
)


class TicketState(TypedDict, total=False):
    ticket: str
    conversation_history: Any
    attempt_number: int

    classification: dict
    categories: list
    primary_category: str

    risk_assessment: dict
    retrieved_docs: list
    context: str

    needs_human_review: bool
    reason: str
    draft_reply: str
    sources: list
    action: str
    payment_stage: str


def _history_text(history):
    """Convert frontend conversation history into searchable text."""
    if not history:
        return ""

    parts = []
    for item in history:
        if isinstance(item, dict):
            role = str(item.get("role", "student"))
            content = str(item.get("content", ""))
            if content:
                parts.append(f"{role}: {content}")
        else:
            parts.append(str(item))

    return "\n".join(parts).lower()


def _detect_payment_stage(ticket, categories, history):
    """
    Payment workflow:
    1. First complaint -> give basic troubleshooting.
    2. Student says they tried the steps -> ask whether it is fixed.
    3. Student says it is still unresolved / needs help -> request details.
    """
    history_text = _history_text(history)
    payment_related = any(
        category in categories
        for category in ("payment", "batch_access")
    )

    if not payment_related:
        return "not_payment"

    unresolved_phrases = (
        "i still need help",
        "still not showing",
        "still not activated",
        "still not working",
        "issue is still unresolved",
        "did all the steps",
        "tried all the steps",
        "didn't work",
        "did not work",
        "not fixed",
        "not resolved",
        "same issue",
        "still missing",
        "still facing",
        "problem persists",
    )

    tried_phrases = (
        "i tried these steps",
        "i have tried",
        "i tried",
        "i did all",
        "i followed the steps",
        "i have done that",
        "already tried",
    )

    # Explicitly choosing that the issue remains unresolved takes priority.
    # Only use the conversation history for stage transitions. The original
    # ticket may already say "still not showing", which must NOT skip the
    # first troubleshooting step.
    if any(phrase in history_text for phrase in unresolved_phrases):
        return "collect_details"

    if any(phrase in history_text for phrase in tried_phrases):
        return "check_result"

    return "troubleshoot"


def classify_ticket_node(state: TicketState):
    ticket = state["ticket"]
    classification = classify_ticket_details(ticket)

    payment_stage = _detect_payment_stage(
        ticket,
        classification["categories"],
        state.get("conversation_history", []),
    )

    return {
        "classification": classification,
        "categories": classification["categories"],
        "primary_category": classification["primary_category"],
        "payment_stage": payment_stage,
    }


def detect_risk_node(state: TicketState):
    return {
        "risk_assessment": detect_student_risk(state["ticket"])
    }


def retrieve_knowledge_node(state: TicketState):
    docs = vector_store.similarity_search(state["ticket"], k=3)

    context_parts = []
    sources = set()

    for index, doc in enumerate(docs, start=1):
        source = doc.metadata.get("source", "Unknown")
        sources.add(source)

        context_parts.append(
            f"Document {index}\n"
            f"Source: {source}\n"
            f"Content:\n{doc.page_content}"
        )

    return {
        "retrieved_docs": docs,
        "context": "\n\n".join(context_parts),
        "sources": sorted(sources),
    }


def escalation_check_node(state: TicketState):
    escalate, reason = should_escalate(
        state["ticket"],
        state["classification"],
        state["retrieved_docs"],
    )

    risk = state["risk_assessment"]

    if risk["needs_human_review"]:
        escalate = True
        reason = (
            "Human review recommended: "
            + risk["reason"]
        )

    return {
        "needs_human_review": escalate,
        "reason": reason,
    }
    #

def generate_reply_node(state: TicketState):
    categories = state["categories"]
    risk = state["risk_assessment"]
    payment_stage = state.get("payment_stage", "not_payment")

    history = state.get("conversation_history", [])

    # Extract student messages from conversation history.
    student_messages = [
        str(message.get("content", "")).strip().lower()
        for message in history
        if isinstance(message, dict)
        and message.get("role") == "student"
    ]

    latest_message = (
        student_messages[-1] if student_messages else ""
    )

    # ======================================================
    # 1. PAYMENT WORKFLOW — DETERMINISTIC RESPONSES
    # ======================================================

    payment_related = any(
        category in categories
        for category in ("payment", "batch_access")
    )

    if payment_related:

        # STAGE 1: Initial complaint.
        # Do not ask for transaction details yet.
        if payment_stage == "troubleshoot":
            return {
                "draft_reply": (
                    "I'm sorry you're facing this payment issue. "
                    "Sometimes payment confirmation or batch activation "
                    "may take some time.\n\n"
                    "Please try these steps:\n"
                    "1. Check your bank or payment app for the transaction "
                    "status.\n"
                    "2. If the payment is pending, check whether it is "
                    "later reversed by your bank.\n"
                    "3. Refresh the PW app or website and check your "
                    "batch again.\n"
                    "4. Log out and log back into your PW account.\n\n"
                    "If the issue is still unresolved, click "
                    "'I Still Need Help' below to continue."
                ),
                "action": "HUMAN_REVIEW",
            }

        # STAGE 2: Student tried the steps and wants more help.
        # Direct the student to the support form.
        if payment_stage == "collect_details":
            return {
                "draft_reply": (
                    "I'm sorry the issue is still unresolved.\n\n"
                    "Please click 'Submit Payment Details' below "
                    "to open the support form. You can provide your "
                    "transaction/order ID, payment date, amount, "
                    "and registered email or phone number there.\n\n"
                    "Your support ticket will be saved when you "
                    "submit the form. This prototype does not "
                    "automatically send an email or WhatsApp notification."
                ),
                "action": "HUMAN_REVIEW",
            }

        # STAGE 3: Ask whether the troubleshooting helped.
        if payment_stage == "check_result":
            return {
                "draft_reply": (
                    "Thanks for trying the troubleshooting steps.\n\n"
                    "Can you access your batch now, or is the payment "
                    "issue still unresolved?\n\n"
                    "If it is still unresolved, click 'I Still Need Help' "
                    "to open the support request process."
                ),
                "action": "HUMAN_REVIEW",
            }

    # ======================================================
    # 2. REFUND WORKFLOW
    # ======================================================

    if "refund" in categories:

        request_phrases = (
            "submit refund request",
            "submit batch change request",
            "proceed with my refund",
            "proceed with a batch change",
            "i want to proceed",
            "i want to request a batch change",
            "i want to submit a refund request",
            "help me submit my request",
            "i would like to proceed",
            "i still need help",
            "i need more help",
        )

        wants_request = any(
            phrase in latest_message
            for phrase in request_phrases
        )

        explanation_phrases = (
            "yes",
            "yes please",
            "please explain",
            "explain the policy",
            "tell me more",
            "understand refund policy",
        )

        wants_explanation = any(
            latest_message == phrase
            or latest_message.startswith(phrase + " ")
            for phrase in explanation_phrases
        )

        if wants_request:
            return {
                "draft_reply": (
                    "I can help you prepare a batch-change support "
                    "request. Please click 'Submit Refund Request' "
                    "below to open the form.\n\n"
                    "Your request will be saved only after you "
                    "submit the form."
                ),
                "action": "HUMAN_REVIEW",
            }

        if wants_explanation:
            return {
                "draft_reply": (
                    "Here is how the policy applies to your situation:\n\n"
                    "1. Online batches and services are non-refundable.\n"
                    "2. If you purchased a batch by mistake, you may be "
                    "eligible to request a change to another batch of "
                    "the same amount.\n"
                    "3. The request must be made within 10 days of purchase.\n"
                    "4. A batch change is not guaranteed; the support "
                    "team must review your request.\n\n"
                    "If you want to request a batch change, click "
                    "'Submit Refund Request' below."
                ),
                "action": "AUTO_REPLY_CANDIDATE",
            }

        return {
            "draft_reply": (
                "According to our refund policy, online batches and "
                "services are non-refundable. However, if you purchased "
                "a batch by mistake, you may be eligible to request a "
                "change to another batch of the same amount within "
                "10 days of purchase.\n\n"
                "Would you like me to explain the policy further, "
                "or would you like to proceed with a support request?"
            ),
            "action": "AUTO_REPLY_CANDIDATE",
        }

    # ======================================================
    # 3. OTHER CATEGORIES — LLM RESPONSE
    # ======================================================

    if "academic_doubt" in categories:
        instructions = """
You are a helpful academic tutor.
Explain academic concepts simply and step by step.
Ask a clarifying question if the academic question is unclear.
Do not invent official PW policies.
"""
    else:
        instructions = """
You are a Physics Wallah student support assistant.
Use the retrieved knowledge base for official policies.
Never invent fees, refund policies, or payment status.
For account-specific issues, recommend human review.
If information is missing, ask for relevant details.
Be polite, concise, and helpful.
Never request passwords, OTPs, or full card details.
Do not claim that a support request has been submitted unless
the backend confirms successful submission.
"""

    prompt = f"""
{instructions}

RULES:
- Address every issue in a multi-issue complaint.
- Do not reveal internal risk scores.
- Do not promise refunds or resolution dates.
- Use conversation history to understand previous answers.
- For technical issues, suggest relevant troubleshooting.
- For academic doubts, explain the concept step by step.
- For fee questions, use the retrieved knowledge base.
- Do not invent information absent from the knowledge base.

STUDENT'S CURRENT TICKET:
{state["ticket"]}

CATEGORIES:
{categories}

PRIMARY CATEGORY:
{state["primary_category"]}

SENTIMENT:
{risk["sentiment"]}

PRIORITY:
{risk["priority"]}

HUMAN REVIEW RECOMMENDED:
{state["needs_human_review"]}

REVIEW REASON:
{state["reason"]}

CONVERSATION HISTORY:
{history}

SUPPORT ATTEMPT:
{state.get("attempt_number", 1)} of 3

KNOWLEDGE BASE:
{state.get("context", "")}

Write a helpful reply to the student.
"""

    response = llm.invoke(prompt)

    return {
        "draft_reply": response.content,
        "action": (
            "HUMAN_REVIEW"
            if state["needs_human_review"]
            else "AUTO_REPLY_CANDIDATE"
        ),
    }

builder = StateGraph(TicketState)

builder.add_node("classify_ticket", classify_ticket_node)
builder.add_node("detect_risk", detect_risk_node)
builder.add_node("retrieve_knowledge", retrieve_knowledge_node)
builder.add_node("escalation_check", escalation_check_node)
builder.add_node("generate_reply", generate_reply_node)

builder.add_edge(START, "classify_ticket")
builder.add_edge("classify_ticket", "detect_risk")
builder.add_edge("detect_risk", "retrieve_knowledge")
builder.add_edge("retrieve_knowledge", "escalation_check")
builder.add_edge("escalation_check", "generate_reply")
builder.add_edge("generate_reply", END)

ticket_graph = builder.compile()


def process_ticket_with_graph(
    ticket,
    conversation_history=None,
    attempt_number=1,
):
    history = conversation_history or []

    result = ticket_graph.invoke({
        "ticket": ticket,
        "conversation_history": history,
        "attempt_number": attempt_number,
    })

    risk = result["risk_assessment"]

    return {
        "ticket": ticket,
        "categories": result["categories"],
        "category": result["primary_category"],
        "sentiment": risk["sentiment"],
        "risk_level": risk["risk_level"],
        "priority": risk["priority"],
        "classifier_needs_human_review":
            result["classification"]["needs_human_review"],
        "risk_needs_human_review":
            risk["needs_human_review"],
        "needs_human_review": result["needs_human_review"],
        "action": result["action"],
        "reason": result["reason"],
        "draft_reply": result["draft_reply"],
        "sources": result["sources"],
    }


if __name__ == "__main__":
    test_ticket = (
        "I paid for my course, but my batch is still not activated."
    )

    print("Running LangGraph Support Ticket Agent...")
    result = process_ticket_with_graph(test_ticket)

    print("\nCategories:", result["categories"])
    print("Risk:", result["risk_level"])
    print("Priority:", result["priority"])
    print("Human review:", result["needs_human_review"])
    print("Action:", result["action"])
    print("Reason:", result["reason"])
    print("\nDraft reply:\n", result["draft_reply"])
    print("\nSources:", result["sources"])