"""
Agent 核心服务：LangGraph + 真实 LLM + 工具调用（增加迭代次数限制）
"""

import os
import ast
from typing import TypedDict, Annotated
import operator
import logging

from langchain_openai import ChatOpenAI
from langchain_core.tools import tool
from langgraph.graph import StateGraph, END
from langgraph.prebuilt import ToolNode

from app.core.config import settings
from app.services.rag import hybrid_search

logger = logging.getLogger(__name__)

# ========== 工具定义 ==========

@tool
def search_knowledge(query: str) -> str:
    """搜索知识库, 用于回答文档相关问题"""
    try:
        results = hybrid_search(query, k=2)
        if not results:
            return "知识库中未找到相关内容"
        return "\n\n".join([f"[文档片段] {r}" for r in results])
    except Exception as e:
        return f"搜索失败: {e}"

@tool
def calculate(expression: str) -> str:
    """数学计算器, 支持加减乘除 (基于AST安全解析) """
    try:
        # 解析为AST, 只允许数字和加减乘除运算
        tree = ast.parse(expression, mode='eval')
        result = _safe_eval(tree.body)
        return f"计算结果: {result}"
    except Exception as e:
        return f"计算失败: {e}"

def _safe_eval(node):
    """
    安全求值: 只允许数字常量和 + - * / 运算
    彻底杜绝 eval 代码注入风险 (包括 Unicode 绕过)
    """
    if isinstance(node, ast.Constant):
        if not isinstance(node.value, (int, float)):
            raise ValueError("只允许数字")
        return node.value
    elif isinstance(node, ast.BinOp):
        left = _safe_eval(node.left)
        right = _safe_eval(node.right)

        if isinstance(node.op, ast.Add):
            return left + right
        elif isinstance(node.op, ast.Sub):
            return left - right
        elif isinstance(node.op, ast.Mult):
            return left * right
        elif isinstance(node.op, ast.Div):
            if right == 0:
                raise ZeroDivisionError("除数不能为零")
            return left / right
        else:
            raise ValueError("不支持的运算符")
    elif isinstance(node, ast.UnaryOp):
        operand = _safe_eval(node.operand)
        if isinstance(node.op, ast.UAdd):
            return +operand
        elif isinstance(node.op, ast.USub):
            return -operand
        else:
            raise ValueError("不支持的一元运算符")

    else:
        raise ValueError(f"不支持的表达式类型: {type(node).__name__}")


@tool
def get_current_time() -> str:
    """获取当前时间"""
    from datetime import datetime
    return datetime.now().strftime("当前时间: %Y-%m-%d %H:%M:%S")

tools = [search_knowledge, calculate, get_current_time]
tool_node = ToolNode(tools)

# ========== 状态图构建 ==========

class AgentState(TypedDict):
    messages: Annotated[list, operator.add]
    iteration_count: int

llm = ChatOpenAI(
    base_url=settings.LLM_BASE_URL,
    api_key=settings.LLM_API_KEY,
    model=settings.LLM_MODEL,
    temperature=0.3,
)
llm_with_tools = llm.bind_tools(tools)

def agent_node(state: AgentState):
    """Agent 思考节点（增加迭代计数）"""
    response = llm_with_tools.invoke(state["messages"])
    return {
        "messages": [response],
        "iteration_count": state.get("iteration_count", 0) + 1
    }

def should_continue(state: AgentState):
    """判断是否继续调用工具（增加迭代计数）"""
    # 最大迭代次数限制, 防止无限循环
    if state.get("iteration_count", 0) >= 5:
        logger.warning(f"Agent达到最大迭代次数(5), 强制终止")
        return "end"

    last_message = state["messages"][-1]
    if hasattr(last_message, "tool_calls") and last_message.tool_calls:
        return "continue"
    return "end"

builder = StateGraph(AgentState)
builder.add_node("agent", agent_node)
builder.add_node("tools", tool_node)
builder.set_entry_point("agent")

builder.add_conditional_edges(
    "agent",
    should_continue,
    {
        "continue": "tools",
        "end": END,
    }
)
builder.add_edge("tools", "agent")

graph = builder.compile()


def run_agent(messages: list) -> str:
    """
    运行 Agent，返回最终回复（带异常捕获 + 迭代限制）
    """
    try:
        # 限制消息长度, 防止token爆炸
        if len(messages) > 50:
            messages = messages[-50:]
            logger.warning("消息历史超过50条, 已截断")

        result = graph.invoke({
            "messages": messages,
            "iteration_count": 0
        })
        last_msg = result["messages"][-1]
        return last_msg.content if hasattr(last_msg, "content") else str(last_msg)

    except Exception as e:
        logger.error(f"Agent执行失败: {e}")
        return "抱歉,服务暂时不可用,请稍后重试."




