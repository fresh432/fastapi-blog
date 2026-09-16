"""
RAG 中文分词测试
验证 jieba 分词后 BM25 在中文场景真正生效
"""

from rank_bm25 import BM25Okapi

from app.services.rag import _tokenize


class TestChineseTokenize:
    """中文分词单元测试"""

    def test_tokenize_chinese(self):
        """中文应被切成多个词, 而不是一整个长词"""
        tokens = _tokenize("缓存穿透的解决方案")
        assert len(tokens) > 1
        assert "缓存" in tokens

    def test_tokenize_filters_blank(self):
        """"空白符 token 应被过滤"""
        tokens = _tokenize("Redis 缓存 穿透")
        assert all(t.strip() for t in tokens)

class TestBM25Chinese:
    """BM25 中文检索对比测试"""

    DOCS = [
        "Redis缓存穿透可以使用布隆过滤器解决",
        "今天天气真不错适合出去散步",
        "数据库索引优化是后端面试的高频考点",
    ]

    def test_bm25_hit_after_jieba(self):
        """分词后: 精确术语能命中目标文档"""
        bm25 = BM25Okapi([_tokenize(d) for d in self.DOCS])
        scores = bm25.get_scores(_tokenize("布隆过滤器"))
        assert scores[0] > scores[1]
        assert scores[0] > 0

    def test_bm25_miss_without_jieba(self):
        """对比: 不分词(原split方式)同一查询命中不了, 证明修复有效"""
        bm25_naive = BM25Okapi([d.split() for d in self.DOCS])
        naive_scores = bm25_naive.get_scores("布隆过滤器".split())
        assert naive_scores[0] == 0