import json
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI

# Load API key from .env
load_dotenv()

# Initialize LLM
llm = ChatOpenAI(
    model="gpt-4.1-mini",
    temperature=0
)

# Available ticket categories
CATEGORIES = [
    "fee_structure",
    "refund",
    "batch_access",
    "payment",
    "technical",
    "academic_doubt",
    "human_review"
]


def classify_ticket_details(ticket: str) -> dict:
    """
    Classify a student support ticket into all relevant categories.
    Human review is required only when the complaint needs
    human intervention or cannot be classified safely.
    """

    prompt = f"""
You are an AI student support ticket classifier for Physics Wallah (PW).

Your task is to identify all relevant categories, select the primary
category, and decide whether human review is required.

Available categories:

- fee_structure: Questions about course prices, course fees,
  offline registration charges, discounts, and fee differences.

- refund: The student asks for a refund or money back.

- batch_access: The student cannot access a purchased batch or course.

- payment: Payment failed, is pending, was deducted incorrectly,
  or a duplicate payment occurred.

- technical: The app, website, login, or video player has a technical issue.

- academic_doubt: The student asks an academic or subject-related question.

- human_review: The complaint is too unclear to classify safely.

Classification rules:

1. Identify ALL relevant categories.

2. Select exactly one primary_category representing the main issue.

3. Multiple categories may apply to the same complaint.

4. General questions about course prices, registration fees,
   discounts, or fee differences must be classified as fee_structure.
   Do not classify a general course fee question as payment.

5. If money was deducted but the batch is not activated, include
   both payment and batch_access.

6. If the app crashes and the purchased batch is missing, include
   both technical and batch_access.

7. If the student requests a refund because of duplicate payment,
   include both refund and payment.

8. Do not assume a refund is requested unless the student asks for
   one or clearly indicates they want their money back.

9. A normal academic question must be classified as academic_doubt.
   Do not request human review merely because official study notes
   are unavailable.

10. A normal technical problem must be classified as technical.
    Do not request human review merely because it is a technical issue.

11. A general question about refund policy must be classified as refund.
    Do not request human review merely because the student asks about
    refund eligibility.

12. A general payment question must be classified as payment.

13. Set needs_human_review to true when:
    - The complaint is too vague or impossible to classify.
    - The student explicitly requests a human support representative.
    - The complaint clearly requires individual account, transaction,
      enrollment, or payment-record verification.
    - The complaint involves suspected unauthorized account access
      or another serious account-security issue.

14. Do not set needs_human_review to true merely because a ticket
    has multiple categories.

15. Do not claim that an account, payment, refund, or batch has
    been verified.

16. Return valid JSON only. Do not use Markdown fences.

Return this exact JSON structure:

{{
    "categories": ["payment", "batch_access"],
    "primary_category": "payment",
    "needs_human_review": true
}}

Student complaint:
{ticket}
"""

    try:
        response = llm.invoke(prompt)
        result_text = response.content.strip()

        # Remove accidental Markdown fences
        if result_text.startswith("```"):
            result_text = result_text.replace("```json", "", 1)
            result_text = result_text.replace("```", "").strip()

        result = json.loads(result_text)

        categories = result.get("categories", [])
        primary_category = result.get(
            "primary_category",
            "human_review"
        )
        needs_human_review = result.get(
            "needs_human_review",
            True
        )

        # Validate output types
        if not isinstance(categories, list):
            raise ValueError("Categories must be a list")

        if not isinstance(needs_human_review, bool):
            raise ValueError("Review flag must be boolean")

        # Validate category names
        if not all(
            isinstance(category, str) and category in CATEGORIES
            for category in categories
        ):
            raise ValueError("Invalid category found")

        # Remove duplicate categories
        categories = list(dict.fromkeys(categories))

        # Validate primary category
        if (
            not isinstance(primary_category, str)
            or primary_category not in CATEGORIES
        ):
            raise ValueError("Invalid primary category")

        # Route unclear complaints to human review
        if (
            not categories
            or primary_category == "human_review"
            or "human_review" in categories
        ):
            return {
                "categories": ["human_review"],
                "primary_category": "human_review",
                "needs_human_review": True
            }

        # Ensure the primary category is included
        if primary_category not in categories:
            categories.insert(0, primary_category)

        return {
            "categories": categories,
            "primary_category": primary_category,
            "needs_human_review": needs_human_review
        }

    except (json.JSONDecodeError, TypeError, ValueError):
        # Safely handle malformed LLM responses
        return {
            "categories": ["human_review"],
            "primary_category": "human_review",
            "needs_human_review": True
        }


def classify_ticket(ticket: str) -> str:
    """
    Backward-compatible function.
    Returns only the primary category.
    """

    result = classify_ticket_details(ticket)
    return result["primary_category"]


if __name__ == "__main__":

    ticket = input("Enter student complaint: ").strip()

    if not ticket:
        print("Please enter a complaint.")
    else:
        result = classify_ticket_details(ticket)

        print("\nTicket:", ticket)
        print("All categories:", result["categories"])
        print("Primary category:", result["primary_category"])
        print(
            "Needs human review:",
            result["needs_human_review"]
        )