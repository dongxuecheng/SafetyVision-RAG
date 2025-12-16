# RAG知识问答系统
技术栈：Langchain、fastAPI、qdrant、Chainlit、docker
使用模型：qwen3-vl-4b、bge-reranker、bge-embedding
功能：提供知识问答UI对话界面(chainlit)和文档管理接口（复用）即可，根据用户问题，从知识库文档搜索相关内容并生成答案
部署：rag知识问答系统使用Docker进行部署，模型接口复用已有的docker的vllm，qdrant也复用docker中已有的qdrant
要求：代码简洁、优雅、易懂、易维护、项目架构清晰、最新、最佳实践
其中，RAG知识问答系统与SafetyVison-RAG系统相当于都是一个三层架构，底层架构复用共同的模型（相同接口），向量库（相同接口但二者是不同的collection），中层架构复用文档管理接口，不同的是各自的顶层逻辑