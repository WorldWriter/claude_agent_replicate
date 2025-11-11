"""Agent入口文件 - 数据挖掘任务"""
import os
from dotenv import load_dotenv
from llm_client import LLMClient
from agent import SimpleAgent

# 加载环境变量
load_dotenv()

# 定义任务
task = """
分析 data/full_gcp_data.csv 的GCP成本数据，执行以下任务：
对比分析下2022年1月和2月的成本总值的变化
"""

if __name__ == "__main__":
    # 初始化LLM客户端
    provider = os.getenv("LLM_PROVIDER", "anthropic")
    llm = LLMClient(provider=provider)

    # 创建Agent并运行
    agent = SimpleAgent(
        llm_client=llm,
        original_task=task,
        max_iterations=5
    )

    result = agent.run(task)
    print(f"\n任务结果: {result}")
