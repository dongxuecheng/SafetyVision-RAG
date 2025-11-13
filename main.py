# --- main.py ---
"""
SafetyVision-RAG API
AI-Powered Safety Hazard Detection System using Vision-Language Models and RAG
基于视觉-语言模型和检索增强生成的AI安全隐患检测系统
"""
import base64
import os
import logging
import tempfile
from pathlib import Path
from typing import Annotated, Optional, List, Dict
from contextlib import asynccontextmanager
from datetime import datetime

from fastapi import FastAPI, UploadFile, File, HTTPException, status, Query
from fastapi.responses import JSONResponse
from fastapi.exceptions import ResponseValidationError
from pydantic import BaseModel, Field, ValidationError

from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import JsonOutputParser
from langchain_core.runnables import RunnablePassthrough, chain
from langchain_core.messages import HumanMessage
from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from langchain_qdrant import QdrantVectorStore
from langchain_community.document_loaders import PyPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from qdrant_client import QdrantClient
from qdrant_client.models import Filter, FieldCondition, MatchValue, Distance, VectorParams

# 配置日志 - 使用更详细的格式
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(message)s',
    handlers=[
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# --- 1. 定义我们想要的 JSON 输出结构 (Pydantic V2) ---
class SafetyViolation(BaseModel):
    """安全违规记录模型"""
    hazard_id: int = Field(description="隐患的唯一编号，从1开始", ge=1)
    hazard_description: str = Field(description="从图片中识别到的具体隐患描述", min_length=1)
    recommendations: str = Field(description="针对隐患的具体整改建议", min_length=1)
    rule_reference: str = Field(description="从向量数据库中检索到的、最相关的安全规范原文", min_length=1)
    model_config = {
        "json_schema_extra": {
            "examples": [{
                "hazard_id": 1,
                "hazard_description": "火灾现场无有效隔离",
                "recommendations": "立即设置警戒线，疏散无关人员",
                "rule_reference": "《消防法》第二十八条"
            }]
        }
    }

class SafetyReport(BaseModel):
    """安全报告模型"""
    report_id: str = Field(description="报告的唯一ID，例如一个UUID")
    violations: List[SafetyViolation] = Field(
        description="在图片中发现的所有隐患列表"
    )
    
    model_config = {
        "json_schema_extra": {
            "examples": [{
                "report_id": "uuid-12345678-1234-5678-1234-567812345678",
                "violations": [
                    {
                        "hazard_id": 1,
                        "hazard_description": "火灾现场无有效隔离",
                        "recommendations": "立即设置警戒线，疏散无关人员",
                        "rule_reference": "《消防法》第二十八条"
                    }
                ]
            }]
        }
    }


# --- 文档管理相关模型 ---
class DocumentDetail(BaseModel):
    """单个文档处理详情"""
    filename: str = Field(description="文件名")
    status: str = Field(description="处理状态: success/skipped/failed")
    chunks: Optional[int] = Field(default=None, description="生成的文本块数量")
    message: str = Field(description="处理消息")


class UploadResponse(BaseModel):
    """文档上传响应模型"""
    success: bool = Field(description="是否成功")
    message: str = Field(description="响应消息")
    results: Dict = Field(description="统计结果")
    details: List[DocumentDetail] = Field(description="每个文档的处理详情")


class DeleteDetail(BaseModel):
    """单个文档删除详情"""
    filename: str = Field(description="文件名")
    status: str = Field(description="删除状态: deleted/not_found/failed")
    chunks_removed: Optional[int] = Field(default=None, description="删除的文本块数量")
    message: str = Field(description="删除消息")


class DeleteResponse(BaseModel):
    """文档删除响应模型"""
    success: bool = Field(description="是否成功")
    message: str = Field(description="响应消息")
    results: Dict = Field(description="统计结果")
    details: List[DeleteDetail] = Field(description="每个文档的删除详情")


class DocumentInfo(BaseModel):
    """文档信息模型"""
    filename: str = Field(description="文件名")
    chunks_count: int = Field(description="文本块数量")
    source: str = Field(description="文档来源路径")




# --- 2. 连接到所有的 vLLM 和 Qdrant 容器 ---
# 使用环境变量配置，提高可配置性

# LLM (Qwen-VL)
llm_qwen = ChatOpenAI(
    model_name=os.environ.get("VLLM_MODEL_NAME", "/model/qwen3-vl-4b"),
    api_key="not-needed",  # vLLM 不需要 API key
    base_url=os.environ.get("VLLM_CHAT_URL", "http://vllm-qwen-vl:8000/v1"),
    temperature=0.1,
    max_tokens=800,  # 增加到800以避免输出被截断
)

# Embedding (BGE-m3)
embeddings_bge = OpenAIEmbeddings(
    model=os.environ.get("VLLM_EMBED_MODEL", "/model/bge-m3"),
    api_key="not-needed",
    base_url=os.environ.get("VLLM_EMBED_URL", "http://vllm-bge-m3:8000/v1"),
)

# Vector Store (Qdrant)
qdrant_host = os.environ.get("QDRANT_HOST", "qdrant-server")
qdrant_port = int(os.environ.get("QDRANT_PORT", "6333"))
collection_name = os.environ.get("QDRANT_COLLECTION", "rag-test")
qdrant_client = QdrantClient(url=f"http://{qdrant_host}:{qdrant_port}")

# 确保集合存在（如果不存在则创建）
def ensure_collection_exists():
    """确保 Qdrant 集合存在，如果不存在则创建"""
    try:
        # 尝试获取集合信息
        qdrant_client.get_collection(collection_name=collection_name)
        logger.info(f"✅ 集合 '{collection_name}' 已存在")
    except Exception as e:
        # 集合不存在，创建新集合
        logger.warning(f"⚠️  集合 '{collection_name}' 不存在，正在创建...")
        try:
            # 创建集合（使用与 BGE-m3 匹配的向量维度）
            qdrant_client.create_collection(
                collection_name=collection_name,
                vectors_config=VectorParams(
                    size=1024,  # BGE-m3 的向量维度
                    distance=Distance.COSINE
                )
            )
            logger.info(f"✅ 成功创建集合 '{collection_name}'")
        except Exception as create_error:
            logger.error(f"❌ 创建集合失败: {create_error}")
            raise

# 启动时确保集合存在
ensure_collection_exists()

# 初始化 Vector Store
vector_store = QdrantVectorStore(
    client=qdrant_client,
    collection_name=collection_name,
    embedding=embeddings_bge,
)

# 创建 RAG 检索器
retriever = vector_store.as_retriever(
    search_kwargs={
        "k": int(os.environ.get("RAG_TOP_K", "2"))
    }
)


# --- 3. (核心) 定义我们的 LangChain "链" (LCEL) ---

# 链 1: VLM 链 (图片 -> 隐患文本) - 使用现代的 @chain 装饰器
def create_vlm_prompt(base64_image: str):
    """辅助函数：将 base64 字符串格式化为 LangChain 的多模态消息"""
    return [
        HumanMessage(
            content=[
                {"type": "text", "text": "你是一个安全专家。分析图片并简洁列出3-5个最重要的安全隐患，每条用一行描述，不要重复。"},
                {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{base64_image}"}}
            ]
        )
    ]

@chain
async def vlm_chain(base64_image: str) -> str:
    """VLM 链：将图片转换为隐患描述文本"""
    logger.info("🔍 VLM 开始分析图片...")
    messages = create_vlm_prompt(base64_image)
    response = await llm_qwen.ainvoke(messages)
    result = response.content if hasattr(response, 'content') else str(response)
    logger.info(f"✅ VLM 分析完成，识别到的隐患:\n{result}")
    return result


# 链 2: RAG + JSON 链 (隐患文本 -> JSON 报告)
rag_prompt_template = """
你是一个安全报告生成器。
根据以下检索到的"相关规范"和"发现的隐患"，生成一份结构化的 JSON 报告。

你必须严格遵循以下 JSON 格式。

{format_instructions}

---
相关规范 (上下文):
{context}

---
发现的隐患 (问题):
{question}
"""

# 创建 JSON 解析器
json_parser = JsonOutputParser(pydantic_object=SafetyReport)

# 创建带日志的上下文处理函数
def format_docs_with_logging(docs):
    """格式化文档并记录日志，限制每个文档最多800字符"""
    truncated_docs = []
    for d in docs:
        content = d.page_content
        if len(content) > 800:
            content = content[:800] + "..."
        truncated_docs.append(content)
    
    formatted = "\n---\n".join(truncated_docs)
    logger.info(f"📚 RAG 检索到 {len(docs)} 个相关规范文档")
    logger.info(f"检索内容预览:\n{formatted[:500]}..." if len(formatted) > 500 else f"检索内容:\n{formatted}")
    return formatted

@chain
async def log_prompt(messages):
    """记录发送给LLM的prompt"""
    full_prompt = str(messages)
    logger.info(f"📝 发送给VLM的prompt长度: {len(full_prompt)} 字符")
    logger.info(f"📝 Prompt前1500字符:\n{full_prompt[:1500]}...")
    if len(full_prompt) > 1500:
        logger.info(f"📝 Prompt后500字符:\n...{full_prompt[-500:]}")
    return messages

@chain
async def log_response(response):
    """记录LLM的响应"""
    response_content = response.content if hasattr(response, 'content') else str(response)
    logger.info(f"💬 VLM返回的原始响应 (前1000字符):\n{response_content[:1000]}...")
    return response

rag_chain = (
    {
        # "retriever | format_docs" 会自动运行 RAG 检索，并将文档列表格式化为字符串
        "context": retriever | format_docs_with_logging,
        # "question" 键会接收 "vlm_chain" 的输出
        "question": RunnablePassthrough(),
        "format_instructions": lambda x: json_parser.get_format_instructions(),
    }
    | ChatPromptTemplate.from_template(rag_prompt_template)
    | log_prompt
    | llm_qwen  # 再次调用 Qwen-VL (它也可以处理纯文本)
    | log_response
    | json_parser
)

# 最终管道: 将两个链"粘合"在一起
full_pipeline = vlm_chain | rag_chain


# --- 4. 生命周期管理 ---
@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    # Startup
    logger.info("🚀 应用启动中...")
    logger.info(f"Qdrant 服务: {qdrant_client.get_collections()}")
    logger.info(f"Collection: {os.environ.get('QDRANT_COLLECTION', 'rag-test')}")
    logger.info("✅ 应用启动完成")
    
    yield
    
    # Shutdown
    logger.info("👋 应用关闭中...")
    qdrant_client.close()
    logger.info("✅ 应用关闭完成")


# --- 5. 创建 FastAPI 应用 ---
app = FastAPI(
    title="SafetyVision-RAG API",
    description="AI-Powered Safety Hazard Detection System | 基于 VLM + RAG 的智能安全隐患检测系统",
    version="2.0.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)


# 健康检查端点
@app.get("/health", tags=["Health"])
async def health_check():
    """健康检查端点"""
    try:
        # 检查 Qdrant 连接
        collections = qdrant_client.get_collections()
        return {
            "status": "healthy",
            "qdrant": "connected",
            "collections": len(collections.collections)
        }
    except Exception as e:
        logger.error(f"健康检查失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"服务不可用: {str(e)}"
        )


@app.post("/analyze_image", response_model=SafetyReport, tags=["Analysis"])
async def analyze_image(
    file: Annotated[UploadFile, File(description="需要分析的图片文件")]
):
    """
    分析图片中的安全隐患
    
    上传一张图片，VLM 将识别隐患，RAG 将检索相关安全规范，
    最后返回一份结构化的 JSON 安全报告。
    
    Args:
        file: 上传的图片文件 (支持 JPEG, PNG 等格式)
        
    Returns:
        SafetyReport: 包含隐患列表和规范引用的结构化报告
        
    Raises:
        HTTPException: 
            - 400: 无效的文件类型或空文件
            - 422: JSON 解析失败
            - 500: 服务器内部错误
    """
    # 记录请求信息
    logger.info(f"📷 收到图片分析请求: {file.filename}")
    logger.info(f"📝 Content-Type: {file.content_type}")
    
    # 1. 验证文件类型
    if not file.content_type or not file.content_type.startswith('image/'):
        logger.warning(f"❌ 无效的文件类型: {file.content_type}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "error": "invalid_content_type",
                "message": f"无效的文件类型: {file.content_type}",
                "accepted_types": ["image/jpeg", "image/png", "image/jpg", "image/webp"]
            }
        )
    
    try:
        # 2. 读取并验证图片
        image_bytes = await file.read()
        if len(image_bytes) == 0:
            logger.warning("❌ 上传的文件为空")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={"error": "empty_file", "message": "上传的文件为空"}
            )
        
        # 检查文件大小 (限制为10MB)
        max_size = 10 * 1024 * 1024  # 10MB
        if len(image_bytes) > max_size:
            logger.warning(f"❌ 文件过大: {len(image_bytes)} bytes")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "error": "file_too_large",
                    "message": f"文件大小超过限制 (最大 {max_size/(1024*1024):.1f}MB)",
                    "size": len(image_bytes)
                }
            )
            
        image_base64 = base64.b64encode(image_bytes).decode("utf-8")
        logger.info(f"✅ 图片编码完成: {len(image_bytes)} bytes")
        logger.info("="*60)
        logger.info("🚀 开始执行完整的 RAG 分析流程...")
        logger.info("="*60)
        
        # 3. 运行 LCEL 管道
        response_json = await full_pipeline.ainvoke(image_base64)
        
        logger.info("="*60)
        logger.info(f"📊 最终生成的报告: {response_json}")
        logger.info(f"✅ 分析完成, 发现 {len(response_json.get('violations', []))} 个隐患")
        logger.info("="*60)
        
        return response_json
        
    except HTTPException:
        # 重新抛出 HTTP 异常
        raise
    
    except (ValueError, ValidationError, ResponseValidationError) as e:
        # JSON解析失败或Pydantic验证失败（通常是VLM输出被截断）
        logger.error(f"❌ 数据验证失败: {type(e).__name__}: {e}", exc_info=True)
        
        # 尝试提取部分结果
        error_detail = {
            "error": "validation_error",
            "message": "模型输出不完整或格式不符合要求，可能是响应被截断",
            "error_type": type(e).__name__,
            "details": str(e),
            "suggestion": "建议：图片可能过于复杂或隐患过多，请尝试更简单的图片或联系管理员增加模型输出长度限制"
        }
        
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=error_detail
        )
        
    except Exception as e:
        logger.error(f"❌ 分析处理失败: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error": "internal_server_error",
                "message": "服务器内部错误，请稍后重试",
                "details": str(e)
            }
        )
    finally:
        # 清理资源
        await file.close()


# 根路径重定向到文档
@app.get("/", tags=["Root"])
async def root():
    """根路径 - 返回 API 信息"""
    return {
        "name": "SafetyVision-RAG",
        "description": "AI-Powered Safety Hazard Detection System",
        "version": "2.0.0",
        "docs": "/docs",
        "health": "/health"
    }


# --- 文档管理接口 ---

# 配置常量
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB per file
MAX_FILES_COUNT = 10               # 一次最多10个文件
COLLECTION_NAME = os.environ.get("QDRANT_COLLECTION", "rag-test")

# 初始化文本分割器
text_splitter = RecursiveCharacterTextSplitter(
    chunk_size=1000,
    chunk_overlap=200,
    length_function=len,
    separators=["\n\n", "\n", "。", "！", "？", ".", "!", "?", " ", ""]
)


def is_document_exists(filename: str) -> bool:
    """
    检查文档是否已存在于向量库中
    
    Args:
        filename: 文件名
        
    Returns:
        是否存在
    """
    try:
        result = qdrant_client.scroll(
            collection_name=COLLECTION_NAME,
            scroll_filter={
                "must": [
                    {"key": "metadata.filename", "match": {"value": filename}}
                ]
            },
            limit=1,
            with_payload=True,
            with_vectors=False
        )
        return len(result[0]) > 0
    except Exception as e:
        logger.error(f"检查文档存在性失败: {e}")
        return False


def get_document_chunks_count(filename: str) -> int:
    """
    获取文档的文本块数量
    
    Args:
        filename: 文件名
        
    Returns:
        文本块数量
    """
    try:
        result = qdrant_client.scroll(
            collection_name=COLLECTION_NAME,
            scroll_filter={
                "must": [
                    {"key": "metadata.filename", "match": {"value": filename}}
                ]
            },
            limit=10000,  # 假设单个文档不会超过10000个chunk
            with_payload=False,
            with_vectors=False
        )
        return len(result[0])
    except Exception as e:
        logger.error(f"获取文档块数量失败: {e}")
        return 0


async def process_pdf_file(
    file: UploadFile,
    skip_existing: bool,
    update_existing: bool
) -> DocumentDetail:
    """
    处理单个PDF文件
    
    Args:
        file: 上传的文件
        skip_existing: 是否跳过已存在的文档
        update_existing: 是否更新已存在的文档
        
    Returns:
        文档处理详情
    """
    filename = file.filename
    
    try:
        # 1. 检查文件类型
        if not filename.lower().endswith('.pdf'):
            return DocumentDetail(
                filename=filename,
                status="failed",
                message="文件格式错误，只支持PDF文件"
            )
        
        # 2. 检查文件大小
        content = await file.read()
        if len(content) > MAX_FILE_SIZE:
            return DocumentDetail(
                filename=filename,
                status="failed",
                message=f"文件过大，超过{MAX_FILE_SIZE/(1024*1024):.1f}MB限制"
            )
        
        # 3. 检查是否已存在
        exists = is_document_exists(filename)
        if exists:
            if skip_existing and not update_existing:
                logger.info(f"⏭️  跳过已存在的文档: {filename}")
                return DocumentDetail(
                    filename=filename,
                    status="skipped",
                    message="文档已存在，已跳过"
                )
            elif update_existing:
                logger.info(f"🔄 更新文档: {filename}")
                # 先删除旧文档
                delete_result = qdrant_client.delete(
                    collection_name=COLLECTION_NAME,
                    points_selector=Filter(
                        must=[
                            FieldCondition(
                                key="metadata.filename",
                                match=MatchValue(value=filename)
                            )
                        ]
                    )
                )
        
        # 4. 保存临时文件
        with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as tmp_file:
            tmp_file.write(content)
            tmp_path = tmp_file.name
        
        try:
            # 5. 加载PDF
            logger.info(f"📄 加载PDF: {filename}")
            loader = PyPDFLoader(tmp_path)
            documents = loader.load()
            
            # 添加元数据
            for doc in documents:
                doc.metadata.update({
                    "source": filename,
                    "filename": filename,
                    "upload_time": datetime.now().isoformat()
                })
            
            # 6. 分割文档
            logger.info(f"✂️  分割文档: {filename}")
            chunks = text_splitter.split_documents(documents)
            
            if not chunks:
                return DocumentDetail(
                    filename=filename,
                    status="failed",
                    message="文档分割失败，未生成文本块"
                )
            
            # 7. 向量化并存储
            logger.info(f"💾 存储文档: {filename}, 共 {len(chunks)} 个文本块")
            QdrantVectorStore.from_documents(
                documents=chunks,
                embedding=embeddings_bge,
                url=f"http://{qdrant_host}:{qdrant_port}",
                collection_name=COLLECTION_NAME,
                force_recreate=False  # 追加模式
            )
            
            logger.info(f"✅ 文档处理成功: {filename}")
            return DocumentDetail(
                filename=filename,
                status="success",
                chunks=len(chunks),
                message="文档上传成功" if not exists else "文档更新成功"
            )
            
        finally:
            # 清理临时文件
            Path(tmp_path).unlink(missing_ok=True)
    
    except Exception as e:
        logger.error(f"❌ 处理文档失败 {filename}: {e}", exc_info=True)
        return DocumentDetail(
            filename=filename,
            status="failed",
            message=f"处理失败: {str(e)}"
        )


@app.post("/api/documents/upload", response_model=UploadResponse, tags=["Documents"])
async def upload_documents(
    files: List[UploadFile] = File(..., description="PDF文件列表，支持批量上传"),
    skip_existing: bool = Query(True, description="是否跳过已存在的文档"),
    update_existing: bool = Query(False, description="是否更新已存在的文档")
) -> UploadResponse:
    """
    上传单个或多个PDF文档到向量库（追加模式）
    
    功能说明：
    - 支持批量上传（最多10个文件）
    - 自动检测重复文档
    - 可选择跳过或更新已存在的文档
    - 返回每个文档的详细处理结果
    
    Args:
        files: PDF文件列表
        skip_existing: 跳过已存在的文档（默认True）
        update_existing: 更新已存在的文档（默认False）
                        注意：update_existing=True时会覆盖skip_existing
        
    Returns:
        上传结果，包含统计信息和每个文档的详细状态
        
    Raises:
        HTTPException: 
            - 400: 文件数量超限或文件类型错误
            - 500: 服务器处理错误
    
    示例：
        单个文件上传：
        curl -X POST "http://localhost:8080/api/documents/upload" \\
             -F "files=@document.pdf"
        
        批量上传：
        curl -X POST "http://localhost:8080/api/documents/upload" \\
             -F "files=@doc1.pdf" \\
             -F "files=@doc2.pdf"
        
        强制更新：
        curl -X POST "http://localhost:8080/api/documents/upload?update_existing=true" \\
             -F "files=@document.pdf"
    """
    logger.info(f"📤 收到文档上传请求，文件数: {len(files)}")
    
    # 1. 验证文件数量
    if len(files) > MAX_FILES_COUNT:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "error": "too_many_files",
                "message": f"文件数量超限，最多支持{MAX_FILES_COUNT}个文件",
                "received": len(files),
                "limit": MAX_FILES_COUNT
            }
        )
    
    # 2. 验证至少有一个文件
    if not files:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "error": "no_files",
                "message": "未接收到任何文件"
            }
        )
    
    # 3. 处理每个文件
    details = []
    processed = 0
    skipped = 0
    updated = 0
    failed = 0
    total_chunks = 0
    
    for file in files:
        detail = await process_pdf_file(file, skip_existing, update_existing)
        details.append(detail)
        
        if detail.status == "success":
            if is_document_exists(detail.filename) and update_existing:
                updated += 1
            else:
                processed += 1
            total_chunks += detail.chunks or 0
        elif detail.status == "skipped":
            skipped += 1
        else:
            failed += 1
    
    # 4. 构建响应
    success = failed == 0
    results = {
        "processed": processed,
        "skipped": skipped,
        "updated": updated,
        "failed": failed,
        "total_chunks": total_chunks,
        "total_files": len(files)
    }
    
    logger.info("="*60)
    logger.info(f"📊 上传统计: {results}")
    logger.info("="*60)
    
    return UploadResponse(
        success=success,
        message="文档上传完成" if success else "部分文档上传失败",
        results=results,
        details=details
    )


@app.delete("/api/documents", response_model=DeleteResponse, tags=["Documents"])
async def delete_documents(
    filenames: List[str] = Query(..., description="要删除的文件名列表，如: ['doc1.pdf', 'doc2.pdf']"),
    force: bool = Query(False, description="强制删除（即使文档不存在也不报错）")
) -> DeleteResponse:
    """
    删除单个或多个文档
    
    功能说明：
    - 支持批量删除
    - 从向量库中完全移除文档的所有文本块
    - 返回每个文档的详细删除结果
    
    Args:
        filenames: 文件名列表
        force: 强制删除模式，不存在的文档也返回成功
        
    Returns:
        删除结果，包含统计信息和每个文档的详细状态
        
    Raises:
        HTTPException: 
            - 400: 参数错误
            - 500: 服务器处理错误
    
    示例：
        删除单个文档：
        curl -X DELETE "http://localhost:8080/api/documents?filenames=doc.pdf"
        
        删除多个文档：
        curl -X DELETE "http://localhost:8080/api/documents?filenames=doc1.pdf&filenames=doc2.pdf"
        
        强制删除：
        curl -X DELETE "http://localhost:8080/api/documents?filenames=doc.pdf&force=true"
    """
    logger.info(f"🗑️  收到文档删除请求，文件数: {len(filenames)}")
    
    # 1. 验证参数
    if not filenames:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "error": "no_filenames",
                "message": "未指定要删除的文件名"
            }
        )
    
    # 2. 处理每个文件
    details = []
    deleted = 0
    not_found = 0
    failed = 0
    
    for filename in filenames:
        try:
            # 检查文档是否存在
            chunks_count = get_document_chunks_count(filename)
            
            if chunks_count == 0:
                logger.info(f"📝 文档不存在: {filename}")
                not_found += 1
                details.append(DeleteDetail(
                    filename=filename,
                    status="not_found",
                    message="文档不存在" if not force else "文档不存在（强制模式，忽略）"
                ))
                continue
            
            # 执行删除
            logger.info(f"🗑️  删除文档: {filename}, 文本块数: {chunks_count}")
            result = qdrant_client.delete(
                collection_name=COLLECTION_NAME,
                points_selector=Filter(
                    must=[
                        FieldCondition(
                            key="metadata.filename",
                            match=MatchValue(value=filename)
                        )
                    ]
                )
            )
            
            deleted += 1
            details.append(DeleteDetail(
                filename=filename,
                status="deleted",
                chunks_removed=chunks_count,
                message="删除成功"
            ))
            logger.info(f"✅ 文档删除成功: {filename}")
            
        except Exception as e:
            logger.error(f"❌ 删除文档失败 {filename}: {e}", exc_info=True)
            failed += 1
            details.append(DeleteDetail(
                filename=filename,
                status="failed",
                message=f"删除失败: {str(e)}"
            ))
    
    # 3. 构建响应
    success = (failed == 0) and (not_found == 0 or force)
    results = {
        "deleted": deleted,
        "not_found": not_found,
        "failed": failed,
        "total_requested": len(filenames)
    }
    
    logger.info("="*60)
    logger.info(f"📊 删除统计: {results}")
    logger.info("="*60)
    
    return DeleteResponse(
        success=success,
        message="文档删除完成" if success else "部分文档删除失败或未找到",
        results=results,
        details=details
    )


@app.get("/api/documents", response_model=List[DocumentInfo], tags=["Documents"])
async def list_documents() -> List[DocumentInfo]:
    """
    列出所有已上传的文档
    
    Returns:
        文档列表，包含文件名、文本块数量等信息
        
    示例：
        curl http://localhost:8080/api/documents
    """
    try:
        # 获取所有点的元数据
        all_docs = {}
        offset = None
        
        while True:
            result = qdrant_client.scroll(
                collection_name=COLLECTION_NAME,
                limit=100,
                offset=offset,
                with_payload=True,
                with_vectors=False
            )
            
            points, next_offset = result
            
            if not points:
                break
            
            for point in points:
                filename = point.payload.get('metadata', {}).get('filename', 'unknown')
                source = point.payload.get('metadata', {}).get('source', filename)
                
                if filename not in all_docs:
                    all_docs[filename] = {
                        'filename': filename,
                        'source': source,
                        'chunks_count': 0
                    }
                all_docs[filename]['chunks_count'] += 1
            
            if next_offset is None:
                break
            offset = next_offset
        
        documents = [
            DocumentInfo(
                filename=info['filename'],
                chunks_count=info['chunks_count'],
                source=info['source']
            )
            for info in all_docs.values()
        ]
        
        logger.info(f"📚 返回文档列表，共 {len(documents)} 个文档")
        return documents
        
    except Exception as e:
        logger.error(f"❌ 获取文档列表失败: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error": "list_documents_failed",
                "message": f"获取文档列表失败: {str(e)}"
            }
        )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8000,
        log_level="info"
    )