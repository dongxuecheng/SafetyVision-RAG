"""
QA service using RAG with LangChain

Reuses existing components:
- SafetyRetriever for document retrieval
- LLM configuration from deps
- Qdrant vector store
"""

from typing import List
from langchain_core.messages import HumanMessage, SystemMessage, AIMessage
from langchain_core.documents import Document

from app.core.deps import get_llm, get_vector_store, get_reranker_client
from app.core.config import get_settings
from app.core.retrieval import SafetyRetriever
from app.schemas.qa import QAResponse, SourceDocument


class QAService:
    """
    RAG-based QA service

    Architecture:
    - Retrieval: Reuses SafetyRetriever (Similarity + Rerank)
    - Generation: Reuses LLM from deps (Qwen-VL)
    - Storage: Uses dedicated QA collection in Qdrant
    """

    def __init__(self):
        self.llm = get_llm()
        self.settings = get_settings()

        # Initialize retriever for QA knowledge base
        self.retriever = SafetyRetriever(
            get_vector_store("qa"),  # Uses qdrant_collection_qa
            reranker_client=get_reranker_client(),
        )

    async def answer_question(self, question: str) -> QAResponse:
        """
        Answer user question using RAG

        Flow:
        1. Retrieve relevant documents from knowledge base
        2. Format retrieved documents as context
        3. Generate answer using LLM with context
        4. Return answer with source documents
        """
        # Step 1: Retrieve relevant documents
        docs = await self.retriever.retrieve_with_fallback(
            query=question,
            k=self.settings.regulations_retrieval_k,  # Reuse existing config
            score_threshold=self.settings.retrieval_score_threshold,
        )

        # Step 2: Check if we have relevant sources
        has_sources = len(docs) > 0 and (
            docs[0].metadata.get("score", 0.0) >= self.settings.min_retrieval_score
        )

        if not has_sources:
            # No relevant documents found
            return QAResponse(
                answer="抱歉，我在知识库中没有找到与您的问题相关的信息。请尝试换个方式提问，或者上传相关文档。",
                sources=[],
                has_relevant_sources=False,
            )

        # Step 3: Format context from retrieved documents
        context = self._format_context(docs)

        # Step 4: Generate answer using LLM
        answer = await self._generate_answer(question, context)

        # Step 5: Format source documents
        sources = self._format_sources(docs)

        return QAResponse(answer=answer, sources=sources, has_relevant_sources=True)

    async def answer_question_stream_simple(self, question: str):
        """
        Answer user question using RAG, return stream without sources, disabled thinking mode.
        Useful for digital avatars (数字人).
        """
        # Step 1: Retrieve relevant documents
        docs = await self.retriever.retrieve_with_fallback(
            query=question,
            k=self.settings.regulations_retrieval_k,
            score_threshold=self.settings.retrieval_score_threshold,
        )

        has_sources = len(docs) > 0 and (
            docs[0].metadata.get("score", 0.0) >= self.settings.min_retrieval_score
        )

        if not has_sources:
            yield "抱歉，我在知识库中没有找到与您的问题相关的信息。"
            return

        context = self._format_context(docs)

        messages = [
            SystemMessage(
                content="""你是一个专业的知识问答助手，负责为数字人提供回答。
根据提供的文档内容回答用户问题。

要求：
1. 答案必须基于提供的文档内容，不要编造信息
2. 如果文档中没有相关信息，请直接回答未找到相关信息
3. 回答要口语化、准确、简洁、易懂，适合直接朗读
4. 尽量不要使用复杂的Markdown格式或表格
"""
            ),
            HumanMessage(
                content=f"""问题: {question}

参考文档:
{context[:self.settings.max_context_length]}

请基于以上文档回答问题。"""
            ),
        ]

        try:
            # 流式返回，并通过 extra_body 禁用思考模式
            async for chunk in self.llm.astream(
                messages,
                extra_body={"chat_template_kwargs": {"enable_thinking": False}}
            ):
                if chunk.content:
                    yield chunk.content
        except Exception as e:
            yield f"抱歉，生成答案时出现错误: {str(e)}"

    def _format_context(self, docs: List[Document]) -> str:
        """
        Format retrieved documents into context string
        """
        context_parts = []

        for i, doc in enumerate(docs[:5], 1):  # Use top 5 documents
            content = doc.page_content[: self.settings.max_doc_length]
            score = doc.metadata.get("score", 0.0)
            filename = doc.metadata.get("filename", "未知来源")

            context_parts.append(
                f"[文档{i}] (来源: {filename}, 相似度: {score:.3f})\n{content}"
            )

        return "\n\n---\n\n".join(context_parts)

    async def _generate_answer(self, question: str, context: str) -> str:
        """
        Generate answer using LLM with retrieved context
        """
        messages = [
            SystemMessage(
                content="""你是一个专业的知识问答助手。根据提供的文档内容回答用户问题。

要求：
1. 答案必须基于提供的文档内容，不要编造信息
2. 如果文档中没有相关信息，明确告知用户
3. 回答要准确、简洁、易懂
4. 适当引用文档来源
5. 使用专业但友好的语气
6. 如需展示数学公式，使用 LaTeX 格式（行内公式用 $...$ ，独立公式用 $$...$$）

回答格式：
- 直接回答问题（100-300字）
- 必要时分点说明
- 标注关键信息来源
"""
            ),
            HumanMessage(
                content=f"""问题: {question}

参考文档:
{context[:self.settings.max_context_length]}

请基于以上文档回答问题。"""
            ),
        ]

        try:
            response = await self.llm.ainvoke(messages)
            return response.content
        except Exception as e:
            return f"抱歉，生成答案时出现错误: {str(e)}"

    async def _generate_answer_stream(self, question: str, context: str):
        """
        Generate answer using LLM with streaming support
        Yields tokens one by one for real-time display
        """
        messages = [
            SystemMessage(
                content="""你是一个专业的知识问答助手。根据提供的文档内容回答用户问题。

要求：
1. 答案必须基于提供的文档内容，不要编造信息
2. 如果文档中没有相关信息，明确告知用户
3. 回答要准确、简洁、易懂
4. 适当引用文档来源
5. 使用专业但友好的语气
6. 如需展示数学公式，使用 LaTeX 格式（行内公式用 $...$ ，独立公式用 $$...$$）

回答格式：
- 直接回答问题（100-300字）
- 必要时分点说明
- 标注关键信息来源
"""
            ),
            HumanMessage(
                content=f"""问题: {question}

参考文档:
{context[:self.settings.max_context_length]}

请基于以上文档回答问题。"""
            ),
        ]

        try:
            # Use astream for streaming response
            async for chunk in self.llm.astream(messages):
                if chunk.content:
                    yield chunk.content
        except Exception as e:
            yield f"抱歉，生成答案时出现错误: {str(e)}"

    async def _generate_answer_stream_with_history(
        self, question: str, context: str, message_history: List[dict]
    ):
        """
        Generate answer with conversation history support

        Args:
            question: Current user question
            context: Retrieved document context
            message_history: List of previous messages [{"role": "user/assistant", "content": "..."}]
        """
        messages = [
            SystemMessage(
                content="""你是一个专业的知识问答助手。根据提供的文档内容和对话历史回答用户问题。

要求：
1. 答案必须基于提供的文档内容，不要编造信息
2. 如果用户提到“上一个问题”或“刚才”，请参考对话历史
3. 回答要准确、简洁、易懂，能够联系上下文
4. 适当引用文档来源
5. 使用专业但友好的语气
6. 如需展示数学公式，使用 LaTeX 格式（行内公式用 $...$ ，独立公式用 $$...$$）

回答格式：
- 直接回答问题（100-300字）
- 必要时分点说明
- 标注关键信息来源
"""
            )
        ]

        # Add conversation history (up to last 5 rounds)
        for msg in message_history[-10:]:
            if msg["role"] == "user":
                messages.append(HumanMessage(content=msg["content"]))
            elif msg["role"] == "assistant":
                messages.append(AIMessage(content=msg["content"]))

        # Add current question with context
        messages.append(
            HumanMessage(
                content=f"""问题: {question}

参考文档:
{context[:self.settings.max_context_length]}

请基于以上文档和对话历史回答问题。"""
            )
        )

        try:
            async for chunk in self.llm.astream(
                messages,
                extra_body={"chat_template_kwargs": {"enable_thinking": False}},
            ):
                if chunk.content:
                    yield chunk.content
        except Exception as e:
            yield f"抱歉，生成答案时出现错误: {str(e)}"

    def _format_sources(self, docs: List[Document]) -> List[SourceDocument]:
        """
        Format documents as source references
        """
        sources = []

        for doc in docs[:5]:  # Return top 5 sources
            filename = doc.metadata.get("filename", "未知来源")
            score = doc.metadata.get("score", 0.0)

            # Extract location
            sheet = doc.metadata.get("sheet_name")
            row_range = doc.metadata.get("row_range")
            row = doc.metadata.get("row_number")
            page = doc.metadata.get("page")
            section = doc.metadata.get("section")

            if sheet and (row_range or row):
                row_info = row_range if row_range else f"{row}"
                location = f"工作表: {sheet}, 行: {row_info}"
            elif page is not None:
                location = f"页码: {page + 1}"
            elif section:
                location = f"章节: {section}"
            else:
                location = "位置未知"

            sources.append(
                SourceDocument(
                    content=doc.page_content[:300],  # Preview first 300 chars
                    filename=filename,
                    location=location,
                    score=score,
                )
            )

        return sources
