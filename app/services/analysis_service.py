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

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.documents import Document
from fastapi import UploadFile, HTTPException, status

from app.core.deps import get_llm, get_vector_store
from app.core.config import get_settings
from app.core.retrieval import SafetyRetriever
from app.schemas.safety import (
    SafetyReport,
    SafetyViolation,
    SafetyViolationLLM,
    HazardList,
    SourceReference,
)


class AnalysisService:
    """
    Service for safety analysis using VLM and RAG

    Implements modern LangChain v1.0+ patterns:
    - with_structured_output for type-safe Pydantic responses
    - Modular retrieval with rerank and similarity strategies
    - Proper async/await throughout
    - Comprehensive error handling
    """

    def __init__(self):
        self.llm = get_llm()
        self.settings = get_settings()

        # Load formatting constants from config
        self.MAX_DOC_LENGTH = self.settings.max_doc_length
        self.MAX_CONTEXT_LENGTH = self.settings.max_context_length
        # Initialize retriever with Rerank support
        from app.core.deps import get_reranker_client

        # Primary retriever: regulations collection (PDF/Markdown/Word)
        self.regulations_retriever = SafetyRetriever(
            get_vector_store("regulations"), reranker_client=get_reranker_client()
        )

        # Secondary retriever: hazard database collection (Excel)
        self.hazard_db_retriever = SafetyRetriever(
            get_vector_store("hazard_db"), reranker_client=get_reranker_client()
        )

        # Backward compatibility
        self.retriever = self.regulations_retriever

        # Structured LLMs for different outputs
        self.hazards_llm = self.llm.with_structured_output(HazardList)
        # Use SafetyViolationLLM (without source_documents) for LLM generation
        self.violation_llm = self.llm.with_structured_output(SafetyViolationLLM)

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
        Multi-collection retrieval strategy:
        1. Primary: regulations collection (PDF/Markdown/Word) - k=3
        2. Fallback: hazard_db collection (Excel) - only if regulations insufficient

        This ensures Excel data doesn't pollute regulation-based retrieval
        """
        all_results = []

        for hazard in hazards_list:
            # Step 1: Try regulations collection first (higher quality)
            regulations_docs = await self.regulations_retriever.retrieve_with_fallback(
                hazard,
                k=self.settings.regulations_retrieval_k,
                score_threshold=self.settings.regulations_score_threshold,
            )

            # Step 2: Check if regulations results are sufficient
            # If we have enough high-quality docs, use them directly
            if (
                regulations_docs
                and len(regulations_docs)
                >= self.settings.regulations_min_sufficient_docs
            ):
                all_results.append(regulations_docs)
                continue

            # Step 3: Regulations insufficient - supplement with hazard_db
            hazard_db_docs = await self.hazard_db_retriever.retrieve_with_fallback(
                hazard,
                k=self.settings.hazard_db_retrieval_k,
                score_threshold=self.settings.hazard_db_score_threshold,
            )

            # Combine: regulations (higher priority) + hazard_db (supplementary)
            combined_docs = regulations_docs + hazard_db_docs
            all_results.append(combined_docs[: self.settings.max_combined_docs])

        return all_results

    def _format_documents(self, docs: List[Document]) -> dict:
        """
        Format retrieved documents into structured context with scores

        Separates content and sources for better prompt clarity
        Extracts similarity scores to help LLM judge relevance objectively
        """
        if not docs:
            return {
                "context": "未检索到相关规范文档。",
                "sources": "无参考文档",
                "source_refs": [],
                "max_score": 0.0,
                "has_high_confidence": False,
            }

        context_parts = []
        sources = set()  # Use set for automatic deduplication
        source_refs = []  # Structured source references
        scores = []  # Collect similarity scores

        for i, doc in enumerate(docs, 1):
            # Extract similarity score from metadata
            score = doc.metadata.get("score", 0.0)
            scores.append(score)

            # Truncate content to avoid token limits
            content = doc.page_content[: self.MAX_DOC_LENGTH]
            # Add score indicator to context
            context_parts.append(f"[文档{i}] (相似度分数: {score:.3f})\n{content}")

            # Collect unique source files and structured references
            filename = doc.metadata.get("filename", "未知来源")
            sheet = doc.metadata.get("sheet_name")
            row_range = doc.metadata.get("row_range")  # New: batch row range
            row = doc.metadata.get("row_number")  # Old: single row (fallback)
            page = doc.metadata.get("page")
            section = doc.metadata.get("section")

            # Build location string
            if sheet and (row_range or row):
                # Excel: prefer row_range (batch), fallback to row_number (legacy)
                row_info = row_range if row_range else f"{row}"
                location = f"工作表: {sheet}, 行: {row_info}"
            elif page is not None:
                # PyPDFLoader uses 0-based indexing, but PDF readers show 1-based page numbers
                # So we add 1 to match what users see in PDF viewers
                location = f"页码: {page + 1}"
            elif section:
                location = f"章节: {section}"
            else:
                location = "位置未知"

            # Add to text sources
            location_suffix = f" ({location})" if location != "位置未知" else ""
            sources.add(f"- {filename}{location_suffix}")

            # Add to structured source references
            source_refs.append(SourceReference(filename=filename, location=location))

        max_score = max(scores) if scores else 0.0

        return {
            "context": "\n---\n".join(context_parts),
            "sources": "\n".join(sorted(sources)),  # Sort for consistency
            "source_refs": source_refs,  # Structured references for API response
            "max_score": max_score,  # Maximum similarity score for objective judgment
            "has_high_confidence": max_score >= 0.7,  # High confidence threshold
        }

    async def _generate_single_violation(
        self, hazard: str, docs: List[Document], hazard_id: int
    ) -> SafetyViolation:
        """
        Generate SafetyViolation for a single hazard with its retrieved documents

        This ensures each hazard has precise rule_reference from relevant docs
        Uses hard threshold (0.4) to filter low-quality retrievals objectively
        """
        formatted = self._format_documents(docs)

        # Hard threshold check: if retrieval score below minimum, directly return as irrelevant
        # This prevents LLM from trying to extract rules from low-quality matches
        if formatted["max_score"] < self.settings.min_retrieval_score:
            default_category = (
                self.settings.hazard_categories[-1]
                if self.settings.hazard_categories
                else "其他"
            )
            default_level = (
                self.settings.hazard_levels[0]
                if self.settings.hazard_levels
                else "一般隐患"
            )
            return SafetyViolation(
                hazard_id=hazard_id,
                hazard_description=hazard,
                hazard_category=default_category,
                hazard_level=default_level,
                recommendations="建议咨询安全专家获取专业整改意见",
                rule_reference=f"未检索到相关规范（检索相似度过低: {formatted['max_score']:.3f}）",
                source_documents=[],
            )

        # Get hazard classification settings from config
        categories_list = "、".join(self.settings.hazard_categories)
        levels_list = "\n   ".join(self.settings.hazard_levels)

        # Build confidence guidance based on score
        max_score = formatted["max_score"]
        if max_score >= self.settings.high_confidence_threshold:
            confidence_level = f"高置信度 (≥{self.settings.high_confidence_threshold})"
            confidence_guidance = "文档很可能与隐患直接相关，仔细提取规范条款"
        elif max_score >= self.settings.medium_confidence_threshold:
            confidence_level = f"中等置信度 ({self.settings.medium_confidence_threshold}-{self.settings.high_confidence_threshold})"
            confidence_guidance = "文档可能相关，需仔细判断关键词匹配度和场景一致性"
        else:
            confidence_level = f"较低置信度 ({self.settings.min_retrieval_score}-{self.settings.medium_confidence_threshold})"
            confidence_guidance = (
                "文档相关性存疑，务必严格检查关键词和场景匹配，谨慎引用"
            )

        messages = [
            SystemMessage(
                content=f"""安全报告生成器。检索相似度: {max_score:.3f}，{confidence_level}。

输出字段（严格遵守长度限制）：
1. hazard_description: 20-40字
2. hazard_category: 必须精确选择：{categories_list}
3. hazard_level: 必须精确选择：{levels_list}
4. recommendations: ≤200字
   - 文档有整改措施时用"[文档依据]"
   - 否则用"[AI建议]"
5. rule_reference: ≤300字
   格式：《规范名》(编号) 第X条：核心要求(≤100字)
   禁止输出冗长原文段落

相关性判断：
- 相关：文档有核心关键词+具体条款+场景匹配
- 不相关：无关键词/场景不符/内容宽泛 → 返回"未检索到相关规范"
- 分数<0.3时优先判断为不相关
"""
            ),
            HumanMessage(
                content=f"""隐患: {hazard}

文档: {formatted['context'][:self.MAX_CONTEXT_LENGTH]}

来源: {formatted['sources']}
"""
            ),
        ]

        try:
            # LLM generates SafetyViolationLLM (without source_documents)
            llm_violation = await self.violation_llm.ainvoke(messages)

            # Only add source_documents if LLM finds relevant regulations
            # Check if rule_reference indicates "no relevant regulations found"
            is_relevant = not any(
                keyword in llm_violation.rule_reference
                for keyword in ["未检索到", "未找到", "未查找到", "检索失败"]
            )

            # Standardize "not found" message format with similarity score
            rule_reference = llm_violation.rule_reference
            if not is_relevant:
                # Replace generic message with score-enriched format for consistency
                rule_reference = f"未检索到相关规范（检索相似度: {formatted['max_score']:.3f}，LLM判断不相关）"

            # Convert to complete SafetyViolation and add source_documents only if relevant
            violation = SafetyViolation(
                hazard_id=hazard_id,
                hazard_description=llm_violation.hazard_description,
                hazard_category=llm_violation.hazard_category,
                hazard_level=llm_violation.hazard_level,
                recommendations=llm_violation.recommendations,
                rule_reference=rule_reference,
                source_documents=(
                    formatted.get("source_refs", []) if is_relevant else []
                ),
            )
            return violation
        except Exception as e:
            # Unified error handling with fallback
            error_msg = str(e)
            is_token_limit = "length limit" in error_msg or "max_tokens" in error_msg

            # Use default values from config
            default_category = (
                self.settings.hazard_categories[-1]
                if self.settings.hazard_categories
                else "其他"
            )
            default_level = (
                self.settings.hazard_levels[0]
                if self.settings.hazard_levels
                else "一般隐患"
            )

            return SafetyViolation(
                hazard_id=hazard_id,
                hazard_description=hazard,
                hazard_category=default_category,
                hazard_level=default_level,
                recommendations=(
                    "[AI建议] 1. 立即停止作业并整改\n[AI建议] 2. 联系安全负责人检查\n[AI建议] 3. 符合规范后方可继续"
                    if is_token_limit
                    else "[AI建议] 请咨询安全专家获取整改建议"
                ),
                rule_reference=(
                    f"未检索到相关规范（检索相似度: {formatted['max_score']:.3f}，LLM生成失败: 输出超长度限制）"
                    if is_token_limit
                    else f"未检索到相关规范（检索相似度: {formatted['max_score']:.3f}，LLM生成失败: {error_msg[:80]}）"
                ),
                source_documents=[],  # Error case should not include source documents
            )
