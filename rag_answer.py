from dotenv import load_dotenv
from langchain_openai import OpenAIEmbeddings, ChatOpenAI
from langchain_community.vectorstores import FAISS

# Load API key from .env
load_dotenv()


# 1. Initialize embedding model
embeddings = OpenAIEmbeddings(
    model="text-embedding-3-small"
)


# 2. Load existing FAISS index
vector_store = FAISS.load_local(
    "faiss_index",
    embeddings,
    allow_dangerous_deserialization=True
)


# 3. Initialize LLM
llm = ChatOpenAI(
    model="gpt-4.1-mini",
    temperature=0
)


# 4. Get student query
query = input("Enter student query: ")

query_lower = query.lower()


# 5. Identify the relevant policy document
if any(word in query_lower for word in [
    "refund", "money back", "return my money"
]):
    target_file = "refund_policy.md"

elif any(word in query_lower for word in [
    "payment", "transaction", "deducted", "payment failed"
]):
    target_file = "payment_support.md"

elif any(word in query_lower for word in [
    "batch access", "batch not showing",
    "cannot access my batch", "course access"
]):
    target_file = "batch_access.md"

elif any(word in query_lower for word in [
    "app", "website", "error", "not working", "technical"
]):
    target_file = "technical_support.md"

elif any(word in query_lower for word in [
    "academic", "study doubt", "subject question",
    "lecture", "course material"
]):
    target_file = "academic_support.md"

else:
    target_file = None


# 6. Retrieve relevant documents from FAISS
results = vector_store.similarity_search(
    query,
    k=5
)


# 7. Prioritize the matching policy document
if target_file:

    matching_docs = [
        doc
        for doc in vector_store.docstore._dict.values()
        if doc.metadata.get("source", "")
        .replace("\\", "/")
        .endswith(target_file)
    ]

    if matching_docs:
        results = matching_docs[:3]


# 8. Prepare context with source citations
context = "\n\n".join(
    f"Source: {doc.metadata.get('source', 'Unknown')}\n"
    f"Content: {doc.page_content}"
    for doc in results
)


# 9. Generate an answer using retrieved information
prompt = f"""
You are a student support assistant.

Answer the student's question using ONLY the
information contained in the retrieved documents.

Rules:
- Do not invent policies or facts.
- Do not promise a refund.
- Do not claim a payment succeeded or failed
  without transaction verification.
- If the available information is insufficient,
  explain that human support is required.
- Include the source filename in your answer.
- Do not claim that a complaint has been resolved.
- Clearly distinguish verified information from
  information that is not available.

Retrieved documents:
{context}

Student question:
{query}
"""


# 10. Call the LLM
response = llm.invoke(prompt)


# 11. Display the final answer
print("\n" + "=" * 50)
print("STUDENT QUERY")
print("=" * 50)
print(query)

print("\n" + "=" * 50)
print("AI GENERATED RESPONSE")
print("=" * 50)
print(response.content)

print("\n" + "=" * 50)
print("RETRIEVED SOURCES")
print("=" * 50)

if results:
    for doc in results:
        print("-", doc.metadata.get("source", "Unknown"))
else:
    print("No relevant documents retrieved.")