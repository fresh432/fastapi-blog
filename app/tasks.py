import time
from app.core.celery_app import celery_app
from app.core.cache import delete_cache, delete_cache_pattern

@celery_app.task
def send_welcome_email(username: str):
    """异步发送欢迎邮件"""
    time.sleep(3)   # 模拟发送耗时
    return f"欢迎邮件已发送至用户 {username}"

@celery_app.task
def count_article_views(article_id: int):
    """异步统计文章阅读量"""
    # 实际场景: 从Redis读取计数, 批量写入数据库
    time.sleep(1)
    return f"文章 {article_id} 阅读量统计完成"

@ celery_app.task
def delete_cache_delayed(cache_key: str, pattern: str = None, delay: int = 2):
    """
    延迟双删: 更新DB后先立即删除缓存, 异步延迟后再删一次
    覆盖DB主从同步延迟和并发读窗口
    """
    time.sleep(delay)
    delete_cache(cache_key)
    if pattern:
        delete_cache_pattern(pattern)
    return f"延迟双删完成: {cache_key}"