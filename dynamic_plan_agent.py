"""
极简 Kimi Agent 实现
- 使用 Kimi API (通过 OpenAI 客户端)
- 核心功能：工具调用、多轮对话
- 只保留 ReadFile 和 WriteFile 两个基础工具
"""

import os
import json
import subprocess
from datetime import datetime
from typing import List, Dict, Any
from openai import OpenAI
from dotenv import load_dotenv


class DynamicPlanAgent:
    """极简 Kimi Agent - 只保留核心功能"""

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

        # 完整动态消息历史
        self.full_messages_history: List[Dict] = []

        # Todo短期记忆
        self.todos: Dict[str, Any] = {"tasks": []}

        # 回合计数
        self._current_turn = 0

        # 模型配置
        self.model = os.getenv("LLM_MODEL", "kimi-k2-turbo-preview")

        # 工作目录
        self.workspace = "agent_workspace"
        os.makedirs(self.workspace, exist_ok=True)

        # 上下文提炼配置
        self.MESSAGE_COUNT_TRIGGER = 24  # 约12轮对话后触发提炼
        self.KEEP_RECENT_MESSAGES = 10   # 保留最近10条消息完整
        self.SUMMARY_MIN_LENGTH = 200    # 只摘要超过200字符的tool result

    # ============================================
    # 动态上下文构建机制
    # ============================================

    def _build_dynamic_messages(self) -> List[Dict]:
        """
        构建完整消息数组(OpenAI格式),动态注入系统上下文

        结构:
        1. System workflow prompt (持久化,指导思考)
        2. System reminder start (动态环境信息)
        3. Conversation history (历史消息)
        4. System reminder end (Todo短期记忆)
        """
        full_messages = []

        # 1. 系统工作流提示(总是第一个)
        full_messages.append({
            "role": "system",
            "content": self._get_system_workflow_prompt()
        })

        # 2. 系统提醒开始(环境信息)
        reminder_start = self._generate_system_reminder_start()
        if reminder_start:
            full_messages.append({
                "role": "system",
                "content": reminder_start
            })

        # 3. 对话历史
        full_messages.extend(self.messages)

        # 4. 系统提醒结束(Todo状态)
        reminder_end = self._generate_system_reminder_end()
        if reminder_end:
            full_messages.append({
                "role": "system",
                "content": reminder_end
            })

        return full_messages

    def _get_system_workflow_prompt(self) -> str:
        """系统工作流提示 - 指导AI如何思考和行动"""
        return """你是一个智能AI助手,可以使用工具来完成任务。

## 核心工作原则

1. **主动使用工具**
   - 不要只是说你要做什么 - 直接调用工具去执行
   - 使用 ReadFile 在处理前先了解数据结构
   - 使用 RunCommand 执行Python脚本进行复杂分析
   - 使用 WriteFile 保存结果和生成的代码

2. **Todo任务管理**
   - 对于复杂任务(3步以上),使用 TodoUpdate 创建和追踪任务
   - 始终保持恰好一个任务处于 "in_progress" 状态
   - **完成任务时提供执行结果**: 使用 result 参数简要说明关键结果
   - 任务状态: "pending" | "in_progress" | "completed"

3. **思考模型**
   在每次回复前思考:
   - 我当前的目标是什么?
   - 我需要什么信息?(如果缺失,使用工具获取)
   - 下一步最合适的行动是什么?
   - 这个行动完成后,任务是否真正完成?

4. **工作空间意识**
   - 所有文件操作都在 agent_workspace/ 目录中进行
   - 相对路径自动解析到工作空间
   - 处理大文件前先检查文件是否存在
   - 对于大文件(显示超过1000字符),编写Python脚本处理

5. **迭代执行**
   - 你可以多次调用工具直到任务完全完成
   - 在进行下一步前先检查工具结果
   - 如果出现错误,分析并修正后重试
   - 只有在任务真正完成时才停止

## 工具使用指南

**ReadFile**: 预览数据结构和内容(截断到1000字符)
**WriteFile**: 保存生成的脚本、结果、报告
**RunCommand**: 执行Python脚本、数据处理命令
**TodoUpdate**: 追踪多步骤工作流的任务进度"""

    def _generate_system_reminder_start(self) -> str:
        """生成动态环境上下文"""
        return f"""<system_context>
当前环境:
- 时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
- 工作空间: {os.path.abspath(self.workspace)}
- 回合: {self._current_turn}
- 可用工具: ReadFile, WriteFile, RunCommand, TodoUpdate
</system_context>"""

    def _generate_system_reminder_end(self) -> str:
        """生成Todo短期记忆"""
        if not self.todos["tasks"]:
            return ""

        # 格式化Todo列表
        todo_lines = ["<todo_memory>", "当前任务:"]
        for task in self.todos["tasks"]:
            status_icon = {
                "pending": "[ ]",
                "in_progress": "[→]",
                "completed": "[✓]"
            }[task["status"]]
            # Show task with result if available
            task_line = f"{status_icon} {task['id']}: {task['description']}"
            if task.get("result"):
                task_line += f" → {task['result']}"
            todo_lines.append(task_line)

        todo_lines.append("\n提醒: 使用 TodoUpdate 工具更新任务状态!")
        todo_lines.append("完成任务时，建议提供 result 参数说明执行结果!")
        todo_lines.append("</todo_memory>")

        return "\n".join(todo_lines)

    def run(self, user_input: str, max_turns: int = 40) -> str:
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

        # 添加用户消息
        self.messages.append({
            "role": "user",
            "content": user_input
        })

        # 主循环
        for turn in range(max_turns):
            self._current_turn = turn + 1  # 追踪当前回合
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
        """调用 Kimi API (使用动态上下文)"""
        try:
            # 智能提炼上下文（如果需要）
            if self._should_refine_context():
                self._refine_context()

            # 构建动态消息上下文并保存
            full_messages = self._build_dynamic_messages()
            self.full_messages_history = full_messages

            response = self.client.chat.completions.create(
                model=self.model,
                messages=full_messages,  # 使用动态消息而非静态历史
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
            if len(result_str) > 200:
                print(f"   结果: {result_str[:200]}...")
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
            {
                "type": "function",
                "function": {
                    "name": "ReadFile",
                    "description": "读取文件内容。注意：最多返回前1000个字符，如果文件过大会被截断。对于大文件建议使用Python脚本分批处理",
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
            },
            {
                "type": "function",
                "function": {
                    "name": "TodoUpdate",
                    "description": "管理任务列表(短期记忆)。用于追踪复杂任务的执行进度。对于3步以上的复杂任务,使用此工具创建和更新待办事项。",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "action": {
                                "type": "string",
                                "enum": ["add", "update_status", "complete"],
                                "description": "操作类型: add=添加新任务, update_status=更新状态, complete=完成任务"
                            },
                            "task_id": {
                                "type": "string",
                                "description": "任务ID (更新/完成操作时必需)"
                            },
                            "description": {
                                "type": "string",
                                "description": "任务描述 (添加操作时必需)"
                            },
                            "status": {
                                "type": "string",
                                "enum": ["pending", "in_progress", "completed"],
                                "description": "任务状态"
                            },
                            "result": {
                                "type": "string",
                                "description": "任务执行结果 (完成任务时建议提供)。简要说明执行的关键结果，帮助后续决策。例如：'成功读取150行数据'、'脚本执行成功，生成图表trend.png'、'发现5个异常值'"
                            }
                        },
                        "required": ["action"]
                    }
                }
            }
        ]

    def _execute_tool(self, tool_name: str, tool_args: Dict) -> str:
        """执行工具"""
        try:
            if tool_name == "ReadFile":
                return self._tool_read_file(tool_args["path"])
            elif tool_name == "WriteFile":
                return self._tool_write_file(tool_args["path"], tool_args["content"])
            elif tool_name == "RunCommand":
                return self._tool_run_command(tool_args["command"])
            elif tool_name == "TodoUpdate":
                return self._tool_todo_update(tool_args)
            else:
                return f"错误: 未知工具 {tool_name}"
        except Exception as e:
            return f"错误: {str(e)}"

    def _resolve_path(self, path: str) -> str:
        """解析路径：绝对路径保持不变，相对路径拼接到 workspace"""
        return path if os.path.isabs(path) else os.path.join(self.workspace, path)

    def _tool_read_file(self, path: str) -> str:
        """读取文件"""
        path = self._resolve_path(path)
        max_chars = 1000  # 最大字符数限制，约2-3k tokens

        try:
            with open(path, 'r', encoding='utf-8') as f:
                content = f.read()

            # 检查是否超出限制
            original_len = len(content)
            if original_len > max_chars:
                content = content[:max_chars]
                return f"⚠️  文件过大，已截断到前 {max_chars} 个字符（总共 {original_len} 字符）\n建议使用 Python 脚本分批处理大文件\n\n{content}"

            return f"成功读取文件 {path} ({original_len} 字符)\n\n{content}"
        except Exception as e:
            return f"读取失败: {e}"

    def _tool_write_file(self, path: str, content: str) -> str:
        """写入文件"""
        path = self._resolve_path(path)
        try:
            # 创建目录
            os.makedirs(os.path.dirname(path) or '.', exist_ok=True)

            # 写入文件
            with open(path, 'w', encoding='utf-8') as f:
                f.write(content)

            return f"成功写入 {path} ({len(content)} 字符)"
        except Exception as e:
            return f"写入失败: {e}"

    def _tool_run_command(self, command: str) -> str:
        """执行终端命令"""
        # 危险命令黑名单
        BLACKLIST = [
            'rm -rf',
            'rm -fr',
            'sudo',
            'shutdown',
            'reboot',
            'mkfs',
            'dd',
            'format',
            ':(){:|:&};:',  # fork bomb
            '> /dev/sda',
            'mv /* /dev/null'
        ]

        # 检查黑名单
        for dangerous_cmd in BLACKLIST:
            if dangerous_cmd in command.lower():
                return f"❌ 拒绝执行: 命令包含危险操作 '{dangerous_cmd}'"

        try:
            # 执行命令，设置200秒超时
            result = subprocess.run(
                command,
                shell=True,
                capture_output=True,
                text=True,
                timeout=200,  # 200秒超时
                cwd=self.workspace  # 在工作目录中执行
            )

            # 组合输出
            output_lines = []
            if result.stdout:
                output_lines.append("标准输出:")
                output_lines.append(result.stdout.strip())
            if result.stderr:
                output_lines.append("错误输出:")
                output_lines.append(result.stderr.strip())

            output = "\n".join(output_lines) if output_lines else "(无输出)"

            # 返回结果
            if result.returncode == 0:
                return f"✓ 命令执行成功 (退出码: {result.returncode})\n\n{output}"
            else:
                return f"⚠️  命令执行失败 (退出码: {result.returncode})\n\n{output}"

        except subprocess.TimeoutExpired:
            return "❌ 命令执行超时 (超过200秒)"
        except Exception as e:
            return f"❌ 命令执行失败: {str(e)}"

    def _tool_todo_update(self, params: Dict) -> str:
        """Todo管理工具 - 短期任务记忆"""
        action = params["action"]

        if action == "add":
            # 添加新任务
            task_id = f"task_{len(self.todos['tasks']) + 1}"
            self.todos["tasks"].append({
                "id": task_id,
                "description": params["description"],
                "status": params.get("status", "pending"),
                "created_at": datetime.now().isoformat()
            })
            return f"✓ 已添加任务 {task_id}: {params['description']}"

        elif action == "update_status":
            # 更新任务状态
            task_id = params["task_id"]
            new_status = params["status"]
            for task in self.todos["tasks"]:
                if task["id"] == task_id:
                    task["status"] = new_status
                    return f"✓ 任务 {task_id} 状态更新为: {new_status}"
            return f"❌ 未找到任务: {task_id}"

        elif action == "complete":
            # 完成任务
            task_id = params["task_id"]
            result = params.get("result", "")  # Get optional result
            for task in self.todos["tasks"]:
                if task["id"] == task_id:
                    task["status"] = "completed"
                    if result:
                        task["result"] = result  # Store result
                        return f"✓ 任务 {task_id} 已完成\n执行结果: {result}"
                    else:
                        return f"✓ 任务 {task_id} 已完成"
            return f"❌ 未找到任务: {task_id}"

        return "❌ 未知操作"

    def _get_final_output(self) -> str:
        """获取最终输出"""
        for msg in reversed(self.messages):
            if msg["role"] == "assistant" and msg.get("content"):
                return msg["content"]
        return "无输出"

    def _save_conversation_log(self):
        """保存对话日志到文件"""
        try:
            # 创建 logs 目录
            os.makedirs("logs", exist_ok=True)

            # 生成文件名（按时间）
            timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
            log_file = f"logs/{timestamp}.txt"

            # 格式化对话内容
            log_content = []
            log_content.append("=" * 60)
            log_content.append(f"对话日志 - {timestamp}")
            log_content.append("=" * 60)
            log_content.append("")

            for i, msg in enumerate(self.full_messages_history, 1):
                role = msg["role"]
                content = msg.get("content", "")

                if role == "user":
                    log_content.append(f"[{i}] 用户:")
                    log_content.append(f"{content}")
                elif role == "system":
                    log_content.append(f"[{i}] 系统:")
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
                    # 截断过长的内容
                    if len(content) > 500:
                        log_content.append(f"{content[:500]}... (已截断)")
                    else:
                        log_content.append(f"{content}")

                log_content.append("=" * 30)

            log_content.append("=" * 60)
            log_content.append(f"对话结束 - 共 {len(self.messages)} 条消息")
            log_content.append("=" * 60)

            # 写入txt文件
            with open(log_file, 'w', encoding='utf-8') as f:
                f.write("\n".join(log_content))

            # 写入json文件（原始消息 + Todo状态 + 完整上下文）
            json_file = log_file.replace('.txt', '.json')
            log_data = {
                "messages": self.messages,
                "todos": self.todos,
                "timestamp": timestamp,
                "turns": len(self.messages),
                "full_context": self.full_messages_history  # 只加这一行
            }
            with open(json_file, 'w', encoding='utf-8') as f:
                json.dump(log_data, f, ensure_ascii=False, indent=2, default=str)

            print(f"\n📝 对话日志已保存: {log_file} + {json_file}")
        except Exception as e:
            print(f"\n⚠️  日志保存失败: {e}")

    # ============================================
    # 智能上下文提炼系统
    # ============================================

    def _should_refine_context(self) -> bool:
        """检查是否需要提炼上下文"""
        return len(self.messages) >= self.MESSAGE_COUNT_TRIGGER

    def _refine_context(self):
        """
        智能提炼上下文 - 只摘要tool results

        保留：
        - 所有 user messages
        - 所有 assistant messages（包括tool_calls）
        - 最近KEEP_RECENT_MESSAGES条消息（完整保留）

        提炼：
        - 旧的 tool results → LLM智能摘要
        """
        if len(self.messages) < self.MESSAGE_COUNT_TRIGGER:
            return

        print(f"\n{'='*60}")
        print(f"🔍 智能提炼上下文")
        print(f"{'='*60}")

        # 计算提炼边界
        refine_boundary = len(self.messages) - self.KEEP_RECENT_MESSAGES

        # 收集需要摘要的tool results
        to_summarize = []
        for i in range(refine_boundary):
            msg = self.messages[i]

            # 只处理tool消息，且未被摘要过，且长度超过阈值
            if (msg['role'] == 'tool' and
                not msg.get('_summarized') and
                len(msg['content']) > self.SUMMARY_MIN_LENGTH):

                to_summarize.append((i, msg['content']))

        if not to_summarize:
            print("无需摘要的tool结果")
            print(f"{'='*60}\n")
            return

        print(f"发现 {len(to_summarize)} 个需要摘要的tool结果")

        # 批量摘要
        for i, original_content in to_summarize:
            try:
                summary = self._summarize_tool_result(original_content)

                # 替换内容
                self.messages[i]['content'] = summary
                self.messages[i]['_summarized'] = True
                self.messages[i]['_original_length'] = len(original_content)

                print(f"  ✓ 已摘要: {len(original_content)} → {len(summary)} 字符")

            except Exception as e:
                print(f"  ⚠️  摘要失败，保留原内容: {e}")
                continue

        print(f"{'='*60}\n")

    def _summarize_tool_result(self, tool_result: str) -> str:
        """
        使用LLM智能摘要tool result

        目标：保留关键信息，提炼重点
        - 文件类型和结构
        - 前几行样本数据
        - 关键特征和发现
        - 执行状态（成功/失败）
        """
        # 摘要提示词
        summary_prompt = f"""请智能提炼以下工具执行结果的关键信息。

要求：
1. **保留重点，去除冗余** - 不是简单压缩，而是提炼关键信息
2. **结构化输出** - 使用清晰的格式展示关键点
3. **保留样本** - 如果是数据/文件，包含前几行样本
4. **突出特征** - 总结数据/输出的关键特征

针对不同类型：
- **ReadFile**: 文件类型、列/字段结构、前3-5行样本、数据特征（时间范围、主要内容等）
- **RunCommand**: 执行状态、关键输出行、错误信息（如有）、最终结果
- **WriteFile**: 文件路径、内容大小、写入状态

输出格式示例：
```
文件类型: CSV (4列×150行)
内容: 2022年1-2月GCP用量数据
列结构: [date, metric_name, value, unit]
前3行样本:
  - 2022-01-01, compute_engine_cpu_hours, 1234.5
  - 2022-01-01, cloud_storage_gb, 500.2
  - 2022-01-02, compute_engine_cpu_hours, 1189.3
关键特征: 覆盖60天，主要指标CPU和存储
```

工具执行结果:
{tool_result[:2000]}{'...' if len(tool_result) > 2000 else ''}

智能摘要:"""

        # 调用LLM API
        try:
            response = self.client.chat.completions.create(
                model=self.model,  # 使用same model确保一致性
                messages=[
                    {
                        "role": "system",
                        "content": "你是一个数据分析助手，擅长提炼关键信息，保留重要特征和样本。"
                    },
                    {
                        "role": "user",
                        "content": summary_prompt
                    }
                ],
                temperature=0.3,  # 稍低温度，确保一致性
                max_tokens=500    # 限制摘要长度
            )

            summary = response.choices[0].message.content.strip()

            # 添加摘要标记
            return f"[智能摘要] {summary}"

        except Exception as e:
            # 失败时返回简化版（首尾保留）
            print(f"LLM摘要失败: {e}")
            lines = tool_result.split('\n')
            first_lines = '\n'.join(lines[:3])
            last_lines = '\n'.join(lines[-2:]) if len(lines) > 5 else ""
            fallback = f"{first_lines}\n...\n{last_lines}" if last_lines else first_lines
            return f"[摘要失败，保留首尾] {fallback}"


# ============================================
# 使用示例
# ============================================

def example_simple():
    """示例1: 简单文件操作"""
    print("\n" + "="*60)
    print("示例: 文件操作")
    print("="*60)

    agent = DynamicPlanAgent()
    result = agent.run("验证下 data/full_gcp_data.csv, 文件太大, 写个python脚本读下前100行. 统计下三列的数量是否一致, 即 Usage Quantity * Cost per Quantity ($) = Unrounded Cost ($), 可以统计下diff ,因为可能有小数点差异")
    print(f"\n最终结果: {result}")


def example_multi_step():
    """示例2: 多步骤任务"""
    print("\n" + "="*60)
    print("示例: 多步骤任务")
    print("="*60)

    agent = DynamicPlanAgent()
    result = agent.run("""
    请完成以下任务:
    1. 找下当前的工作目录下有什么? 找到data/full_gcp_data.csv
    2. 写个python 脚本,并运行(当前已经有相关脚本, 可直接运行). 该脚本的功能是读取data/full_gcp_data.csv 文件, 并打印出文件的行数和列数.
    3. 对比2022年1月和2022年2月的各指标用量趋势, 并绘制下趋势图.
    4. 对比每天的的波动情况, 识别异常信号(如异常高或低的天).
    5. 生成分析报告, 包括趋势图和异常信号分析.
    """)
    print(f"\n最终结果: {result}")

def example_comprehensive_task():
    """示例3: 复杂任务"""
    print("\n" + "="*60)
    print("示例: 多步骤任务")
    print("="*60)

    agent = DynamicPlanAgent()
    result = agent.run("""
    请你帮我分析下工作目录下的data/full_gcp_data.csv, 探索性分析2022年1月和2022年2月的各指标用量趋势, 并生成报告
    """)
    print(f"\n最终结果: {result}")


def example_with_todo():
    """示例3: 使用Todo追踪复杂任务"""
    print("\n" + "="*60)
    print("示例: Todo任务追踪")
    print("="*60)

    agent = DynamicPlanAgent()
    result = agent.run("""
    完成以下数据分析任务:
    1. 读取 data/full_gcp_data.csv 文件(如果文件过大,使用Python脚本处理)
    2. 分析2022年1月和2月的用量趋势
    3. 识别用量最高的前5个资源
    4. 绘制趋势对比图
    5. 生成分析报告

    这是一个多步骤任务，请使用Todo工具追踪进度。
    """)
    print(f"\n最终结果: {result}")



if __name__ == "__main__":
    # 检查 API Key
    load_dotenv()
    if not os.getenv("MOONSHOT_API_KEY"):
        print("❌ 请在 .env 文件中设置 MOONSHOT_API_KEY")
        exit(1)

    # 运行示例
    # example_simple()
    # example_multi_step()
    example_comprehensive_task()

