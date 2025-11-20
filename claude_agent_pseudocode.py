"""
Claude Agent 最简框架 - 核心机制实现
基于逆向工程的真实架构简化版
"""

import anthropic
import json
import os
from typing import List, Dict, Any
from datetime import datetime

# ============================================
# 1. 核心Agent类
# ============================================

class SimpleClaudeAgent:
    """
    最简Claude Agent实现
    核心特点:
    1. 无预定义循环 - 响应式流程
    2. System Prompt驱动 - 而非硬编码步骤
    3. 动态上下文 - 每次调用动态构建
    4. Todo短期记忆 - 自我追踪进度
    """
    
    def __init__(self, api_key: str):
        self.client = anthropic.Anthropic(api_key=api_key)
        self.messages: List[Dict] = []
        self.todos: Dict[str, Any] = {"tasks": []}
        self.claude_md_memory = ""  # 长期记忆
        
    # ============================================
    # 主运行循环 - 响应式而非预定义
    # ============================================
    
    def run(self, user_input: str, max_turns: int = 10):
        """
        主运行循环:响应式处理,无预定义步骤
        
        关键:不是 while not done: plan -> execute
        而是:接收消息 -> Claude决定 -> 执行工具 -> 继续(如果需要)
        """
        print(f"\n{'='*60}")
        print(f"用户: {user_input}")
        print(f"{'='*60}\n")
        
        # 添加用户消息
        self.messages.append({
            "role": "user",
            "content": user_input
        })
        
        # 响应式循环:让Claude自己决定何时停止
        turn = 0
        while turn < max_turns:
            turn += 1
            print(f"\n--- 回合 {turn} ---")
            
            # 1. 构建动态上下文(关键!)
            context = self._build_dynamic_context()
            
            # 2. 调用Claude(System Prompt引导决策)
            response = self._call_claude(context)
            
            # 3. 处理响应
            stop = self._process_response(response)
            
            if stop:
                print("\n✓ 任务完成!")
                break
        
        return self._get_final_output()
    
    # ============================================
    # 动态上下文构建 - 每次都重新组装
    # ============================================
    
    def _build_dynamic_context(self) -> Dict:
        """
        关键机制:动态注入信息
        不同于传统框架把所有信息都塞进messages
        """
        # System Reminder Start - 动态环境信息
        system_reminder_start = self._generate_system_reminder_start()
        
        # System Reminder End - Todo短期记忆
        system_reminder_end = self._generate_system_reminder_end()
        
        # 组装完整上下文
        full_messages = []
        
        # 添加环境信息(作为system消息)
        if system_reminder_start:
            full_messages.append({
                "role": "user",
                "content": f"<system_context>\n{system_reminder_start}\n</system_context>"
            })
        
        # 添加历史消息
        full_messages.extend(self.messages)
        
        # 添加Todo记忆(最后)
        if system_reminder_end:
            full_messages.append({
                "role": "user", 
                "content": f"<todo_memory>\n{system_reminder_end}\n</todo_memory>"
            })
        
        return {
            "system": self._get_system_workflow_prompt(),
            "messages": full_messages
        }
    
    # ============================================
    # System Prompts - 这是"规划"的核心!
    # ============================================
    
    def _get_system_workflow_prompt(self) -> str:
        """
        System Workflow Prompt - 替代硬编码的规划逻辑
        这里定义"如何思考和行动",而非"执行什么步骤"
        """
        return """你是一个AI助手,可以使用工具来完成任务。

## 工作原则
1. **主动使用工具** - 不要只是说你要做什么,直接调用工具去做
2. **管理Todo列表** - 对于复杂任务,用TodoUpdate工具追踪进度
3. **分解子任务** - 遇到独立任务时,可以用SubAgent工具隔离处理
4. **验证工作** - 执行操作后,检查结果是否符合预期

## Todo管理规则
- 复杂任务(3+步骤)必须创建Todo列表
- 同时只有一个任务处于in_progress状态
- 完成任务后立即标记为completed
- 任务状态: pending | in_progress | completed

## 思考模式
在每次回复前:
1. 我当前的目标是什么?
2. 我需要什么信息?(如果需要,使用工具获取)
3. 下一步最合适的行动是什么?
4. 这个行动完成后,任务是否完成?

记住:你可以多次使用工具,直到完全完成任务。"""
    
    def _generate_system_reminder_start(self) -> str:
        """动态环境信息"""
        return f"""## 当前环境
- 时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
- 工作目录: {os.getcwd()}
- 可用工具: ReadFile, WriteFile, BashCommand, TodoUpdate, SubAgent"""
    
    def _generate_system_reminder_end(self) -> str:
        """Todo短期记忆"""
        if not self.todos["tasks"]:
            return ""
        
        return f"""## 当前待办事项
{json.dumps(self.todos, indent=2, ensure_ascii=False)}

请根据待办事项继续工作。记得更新任务状态!"""
    
    # ============================================
    # Claude API调用
    # ============================================
    
    def _call_claude(self, context: Dict) -> Any:
        """调用Claude API"""
        try:
            response = self.client.messages.create(
                model="claude-sonnet-4-20250514",
                max_tokens=4096,
                system=context["system"],
                messages=context["messages"],
                tools=self._get_tools()
            )
            return response
        except Exception as e:
            print(f"❌ API调用失败: {e}")
            return None
    
    # ============================================
    # 响应处理 - 工具调用的核心
    # ============================================
    
    def _process_response(self, response) -> bool:
        """
        处理Claude响应
        返回True表示任务完成,False表示需要继续
        """
        if not response:
            return True
        
        # 保存assistant消息
        assistant_message = {
            "role": "assistant",
            "content": response.content
        }
        self.messages.append(assistant_message)
        
        # 检查是否有工具调用
        has_tool_use = any(block.type == "tool_use" for block in response.content)
        
        if not has_tool_use:
            # 没有工具调用,说明Claude认为完成了
            for block in response.content:
                if hasattr(block, "text"):
                    print(f"\n助手: {block.text}")
            return True
        
        # 执行所有工具调用
        tool_results = []
        for block in response.content:
            if block.type == "tool_use":
                print(f"\n🔧 调用工具: {block.name}")
                print(f"   参数: {json.dumps(block.input, ensure_ascii=False, indent=2)}")
                
                result = self._execute_tool(block.name, block.input)
                
                print(f"   结果: {result[:200]}..." if len(str(result)) > 200 else f"   结果: {result}")
                
                tool_results.append({
                    "type": "tool_result",
                    "tool_use_id": block.id,
                    "content": str(result)
                })
        
        # 添加工具结果到消息历史
        self.messages.append({
            "role": "user",
            "content": tool_results
        })
        
        # 继续下一轮
        return False
    
    # ============================================
    # 工具定义
    # ============================================
    
    def _get_tools(self) -> List[Dict]:
        """定义可用工具"""
        return [
            {
                "name": "ReadFile",
                "description": "读取文件内容",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "path": {"type": "string", "description": "文件路径"}
                    },
                    "required": ["path"]
                }
            },
            {
                "name": "WriteFile",
                "description": "写入文件内容",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "path": {"type": "string", "description": "文件路径"},
                        "content": {"type": "string", "description": "文件内容"}
                    },
                    "required": ["path", "content"]
                }
            },
            {
                "name": "BashCommand",
                "description": "执行bash命令",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "command": {"type": "string", "description": "要执行的命令"}
                    },
                    "required": ["command"]
                }
            },
            {
                "name": "TodoUpdate",
                "description": "更新Todo列表(短期记忆)",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "action": {
                            "type": "string", 
                            "enum": ["add", "update_status", "complete"],
                            "description": "操作类型"
                        },
                        "task_id": {"type": "string", "description": "任务ID(更新时需要)"},
                        "task_description": {"type": "string", "description": "任务描述(添加时需要)"},
                        "status": {
                            "type": "string",
                            "enum": ["pending", "in_progress", "completed"],
                            "description": "任务状态"
                        }
                    },
                    "required": ["action"]
                }
            },
            {
                "name": "SubAgent",
                "description": "启动子Agent处理独立任务(上下文隔离)",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "task": {"type": "string", "description": "子任务描述"}
                    },
                    "required": ["task"]
                }
            }
        ]
    
    # ============================================
    # 工具执行实现
    # ============================================
    
    def _execute_tool(self, tool_name: str, tool_input: Dict) -> str:
        """执行工具调用"""
        try:
            if tool_name == "ReadFile":
                return self._tool_read_file(tool_input["path"])
            
            elif tool_name == "WriteFile":
                return self._tool_write_file(tool_input["path"], tool_input["content"])
            
            elif tool_name == "BashCommand":
                return self._tool_bash_command(tool_input["command"])
            
            elif tool_name == "TodoUpdate":
                return self._tool_todo_update(tool_input)
            
            elif tool_name == "SubAgent":
                return self._tool_sub_agent(tool_input["task"])
            
            else:
                return f"错误: 未知工具 {tool_name}"
        
        except Exception as e:
            return f"错误: {str(e)}"
    
    def _tool_read_file(self, path: str) -> str:
        """读取文件"""
        try:
            with open(path, 'r', encoding='utf-8') as f:
                return f.read()
        except Exception as e:
            return f"读取失败: {e}"
    
    def _tool_write_file(self, path: str, content: str) -> str:
        """写入文件"""
        try:
            os.makedirs(os.path.dirname(path) or '.', exist_ok=True)
            with open(path, 'w', encoding='utf-8') as f:
                f.write(content)
            return f"成功写入 {path}"
        except Exception as e:
            return f"写入失败: {e}"
    
    def _tool_bash_command(self, command: str) -> str:
        """执行bash命令(简化版,实际应该有安全检查)"""
        import subprocess
        try:
            result = subprocess.run(
                command, 
                shell=True, 
                capture_output=True, 
                text=True,
                timeout=10
            )
            return result.stdout + result.stderr
        except Exception as e:
            return f"执行失败: {e}"
    
    def _tool_todo_update(self, params: Dict) -> str:
        """Todo管理工具"""
        action = params["action"]
        
        if action == "add":
            task_id = f"task_{len(self.todos['tasks']) + 1}"
            self.todos["tasks"].append({
                "id": task_id,
                "description": params["task_description"],
                "status": params.get("status", "pending"),
                "created_at": datetime.now().isoformat()
            })
            return f"已添加任务 {task_id}"
        
        elif action == "update_status":
            for task in self.todos["tasks"]:
                if task["id"] == params["task_id"]:
                    task["status"] = params["status"]
                    return f"已更新 {params['task_id']} 状态为 {params['status']}"
            return "任务未找到"
        
        elif action == "complete":
            for task in self.todos["tasks"]:
                if task["id"] == params["task_id"]:
                    task["status"] = "completed"
                    return f"已完成任务 {params['task_id']}"
            return "任务未找到"
        
        return "未知操作"
    
    def _tool_sub_agent(self, task: str) -> str:
        """
        Sub Agent:上下文隔离
        创建新Agent实例,独立处理任务,只返回结果
        """
        print(f"\n  → 启动Sub Agent处理: {task}")
        
        sub_agent = SimpleClaudeAgent(api_key=self.client.api_key)
        result = sub_agent.run(task, max_turns=5)
        
        print(f"  ← Sub Agent完成")
        return result
    
    def _get_final_output(self) -> str:
        """获取最终输出"""
        for msg in reversed(self.messages):
            if msg["role"] == "assistant":
                for block in msg["content"]:
                    if hasattr(block, "text"):
                        return block.text
        return "无输出"


# ============================================
# 2. 使用示例
# ============================================

def example_simple_task():
    """示例1: 简单任务"""
    print("\n" + "="*60)
    print("示例1: 简单文件操作")
    print("="*60)
    
    agent = SimpleClaudeAgent(api_key=os.getenv("ANTHROPIC_API_KEY"))
    agent.run("创建一个test.txt文件,内容是'Hello Claude Agent!'")


def example_complex_task():
    """示例2: 复杂任务(会使用Todo)"""
    print("\n" + "="*60)
    print("示例2: 复杂任务(自动使用Todo追踪)")
    print("="*60)
    
    agent = SimpleClaudeAgent(api_key=os.getenv("ANTHROPIC_API_KEY"))
    agent.run("""
    创建一个Python项目结构:
    1. 创建 src/ 目录
    2. 在src/里创建main.py文件,包含一个hello函数
    3. 创建tests/目录
    4. 在tests/里创建test_main.py,测试hello函数
    5. 创建README.md说明项目结构
    """)


def example_with_sub_agent():
    """示例3: Sub Agent使用"""
    print("\n" + "="*60)
    print("示例3: Sub Agent上下文隔离")
    print("="*60)
    
    agent = SimpleClaudeAgent(api_key=os.getenv("ANTHROPIC_API_KEY"))
    agent.run("""
    分析当前目录下所有Python文件,统计:
    1. 总行数
    2. 函数数量
    3. 类数量
    
    对每个文件使用sub agent独立分析,最后汇总结果。
    """)


# ============================================
# 3. 对比:传统Agent vs Claude Agent
# ============================================

def show_architecture_comparison():
    """展示架构对比"""
    print("""
╔══════════════════════════════════════════════════════════════╗
║           传统Agent  vs  Claude Agent架构对比                  ║
╠══════════════════════════════════════════════════════════════╣
║ 传统Agent:                                                    ║
║   while not done:                                            ║
║       plan = agent.plan()        # ← 预先生成完整计划          ║
║       for step in plan:          # ← 遍历固定步骤              ║
║           execute(step)          # ← 执行预定步骤              ║
║       reflect()                  # ← 独立反思阶段              ║
║                                                               ║
║ Claude Agent:                                                ║
║   async for message in queue:   # ← 事件驱动                  ║
║       context = build_dynamic()  # ← 动态注入信息              ║
║       response = claude(         # ← System Prompt引导        ║
║           system=workflow_prompt # ← "规划"在这里!            ║
║       )                                                       ║
║       if tool_use:              # ← 响应式工具调用             ║
║           execute_and_continue() # ← 执行后继续               ║
║                                                               ║
╠══════════════════════════════════════════════════════════════╣
║ 关键差异:                                                      ║
║ 1. 无预定义循环 → 响应式流程                                   ║
║ 2. System Prompt驱动 → 替代硬编码规划                         ║
║ 3. 动态上下文注入 → 每次调用重新组装                           ║
║ 4. Todo短期记忆 → 自我追踪进度                                ║
║ 5. Sub Agent隔离 → 上下文空间优化                             ║
╚══════════════════════════════════════════════════════════════╝
    """)


# ============================================
# 运行示例
# ============================================

if __name__ == "__main__":
    # 显示架构对比
    show_architecture_comparison()
    
    # 确保设置了API key
    if not os.getenv("ANTHROPIC_API_KEY"):
        print("请设置 ANTHROPIC_API_KEY 环境变量")
        exit(1)
    
    # 运行示例
    example_simple_task()
    # example_complex_task()
    # example_with_sub_agent()