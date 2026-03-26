"""
Kimi Agent - Plan → Execute 两阶段工作流
- 阶段一: 并行完整读取所有文件，制定计划
- 阶段二: 按计划顺序执行
- CSV 文件自动显示前10行 + 总行数
"""

import csv
import os
import json
import subprocess
import threading
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from typing import List, Dict, Any
from openai import OpenAI
from dotenv import load_dotenv


# ── Anthropic response adapters ────────────────────────────────────────────────
# Wrap Anthropic SDK responses so _process_response() sees the same interface
# as OpenAI responses (choices[0].message.content / .tool_calls).

class _AnthropicFunction:
    def __init__(self, block):
        self.name = block.name
        self.arguments = json.dumps(block.input, ensure_ascii=False)


class _AnthropicToolCall:
    def __init__(self, block):
        self.id = block.id
        self.function = _AnthropicFunction(block)


class _AnthropicMessage:
    def __init__(self, response):
        self.tool_calls = []
        texts = []
        for block in response.content:
            if block.type == "tool_use":
                self.tool_calls.append(_AnthropicToolCall(block))
            elif block.type == "text":
                texts.append(block.text)
        self.content = "\n".join(texts) if texts else ""
        self.reasoning_content = None
        if not self.tool_calls:
            self.tool_calls = None


class _AnthropicChoice:
    def __init__(self, response):
        self.message = _AnthropicMessage(response)


class _AnthropicResponse:
    def __init__(self, response):
        self.choices = [_AnthropicChoice(response)]


class KimiAgent:
    """Kimi Agent - Plan → Execute 两阶段工作流"""

    def __init__(self, api_key: str = None, plan_mode: str = "auto"):
        """初始化 Agent

        Args:
            api_key: Kimi API密钥
            plan_mode: 规划模式 - "auto" | "interactive" | "disabled"
        """
        load_dotenv()

        # 根据 LLM_PROVIDER 动态选择 API 客户端
        self.provider = os.getenv("LLM_PROVIDER", "kimi").lower()
        if self.provider == "gemini":
            self.client = OpenAI(
                api_key=api_key or os.getenv("GEMINI_API_KEY"),
                base_url=os.getenv("GEMINI_API_BASE", "https://generativelanguage.googleapis.com/v1beta/openai/")
            )
            self.model = os.getenv("LLM_MODEL", "gemini-2.0-flash")
        elif self.provider == "minimax":
            try:
                import anthropic
                self.client = anthropic.Anthropic(
                    api_key=api_key or os.getenv("MINIMAX_API_KEY"),
                    base_url=os.getenv("MINIMAX_API_BASE", "https://api.minimax.io/anthropic")
                )
            except ImportError:
                raise ImportError("pip install anthropic")
            self.model = os.getenv("LLM_MODEL", "MiniMax-M1")
        elif self.provider == "claude":
            # Anthropic SDK (非 OpenAI 兼容)
            try:
                import anthropic
                self.client = anthropic.Anthropic(api_key=api_key or os.getenv("ANTHROPIC_API_KEY"))
            except ImportError:
                raise ImportError("pip install anthropic")
            self.model = os.getenv("LLM_MODEL", "claude-sonnet-4-6")
        else:  # kimi (默认)
            self.client = OpenAI(
                api_key=api_key or os.getenv("MOONSHOT_API_KEY"),
                base_url=os.getenv("KIMI_API_BASE", "https://api.moonshot.ai/v1")
            )
            self.model = os.getenv("LLM_MODEL", "kimi-k2.5")

        print(f"使用 {self.provider} API, 模型: {self.model}")

        # 消息历史
        self.messages: List[Dict] = []

        # 完整动态消息历史
        self.full_messages_history: List[Dict] = []

        # Todo短期记忆
        self.todos: Dict[str, Any] = {"tasks": []}

        # 回合计数
        self._current_turn = 0

        # 工作目录
        self.workspace = "agent_workspace"
        os.makedirs(self.workspace, exist_ok=True)

        # 并发工具调用锁（保护 TodoUpdate add 操作的 task_id 生成）
        self._todo_lock = threading.Lock()

        # Plan mode
        self._plan_mode: str = plan_mode
        self._phase: str = "execute" if plan_mode == "disabled" else "plan"
        self._plan: Dict[str, Any] = {}


    # ============================================
    # 动态上下文构建机制
    # ============================================

    def _build_dynamic_messages(self) -> List[Dict]:
        """
        构建完整消息数组(OpenAI格式),静态/动态分离以支持前缀缓存

        结构:
        [system] base.md (静态,可缓存)
        [user/assistant/tool...] 对话历史
        最后一条 user 消息末尾追加: <system_context> + <todo_memory> + <phase_reminder>
        """
        full_messages = []

        # 1. system 只放静态内容（支持 Anthropic prompt caching）
        static_prompt = self._get_system_workflow_prompt()
        self._system_blocks = [
            {"type": "text", "text": static_prompt, "cache_control": {"type": "ephemeral"}}
        ]
        full_messages.append({"role": "system", "content": static_prompt})

        # 2. 对话历史
        full_messages.extend(self.messages)

        # 3. 动态内容拼接到最后一条 user 消息末尾（不破坏前缀缓存）
        dynamic_parts = []
        reminder_start = self._generate_system_reminder_start()
        if reminder_start:
            dynamic_parts.append(reminder_start)
        reminder_end = self._generate_system_reminder_end()
        if reminder_end:
            dynamic_parts.append(reminder_end)
        phase_reminder = self._generate_phase_reminder()
        if phase_reminder:
            dynamic_parts.append(phase_reminder)

        if dynamic_parts:
            dynamic_text = "\n\n".join(dynamic_parts)
            for i in range(len(full_messages) - 1, -1, -1):
                if full_messages[i]["role"] == "user":
                    full_messages[i] = dict(full_messages[i])  # 不修改原始 messages
                    full_messages[i]["content"] += "\n\n" + dynamic_text
                    break

        return full_messages

    def _get_system_workflow_prompt(self) -> str:
        """系统工作流提示 - 根据 plan_mode 加载不同 base"""
        filename = 'base_noplan.md' if self._plan_mode == 'disabled' else 'base.md'
        path = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                            '.claude', 'skills', 'da-code-solver', 'reference', filename)
        with open(path, 'r', encoding='utf-8') as f:
            return f.read()

    def _generate_system_reminder_start(self) -> str:
        """生成动态环境上下文"""
        return f"""<system-reminder>
当前环境:
- 时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
- 工作空间: {os.path.abspath(self.workspace)}
- 回合: {self._current_turn}
</system-reminder>"""

    def _generate_phase_reminder(self) -> str:
        """生成阶段提醒"""
        if self._plan_mode == "disabled":
            return ""
        if self._phase == "plan":
            return """<system-reminder>
规划模式已激活。你当前处于规划阶段——你只能读取和分析文件，不得写入文件、执行命令或做出任何更改。此约束优先于你收到的其他所有指令。

请先读取所有相关文件，分析数据结构和任务需求，然后调用 SubmitPlan 提交结构化执行计划。
</system-reminder>"""
        else:
            return """<system-reminder>
执行模式已激活。计划已批准，请按照已批准计划执行任务。
</system-reminder>"""

    def _generate_system_reminder_end(self) -> str:
        """生成Todo短期记忆 + 已批准计划"""
        if not self.todos["tasks"] and not self._plan:
            return ""

        lines = ["<system-reminder>"]

        # 格式化Todo列表
        if self.todos["tasks"]:
            lines.append("当前任务:")
            for task in self.todos["tasks"]:
                status_icon = {
                    "pending": "[ ]",
                    "in_progress": "[→]",
                    "completed": "[✓]"
                }[task["status"]]
                task_line = f"{status_icon} {task['id']}: {task['description']}"
                if task.get("result"):
                    task_line += f" → {task['result']}"
                lines.append(task_line)

            lines.append("")
            lines.append("提醒: 使用 TodoUpdate 工具更新任务状态!")
            lines.append("完成任务时，建议提供 result 参数说明执行结果!")

        # 注入已批准的计划
        if self._plan and self._phase == "execute":
            lines.append("")
            lines.append("已批准计划:")
            spec = self._plan.get("output_spec", {})
            lines.append(f"输出: {spec.get('filename', '')} ({spec.get('format', '')})")
            if spec.get("columns"):
                lines.append(f"列: {spec['columns']}")
            if spec.get("notes"):
                lines.append(f"备注: {spec['notes']}")

        lines.append("</system-reminder>")
        return "\n".join(lines)

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
                # 规划阶段未调用 SubmitPlan 就想停止，强制要求提交计划
                if self._phase == "plan" and self._plan_mode != "disabled":
                    print("\n⚠️ 规划阶段未调用 SubmitPlan，强制要求提交...")
                    self.messages.append({
                        "role": "user",
                        "content": "你还在规划阶段，必须调用 SubmitPlan 工具提交结构化计划，才能进入执行阶段。请立即调用 SubmitPlan。"
                    })
                    continue
                print("\n✓ 任务完成!")
                break

        # 保存对话日志
        self._save_conversation_log()

        return self._get_final_output()

    def _call_kimi(self) -> Any:
        """调用 LLM API (使用动态上下文)"""
        if self.provider in ["claude", "minimax"]:
            return self._call_anthropic()
        try:
            # 构建动态消息上下文并保存
            full_messages = self._build_dynamic_messages()
            self.full_messages_history = full_messages

            # thinking 模型 (k2.5, k2-thinking) 只允许 temperature=1
            temp = 1.0 if "k2.5" in self.model or "thinking" in self.model else 0.3

            response = self.client.chat.completions.create(
                model=self.model,
                messages=full_messages,
                tools=self._get_tools(),
                temperature=temp
            )
            return response
        except Exception as e:
            print(f"❌ API 调用失败: {e}")
            return None

    def _messages_to_anthropic(self, messages: List[Dict]) -> List[Dict]:
        """将 OpenAI 格式的消息历史转换为 Anthropic 格式"""
        result = []
        i = 0
        while i < len(messages):
            msg = messages[i]
            role = msg.get("role")

            if role == "user":
                result.append({"role": "user", "content": msg["content"]})
            elif role == "assistant":
                content_blocks = []
                if msg.get("content"):
                    content_blocks.append({"type": "text", "text": msg["content"]})
                if msg.get("tool_calls"):
                    for tc in msg["tool_calls"]:
                        fn = tc.function if hasattr(tc, 'function') else tc.get('function', {})
                        name = fn.name if hasattr(fn, 'name') else fn.get('name', '')
                        args_str = fn.arguments if hasattr(fn, 'arguments') else fn.get('arguments', '{}')
                        tc_id = tc.id if hasattr(tc, 'id') else tc.get('id', '')
                        content_blocks.append({
                            "type": "tool_use",
                            "id": tc_id,
                            "name": name,
                            "input": json.loads(args_str) if isinstance(args_str, str) else args_str
                        })
                if content_blocks:
                    result.append({"role": "assistant", "content": content_blocks})
            elif role == "tool":
                # Anthropic: tool results must be in a user message
                tool_results = [{"type": "tool_result", "tool_use_id": msg["tool_call_id"], "content": msg["content"]}]
                # 合并连续的 tool messages
                while i + 1 < len(messages) and messages[i + 1].get("role") == "tool":
                    i += 1
                    tool_results.append({
                        "type": "tool_result",
                        "tool_use_id": messages[i]["tool_call_id"],
                        "content": messages[i]["content"]
                    })
                result.append({"role": "user", "content": tool_results})
            # system messages are handled separately
            i += 1
        return result

    def _call_anthropic(self) -> Any:
        """调用 Anthropic API (Claude / MiniMax-Anthropic)"""
        try:
            full_messages = self._build_dynamic_messages()
            self.full_messages_history = full_messages

            # 分离 system 和非 system 消息
            non_system = [m for m in full_messages if m["role"] != "system"]
            anthropic_messages = self._messages_to_anthropic(non_system)

            # 在倒数第二条 user 消息上设 cache_control，缓存对话历史前缀
            user_indices = [i for i, m in enumerate(anthropic_messages) if m["role"] == "user"]
            if len(user_indices) >= 2:
                idx = user_indices[-2]
                msg = anthropic_messages[idx]
                content = msg["content"]
                if isinstance(content, str):
                    msg["content"] = [{"type": "text", "text": content, "cache_control": {"type": "ephemeral"}}]
                elif isinstance(content, list) and content:
                    content[-1] = dict(content[-1])
                    content[-1]["cache_control"] = {"type": "ephemeral"}

            # 转换工具格式: OpenAI → Anthropic
            tools = []
            for t in self._get_tools():
                fn = t["function"]
                tools.append({
                    "name": fn["name"],
                    "description": fn["description"],
                    "input_schema": fn["parameters"]
                })

            response = self.client.messages.create(
                model=self.model,
                max_tokens=16000,
                system=self._system_blocks,  # list of blocks, 支持 cache_control
                messages=anthropic_messages,
                tools=tools,
                temperature=1.0
            )
            return _AnthropicResponse(response)
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

        # 保存 assistant 消息（兼容 thinking 模型）
        assistant_msg = {
            "role": "assistant",
            "content": message.content or "",
        }
        # thinking 模型返回 reasoning_content，必须在后续请求中回传
        reasoning = getattr(message, "reasoning_content", None)
        if reasoning:
            assistant_msg["reasoning_content"] = reasoning
        # tool_calls 为空时不传，避免部分 API 报错
        if message.tool_calls:
            assistant_msg["tool_calls"] = message.tool_calls
        self.messages.append(assistant_msg)

        # 如果没有工具调用，说明任务完成
        if not message.tool_calls:
            if message.content:
                print(f"\n助手: {message.content}")
            return True

        # 并行执行所有工具调用
        n = len(message.tool_calls)
        if n > 1:
            print(f"\n⚡ 并行执行 {n} 个工具调用")

        def _run_one(tool_call):
            tool_name = tool_call.function.name
            tool_args = json.loads(tool_call.function.arguments)
            print(f"\n🔧 调用工具: {tool_name}")
            print(f"   参数: {json.dumps(tool_args, ensure_ascii=False, indent=2)}")
            return str(self._execute_tool(tool_name, tool_args))

        if n == 1:
            results = [_run_one(message.tool_calls[0])]
        else:
            with ThreadPoolExecutor(max_workers=n) as executor:
                results = list(executor.map(_run_one, message.tool_calls))

        # 按原始顺序追加结果到消息历史
        for tool_call, result_str in zip(message.tool_calls, results):
            if len(result_str) > 200:
                print(f"   [{tool_call.function.name}] 结果: {result_str[:200]}...")
            else:
                print(f"   [{tool_call.function.name}] 结果: {result_str}")
            self.messages.append({
                "role": "tool",
                "tool_call_id": tool_call.id,
                "content": result_str
            })

        return False

    def _get_tools(self) -> List[Dict]:
        """定义可用工具 - 按阶段返回不同工具集"""
        read_file_tool = {
            "type": "function",
            "function": {
                "name": "ReadFile",
                "description": "读取文件内容。CSV文件自动显示前10行+总行数。其他文件最多返回前20000个字符，如果文件过大会被截断，建议使用Python脚本分批处理",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "path": {"type": "string", "description": "文件路径"}
                    },
                    "required": ["path"]
                }
            }
        }
        todo_update_tool = {
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
                        "task_id": {"type": "string", "description": "任务ID (更新/完成操作时必需)"},
                        "description": {"type": "string", "description": "任务描述 (添加操作时必需)"},
                        "status": {
                            "type": "string",
                            "enum": ["pending", "in_progress", "completed"],
                            "description": "任务状态"
                        },
                        "result": {
                            "type": "string",
                            "description": "任务执行结果 (完成任务时建议提供)。简要说明执行的关键结果，帮助后续决策。"
                        }
                    },
                    "required": ["action"]
                }
            }
        }
        base_tools = [read_file_tool, todo_update_tool]

        if self._phase == "plan":
            # 规划阶段：只读 + SubmitPlan
            submit_plan_tool = {
                "type": "function",
                "function": {
                    "name": "SubmitPlan",
                    "description": "提交执行计划以获得批准。规划阶段读取分析完所有文件后调用此工具。",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "analysis": {"type": "string", "description": "对任务的分析（数据特征、关键需求、潜在难点）"},
                            "subtasks": {
                                "type": "array",
                                "items": {
                                    "type": "object",
                                    "properties": {
                                        "id": {"type": "string"},
                                        "description": {"type": "string"},
                                        "depends_on": {"type": "array", "items": {"type": "string"}}
                                    },
                                    "required": ["id", "description"]
                                },
                                "description": "子任务列表（含依赖关系）"
                            },
                            "output_spec": {
                                "type": "object",
                                "properties": {
                                    "filename": {"type": "string"},
                                    "format": {"type": "string"},
                                    "columns": {"type": "array", "items": {"type": "string"}},
                                    "notes": {"type": "string"}
                                },
                                "required": ["filename", "format"],
                                "description": "核心产物的格式规格"
                            }
                        },
                        "required": ["analysis", "subtasks", "output_spec"]
                    }
                }
            }
            return base_tools + [submit_plan_tool]
        else:  # execute
            write_file_tool = {
                "type": "function",
                "function": {
                    "name": "WriteFile",
                    "description": "写入文件内容",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "path": {"type": "string", "description": "文件路径"},
                            "content": {"type": "string", "description": "文件内容"}
                        },
                        "required": ["path", "content"]
                    }
                }
            }
            run_command_tool = {
                "type": "function",
                "function": {
                    "name": "RunCommand",
                    "description": "执行终端命令。注意：禁止使用危险命令如 rm -rf, sudo, shutdown 等",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "command": {"type": "string", "description": "要执行的命令，例如 'ls -la' 或 'python script.py'"}
                        },
                        "required": ["command"]
                    }
                }
            }
            return base_tools + [write_file_tool, run_command_tool]

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
            elif tool_name == "SubmitPlan":
                return self._tool_submit_plan(tool_args)
            else:
                return f"错误: 未知工具 {tool_name}"
        except Exception as e:
            return f"错误: {str(e)}"

    def _resolve_path(self, path: str) -> str:
        """解析路径：绝对路径保持不变，相对路径解析到工作空间"""
        if os.path.isabs(path):
            return path
        return os.path.join(self.workspace, path)

    def _tool_read_file(self, path: str) -> str:
        """读取文件，CSV文件返回前10行预览，其他文件截断到20000字符"""
        path = self._resolve_path(path)

        try:
            # CSV 文件：显示前10行 + 总行数
            if path.lower().endswith('.csv'):
                with open(path, newline='', encoding='utf-8') as f:
                    reader = csv.reader(f)
                    rows = [next(reader, None) for _ in range(11)]  # header + 10 data rows
                    rows = [r for r in rows if r is not None]

                # 统计总行数（不含表头）
                with open(path, encoding='utf-8') as f:
                    total = sum(1 for _ in f) - 1

                header = rows[0] if rows else []
                preview = '\n'.join(','.join(r) for r in rows)
                return f"CSV 文件: {path}\n总行数: {total} 行 × {len(header)} 列\n列名: {header}\n\n前10行:\n{preview}"

            # 其他文件：读取并截断到20000字符
            max_chars = 20000
            with open(path, 'r', encoding='utf-8') as f:
                content = f.read()

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
                timeout=500,  # 500秒超时（支持长时间 ML 训练任务）
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
            # 添加新任务（加锁保证并发时 task_id 唯一）
            with self._todo_lock:
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

    def _tool_submit_plan(self, params: Dict) -> str:
        """处理 SubmitPlan 调用：存储计划，自动填充 todo，切换阶段"""
        self._plan = params

        # 从 subtasks 自动填充 TodoUpdate
        for subtask in params.get("subtasks", []):
            with self._todo_lock:
                self.todos["tasks"].append({
                    "id": subtask["id"],
                    "description": subtask["description"],
                    "status": "pending",
                    "created_at": datetime.now().isoformat()
                })

        if self._plan_mode == "auto":
            self._phase = "execute"
            return "✅ 计划已批准，进入执行阶段。请按计划开始执行任务。"

        # interactive 模式：CLI 交互审批
        approved, feedback = self._request_plan_approval()
        if approved:
            self._phase = "execute"
            return "✅ 计划已批准，进入执行阶段。请按计划开始执行任务。"
        else:
            # 清空 todo，等待重新提交
            self.todos["tasks"] = []
            return f"❌ 计划被拒绝: {feedback}\n请修改后重新调用 SubmitPlan。"

    def _request_plan_approval(self) -> tuple:
        """CLI 交互式计划审批"""
        print("\n" + "=" * 60)
        print("📋 执行计划待审批")
        print("=" * 60)
        print(f"\n分析:\n{self._plan.get('analysis', '')}")
        print(f"\n子任务:")
        for st in self._plan.get("subtasks", []):
            deps = f" → 依赖: {st['depends_on']}" if st.get("depends_on") else ""
            print(f"  [{st['id']}] {st['description']}{deps}")
        spec = self._plan.get("output_spec", {})
        print(f"\n输出: {spec.get('filename', '?')} ({spec.get('format', '?')})")
        if spec.get("columns"):
            print(f"  列: {spec['columns']}")
        print("=" * 60)

        answer = input("\n批准? (y=批准 / 其他=反馈修改意见): ").strip()
        if answer.lower() in ("y", "yes", ""):
            return True, "approved"
        return False, answer

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
                "plan": self._plan,
                "plan_mode": self._plan_mode,
                "timestamp": timestamp,
                "turns": len(self.messages),
                "full_context": self.full_messages_history
            }
            with open(json_file, 'w', encoding='utf-8') as f:
                json.dump(log_data, f, ensure_ascii=False, indent=2, default=str)

            print(f"\n📝 对话日志已保存: {log_file} + {json_file}")
        except Exception as e:
            print(f"\n⚠️  日志保存失败: {e}")



def example():
    """示例: 简单文件操作"""
    agent = KimiAgent()
    result = agent.run("验证下 data/full_gcp_data.csv, 文件太大, 写个python脚本读下前100行. 统计下三列的数量是否一致, 即 Usage Quantity * Cost per Quantity ($) = Unrounded Cost ($), 可以统计下diff ,因为可能有小数点差异")
    print(f"\n最终结果: {result}")


# 向后兼容别名（test/run_benchmark.py 等文件使用）
DynamicPlanAgent = KimiAgent


if __name__ == "__main__":
    load_dotenv()
    if not os.getenv("MOONSHOT_API_KEY"):
        print("❌ 请在 .env 文件中设置 MOONSHOT_API_KEY")
        exit(1)
    example()
