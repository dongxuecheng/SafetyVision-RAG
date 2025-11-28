from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from qdrant_client.models import Distance, VectorParams
from langchain_qdrant import QdrantVectorStore
from qdrant_client import QdrantClient
from langchain_community.document_loaders import PyPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain.tools import tool
from langchain.agents import create_agent

model = ChatOpenAI(
    model="/model/qwen3-vl-4b",
    base_url="http://vllm-qwen-vl:8000/v1",
    api_key="EMPTY",
    temperature=0.1,
    max_tokens=1024,
)

embeddings = OpenAIEmbeddings(
    model="/model/bge-m3",
    api_key="not-needed",
    base_url="http://vllm-bge-m3:8000/v1",
)

client = QdrantClient("http://qdrant-server:6333")
if not client.collection_exists("rag-test"):
    client.create_collection(
        collection_name="rag-test",
        vectors_config=VectorParams(size=1024, distance=Distance.COSINE),
    )
vector_store = QdrantVectorStore(
    client=client,
    collection_name="rag-test",
    embedding=embeddings,
)

loader = PyPDFLoader("../example_data/nke-10k-2023.pdf")
docs = loader.load()
assert len(docs) == 1
print(f"Total characters: {len(docs[0].page_content)}")

text_splitter = RecursiveCharacterTextSplitter(
    chunk_size=1000,  # chunk size (characters)
    chunk_overlap=200,  # chunk overlap (characters)
    add_start_index=True,  # track index in original document
)
all_splits = text_splitter.split_documents(docs)
print(f"Split blog post into {len(all_splits)} sub-documents.")

document_ids = vector_store.add_documents(documents=all_splits)
print(document_ids[:3])


@tool(response_format="content_and_artifact")
def retrieve_context(query: str):
    """Retrieve information to help answer a query."""
    retrieved_docs = vector_store.similarity_search(query, k=2)
    serialized = "\n\n".join(
        (f"Source: {doc.metadata}\nContent: {doc.page_content}")
        for doc in retrieved_docs
    )
    return serialized, retrieved_docs


tools = [retrieve_context]
# If desired, specify custom instructions
prompt = (
    "You have access to a tool that retrieves context from a blog post. "
    "Use the tool to help answer user queries."
)
agent = create_agent(model, tools, system_prompt=prompt)

query = (
    "What is the standard method for Task Decomposition?\n\n"
    "Once you get the answer, look up common extensions of that method."
)

for event in agent.stream(
    {"messages": [{"role": "user", "content": query}]},
    stream_mode="values",
):
    event["messages"][-1].pretty_print()
