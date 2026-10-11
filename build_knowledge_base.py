import os
from pathlib import Path

from dotenv import load_dotenv
from langchain_openai import OpenAIEmbeddings
from langchain_community.vectorstores import FAISS
from langchain_community.document_loaders import DirectoryLoader, TextLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter

# Load API key
load_dotenv()

# Knowledge Base folder
knowledge_base_path = Path("knowledge_base")

# Load all Markdown files
loader = DirectoryLoader(
    str(knowledge_base_path),
    glob="*.md",
    loader_cls=TextLoader,
    loader_kwargs={"encoding": "utf-8"}
)

documents = loader.load()

# Manually assign source names
source_names = {
    "payment_batch_refund.md": "PW Official Refund and Payment Policy",
    "academic_support.md": "Academic Support Guidelines",
    "technical_support.md": "Technical Troubleshooting Guide",
    "fee_structure.md": "Physics Wallah Fee Structure"
}

for doc in documents:
    filename = os.path.basename(doc.metadata.get("source", ""))

    if filename in source_names:
        doc.metadata["source"] = source_names[filename]

    doc.metadata["display_name"] = doc.metadata["source"]

if not documents:
    raise ValueError("No Markdown documents found in knowledge_base!")

print(f"Loaded {len(documents)} documents")

# Split documents into smaller chunks
text_splitter = RecursiveCharacterTextSplitter(
    chunk_size=500,
    chunk_overlap=50
)

chunks = text_splitter.split_documents(documents)

print(f"Created {len(chunks)} text chunks")

# Convert text chunks into embeddings
embeddings = OpenAIEmbeddings(
    model="text-embedding-3-small"
)

# Create FAISS vector store
vector_store = FAISS.from_documents(
    chunks,
    embeddings
)

# Save locally
vector_store.save_local("faiss_index")

print("FAISS Knowledge Base created successfully!")