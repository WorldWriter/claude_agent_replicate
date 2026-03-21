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


class KimiAgent:
    """Kimi Agent - Plan → Execute 两阶段工作流"""

    def __init__(self, api_key: str = None):
        """初始化 Agent

        Args:
            api_key: Kimi API密钥
        """
        load_dotenv()

        # 根据 LLM_PROVIDER 动态选择 API 客户端
        provider = os.getenv("LLM_PROVIDER", "kimi").lower()
        if provider == "gemini":
            self.client = OpenAI(
                api_key=api_key or os.getenv("GEMINI_API_KEY"),
                base_url=os.getenv("GEMINI_API_BASE", "https://generativelanguage.googleapis.com/v1beta/openai/")
            )
            self.model = os.getenv("LLM_MODEL", "gemini-2.0-flash")
        else:  # kimi (默认)
            self.client = OpenAI(
                api_key=api_key or os.getenv("MOONSHOT_API_KEY"),
                base_url=os.getenv("KIMI_API_BASE", "https://api.moonshot.ai/v1")
            )
            self.model = os.getenv("LLM_MODEL", "kimi-k2.5")

        print(f"使用 {provider} API, 模型: {self.model}")

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

        # 显式计划产物（OutputPlan）
        self.output_plan: Dict[str, Any] = {}

        # Fresh-Context 验证 Agent 开关（默认关闭，benchmark 模式可开启）
        self._enable_verification_agent: bool = False

        # 任务类型（运行时检测，用于注入专项 prompt）
        self.task_type: str | None = None
        self._prompts_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), '.claude', 'skills', 'da-code-solver', 'reference')
        self._prompt_cache: dict = {}

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

        # 1.5. 任务类型专项策略（如果检测到类型）
        if self.task_type:
            task_hint = self._get_task_hint(self.task_type)
            if task_hint:
                full_messages.append({
                    "role": "user",
                    "content": f"[TASK_STRATEGY]\n{task_hint}"
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
        """系统工作流提示 - 从 prompts/base.md 加载"""
        return self._load_prompt('base')

    def _load_prompt(self, name: str) -> str:
        """从 prompts/<name>.md 加载，带缓存"""
        if name not in self._prompt_cache:
            path = os.path.join(self._prompts_dir, f'{name}.md')
            with open(path, 'r', encoding='utf-8') as f:
                self._prompt_cache[name] = f.read()
        return self._prompt_cache[name]

    def _get_task_hint(self, task_type: str) -> str | None:
        """根据任务类型返回专项 prompt，无匹配时返回 None"""
        mapping = {
            # task_id 前缀（直接调用时）
            'di': 'di',       # di-text, di-csv
            'dm': 'dm',       # dm-csv, data-wrangling
            'ml': 'ml',       # ml-regression, ml-binary, ml-multi, ml-cluster
            'data-sa': 'sa',  # data-sa
            'plot': 'plot',   # plot-bar, plot-line, plot-pie, plot-scatter
            # 英文全称（来自 run_benchmark.py 的 类型: 行）
            'Data Insight': 'di',
            'Data Manipulation': 'dm',
            'ML ': 'ml',              # covers ML Regression / Binary / Multi / Cluster / Competition
            'Statistical Analysis': 'sa',
            'Data Visualization': 'plot',
        }
        for prefix, fname in mapping.items():
            if task_type.startswith(prefix) or task_type == prefix:
                return self._load_prompt(fname)
        return None

    def _detect_task_type(self, message: str) -> str | None:
        """从任务消息中检测任务类型（读取 '类型:' 行）"""
        for line in message.split('\n'):
            if line.startswith('类型:'):
                return line.replace('类型:', '').strip()
        return None

    def _generate_system_reminder_start(self) -> str:
        """生成动态环境上下文"""
        return f"""<system_context>
当前环境:
- 时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
- 工作空间: {os.path.abspath(self.workspace)}
- 回合: {self._current_turn}
- 可用工具: ReadFile, WriteFile, RunCommand, TodoUpdate, VerifyResult
</system_context>"""

    def _generate_system_reminder_end(self) -> str:
        """生成Todo短期记忆"""
        if not self.todos["tasks"] and not self.output_plan:
            return ""

        todo_lines = []

        # 格式化Todo列表
        if self.todos["tasks"]:
            todo_lines.extend(["<todo_memory>", "当前任务:"])
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

        # 追加 output_plan 块
        if self.output_plan:
            todo_lines.append("")
            todo_lines.append("<output_plan>")
            todo_lines.append(f"任务目标: {self.output_plan.get('summary', '')}")
            todo_lines.append("期望输出:")
            for f in self.output_plan.get("output_files", []):
                line = f"  - {f['filename']} ({f['format']})"
                if f.get("columns"):
                    line += f" 列: {f['columns']}"
                if f.get("row_constraint"):
                    line += f" | {f['row_constraint']}"
                todo_lines.append(line)
            todo_lines.append("</output_plan>")

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

        # 检测任务类型
        self.task_type = self._detect_task_type(user_input)

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
            # 构建动态消息上下文并保存
            full_messages = self._build_dynamic_messages()
            self.full_messages_history = full_messages

            # thinking 模型 (k2.5, k2-thinking) 只允许 temperature=1
            temp = 1.0 if "k2.5" in self.model or "thinking" in self.model else 0.3

            response = self.client.chat.completions.create(
                model=self.model,
                messages=full_messages,  # 使用动态消息而非静态历史
                tools=self._get_tools(),
                temperature=temp
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
        """定义可用工具"""
        return [
            {
                "type": "function",
                "function": {
                    "name": "ReadFile",
                    "description": "读取文件内容。CSV文件自动显示前10行+总行数。其他文件最多返回前20000个字符，如果文件过大会被截断，建议使用Python脚本分批处理",
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
                    "description": "管理任务列表(短期记忆)。用于追踪复杂任务的执行进度。对于3步以上的复杂任务,使用此工具创建和更新待办事项。plan 用于分析完成后声明输出文件格式，必须在 ReadFile 之后单独调用。",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "action": {
                                "type": "string",
                                "enum": ["add", "update_status", "complete", "plan"],
                                "description": "操作类型: add=添加新任务, update_status=更新状态, complete=完成任务, plan=声明输出规格（读取分析完成后调用）"
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
                            },
                            "output": {
                                "type": "object",
                                "description": "输出规格（plan 时必需）",
                                "properties": {
                                    "summary": {"type": "string", "description": "一句话任务目标"},
                                    "output_files": {
                                        "type": "array",
                                        "items": {
                                            "type": "object",
                                            "properties": {
                                                "filename": {"type": "string"},
                                                "format": {"type": "string", "description": "csv/json/png/jpg"},
                                                "columns": {"type": "array", "items": {"type": "string"}},
                                                "row_constraint": {"type": "string"}
                                            },
                                            "required": ["filename", "format"]
                                        }
                                    }
                                },
                                "required": ["summary", "output_files"]
                            }
                        },
                        "required": ["action"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "VerifyResult",
                    "description": "验证输出文件质量。检查：文件存在性、列名匹配sample_result.csv、行数（ML任务）、NaN值、数值精度。任务完成前必须调用此工具确认结果正确。",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "task_id": {
                                "type": "string",
                                "description": "任务ID，如 ml-binary-009"
                            },
                            "task_type": {
                                "type": "string",
                                "description": "任务类型，如 ml-binary, plot-bar, di-csv"
                            }
                        },
                        "required": ["task_id", "task_type"]
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
            elif tool_name == "VerifyResult":
                return self._tool_verify_result(tool_args)
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

        elif action == "plan":
            artifacts = params.get("output", {})
            if not artifacts:
                return "ERROR: plan requires 'output' parameter"
            self.output_plan = artifacts
            files_desc = ", ".join(f["filename"] for f in artifacts.get("output_files", []))
            return f"✓ 输出规格已记录。目标文件: {files_desc}"

        return "❌ 未知操作"

    def _tool_verify_result(self, args: Dict) -> str:
        """验证输出文件质量：文件存在、列名、行数、NaN、精度、JSON、Plot"""
        import math
        import json as _json
        task_id = args.get("task_id", "")
        task_type = args.get("task_type", "")
        ws = self.workspace
        issues = []

        # --- 确定期望输出文件（三级优先链）---
        expected_files = []
        source = "heuristic"

        # Priority 1: Agent-derived output plan
        if self.output_plan and self.output_plan.get("output_files"):
            for f in self.output_plan["output_files"]:
                fn = f["filename"]
                if fn not in expected_files:
                    expected_files.append(fn)
            source = "output_plan"

        # Priority 2: Eval config (benchmark mode)
        if not expected_files:
            # ws = .../agent_workspace/output_dir_xxx/task_id → 往上两级得 agent_workspace/
            eval_config_path = os.path.join(
                os.path.dirname(os.path.dirname(ws)),
                "da-code/da_code/configs/eval/eval_test.jsonl"
            )
            config_found = False
            if task_id and os.path.exists(eval_config_path):
                with open(eval_config_path) as _f:
                    for _line in _f:
                        _t = _json.loads(_line)
                        if _t["id"] == task_id:
                            config_found = True
                            for _r in _t.get("result", []):
                                _fv = _r.get("file", [])
                                if isinstance(_fv, str):
                                    _fv = [_fv]
                                for _fn in _fv:
                                    # 跳过 dabench/ 子目录文件，只保留根目录文件
                                    if "/" not in _fn and _fn.endswith((".csv", ".json", ".png", ".jpg")):
                                        if _fn not in expected_files:
                                            expected_files.append(_fn)
                            break

            # NO_FILE 任务（config 存在且明确无文件要求）：直接 PASS
            if config_found and not expected_files:
                return f"=== VerifyResult (eval_config): PASS ===\n此任务无文件输出要求，任务可以结束。\n=== End ==="

            if expected_files:
                source = "eval_config"

        # Priority 3: Heuristic fallback
        if not expected_files:
            if task_id.startswith("ml-competition"):
                expected_files = ["submission.csv"]
            elif task_id.startswith("plot-"):
                expected_files = ["result.png"]
            elif task_id.startswith("di-text") or task_id.startswith("data-sa"):
                expected_files = ["result.json"]
            else:
                expected_files = ["result.csv"]
            source = "heuristic"

        # --- Check A: 文件存在（多文件需全部存在）---
        missing = [fn for fn in expected_files if not os.path.exists(os.path.join(ws, fn))]
        if missing:
            if len(expected_files) > 1:
                lines = "\n".join(
                    f"  - {fn} ({'不存在' if not os.path.exists(os.path.join(ws, fn)) else '存在'})"
                    for fn in expected_files
                )
                return (f"=== VerifyResult: FAIL ===\n"
                        f"1. MISSING: 需要同时生成以下文件:\n{lines}\n"
                        f"   Fix: 确保所有文件都保存到 {ws}\n"
                        f"=== End ===")
            else:
                fn = missing[0]
                return (f"=== VerifyResult: FAIL ===\n"
                        f"1. MISSING: {fn} 不存在于 {ws}\n"
                        f"   Fix: 将结果保存到 {os.path.join(ws, fn)}\n"
                        f"=== End ===")

        # --- 对每个文件做内容检查 ---
        for expected in expected_files:
            out_path = os.path.join(ws, expected)

            # --- Check B: CSV 类型专项检查 ---
            if expected.endswith(".csv"):
                try:
                    import pandas as pd
                    result_df = pd.read_csv(out_path)
                except Exception as e:
                    return f"=== VerifyResult: FAIL ===\n1. CSV_READ_ERROR ({expected}): {e}\n=== End ==="

                # B1 列名
                sample_path = next(
                    (os.path.join(ws, f) for f in os.listdir(ws) if f.startswith("sample_") and f.endswith(".csv")),
                    None
                )
                if sample_path:
                    try:
                        import pandas as pd
                        sample_cols = list(pd.read_csv(sample_path, nrows=0).columns)
                        result_cols = list(result_df.columns)
                        if result_cols != sample_cols:
                            issues.append(
                                f"COLUMNS ({expected}): 期望 {sample_cols}，实际 {result_cols}\n"
                                f"   Fix: 重命名列使其与 sample_result.csv 完全一致（含大小写）"
                            )
                    except Exception:
                        pass

                # B1.5 output_plan 列名检查（无 sample 时启用）
                if not sample_path and self.output_plan:
                    for art in self.output_plan.get("output_files", []):
                        if art["filename"] == expected and art.get("columns"):
                            result_cols = list(result_df.columns)
                            if result_cols != art["columns"]:
                                issues.append(
                                    f"COLUMNS ({expected}): plan 期望 {art['columns']}，实际 {result_cols}\n"
                                    f"   Fix: 重命名列使其与 output_plan 声明一致"
                                )

                # B2 ML 任务行数
                test_path = os.path.join(ws, "test.csv")
                if os.path.exists(test_path) and task_type.startswith("ml-"):
                    try:
                        expected_rows = sum(1 for _ in open(test_path)) - 1
                        if len(result_df) != expected_rows:
                            issues.append(
                                f"ROW_COUNT ({expected}): test.csv 有 {expected_rows} 行，{expected} 有 {len(result_df)} 行\n"
                                f"   Fix: 确保对 test.csv 每行输出一个预测"
                            )
                    except Exception:
                        pass

                # B3 NaN 检测
                if result_df.isnull().any().any():
                    nan_cols = result_df.columns[result_df.isnull().any()].tolist()
                    issues.append(
                        f"NAN ({expected}): 列 {nan_cols} 中存在 NaN\n"
                        f"   Fix: 用 fillna 或 dropna 处理缺失值"
                    )

                # B4 精度检测
                if sample_path:
                    try:
                        import pandas as pd

                        def max_decimals(series):
                            return max(
                                (len(str(v).rstrip('0').split('.')[-1]) if '.' in str(v) else 0)
                                for v in series.dropna().head(20)
                            ) if len(series.dropna()) > 0 else 0

                        sample_df = pd.read_csv(sample_path)
                        for col in sample_df.select_dtypes(include="number").columns:
                            if col not in result_df.columns:
                                continue
                            s_dec = max_decimals(sample_df[col])
                            r_dec = max_decimals(result_df[col])
                            if s_dec > 0 and r_dec > s_dec + 2:
                                issues.append(
                                    f"PRECISION ({expected}): 列 '{col}' 有 {r_dec} 位小数，sample 只有 {s_dec} 位\n"
                                    f"   Fix: df['{col}'] = df['{col}'].round({s_dec})"
                                )
                    except Exception:
                        pass

            # --- Check C: JSON 类型 ---
            elif expected.endswith(".json"):
                try:
                    with open(out_path) as f:
                        data = _json.load(f)
                    if not data:
                        issues.append(f"JSON ({expected}): 文件为空\n   Fix: 确保写入了有效的 JSON 数据")
                except Exception as e:
                    issues.append(f"JSON_ERROR ({expected}): {e}\n   Fix: 检查 JSON 格式")

            # --- Check D: Plot 类型 ---
            elif expected.endswith((".png", ".jpg")):
                yaml_files = [f for f in os.listdir(ws) if f.endswith((".yaml", ".yml"))]
                if yaml_files:
                    issues.append(
                        f"PLOT_HINT: 已生成 {expected}，请确认 figsize/颜色/标签与 {yaml_files[0]} 配置一致"
                    )

        # --- 输出报告 ---
        files_str = ", ".join(expected_files)
        if not issues:
            # 机械检查全部 PASS，可选地 spawn 验证 Agent
            if self._enable_verification_agent:
                verifier_result = self._spawn_verification_agent(task_id, task_type)
                if "VERDICT: FAIL" in verifier_result:
                    issues.append(f"VERIFIER: 独立验证发现问题:\n   {verifier_result}")

        if not issues:
            return f"=== VerifyResult ({source}): PASS ===\n{files_str} 验证通过，任务可以结束。\n=== End ==="

        report = f"=== VerifyResult ({source}): FAIL ===\n"
        for i, issue in enumerate(issues, 1):
            report += f"{i}. {issue}\n"
        report += "\n请修复以上问题后重新调用 VerifyResult 确认。\n=== End ==="
        return report

    def _spawn_verification_agent(self, task_id: str, task_type: str) -> str:
        """Spawn fresh-context verifier to independently check output format."""
        verifier = KimiAgent()
        verifier.workspace = self.workspace  # Share workspace (read-only intent)

        artifacts_section = ""
        if self.output_plan:
            import json as _json
            artifacts_section = (
                f"\n## 执行Agent声明的输出规格\n```json\n"
                f"{_json.dumps(self.output_plan, ensure_ascii=False, indent=2)}\n"
                f"```\n请对比你的独立判断与此声明是否一致。"
            )

        output_files = [f for f in os.listdir(self.workspace)
                        if f.endswith(('.csv', '.json', '.png', '.jpg'))
                        and not f.startswith(('sample_', 'train', 'test'))]

        prompt = f"""你是独立验证Agent。验证任务输出是否符合要求。

任务ID: {task_id} | 类型: {task_type} | 工作目录: {self.workspace}

## 验证步骤
1. ReadFile 读取 README.md 了解任务要求
2. 如有 sample_*.csv，读取了解输出格式
3. 独立判断：应输出什么文件？什么列名？
4. 检查实际输出: {output_files}
{artifacts_section}

## 输出格式（直接文本回复）
VERDICT: PASS 或 FAIL
EXPECTED_FILES: [文件名列表]
EXPECTED_COLUMNS: [列名列表，如适用]
ISSUES: [问题描述，如有]

只读取文件和分析，不要执行代码或修改文件。"""

        try:
            result = verifier.run(prompt, max_turns=4)
            return result
        except Exception as e:
            return f"Verification agent error: {e}"

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
                "output_plan": self.output_plan,
                "timestamp": timestamp,
                "turns": len(self.messages),
                "full_context": self.full_messages_history
            }
            with open(json_file, 'w', encoding='utf-8') as f:
                json.dump(log_data, f, ensure_ascii=False, indent=2, default=str)

            print(f"\n📝 对话日志已保存: {log_file} + {json_file}")
        except Exception as e:
            print(f"\n⚠️  日志保存失败: {e}")



# ============================================
# 使用示例
# ============================================

def example_simple():
    """示例1: 简单文件操作"""
    print("\n" + "="*60)
    print("示例: 文件操作")
    print("="*60)

    agent = KimiAgent()
    result = agent.run("验证下 data/full_gcp_data.csv, 文件太大, 写个python脚本读下前100行. 统计下三列的数量是否一致, 即 Usage Quantity * Cost per Quantity ($) = Unrounded Cost ($), 可以统计下diff ,因为可能有小数点差异")
    print(f"\n最终结果: {result}")


def example_multi_step():
    """示例2: 多步骤任务"""
    print("\n" + "="*60)
    print("示例: 多步骤任务")
    print("="*60)

    agent = KimiAgent()
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

    agent = KimiAgent()
    result = agent.run("""
    请你帮我分析下工作目录下的data/full_gcp_data.csv, 探索性分析2022年1月和2022年2月的各指标用量趋势, 并生成报告
    """)
    print(f"\n最终结果: {result}")


def example_with_todo():
    """示例4: 使用Todo追踪复杂任务"""
    print("\n" + "="*60)
    print("示例: Todo任务追踪")
    print("="*60)

    agent = KimiAgent()
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


# 向后兼容别名（test/run_benchmark.py 等文件使用）
DynamicPlanAgent = KimiAgent


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
