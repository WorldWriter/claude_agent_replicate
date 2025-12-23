"""
SubAgent 示例：批量分析多个文件
每个文件用独立的 SubAgent 处理
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dynamic_plan_agent import DynamicPlanAgent
from dotenv import load_dotenv

def main():
    load_dotenv()

    if not os.getenv("MOONSHOT_API_KEY"):
        print("❌ 请在 .env 文件中设置 MOONSHOT_API_KEY")
        return

    agent = DynamicPlanAgent(max_depth=2)

    result = agent.run("""
    分析 agent_workspace 目录下的所有 .py 文件:

    对每个文件使用 SubAgent 独立分析:
    1. 统计代码行数
    2. 计算函数数量
    3. 识别类定义

    在主 Agent 中汇总:
    - 总代码行数
    - 总函数数量
    - 总类数量
    - 最大/最小文件信息
    """, max_turns=30)

    print("\n" + "="*60)
    print("最终结果:")
    print("="*60)
    print(result)

if __name__ == "__main__":
    main()
