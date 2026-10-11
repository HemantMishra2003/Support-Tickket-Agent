from dotenv import load_dotenv
from langchain_openai import OpenAIEmbeddings
from langchain_community.vectorstores import FAISS

load_dotenv()

embeddings = OpenAIEmbeddings(
    model="text-embedding-3-small"
)

vector_store = FAISS.load_local(
    "faiss_index",
    embeddings,
    allow_dangerous_deserialization=True
)

print("\n=== PW Knowledge Base Retrieval Tester ===")
print("Type 'exit' to stop testing.\n")

while True:
    query = input("Enter student query: ").strip()

    if query.lower() == "exit":
        print("Testing finished.")
        break

    if not query:
        print("Please enter a query.\n")
        continue

    results = vector_store.similarity_search_with_score(
        query,
        k=5
    )

    print("\nStudent Query:", query)
    print("\nRetrieved Documents:\n")

    for i, (doc, score) in enumerate(results, start=1):
        print(f"\nResult {i}")
        print("Source:", doc.metadata.get("source", "Unknown"))
        print("Distance:", round(float(score), 4))
        print("Content:")
        print(doc.page_content)
        print("-" * 60)

    print()