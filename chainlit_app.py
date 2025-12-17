"""
Chainlit UI for RAG-based QA System

Provides conversational interface for knowledge base Q&A
"""

import chainlit as cl
from typing import List
from langchain_core.messages import HumanMessage, SystemMessage, AIMessage

# Import from our FastAPI app
from app.services.qa_service import QAService
from app.schemas.qa import SourceDocument


# Initialize QA service
qa_service = QAService()


@cl.set_starters
async def set_starters():
    """
    Define starter prompts shown on the home page before chat begins

    Best Practice: Use starters to guide users on how to interact with the system
    """
    return [
        cl.Starter(
            label="安全规范查询",
            message="施工现场的临时用电有哪些安全要求？",
        ),
        cl.Starter(
            label="隐患整改措施",
            message="高处作业未系安全带应该如何整改？需要依据哪些规范？",
        ),
        cl.Starter(
            label="规范条文解读",
            message="请解释《建筑施工高处作业安全技术规范》中关于安全防护的具体要求",
        ),
        cl.Starter(
            label="设备安全标准",
            message="塔吊作业需要满足哪些安全标准？",
        ),
    ]


@cl.on_chat_start
async def on_chat_start():
    """
    Called when a new chat session starts

    Best Practice: Use for session initialization, not welcome messages
    (Welcome messages should be in starters or displayed via UI)
    """
    # Initialize message history in session
    cl.user_session.set("message_history", [])


@cl.on_message
async def on_message(message: cl.Message):
    """
    Handle user messages with streaming support and conversation history
    """
    user_question = message.content

    # Get conversation history from session
    message_history = cl.user_session.get("message_history", [])

    # Create empty message for streaming
    msg = cl.Message(content="")
    await msg.send()

    try:
        # Step 1: Retrieve relevant documents
        docs = await qa_service.retriever.retrieve_with_fallback(
            query=user_question,
            k=qa_service.settings.regulations_retrieval_k,
            score_threshold=qa_service.settings.retrieval_score_threshold,
        )

        # Step 2: Check if we have relevant sources
        has_sources = len(docs) > 0 and (
            docs[0].metadata.get("score", 0.0)
            >= qa_service.settings.min_retrieval_score
        )

        if not has_sources:
            # No relevant documents found
            no_result_msg = "抱歉，我在知识库中没有找到与您的问题相关的信息。请尝试换个方式提问，或者上传相关文档。"
            await msg.stream_token(no_result_msg)
            await msg.update()

            # Update history even for no-result responses
            message_history.append({"role": "user", "content": user_question})
            message_history.append({"role": "assistant", "content": no_result_msg})
            cl.user_session.set("message_history", message_history)
            return

        # Step 3: Format context
        context = qa_service._format_context(docs)

        # Step 4: Stream answer token by token (with conversation history)
        full_answer = ""
        async for token in qa_service._generate_answer_stream_with_history(
            user_question, context, message_history
        ):
            await msg.stream_token(token)
            full_answer += token

        # Step 5: Add sources after answer is complete
        sources_text = "\n\n📚 **参考来源：**\n"
        text_elements: List[cl.Text] = []

        for idx, doc in enumerate(docs[:5], 1):
            source_name = f"source_{idx}"
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

            # Create expandable source element
            text_elements.append(
                cl.Text(
                    name=source_name,
                    content=f"""**文件:** {filename}
**位置:** {location}
**相似度:** {score:.3f}

**内容:**
{doc.page_content[:300]}
""",
                    display="side",
                )
            )

            # 禁用超链接，使用纯文本显示
            sources_text += f"{idx}. {filename} (相似度: {score:.2f})\n"

        # Stream sources
        await msg.stream_token(sources_text)
        msg.elements = text_elements
        await msg.update()

        # Step 6: Update conversation history
        message_history.append({"role": "user", "content": user_question})
        message_history.append({"role": "assistant", "content": full_answer})

        # Keep only last 10 messages (5 rounds) to avoid token limits
        if len(message_history) > 10:
            message_history = message_history[-10:]

        cl.user_session.set("message_history", message_history)

    except Exception as e:
        error_msg = f"\n\n❌ 抱歉，处理您的问题时出现错误：{str(e)}"
        await msg.stream_token(error_msg)
        await msg.update()

        # Update history even for errors
        message_history.append({"role": "user", "content": user_question})
        message_history.append({"role": "assistant", "content": error_msg})
        cl.user_session.set("message_history", message_history)


@cl.on_chat_end
async def on_chat_end():
    """
    Called when chat session ends
    """
    pass


if __name__ == "__main__":
    # This is just for reference - Chainlit runs with: chainlit run chainlit_app.py
    pass
