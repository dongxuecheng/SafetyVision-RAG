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
import asyncio
from typing import List
from uuid import uuid4

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.documents import Document
from langchain_core.runnables import chain
from fastapi import UploadFile, HTTPException, status

from app.core.deps import get_llm, get_vector_store
from app.core.config import get_settings
from app.core.retrieval import SafetyRetriever
from app.schemas.safety import SafetyReport, SafetyViolation, HazardList


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
    # Note: This is kept for backward compatibility but not actively used in per-hazard retrieval
    SYSTEM_PROMPT = """你是安全报告生成器。根据发现的隐患和检索到的规范，生成结构化安全报告。

分析要求：
1. rule_reference 根据文档内容灵活填写（有标准编号则引用标准，无则引用原文）
2. 如果未检索到相关规范，在 rule_reference 中说明"未找到相关规范"
3. 严格按照 SafetyReport schema 返回结构化数据
"""

    def __init__(self):
        self.llm = get_llm()
        self.settings = get_settings()
        # Initialize retriever with Rerank support
        from app.core.deps import get_reranker_client

        self.retriever = SafetyRetriever(
            get_vector_store(), reranker_client=get_reranker_client()
        )
        # Structured LLMs for different outputs
        self.hazards_llm = self.llm.with_structured_output(HazardList)
        self.violation_llm = self.llm.with_structured_output(SafetyViolation)

    async def analyze_image(self, file: UploadFile) -> SafetyReport:
        """
        Analyze image for safety hazards using per-hazard retrieval

        Flow:
        1. VLM extracts structured hazard list
        2. Each hazard independently retrieves relevant regulations
        3. Each hazard generates individual SafetyViolation with specific rule_reference
        4. Combine all violations into final report
        """
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

        # Step 1: Extract structured hazard list using VLM
        image_b64 = base64.b64encode(image_bytes).decode()
        hazards_list = await self._extract_hazards_as_list(image_b64)

        if not hazards_list:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="No safety hazards detected in the image",
            )

        # Step 2: Batch retrieve documents for each hazard (parallel)
        docs_per_hazard = await self._batch_retrieve_per_hazard(hazards_list)

        # Step 3: Generate violations for each hazard (parallel)
        violation_tasks = [
            self._generate_single_violation(hazard, docs, i + 1)
            for i, (hazard, docs) in enumerate(zip(hazards_list, docs_per_hazard))
        ]
        violations = await asyncio.gather(*violation_tasks)

        # Step 4: Assemble final report
        report = SafetyReport(
            report_id=str(uuid4()),
            violations=violations,
        )

        return report

    async def _extract_hazards_as_list(self, image_b64: str) -> List[str]:
        """
        Extract hazards from image as structured list using VLM

        Returns list of hazard descriptions (e.g., ["未佩戴安全帽", "高空作业无安全带"])
        """
        messages = [
            SystemMessage(
                content="""你是安全专家。分析图片并提取安全隐患。

要求：
1. 每条隐患用简洁语言描述（10-20字）
2. 按严重程度排序（最严重的在前）
3. 提取 1-5 个最重要的隐患
4. 返回结构化的隐患列表
"""
            ),
            HumanMessage(
                content=[
                    {
                        "type": "text",
                        "text": "请分析图片中的安全隐患：",
                    },
                    {
                        "type": "image_url",
                        "image_url": {"url": f"data:image/png;base64,{image_b64}"},
                    },
                ]
            ),
        ]

        try:
            result = await self.hazards_llm.ainvoke(messages)
            return result.hazards
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"VLM 隐患提取失败: {str(e)}",
            )

    async def _batch_retrieve_per_hazard(
        self, hazards_list: List[str]
    ) -> List[List[Document]]:
        """
        Batch retrieve documents for each hazard in parallel

        Each hazard gets independent retrieval for precise rule matching
        """
        tasks = [
            self.retriever.retrieve_with_fallback(hazard, k=3)
            for hazard in hazards_list
        ]
        return await asyncio.gather(*tasks)

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

    async def _generate_single_violation(
        self, hazard: str, docs: List[Document], hazard_id: int
    ) -> SafetyViolation:
        """
        Generate SafetyViolation for a single hazard with its retrieved documents

        This ensures each hazard has precise rule_reference from relevant docs
        """
        formatted = self._format_documents(docs)

        messages = [
            SystemMessage(
                content="""你是安全报告生成器。为单条隐患生成 SafetyViolation。

输出要求（简洁明确）：
1. hazard_description: 隐患的详细描述（20-50字）
2. recommendations: 整改建议（1-3条，每条不超过30字）
3. rule_reference: 规范引用（根据检索到的文档内容灵活填写）

- 不要编造不存在的标准编号或条款号
- 不要添加检索文档中没有的内容
- 必须保留来源的精确定位信息（如 Excel 的工作表名和行号,doc文档的页码等）

关键原则：如实转述检索到的内容，根据文档实际格式选择合适的引用方式
"""
            ),
            HumanMessage(
                content=f"""隐患: {hazard}

相关规范:
{formatted['context'][:1500]}

来源: {formatted['sources']}
"""
            ),
        ]

        try:
            # Retry with increased max_tokens if needed
            violation = await self.violation_llm.ainvoke(messages)
            violation.hazard_id = hazard_id
            return violation
        except Exception as e:
            # Fallback: return minimal violation
            error_msg = str(e)
            if "length limit" in error_msg or "max_tokens" in error_msg:
                # Token limit exceeded, return simplified violation
                return SafetyViolation(
                    hazard_id=hazard_id,
                    hazard_description=hazard,
                    recommendations="1. 立即停止作业并整改\n2. 联系安全负责人检查\n3. 符合规范后方可继续",
                    rule_reference="未找到相关规范（输出超过长度限制，请优化检索文档）",
                )
            else:
                # Other errors
                return SafetyViolation(
                    hazard_id=hazard_id,
                    hazard_description=hazard,
                    recommendations="请咨询安全专家获取整改建议",
                    rule_reference=f"未找到相关规范（检索失败: {error_msg[:100]}）",
                )
