"""
SubAgent 示例：测试递归深度限制
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

    # 设置 max_depth=2，测试深度限制
    agent = DynamicPlanAgent(max_depth=2)

    result = agent.run("""
    测试 SubAgent 递归深度限制:

    1. 主 Agent (深度 0) 创建 SubAgent A (深度 1)
    2. SubAgent A 创建 SubAgent B (深度 2)
    3. SubAgent B 尝试创建 SubAgent C (深度 3) - 应该失败

    观察深度限制的错误提示
    """, max_turns=15)

    print("\n" + "="*60)
    print("最终结果:")
    print("="*60)
    print(result)

if __name__ == "__main__":
    main()
