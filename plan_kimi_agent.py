"""
Plan Kimi Agent - Stage 2 实现
- 动态计划调整能力
- 计划文件持久化 (plan.md)
- 基于执行结果重新规划
"""

import os
import json
import subprocess
from datetime import datetime
from typing import List, Dict, Any
from openai import OpenAI
from dotenv import load_dotenv


class PlanKimiAgent:
    """Plan Agent - 具有动态计划调整能力"""

    def __init__(self, api_key: str = None):
        """初始化 Agent"""
        load_dotenv()

        # 初始化 Kimi API 客户端
        self.client = OpenAI(
            api_key=api_key or os.getenv("MOONSHOT_API_KEY"),
            base_url="https://api.moonshot.ai/v1"
        )

        # 消息历史
        self.messages: List[Dict] = []

        # 模型配置
        self.model = os.getenv("LLM_MODEL", "kimi-k2-turbo-preview")

        # 工作目录
        self.workspace = "agent_workspace"
        os.makedirs(self.workspace, exist_ok=True)

        # 计划文件路径
        self.plan_file = os.path.join(self.workspace, "plan.md")

    def _get_system_prompt(self) -> str:
        """获取系统提示词 - 指导 Agent 如何使用计划能力"""
        return """你是一个具有计划能力的智能助手。你的工作方式是：

## 工作流程
1. **理解任务**: 分析用户需求，理解最终目标
2. **创建计划**: 使用 CreatePlan 工具创建初始计划
3. **执行步骤**: 逐步执行计划中的任务
4. **动态调整**: 根据执行结果调整计划（添加、修改、跳过步骤）
5. **完成总结**: 所有步骤完成后给出总结

## 计划调整原则
- 如果某步骤执行结果与预期不符，及时调整后续计划
- 如果发现需要额外步骤，使用 UpdatePlan 添加
- 如果某步骤不再需要，标记为跳过并说明原因
- 每次调整都要在执行日志中记录原因

## 工具使用
- CreatePlan: 任务开始时创建计划
- UpdatePlan: 更新步骤状态或调整计划
- ReadPlan: 查看当前计划状态
- ReadFile/WriteFile/RunCommand: 执行具体任务

## 注意事项
- 计划要具体、可执行，每个步骤都应该明确
- 步骤之间要有逻辑顺序
- 遇到错误时要分析原因并调整计划
- 保持计划文件的更新，让用户能看到进度"""

    def run(self, user_input: str, max_turns: int = 30) -> str:
        """
        主运行循环

        Args:
            user_input: 用户输入
            max_turns: 最大轮次

        Returns:
            最终输出
        """
        print(f"\n{'='*60}")
        print(f"用户: {user_input}")
        print(f"{'='*60}\n")

        # 添加系统提示
        self.messages.append({
            "role": "system",
            "content": self._get_system_prompt()
        })

        # 添加用户消息
        self.messages.append({
            "role": "user",
            "content": user_input
        })

        # 主循环
        for turn in range(max_turns):
            print(f"\n--- 回合 {turn + 1} ---")

            # 调用 Kimi API
            response = self._call_kimi()

            if not response:
                break

            # 处理响应
            should_stop = self._process_response(response)

            if should_stop:
                print("\n✓ 任务完成!")
                break

        # 保存对话日志
        self._save_conversation_log()

        return self._get_final_output()

    def _call_kimi(self) -> Any:
        """调用 Kimi API"""
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=self.messages,
                tools=self._get_tools(),
                temperature=0.3
            )
            return response
        except Exception as e:
            print(f"❌ API 调用失败: {e}")
            return None

    def _process_response(self, response) -> bool:
        """
        处理 API 响应

        Returns:
            True 表示任务完成，False 表示继续
        """
        message = response.choices[0].message

        # 保存 assistant 消息
        self.messages.append({
            "role": "assistant",
            "content": message.content,
            "tool_calls": message.tool_calls
        })

        # 如果没有工具调用，说明任务完成
        if not message.tool_calls:
            if message.content:
                print(f"\n助手: {message.content}")
            return True

        # 执行工具调用
        for tool_call in message.tool_calls:
            tool_name = tool_call.function.name
            tool_args = json.loads(tool_call.function.arguments)

            print(f"\n🔧 调用工具: {tool_name}")
            print(f"   参数: {json.dumps(tool_args, ensure_ascii=False, indent=2)}")

            # 执行工具
            result = self._execute_tool(tool_name, tool_args)

            # 显示结果
            result_str = str(result)
            if len(result_str) > 300:
                print(f"   结果: {result_str[:300]}...")
            else:
                print(f"   结果: {result_str}")

            # 添加工具结果到消息历史
            self.messages.append({
                "role": "tool",
                "tool_call_id": tool_call.id,
                "content": result_str
            })

        return False

    def _get_tools(self) -> List[Dict]:
        """定义可用工具"""
        return [
            # ===== 计划工具 =====
            {
                "type": "function",
                "function": {
                    "name": "CreatePlan",
                    "description": "创建任务计划。在开始执行任务前调用此工具创建计划。",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "goal": {
                                "type": "string",
                                "description": "任务的最终目标"
                            },
                            "steps": {
                                "type": "array",
                                "items": {
                                    "type": "string"
                                },
                                "description": "计划步骤列表，每个步骤是一个字符串描述"
                            }
                        },
                        "required": ["goal", "steps"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "UpdatePlan",
                    "description": "更新计划状态或调整计划。可以标记步骤完成、添加新步骤、或记录执行日志。",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "action": {
                                "type": "string",
                                "enum": ["complete", "skip", "add", "log"],
                                "description": "操作类型: complete=完成步骤, skip=跳过步骤, add=添加步骤, log=记录日志"
                            },
                            "step_index": {
                                "type": "integer",
                                "description": "步骤索引（从1开始），用于 complete 和 skip 操作"
                            },
                            "content": {
                                "type": "string",
                                "description": "内容：新步骤描述（add）或日志内容（log）或跳过原因（skip）"
                            },
                            "insert_after": {
                                "type": "integer",
                                "description": "插入位置（用于 add 操作），在哪个步骤后插入，0表示插入到开头"
                            }
                        },
                        "required": ["action"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "ReadPlan",
                    "description": "读取当前计划状态，查看所有步骤和执行日志",
                    "parameters": {
                        "type": "object",
                        "properties": {},
                        "required": []
                    }
                }
            },
            # ===== 文件工具 =====
            {
                "type": "function",
                "function": {
                    "name": "ReadFile",
                    "description": "读取文件内容。注意：最多返回前10000个字符，如果文件过大会被截断。对于大文件建议使用Python脚本分批处理",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "path": {
                                "type": "string",
                                "description": "文件路径"
                            }
                        },
                        "required": ["path"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "WriteFile",
                    "description": "写入文件内容",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "path": {
                                "type": "string",
                                "description": "文件路径"
                            },
                            "content": {
                                "type": "string",
                                "description": "文件内容"
                            }
                        },
                        "required": ["path", "content"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "RunCommand",
                    "description": "执行终端命令。注意：禁止使用危险命令如 rm -rf, sudo, shutdown 等",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "command": {
                                "type": "string",
                                "description": "要执行的命令，例如 'ls -la' 或 'python script.py'"
                            }
                        },
                        "required": ["command"]
                    }
                }
            }
        ]

    def _execute_tool(self, tool_name: str, tool_args: Dict) -> str:
        """执行工具"""
        try:
            # 计划工具
            if tool_name == "CreatePlan":
                return self._tool_create_plan(tool_args["goal"], tool_args["steps"])
            elif tool_name == "UpdatePlan":
                return self._tool_update_plan(tool_args)
            elif tool_name == "ReadPlan":
                return self._tool_read_plan()
            # 文件工具
            elif tool_name == "ReadFile":
                return self._tool_read_file(tool_args["path"])
            elif tool_name == "WriteFile":
                return self._tool_write_file(tool_args["path"], tool_args["content"])
            elif tool_name == "RunCommand":
                return self._tool_run_command(tool_args["command"])
            else:
                return f"错误: 未知工具 {tool_name}"
        except Exception as e:
            return f"错误: {str(e)}"

    # ===== 计划工具实现 =====

    def _tool_create_plan(self, goal: str, steps: List[str]) -> str:
        """创建计划文件"""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        content = f"""# 任务计划

## 目标
{goal}

## 步骤
"""
        for i, step in enumerate(steps, 1):
            content += f"- [ ] {i}. {step}\n"

        content += f"""
## 执行日志
- [{timestamp}] 计划创建完成，共 {len(steps)} 个步骤
"""

        # 写入计划文件
        try:
            with open(self.plan_file, 'w', encoding='utf-8') as f:
                f.write(content)
            return f"✓ 计划已创建: {self.plan_file}\n目标: {goal}\n步骤数: {len(steps)}"
        except Exception as e:
            return f"❌ 创建计划失败: {e}"

    def _tool_update_plan(self, args: Dict) -> str:
        """更新计划"""
        action = args.get("action")
        step_index = args.get("step_index")
        content = args.get("content", "")
        insert_after = args.get("insert_after", 0)

        try:
            # 读取当前计划
            with open(self.plan_file, 'r', encoding='utf-8') as f:
                plan_content = f.read()

            timestamp = datetime.now().strftime("%H:%M:%S")
            lines = plan_content.split('\n')

            if action == "complete":
                # 标记步骤完成
                step_pattern = f"- [ ] {step_index}."
                for i, line in enumerate(lines):
                    if step_pattern in line:
                        lines[i] = line.replace("- [ ]", "- [x]")
                        break
                log_entry = f"- [{timestamp}] ✓ 完成步骤 {step_index}"

            elif action == "skip":
                # 跳过步骤
                step_pattern = f"- [ ] {step_index}."
                for i, line in enumerate(lines):
                    if step_pattern in line:
                        lines[i] = line.replace("- [ ]", "- [~]") + f" (跳过: {content})"
                        break
                log_entry = f"- [{timestamp}] ~ 跳过步骤 {step_index}: {content}"

            elif action == "add":
                # 添加新步骤
                # 找到步骤列表的位置
                step_section_start = -1
                step_section_end = -1
                step_count = 0

                for i, line in enumerate(lines):
                    if line.startswith("- ["):
                        if step_section_start == -1:
                            step_section_start = i
                        step_section_end = i
                        step_count += 1

                # 新步骤编号
                new_step_num = step_count + 1
                new_step_line = f"- [ ] {new_step_num}. {content}"

                if insert_after == 0:
                    # 插入到开头
                    lines.insert(step_section_start, new_step_line)
                else:
                    # 插入到指定位置后
                    insert_pos = step_section_start + insert_after
                    if insert_pos <= step_section_end + 1:
                        lines.insert(insert_pos, new_step_line)
                    else:
                        lines.insert(step_section_end + 1, new_step_line)

                log_entry = f"- [{timestamp}] + 添加步骤 {new_step_num}: {content}"

            elif action == "log":
                # 添加日志
                log_entry = f"- [{timestamp}] {content}"
            else:
                return f"❌ 未知操作: {action}"

            # 添加日志条目
            # 找到执行日志部分并添加
            log_section_found = False
            for i, line in enumerate(lines):
                if "## 执行日志" in line:
                    log_section_found = True
                    # 在日志部分末尾添加
                    # 找到下一个 ## 或文件末尾
                    insert_pos = len(lines)
                    for j in range(i + 1, len(lines)):
                        if lines[j].startswith("## "):
                            insert_pos = j
                            break
                    lines.insert(insert_pos, log_entry)
                    break

            if not log_section_found:
                lines.append("\n## 执行日志")
                lines.append(log_entry)

            # 写回文件
            with open(self.plan_file, 'w', encoding='utf-8') as f:
                f.write('\n'.join(lines))

            return f"✓ 计划已更新: {action}"

        except FileNotFoundError:
            return "❌ 计划文件不存在，请先使用 CreatePlan 创建计划"
        except Exception as e:
            return f"❌ 更新计划失败: {e}"

    def _tool_read_plan(self) -> str:
        """读取计划"""
        try:
            with open(self.plan_file, 'r', encoding='utf-8') as f:
                content = f.read()
            return f"当前计划:\n\n{content}"
        except FileNotFoundError:
            return "计划文件不存在，请先使用 CreatePlan 创建计划"
        except Exception as e:
            return f"读取计划失败: {e}"

    # ===== 文件工具实现 =====

    def _resolve_path(self, path: str) -> str:
        """解析路径：绝对路径保持不变，相对路径拼接到 workspace"""
        return path if os.path.isabs(path) else os.path.join(self.workspace, path)

    def _tool_read_file(self, path: str) -> str:
        """读取文件"""
        path = self._resolve_path(path)
        max_chars = 10000

        try:
            with open(path, 'r', encoding='utf-8') as f:
                content = f.read()

            original_len = len(content)
            if original_len > max_chars:
                content = content[:max_chars]
                return f"⚠️ 文件过大，已截断到前 {max_chars} 个字符（总共 {original_len} 字符）\n建议使用 Python 脚本分批处理大文件\n\n{content}"

            return f"成功读取文件 {path} ({original_len} 字符)\n\n{content}"
        except Exception as e:
            return f"读取失败: {e}"

    def _tool_write_file(self, path: str, content: str) -> str:
        """写入文件"""
        path = self._resolve_path(path)
        try:
            os.makedirs(os.path.dirname(path) or '.', exist_ok=True)
            with open(path, 'w', encoding='utf-8') as f:
                f.write(content)
            return f"成功写入 {path} ({len(content)} 字符)"
        except Exception as e:
            return f"写入失败: {e}"

    def _tool_run_command(self, command: str) -> str:
        """执行终端命令"""
        BLACKLIST = [
            'rm -rf', 'rm -fr', 'sudo', 'shutdown', 'reboot',
            'mkfs', 'dd', 'format', ':(){:|:&};:', '> /dev/sda', 'mv /* /dev/null'
        ]

        for dangerous_cmd in BLACKLIST:
            if dangerous_cmd in command.lower():
                return f"❌ 拒绝执行: 命令包含危险操作 '{dangerous_cmd}'"

        try:
            result = subprocess.run(
                command,
                shell=True,
                capture_output=True,
                text=True,
                timeout=60,
                cwd=self.workspace
            )

            output_lines = []
            if result.stdout:
                output_lines.append("标准输出:")
                output_lines.append(result.stdout.strip())
            if result.stderr:
                output_lines.append("错误输出:")
                output_lines.append(result.stderr.strip())

            output = "\n".join(output_lines) if output_lines else "(无输出)"

            if result.returncode == 0:
                return f"✓ 命令执行成功 (退出码: {result.returncode})\n\n{output}"
            else:
                return f"⚠️ 命令执行失败 (退出码: {result.returncode})\n\n{output}"

        except subprocess.TimeoutExpired:
            return "❌ 命令执行超时 (超过60秒)"
        except Exception as e:
            return f"❌ 命令执行失败: {str(e)}"

    def _get_final_output(self) -> str:
        """获取最终输出"""
        for msg in reversed(self.messages):
            if msg["role"] == "assistant" and msg.get("content"):
                return msg["content"]
        return "无输出"

    def _save_conversation_log(self):
        """保存对话日志"""
        try:
            os.makedirs("logs", exist_ok=True)
            timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
            log_file = f"logs/plan_{timestamp}.txt"

            log_content = []
            log_content.append("=" * 60)
            log_content.append(f"Plan Agent 对话日志 - {timestamp}")
            log_content.append("=" * 60)
            log_content.append("")

            for i, msg in enumerate(self.messages, 1):
                role = msg["role"]
                content = msg.get("content", "")

                if role == "system":
                    log_content.append(f"[{i}] 系统提示: (已省略)")
                elif role == "user":
                    log_content.append(f"[{i}] 用户:")
                    log_content.append(f"{content}")
                elif role == "assistant":
                    log_content.append(f"[{i}] 助手:")
                    if content:
                        log_content.append(f"{content}")
                    if msg.get("tool_calls"):
                        log_content.append("  工具调用:")
                        for tc in msg["tool_calls"]:
                            log_content.append(f"    - {tc.function.name}")
                            log_content.append(f"      参数: {tc.function.arguments}")
                elif role == "tool":
                    log_content.append(f"[{i}] 工具结果:")
                    if len(content) > 500:
                        log_content.append(f"{content[:500]}... (已截断)")
                    else:
                        log_content.append(f"{content}")

                log_content.append("=" * 30)

            # 写入文件
            with open(log_file, 'w', encoding='utf-8') as f:
                f.write("\n".join(log_content))

            json_file = log_file.replace('.txt', '.json')
            with open(json_file, 'w', encoding='utf-8') as f:
                json.dump(self.messages, f, ensure_ascii=False, indent=2, default=str)

            print(f"\n📝 对话日志已保存: {log_file}")
        except Exception as e:
            print(f"\n⚠️ 日志保存失败: {e}")


# ============================================
# 使用示例
# ============================================

def example_data_analysis():
    """示例: 数据分析任务（需要计划和动态调整）"""
    print("\n" + "="*60)
    print("Plan Agent 示例: GCP 数据分析")
    print("="*60)

    agent = PlanKimiAgent()
    result = agent.run("""
    分析 GCP 云资源使用数据，完成以下任务：

    1. 了解数据结构和规模
    2. 找出使用量最大的前5个资源
    3. 分析这些资源的使用趋势
    4. 生成分析报告

    数据文件: data/full_gcp_data.csv
    """)
    print(f"\n最终结果: {result}")


def example_simple():
    """示例: 简单任务"""
    print("\n" + "="*60)
    print("Plan Agent 示例: 简单文件操作")
    print("="*60)

    agent = PlanKimiAgent()
    result = agent.run("创建一个 Python 脚本，读取 data/full_gcp_data.csv 的前10行并打印")
    print(f"\n最终结果: {result}")


if __name__ == "__main__":
    load_dotenv()
    if not os.getenv("MOONSHOT_API_KEY"):
        print("❌ 请在 .env 文件中设置 MOONSHOT_API_KEY")
        exit(1)

    # 运行示例
    example_data_analysis()
    # example_simple()
