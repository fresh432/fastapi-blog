import time
import logging

from app.core.celery_app import celery_app
from app.core.cache import redis_client, delete_cache, delete_cache_pattern

logger = logging.getLogger(__name__)

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

@celery_app.task
def delete_cache_delayed(cache_key: str, pattern: str = None):
    """
    延迟双删的第二次删除: 由发布侧apply_async(countdown=N)调度, 到点投递worker立即执行
    覆盖DB主从同步延迟和并发读窗口
    """
    delete_cache(cache_key)
    if pattern:
        delete_cache_pattern(pattern)
    return f"延迟双删完成: {cache_key}"

def safe_delay(task, *args, countdown: int = None, **kwargs) -> bool:
    """
    Celery任务发布的统一安全出口
    - countdown: 延迟秒数, 指定时走apply_async由Celery调度器延迟投递(不占用worker空等)
    - Redis/broker不可用时快速失败(Celery已配置快速失败, 异常立即抛出由本函数接住)
    - 返回True表示发布成功, False表示发布失败已降级
    """
    try:
        redis_client.ping()
    except Exception as e:
        logger.warning(f"broker不可用, 任务降级跳过: {task.name}, 原因: {e}")
        return False
    try:
        if countdown is not None:
            task.apply_async(args=list(args), kwargs=kwargs, countdown=countdown)
        else:
            task.delay(*args, **kwargs)
        return True
    except Exception as e:
        logger.warning(f"Celery任务发布失败, 已降级跳过: {task.name}, 参数: {args}, 错误: {e}")
        return False