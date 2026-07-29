import time
from app.core.celery_app import celery_app

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