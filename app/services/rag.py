"""
RAG 核心服务：文档加载 → 切分 → Embedding → 存储 → 检索
"""

import os
from typing import List

from langchain_community.document_loaders import TextLoader
from langchain_community.embeddings import DashScopeEmbeddings
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.vectorstores import Chroma

from app.core.config import settings

UPLOAD_DIR = "./uploads"
CHROMA_DIR = "./chroma_db"
os.makedirs(UPLOAD_DIR, exist_ok=True)

# Embedding 客户端 (复用 LLM 配置)
embeddings = DashScopeEmbeddings(
    dashscope_api_key=settings.QW_API_KEY,
    model="text-embedding-v3",
)

# 全局向量库实例
_vectorstore = None

def get_vectorstore():
    """获取或创建向量库"""
    global _vectorstore
    if _vectorstore is None:
        _vectorstore = Chroma(
            persist_directory=CHROMA_DIR,
            embedding_function=embeddings,
        )
    return _vectorstore

def process_document(file_path: str) -> int:
    """
    处理文档: 加载 -> 切分 -> 存入向量库
    返回切分后的 chunk 数量
    """
    loader = TextLoader(file_path, encoding="utf-8")
    documents = loader.load()

    splitter = RecursiveCharacterTextSplitter(
        chunk_size=500,
        chunk_overlap=50,
        separators=["\n\n", "\n", ".", ",", " ", ""],
    )
    chunks = splitter.split_documents(documents)

    vectorstore = get_vectorstore()
    vectorstore.add_documents(chunks)
    vectorstore.persist()

    return len(chunks)

def search_knowledge(query: str, k: int = 3) -> List[str]:
    """检索知识库, 返回 top-k 文本片段"""
    vectorstore = get_vectorstore()
    results = vectorstore.similarity_search(query, k=k)
    return [doc.page_content for doc in results]

