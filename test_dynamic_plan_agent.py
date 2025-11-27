"""
测试 Dynamic Plan Agent
验证 system prompt 和 dynamic context 机制
"""

from dynamic_plan_agent import MinimalKimiAgent
import os
from dotenv import load_dotenv

def test_dynamic_context():
    """测试动态上下文构建"""
    print("\n" + "="*60)
    print("测试1: 验证动态上下文构建")
    print("="*60)

    load_dotenv()
    agent = MinimalKimiAgent()

    # 检查初始化
    assert agent.todos == {"tasks": []}, "Todo初始化失败"
    assert agent._current_turn == 0, "回合计数初始化失败"
    print("✓ 初始化成功")

    # 检查动态消息构建
    agent.messages.append({"role": "user", "content": "测试消息"})
    dynamic_messages = agent._build_dynamic_messages()

    # 验证消息结构
    assert len(dynamic_messages) >= 2, "动态消息构建失败"
    assert dynamic_messages[0]["role"] == "system", "第一条消息应该是system"
    assert "工作原则" in dynamic_messages[0]["content"], "缺少系统工作流提示"
    print(f"✓ 动态消息构建成功, 共 {len(dynamic_messages)} 条消息")

    # 检查系统提醒
    system_reminder = agent._generate_system_reminder_start()
    assert "当前环境" in system_reminder, "缺少环境信息"
    assert "工作空间" in system_reminder, "缺少工作空间信息"
    print("✓ 系统提醒生成成功")


def test_todo_functionality():
    """测试Todo功能"""
    print("\n" + "="*60)
    print("测试2: 验证Todo管理功能")
    print("="*60)

    load_dotenv()
    agent = MinimalKimiAgent()

    # 测试添加任务
    result = agent._tool_todo_update({"action": "add", "description": "测试任务1"})
    assert "已添加任务" in result, "添加任务失败"
    assert len(agent.todos["tasks"]) == 1, "任务未添加到列表"
    print(f"✓ {result}")

    # 测试更新状态
    result = agent._tool_todo_update({"action": "update_status", "task_id": "task_1", "status": "in_progress"})
    assert "状态更新为" in result, "更新状态失败"
    assert agent.todos["tasks"][0]["status"] == "in_progress", "状态未更新"
    print(f"✓ {result}")

    # 测试完成任务
    result = agent._tool_todo_update({"action": "complete", "task_id": "task_1"})
    assert "已完成" in result, "完成任务失败"
    assert agent.todos["tasks"][0]["status"] == "completed", "任务状态未更新为completed"
    print(f"✓ {result}")

    # 测试Todo显示
    todo_reminder = agent._generate_system_reminder_end()
    assert "[✓] task_1" in todo_reminder, "Todo显示格式错误"
    print("✓ Todo提醒生成成功")


def test_tool_registration():
    """测试工具注册"""
    print("\n" + "="*60)
    print("测试3: 验证工具注册")
    print("="*60)

    load_dotenv()
    agent = MinimalKimiAgent()

    tools = agent._get_tools()
    tool_names = [tool["function"]["name"] for tool in tools]

    assert "ReadFile" in tool_names, "ReadFile工具缺失"
    assert "WriteFile" in tool_names, "WriteFile工具缺失"
    assert "RunCommand" in tool_names, "RunCommand工具缺失"
    assert "TodoUpdate" in tool_names, "TodoUpdate工具缺失"

    print(f"✓ 所有工具已注册: {', '.join(tool_names)}")

    # 检查TodoUpdate工具定义
    todo_tool = next(t for t in tools if t["function"]["name"] == "TodoUpdate")
    actions = todo_tool["function"]["parameters"]["properties"]["action"]["enum"]
    assert "add" in actions, "缺少add操作"
    assert "update_status" in actions, "缺少update_status操作"
    assert "complete" in actions, "缺少complete操作"
    print("✓ TodoUpdate工具定义完整")


if __name__ == "__main__":
    # 检查 API Key
    load_dotenv()
    if not os.getenv("MOONSHOT_API_KEY"):
        print("❌ 请在 .env 文件中设置 MOONSHOT_API_KEY")
        print("⚠️  跳过API调用测试，仅运行本地测试")

    # 运行测试
    try:
        test_dynamic_context()
        test_todo_functionality()
        test_tool_registration()

        print("\n" + "="*60)
        print("✓ 所有测试通过!")
        print("="*60)
        print("\n优化总结:")
        print("1. ✓ 动态上下文构建机制已实现")
        print("2. ✓ 系统工作流提示已添加")
        print("3. ✓ Todo任务管理功能已集成")
        print("4. ✓ 回合追踪功能已启用")
        print("5. ✓ 日志增强(包含Todo状态)")
        print("\n下一步: 运行 example_with_todo() 测试完整工作流")

    except AssertionError as e:
        print(f"\n❌ 测试失败: {e}")
    except Exception as e:
        print(f"\n❌ 错误: {e}")
