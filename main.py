"""
SafetyVision-RAG API - Refactored
AI-Powered Safety Hazard Detection using VLM + RAG
"""

import base64
import os
import tempfile
from pathlib import Path
from datetime import datetime
from contextlib import asynccontextmanager
from typing import Annotated, List, Optional, Dict

from fastapi import FastAPI, UploadFile, File, HTTPException, status, Query
from pydantic import BaseModel, Field

from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import JsonOutputParser
from langchain_core.runnables import RunnablePassthrough, RunnableLambda, chain
from langchain_core.messages import HumanMessage
from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from langchain_qdrant import QdrantVectorStore
from langchain_text_splitters import RecursiveCharacterTextSplitter
from qdrant_client import QdrantClient
from src.document_processors import DocumentProcessorFactory
from qdrant_client.models import (
    Filter,
    FieldCondition,
    MatchValue,
    Distance,
    VectorParams,
)


# ============================================================================
# Configuration
# ============================================================================


class Config:
    """Application configuration"""

    QDRANT_URL = f"http://{os.getenv('QDRANT_HOST', 'qdrant-server')}:{os.getenv('QDRANT_PORT', '6333')}"
    COLLECTION = os.getenv("QDRANT_COLLECTION", "rag-test")
    VLM_URL = os.getenv("VLLM_CHAT_URL", "http://vllm-qwen-vl:8000/v1")
    EMBED_URL = os.getenv("VLLM_EMBED_URL", "http://vllm-bge-m3:8000/v1")
    VLM_MODEL = os.getenv("VLLM_MODEL_NAME", "/model/qwen3-vl-4b")
    EMBED_MODEL = os.getenv("VLLM_EMBED_MODEL", "/model/bge-m3")
    MAX_FILE_SIZE = 50 * 1024 * 1024  # 增加到50MB
    MAX_FILES = 10
    CHUNK_SIZE = 1000
    CHUNK_OVERLAP = 200


# ============================================================================
# Models
# ============================================================================


class SafetyViolation(BaseModel):
    hazard_id: int = Field(ge=1)
    hazard_description: str
    recommendations: str
    rule_reference: str


class SafetyReport(BaseModel):
    report_id: str
    violations: List[SafetyViolation]


class DocumentDetail(BaseModel):
    filename: str
    status: str
    chunks: Optional[int] = None
    message: str


# ============================================================================
# Global Resources
# ============================================================================

qdrant_client = QdrantClient(url=Config.QDRANT_URL)

llm = ChatOpenAI(
    model_name=Config.VLM_MODEL,
    api_key="not-needed",
    base_url=Config.VLM_URL,
    temperature=0.1,
    max_tokens=800,
)

embeddings = OpenAIEmbeddings(
    model=Config.EMBED_MODEL, api_key="not-needed", base_url=Config.EMBED_URL
)

text_splitter = RecursiveCharacterTextSplitter(
    chunk_size=Config.CHUNK_SIZE,
    chunk_overlap=Config.CHUNK_OVERLAP,
    separators=["\n\n", "\n", "。", "！", "？", ".", "!", "?", " "],
)


# ============================================================================
# Utility Functions
# ============================================================================


def ensure_collection():
    """Ensure Qdrant collection exists."""
    try:
        qdrant_client.get_collection(Config.COLLECTION)
    except:
        qdrant_client.create_collection(
            collection_name=Config.COLLECTION,
            vectors_config=VectorParams(size=1024, distance=Distance.COSINE),
        )


def get_vector_store() -> QdrantVectorStore:
    """Get vector store instance."""
    return QdrantVectorStore(
        client=qdrant_client, collection_name=Config.COLLECTION, embedding=embeddings
    )


# ============================================================================
# LangChain Chains
# ============================================================================


@chain
async def vlm_chain(image_b64: str) -> str:
    """VLM chain: Extract hazards from image."""
    messages = [
        HumanMessage(
            content=[
                {
                    "type": "text",
                    "text": "你是安全专家。分析图片并简洁列出1-5个最重要的安全隐患，每条用一行描述。",
                },
                {
                    "type": "image_url",
                    "image_url": {"url": f"data:image/png;base64,{image_b64}"},
                },
            ]
        )
    ]
    response = await llm.ainvoke(messages)
    return response.content


def create_rag_chain():
    """Create RAG chain for report generation."""
    template = """你是安全报告生成器。根据检索到的规范和发现的隐患，生成结构化JSON报告。

{format_instructions}

---
相关规范:
{context}

---
参考文档来源:
{sources}

---
发现的隐患:
{question}

重要说明：
1. rule_reference 字段必须按照以下格式填写，若没有对应的字段，则直接不写，不要乱编！！！：
   《标准名称》(标准编号) 第某条规定：具体规定内容。来自文档：文件名1, 文件名2
   
2. 示例格式：
   《xxx标准》第x条规定：xxxx,xxx。来自文档：安全规范.pdf
   
3. 如果检索到的文档中没有明确的标准编号，则只需写标准名称和具体规定内容即可，不要编造编号。
4. 必须在末尾注明"来自文档："后跟上述"参考文档来源"中的文件名。
5. 如果涉及多个文档，用逗号分隔文件名。
6. 如果没有任何相关标准，请将rule_reference字段设置为，"暂无相关标准"。
"""
    parser = JsonOutputParser(pydantic_object=SafetyReport)
    retriever = get_vector_store().as_retriever(search_kwargs={"k": 3})

    def format_docs_with_sources(docs):
        """格式化文档内容并提取来源"""
        context_parts = []
        sources_parts = []
        seen_files = set()

        for i, doc in enumerate(docs, 1):
            # 添加文档内容
            context_parts.append(f"[文档{i}] {doc.page_content[:800]}")

            # 提取文件名
            filename = doc.metadata.get("filename", "未知来源")
            if filename not in seen_files:
                seen_files.add(filename)
                sources_parts.append(f"- {filename}")

        return {
            "context": "\n---\n".join(context_parts),
            "sources": "\n".join(sources_parts) if sources_parts else "无参考文档",
        }

    return (
        {
            "docs": retriever,
            "question": RunnablePassthrough(),
        }
        | RunnableLambda(
            lambda x: {
                **format_docs_with_sources(x["docs"]),
                "question": x["question"],
                "format_instructions": parser.get_format_instructions(),
            }
        )
        | ChatPromptTemplate.from_template(template)
        | llm
        | parser
    )


# ============================================================================
# FastAPI App
# ============================================================================


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan."""
    ensure_collection()
    yield
    qdrant_client.close()


app = FastAPI(
    title="SafetyVision-RAG",
    description="AI-Powered Safety Hazard Detection System",
    version="2.0.0",
    lifespan=lifespan,
)


@app.get("/health")
async def health():
    """Health check."""
    collections = qdrant_client.get_collections()
    return {"status": "healthy", "collections": len(collections.collections)}


@app.post("/analyze_image", response_model=SafetyReport)
async def analyze_image(file: Annotated[UploadFile, File()]):
    """Analyze image for safety hazards."""
    if not file.content_type or not file.content_type.startswith("image/"):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Invalid file type")

    image_bytes = await file.read()
    if len(image_bytes) > Config.MAX_FILE_SIZE:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "File too large")

    image_b64 = base64.b64encode(image_bytes).decode()
    hazards = await vlm_chain.ainvoke(image_b64)
    rag_chain = create_rag_chain()
    return await rag_chain.ainvoke(hazards)


@app.post("/api/documents/upload")
async def upload_documents(
    files: List[UploadFile] = File(...), skip_existing: bool = Query(True)
):
    """Upload documents (PDF, Word, Excel)."""
    if len(files) > Config.MAX_FILES:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Too many files")

    # Supported extensions
    supported_exts = (".pdf", ".docx", ".doc", ".xlsx", ".xls")

    details = []
    for file in files:
        if not file.filename.lower().endswith(supported_exts):
            details.append(
                DocumentDetail(
                    filename=file.filename,
                    status="failed",
                    message=f"Unsupported format. Supported: {', '.join(supported_exts)}",
                )
            )
            continue

        content = await file.read()
        if len(content) > Config.MAX_FILE_SIZE:
            details.append(
                DocumentDetail(
                    filename=file.filename, status="failed", message="File too large"
                )
            )
            continue

        # Check if exists
        result = qdrant_client.scroll(
            collection_name=Config.COLLECTION,
            scroll_filter={
                "must": [
                    {"key": "metadata.filename", "match": {"value": file.filename}}
                ]
            },
            limit=1,
            with_vectors=False,
        )

        if len(result[0]) > 0 and skip_existing:
            details.append(
                DocumentDetail(
                    filename=file.filename, status="skipped", message="Already exists"
                )
            )
            continue

        # Process document based on type
        file_ext = Path(file.filename).suffix.lower()
        with tempfile.NamedTemporaryFile(delete=False, suffix=file_ext) as tmp:
            tmp.write(content)
            tmp_path = tmp.name

        try:
            metadata = {
                "filename": file.filename,
                "upload_time": datetime.now().isoformat(),
            }

            # Use appropriate processor
            chunks = DocumentProcessorFactory.process(
                tmp_path, metadata, Config.CHUNK_SIZE, Config.CHUNK_OVERLAP
            )

            QdrantVectorStore.from_documents(
                documents=chunks,
                embedding=embeddings,
                url=Config.QDRANT_URL,
                collection_name=Config.COLLECTION,
                force_recreate=False,
            )

            details.append(
                DocumentDetail(
                    filename=file.filename,
                    status="success",
                    chunks=len(chunks),
                    message="Uploaded successfully",
                )
            )
        except ValueError as e:
            # Handle unsupported format errors
            details.append(
                DocumentDetail(
                    filename=file.filename,
                    status="failed",
                    message=str(e),
                )
            )
        except Exception as e:
            # Handle other processing errors
            details.append(
                DocumentDetail(
                    filename=file.filename,
                    status="failed",
                    message=f"Processing failed: {str(e)}",
                )
            )
        finally:
            Path(tmp_path).unlink(missing_ok=True)

    success_count = sum(1 for d in details if d.status == "success")
    return {
        "success": success_count == len(files),
        "message": f"Processed {len(files)} files, {success_count} succeeded",
        "details": details,
    }


@app.delete("/api/documents")
async def delete_documents(filenames: List[str] = Query(...)):
    """Delete documents."""
    results = []
    for filename in filenames:
        result = qdrant_client.scroll(
            collection_name=Config.COLLECTION,
            scroll_filter={
                "must": [{"key": "metadata.filename", "match": {"value": filename}}]
            },
            limit=10000,
            with_vectors=False,
        )

        if len(result[0]) == 0:
            results.append({"filename": filename, "status": "not_found"})
            continue

        qdrant_client.delete(
            collection_name=Config.COLLECTION,
            points_selector=Filter(
                must=[
                    FieldCondition(
                        key="metadata.filename", match=MatchValue(value=filename)
                    )
                ]
            ),
        )

        results.append(
            {
                "filename": filename,
                "status": "deleted",
                "chunks_removed": len(result[0]),
            }
        )

    return {"success": True, "results": results}


@app.get("/api/documents")
async def list_documents():
    """List all documents."""
    all_docs = {}
    offset = None

    while True:
        points, offset = qdrant_client.scroll(
            collection_name=Config.COLLECTION,
            limit=100,
            offset=offset,
            with_payload=True,
            with_vectors=False,
        )

        if not points:
            break

        for point in points:
            filename = point.payload.get("metadata", {}).get("filename", "unknown")
            all_docs.setdefault(filename, 0)
            all_docs[filename] += 1

        if offset is None:
            break

    return [
        {"filename": name, "chunks_count": count} for name, count in all_docs.items()
    ]


@app.get("/")
async def root():
    return {"name": "SafetyVision-RAG", "version": "2.0.0", "docs": "/docs"}
