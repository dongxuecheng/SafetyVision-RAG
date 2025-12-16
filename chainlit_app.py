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


@cl.on_chat_start
async def on_chat_start():
    """
    Called when a new chat session starts
    """
    # Initialize message history in session
    cl.user_session.set("message_history", [])

    # Send welcome message
    await cl.Message(
        content="""👋 欢迎使用 RAG 知识问答系统！

我可以帮您：
✅ 回答知识库中的专业问题
✅ 查找相关文档和参考依据
✅ 提供准确的信息来源

💡 使用建议：
- 提问要具体明确
- 可以追问深入细节
- 我会标注信息来源

请开始提问吧！"""
    ).send()


@cl.on_message
async def on_message(message: cl.Message):
    """
    Handle user messages
    """
    user_question = message.content

    # Show loading message
    msg = cl.Message(content="")
    await msg.send()

    try:
        # Get answer from QA service
        response = await qa_service.answer_question(user_question)

        # Format answer with sources
        answer_text = response.answer

        # Create text elements for sources
        text_elements: List[cl.Text] = []

        if response.has_relevant_sources and response.sources:
            answer_text += "\n\n📚 **参考来源：**\n"

            for idx, source in enumerate(response.sources, 1):
                source_name = f"source_{idx}"

                # Create expandable source element
                text_elements.append(
                    cl.Text(
                        name=source_name,
                        content=f"""**文件:** {source.filename}
**位置:** {source.location}
**相似度:** {source.score:.3f}

**内容:**
{source.content}
""",
                        display="side",  # Display in sidebar
                    )
                )

                # Add source reference to answer
                answer_text += f"{idx}. [{source.filename}](#{source_name}) (相似度: {source.score:.2f})\n"
        else:
            answer_text += "\n\n💡 *未找到相关文档，建议补充知识库或换个方式提问*"

        # Update message with answer
        msg.content = answer_text
        msg.elements = text_elements
        await msg.update()

    except Exception as e:
        msg.content = f"❌ 抱歉，处理您的问题时出现错误：{str(e)}"
        await msg.update()


@cl.on_chat_end
async def on_chat_end():
    """
    Called when chat session ends
    """
    pass


# Optional: Custom settings
@cl.set_chat_profiles
async def chat_profile():
    """
    Define chat profiles (optional)
    """
    return [
        cl.ChatProfile(
            name="QA Assistant",
            markdown_description="基于知识库的问答助手",
            icon="https://picsum.photos/200",
        ),
    ]


if __name__ == "__main__":
    # This is just for reference - Chainlit runs with: chainlit run chainlit_app.py
    pass
