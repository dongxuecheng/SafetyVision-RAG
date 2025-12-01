"""
Safety analysis service using VLM and RAG
"""
import base64
from typing import Dict

from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import JsonOutputParser
from langchain_core.runnables import RunnablePassthrough, RunnableLambda
from langchain_core.messages import HumanMessage
from fastapi import UploadFile, HTTPException, status

from app.core.deps import get_llm, get_vector_store
from app.core.config import get_settings
from app.schemas.safety import SafetyReport


class AnalysisService:
    """Service for safety analysis"""
    
    def __init__(self):
        self.llm = get_llm()
        self.settings = get_settings()
    
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
    
    def _create_rag_chain(self):
        """Create RAG chain for report generation"""
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
1. rule_reference 字段必须按照以下格式填写：
   《标准名称》(标准编号) 第X.X.X条规定：具体规定内容。来自文档：文件名1, 文件名2
   
2. 示例格式：
   《建筑施工安全检查标准》(JGJ59-2011) 第3.1.11条规定：基坑边坡稳定，无积水。来自文档：安全规范.pdf
   
3. 如果检索到的文档中没有明确的标准编号，也要尽量提取标准名称和具体条款内容
4. 必须在末尾注明"来自文档："后跟上述"参考文档来源"中的文件名
5. 如果涉及多个文档，用逗号分隔文件名
"""
        parser = JsonOutputParser(pydantic_object=SafetyReport)
        retriever = get_vector_store().as_retriever(search_kwargs={"k": 3})
        
        def format_docs_with_sources(docs):
            """Format documents with source information"""
            context_parts = []
            sources_parts = []
            seen_files = set()
            
            for i, doc in enumerate(docs, 1):
                context_parts.append(f"[文档{i}] {doc.page_content[:800]}")
                filename = doc.metadata.get("filename", "未知来源")
                if filename not in seen_files:
                    seen_files.add(filename)
                    sources_parts.append(f"- {filename}")
            
            return {
                "context": "\n---\n".join(context_parts),
                "sources": "\n".join(sources_parts) if sources_parts else "无参考文档"
            }
        
        return (
            {
                "docs": retriever,
                "question": RunnablePassthrough(),
            }
            | RunnableLambda(lambda x: {
                **format_docs_with_sources(x["docs"]),
                "question": x["question"],
                "format_instructions": parser.get_format_instructions()
            })
            | ChatPromptTemplate.from_template(template)
            | self.llm
            | parser
        )
