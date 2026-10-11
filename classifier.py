def classify_ticket(ticket):

    ticket_lower = ticket.lower()

    # 1. Refund
    refund_keywords = [
        "refund",
        "money back",
        "return my money",
        "cancel and refund"
    ]

    # 2. Payment
    payment_keywords = [
        "payment",
        "paid",
        "transaction",
        "deducted",
        "payment failed",
        "money deducted"
    ]

    # 3. Batch access
    batch_keywords = [
        "batch",
        "course access",
        "enrollment",
        "not activated",
        "not showing in my account",
        "cannot access"
    ]

    # 4. Technical issue
    technical_keywords = [
        "error",
        "bug",
        "not working",
        "app crashing",
        "app crash",
        "website issue",
        "technical problem"
    ]

    # 5. Academic doubt
    academic_keywords = [
        "doubt",
        "explain",
        "understand",
        "question",
        "physics",
        "chemistry",
        "mathematics",
        "maths",
        "concept",
        "lecture"
    ]

    # Priority 1: Payment verification issues
    if any(word in ticket_lower for word in [
        "money deducted",
        "payment failed",
        "deducted",
        "not activated"
    ]):
        return "payment"

    # Priority 2: Refund
    elif any(word in ticket_lower for word in refund_keywords):
        return "refund"

    # Priority 3: Batch access
    elif any(word in ticket_lower for word in batch_keywords):
        return "batch_access"

    # Priority 4: Technical
    elif any(word in ticket_lower for word in technical_keywords):
        return "technical"

    # Priority 5: Academic doubt
    elif any(word in ticket_lower for word in academic_keywords):
        return "academic_doubt"

    # Unknown category
    else:
        return "human_review"


if __name__ == "__main__":

    ticket = input("Enter student complaint: ")

    category = classify_ticket(ticket)

    print("\nTicket:", ticket)
    print("Category:", category)