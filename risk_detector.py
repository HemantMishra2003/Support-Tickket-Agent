import json

from dotenv import load_dotenv
from langchain_openai import ChatOpenAI


# Load environment variables
load_dotenv()


# Initialize LLM
llm = ChatOpenAI(
    model="gpt-4.1-mini",
    temperature=0
)


def detect_student_risk(ticket: str) -> dict:
    """
    Detect student sentiment, risk level, priority,
    and whether human review is required.
    """

    prompt = f"""
You are a student support risk detection system.

Analyze the student's complaint.

Return valid JSON with these fields:

1. sentiment:
   One of: positive, neutral, frustrated, angry

2. risk_level:
   One of: low, medium, high

3. priority:
   One of: low, normal, high, urgent

4. needs_human_review:
   Boolean: true or false

5. reason:
   A short explanation for the decision.

Guidelines:

- Angry language alone does not automatically mean high risk.
- Repeated unresolved complaints increase priority.
- Payment disputes involving deducted money may need
  human verification.
- Threats of legal action or explicit safety concerns
  require human attention.
- Urgent words alone do not automatically mean urgent priority.
- Be conservative. Do not invent facts about the student.
- A neutral, routine question should generally have low risk
  and normal priority.
- A frustrated student with repeated unresolved issues
  should generally receive high priority.
- If the complaint is unclear, prefer human review.

Student complaint:
{ticket}

Return JSON only:

{{
    "sentiment": "frustrated",
    "risk_level": "high",
    "priority": "high",
    "needs_human_review": true,
    "reason": "The student reports repeated unresolved issues."
}}
"""

    try:
        response = llm.invoke(prompt)

        text = response.content.strip()

        # Remove accidental Markdown fences
        if text.startswith("```"):
            text = text.replace("```json", "", 1)
            text = text.replace("```", "").strip()

        result = json.loads(text)

        allowed_sentiments = {
            "positive",
            "neutral",
            "frustrated",
            "angry"
        }

        allowed_risk_levels = {
            "low",
            "medium",
            "high"
        }

        allowed_priorities = {
            "low",
            "normal",
            "high",
            "urgent"
        }

        sentiment = result.get("sentiment")
        risk_level = result.get("risk_level")
        priority = result.get("priority")
        needs_review = result.get("needs_human_review")
        reason = result.get("reason", "")

        # Validate the response
        if sentiment not in allowed_sentiments:
            raise ValueError("Invalid sentiment")

        if risk_level not in allowed_risk_levels:
            raise ValueError("Invalid risk level")

        if priority not in allowed_priorities:
            raise ValueError("Invalid priority")

        if not isinstance(needs_review, bool):
            raise ValueError("Review flag must be boolean")

        if not isinstance(reason, str):
            raise ValueError("Reason must be text")

        # Conservative safety rules
        if risk_level == "high" or priority == "urgent":
            needs_review = True

        return {
            "sentiment": sentiment,
            "risk_level": risk_level,
            "priority": priority,
            "needs_human_review": needs_review,
            "reason": reason
        }

    except (json.JSONDecodeError, TypeError, ValueError):
        # Fail safely when the model response is invalid
        return {
            "sentiment": "neutral",
            "risk_level": "medium",
            "priority": "normal",
            "needs_human_review": True,
            "reason": "Risk assessment could not be validated."
        }


if __name__ == "__main__":

    ticket = input("Enter student complaint: ").strip()

    if not ticket:
        print("Please enter a complaint.")
    else:
        result = detect_student_risk(ticket)

        print("\nRISK ASSESSMENT")
        print(json.dumps(result, indent=4))