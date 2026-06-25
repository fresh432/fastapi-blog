"""
FastAPI 博客系统入口
学习要点：FastAPI 实例、路由装饰器、自动文档
"""

from fastapi import FastAPI

# 创建 FastAPI 实例
app = FastAPI(
    title = "个人博客系统",
    description = "学习 FastAPI 的后端项目",
    version = "0.1.0"
)

@app.get("/")
def read_root():
    """根路径: 返回欢迎信息"""
    return {
        "message" : "Hello World",
        "docs" : "访问 / docs 查看 API 文档"
    }

@app.get("/hello/{name}")
def say_hello(name: str):
    """路径参数: 返回个性化问候"""
    return {"message" : f"Hello, {name}!"}

@app.get("/items/{item_id}")
def read_item(item_id: int, q: str = None):
    """路径参数 + 查询参数"""
    return {"item_id": item_id, "q": q}
