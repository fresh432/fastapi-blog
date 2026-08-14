"""
RAG 核心服务：混合检索（向量 + 关键词 BM25）
"""

import os
from typing import List
from collections import defaultdict

from langchain_community.document_loaders import TextLoader
from langchain_community.embeddings import DashScopeEmbeddings
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.vectorstores import Chroma
from rank_bm25 import BM25Okapi

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
_bm25 = None
_all_chunks = []

def get_vectorstore():
    """获取或创建向量库"""
    global _vectorstore
    if _vectorstore is None:
        _vectorstore = Chroma(
            persist_directory=CHROMA_DIR,
            embedding_function=embeddings,
        )
    return _vectorstore

def _build_bm25():
    """构建BM25关键词索引"""
    global _bm25, _all_chunks
    vectorstore = get_vectorstore()

    # 从Chroma获取所有文档
    _all_chunks = vectorstore.get()
    if not _all_chunks or not _all_chunks.get("documents"):
        return

    documents = _all_chunks.get("documents", []) if _all_chunks else []
    tokenized_docs = [doc.split() for doc in documents]
    _bm25 = BM25Okapi(tokenized_docs)

def process_document(file_path: str) -> int:
    """
    处理文档: 加载 -> 切分 -> 存入向量库 + 重建BM25
    返回切分后的 chunk 数量
    """
    global _bm25

    if not os.path.exists(file_path):
        raise FileNotFoundError(f"文件不存在: {file_path}")

    loader = TextLoader(file_path, encoding="utf-8")
    documents = loader.load()

    if not documents or not documents[0].page_content.strip():
        return 0 # 空文档,不处理

    splitter = RecursiveCharacterTextSplitter(
        chunk_size=500,
        chunk_overlap=50,
        separators=["\n\n", "\n", ".", ",", " ", ""],
    )
    chunks = splitter.split_documents(documents)

    vectorstore = get_vectorstore()
    vectorstore.add_documents(chunks)
    vectorstore.persist()

    # 重建BM25索引
    _bm25 = None
    _build_bm25()

    return len(chunks)

def _reciprocal_rank_fusion(vector_results: List[str], keyword_results: List[str], k: int = 60) -> List[str]:
    """
    RRF融合:Reciprocal Rank Fusion
    score = Σ 1/(k + rank)
    """
    scores = defaultdict(float)

    for rank, doc in enumerate(vector_results):
        scores[doc] += 1.0 / (k + rank + 1)

    for rank, doc in enumerate(keyword_results):
        scores[doc] += 1.0 / (k + rank + 1)

    # 按分数排序
    sorted_docs = sorted(scores.items(), key=lambda x: x[1], reverse=True)
    return [doc for doc, _ in sorted_docs]

def hybrid_search(query: str, k: int = 3) -> List[str]:
    """混合检索: 向量相似度 + BM25关键词, RRF融合重排序"""
    # 向量检索
    vectorstore = get_vectorstore()

    # 检查向量库是否为空
    try:
        count = vectorstore._collection.count()
        if count == 0:
            return []
    except Exception:
        return []

    vector_docs = vectorstore.similarity_search(query, k=k*2)
    vector_results = [doc.page_content for doc in vector_docs]

    # 关键词检索 (BM25)
    keyword_results = []
    if _bm25 is None:
        _build_bm25()

    if _bm25:
        tokenized_query = query.split()
        bm25_scores = _bm25.get_scores(tokenized_query)

        # 获取top-k索引
        top_indices = sorted(range(len(bm25_scores)), key=lambda i: bm25_scores[i], reverse=True)[:k*2]

        documents = _all_chunks.get("document", []) if _all_chunks else []
        keyword_results = [documents[i] for i in top_indices if i < len(documents)]

    # RRF融合
    fused = _reciprocal_rank_fusion(vector_results, keyword_results)

    return fused[:k]
