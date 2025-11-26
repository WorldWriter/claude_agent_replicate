"""
测试战略-战术分层架构
"""

import os
from dotenv import load_dotenv
from plan_kimi_agent import PlanKimiAgent


def test_strategic_mode():
    """测试战略模式"""
    print("\n" + "="*60)
    print("测试 1: 战略模式 - ExploreWorkspace")
    print("="*60)

    # 使用假 API KEY 进行离线测试
    agent = PlanKimiAgent(api_key="test_key_123", mode="strategic")

    # 模拟工具调用：ExploreWorkspace
    result = agent._tool_explore_workspace()
    print(f"\nExploreWorkspace 结果:\n{result}")

    assert "工作空间探索完成" in result
    print("✓ ExploreWorkspace 测试通过")


def test_tactical_mode():
    """测试战术模式"""
    print("\n" + "="*60)
    print("测试 2: 战术模式 - 工具过滤")
    print("="*60)

    agent = PlanKimiAgent(api_key="test_key_123", mode="tactical")

    # 检查战术模式只有基础工具
    tools = agent._get_tools()
    tool_names = {tool["function"]["name"] for tool in tools}

    print(f"\n战术模式可用工具: {tool_names}")

    assert tool_names == {"ReadFile", "WriteFile", "RunCommand"}
    print("✓ 战术模式工具过滤测试通过")


def test_context_building():
    """测试动态上下文构建"""
    print("\n" + "="*60)
    print("测试 3: 动态上下文构建")
    print("="*60)

    agent = PlanKimiAgent(api_key="test_key_123", mode="strategic")
    agent.messages.append({"role": "user", "content": "测试消息"})

    # 构建动态上下文
    context = agent._build_dynamic_context()

    print(f"\n上下文消息数量: {len(context)}")
    print(f"包含工作空间快照: {'workspace_context' in str(context)}")

    assert len(context) > 0
    print("✓ 动态上下文构建测试通过")


def test_system_prompts():
    """测试 System Prompts"""
    print("\n" + "="*60)
    print("测试 4: System Prompts")
    print("="*60)

    strategic = PlanKimiAgent(api_key="test_key_123", mode="strategic")
    tactical = PlanKimiAgent(api_key="test_key_123", mode="tactical")

    strategic_prompt = strategic._get_system_prompt()
    tactical_prompt = tactical._get_system_prompt()

    print(f"\n战略层提示词长度: {len(strategic_prompt)} 字符")
    print(f"战术层提示词长度: {len(tactical_prompt)} 字符")

    assert "Strategic Agent" in strategic_prompt
    assert "Tactical Agent" in tactical_prompt
    assert "DelegateToTactical" in strategic_prompt
    assert "DelegateToTactical" not in tactical_prompt

    print("✓ System Prompts 测试通过")


def test_workspace_scan():
    """测试工作空间扫描"""
    print("\n" + "="*60)
    print("测试 5: 工作空间扫描")
    print("="*60)

    agent = PlanKimiAgent(api_key="test_key_123")
    result = agent._scan_workspace()

    print(f"\n扫描结果:")
    print(f"- 数据文件: {len(result['data_files'])} 个")
    print(f"- 脚本文件: {len(result['scripts'])} 个")
    print(f"- 输出文件: {len(result['outputs'])} 个")
    print(f"- 总文件数: {result['total_files']} 个")

    assert "data_files" in result
    assert "scripts" in result
    print("✓ 工作空间扫描测试通过")


def main():
    """运行所有测试"""
    load_dotenv()

    if not os.getenv("MOONSHOT_API_KEY"):
        print("⚠️ 警告：未设置 MOONSHOT_API_KEY，仅运行离线测试")

    print("\n" + "="*60)
    print("开始测试战略-战术分层架构")
    print("="*60)

    try:
        test_strategic_mode()
        test_tactical_mode()
        test_context_building()
        test_system_prompts()
        test_workspace_scan()

        print("\n" + "="*60)
        print("✓ 所有测试通过！")
        print("="*60)
        print("\n架构改造成功：")
        print("- 响应式单层架构 ✓")
        print("- 战略-战术分离 ✓")
        print("- 动态上下文管理 ✓")
        print("- System Prompt 驱动 ✓")
        print("- 工具过滤机制 ✓")

    except AssertionError as e:
        print(f"\n❌ 测试失败: {e}")
        raise
    except Exception as e:
        print(f"\n❌ 错误: {e}")
        raise


if __name__ == "__main__":
    main()
