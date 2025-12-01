"""
Safety analysis service using VLM and RAG

Implements RAG following LangChain v1.0+ best practices:
- with_structured_output for type-safe responses
- Modular retrieval tool pattern
- Proper error handling
- Async-first design
- Clear separation of concerns
"""

import base64
from typing import List

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.documents import Document
from langchain_core.runnables import chain
from fastapi import UploadFile, HTTPException, status

from app.core.deps import get_llm, get_vector_store
from app.core.config import get_settings
from app.core.retrieval import SafetyRetriever
from app.schemas.safety import SafetyReport


class AnalysisService:
    """
    Service for safety analysis using VLM and RAG

    Implements modern LangChain v1.0+ patterns:
    - with_structured_output for type-safe Pydantic responses
    - Modular retrieval with multiple strategies (MMR, similarity)
    - @chain decorator for cleaner composition
    - Proper async/await throughout
    - Comprehensive error handling
    """

    # Class-level system prompt (avoids lru_cache on instance methods)
    SYSTEM_PROMPT = """你是安全报告生成器。根据发现的隐患和检索到的规范，生成结构化安全报告。

分析要求：
1. rule_reference 格式：《标准名称》(标准编号) 第X.X.X条规定：具体内容。
2. 如果未检索到相关规范，在 rule_reference 中说明"未找到相关规范"
3. 严格按照 SafetyReport schema 返回结构化数据
"""

    def __init__(self):
        self.llm = get_llm()
        self.settings = get_settings()
        self.retriever = SafetyRetriever(get_vector_store())
        # Create structured output model using with_structured_output
        self.structured_llm = self.llm.with_structured_output(SafetyReport)

    async def analyze_image(self, file: UploadFile) -> SafetyReport:
        """Analyze image for safety hazards"""
        # Validate file type
        if not file.content_type or not file.content_type.startswith("image/"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid file type. Only images are supported",
            )

        # Read and validate file size
        image_bytes = await file.read()
        if len(image_bytes) > self.settings.max_file_size:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="File too large",
            )

        # Extract hazards from image
        image_b64 = base64.b64encode(image_bytes).decode()
        hazards = await self._extract_hazards(image_b64)

        # Generate report using RAG
        rag_chain = self._create_rag_chain()
        report = await rag_chain.ainvoke(hazards)

        return report

    async def _extract_hazards(self, image_b64: str) -> str:
        """Extract hazards from image using VLM"""
        messages = [
            HumanMessage(
                content=[
                    {
                        "type": "text",
                        "text": "你是安全专家。分析图片并简洁列出3-5个最重要的安全隐患，每条用一行描述。",
                    },
                    {
                        "type": "image_url",
                        "image_url": {"url": f"data:image/png;base64,{image_b64}"},
                    },
                ]
            )
        ]
        response = await self.llm.ainvoke(messages)
        return response.content

    async def _retrieve_safety_context(self, query: str) -> List[Document]:
        """
        Retrieve relevant safety regulations and standards

        Uses SafetyRetriever with automatic fallback strategy
        """
        return await self.retriever.retrieve_with_fallback(query, k=5)

    def _format_documents(self, docs: List[Document]) -> dict:
        """
        Format retrieved documents into structured context

        Separates content and sources for better prompt clarity
        """
        if not docs:
            return {
                "context": "未检索到相关规范文档。",
                "sources": "无参考文档",
            }

        context_parts = []
        sources_parts = []
        seen_files = set()

        for i, doc in enumerate(docs, 1):
            # Truncate content to avoid token limits
            content = doc.page_content[:800]
            context_parts.append(f"[文档{i}] {content}")

            # Collect unique source files
            filename = doc.metadata.get("filename", "未知来源")
            if filename not in seen_files:
                seen_files.add(filename)
                sheet = doc.metadata.get("sheet_name", "")
                row = doc.metadata.get("row_number", "")
                location = f" (工作表: {sheet}, 行: {row})" if sheet and row else ""
                sources_parts.append(f"- {filename}{location}")

        return {
            "context": "\n---\n".join(context_parts),
            "sources": "\n".join(sources_parts),
        }

    def _build_analysis_messages(
        self, hazards: str, context: str, sources: str
    ) -> List:
        """Build messages for structured output generation"""
        return [
            SystemMessage(content=self.SYSTEM_PROMPT),
            HumanMessage(
                content=f"""请根据以下信息生成安全报告：

【相关规范】
{context}

【参考文档来源】
{sources}

【发现的隐患】
{hazards}
"""
            ),
        ]

    def _create_rag_chain(self):
        """
        Create RAG chain using modern LangChain v1.0+ patterns

        Uses with_structured_output for automatic Pydantic validation
        """

        @chain
        async def rag_chain(hazards: str) -> SafetyReport:
            """Execute RAG pipeline: retrieve -> format -> generate"""
            try:
                # Step 1: Retrieve relevant documents
                docs = await self._retrieve_safety_context(hazards)

                # Step 2: Format documents
                formatted = self._format_documents(docs)

                # Step 3: Build messages
                messages = self._build_analysis_messages(
                    hazards=hazards,
                    context=formatted["context"],
                    sources=formatted["sources"],
                )

                # Step 4: Generate structured report
                # with_structured_output automatically:
                # - Injects schema into prompt
                # - Validates response against Pydantic model
                # - Retries on validation errors
                # - Returns typed SafetyReport instance (not dict!)
                report = await self.structured_llm.ainvoke(messages)

                return report

            except Exception as e:
                # Graceful error handling
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=f"RAG 处理失败: {str(e)}",
                )

        return rag_chain
