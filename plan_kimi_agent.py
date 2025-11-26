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

    def __init__(self, api_key: str = None, mode: str = "strategic"):
        """
        初始化 Agent

        Args:
            api_key: Kimi API密钥
            mode: Agent模式 - "strategic"（战略层）或 "tactical"（战术层）
        """
        load_dotenv()

        # 初始化 Kimi API 客户端
        self.client = OpenAI(
            api_key=api_key or os.getenv("MOONSHOT_API_KEY"),
            base_url="https://api.moonshot.ai/v1"
        )

        # Agent 模式
        self.mode = mode

        # 消息历史
        self.messages: List[Dict] = []

        # 模型配置
        self.model = os.getenv("LLM_MODEL", "kimi-k2-turbo-preview")

        # 工作目录
        self.workspace = "agent_workspace"
        os.makedirs(self.workspace, exist_ok=True)

        # 计划文件路径
        self.plan_file = os.path.join(self.workspace, "plan.md")

        # 工作空间缓存（用于动态上下文）
        self._workspace_cache = None

        # API密钥（用于创建SubAgent）
        self.api_key = api_key or os.getenv("MOONSHOT_API_KEY")

    def _get_system_prompt(self) -> str:
        """获取系统提示词（根据 mode 返回不同提示）"""
        if self.mode == "tactical":
            return self._get_tactical_prompt()
        else:
            return self._get_strategic_prompt()

    def _get_strategic_prompt(self) -> str:
        """战略层 System Prompt（引导高层决策）"""
        return """你是一个具有战略规划能力的智能助手（Strategic Agent）。

## 战略思维模式

### 初始化阶段（首次接收任务）
1. 调用 ExploreWorkspace 了解工作空间资源
2. 分析任务复杂度：
   - 简单任务（1-2步）：直接使用 ReadFile/WriteFile/RunCommand 执行
   - 中等任务（3-7步）：使用 CreatePlan 创建高层计划
   - 复杂任务（8+步）：分阶段规划，逐步推进

### 执行决策（何时委派给战术层）
对于每个步骤，判断：
- **直接执行**：简单文件操作（读取配置、写入结果文件）
- **委派战术层**：使用 DelegateToTactical 处理复杂执行
  - 数据处理（pandas/numpy 操作）
  - 统计计算和分析
  - 可视化生成
  - 模型训练
  - 目标：3-7 步完成的中等粒度任务

### 用户交互（何时请求确认）
遇到以下情况必须调用 GetUserConfirmation：
- 数据处理策略不明确（如何处理缺失值？删除还是填充？）
- 有多种技术方案选择（使用哪个模型/库？）
- 需要删除数据或做破坏性操作
- 任务需求存在歧义

### 结果整合
战术任务完成后：
1. 使用 UpdatePlan 记录结果摘要（仅高层结果，不要执行细节）
2. 分析是否有问题需要调整策略
3. 决定下一步行动

### 上下文管理原则
- 只保存：用户需求、计划、执行结果摘要、当前问题
- 不保存：战术层执行细节、中间工具调用、完整日志
- 每轮通过 <workspace_context> 和 <current_plan> 获取最新状态

## 可用工具
- **ExploreWorkspace**: 探索工作空间（初始化时调用）
- **CreatePlan/UpdatePlan/ReadPlan**: 计划管理
- **DelegateToTactical**: 委派战术任务（核心工具！）
- **GetUserConfirmation**: 请求用户输入
- **ReadFile/WriteFile/RunCommand**: 直接执行简单操作

## 工作原则
- 主动使用工具，不要只说要做什么
- 遇到复杂执行任务时委派给战术层
- 保持计划文件更新，让用户看到进度
- 遇到歧义时请求用户确认"""

    def _get_tactical_prompt(self) -> str:
        """战术层 System Prompt（引导专注执行）"""
        return """你是战术执行 Agent（Tactical Agent），专注完成具体任务。

## 执行原则
1. **专注**：仅处理当前任务，忽略无关工作
2. **准确**：优先正确性，3-7 步完成目标
3. **诚实**：无法完成时立即报告原因和建议
4. **简洁**：返回结果，不要解释详细过程

## 禁止行为
- 不要创建高层计划（你的任务已被战略层定义）
- 不要请求用户确认（报告问题即可）
- 不要访问其他任务的结果
- 不要偏离任务目标做额外工作

## 可用工具
仅限：ReadFile, WriteFile, RunCommand

## 失败报告格式
如无法完成，在最后一条消息中说明：
```
STATUS: FAILED
REASON: [具体原因，如"缺少 pandas 包"或"数据格式错误"]
SUGGESTION: [建议，如"pip install pandas"或"检查数据文件格式"]
```

## 成功报告格式
完成后说明：
```
STATUS: SUCCESS
RESULT: [结果摘要，如"已生成 summary.json，包含 10 列统计信息"]
OUTPUT_FILES: [输出文件列表]
```"""

    # ============================================
    # 动态上下文构建（新增）
    # ============================================

    def _build_dynamic_context(self) -> List[Dict]:
        """
        动态构建上下文（借鉴 claude_agent 架构）

        Returns:
            完整的消息列表（包含动态注入的信息）
        """
        full_messages = []

        # 战略模式：注入工作空间快照
        if self.mode == "strategic":
            workspace_snapshot = self._get_workspace_snapshot()
            if workspace_snapshot:
                full_messages.append({
                    "role": "user",
                    "content": f"<workspace_context>\n{workspace_snapshot}\n</workspace_context>"
                })

        # 添加压缩后的历史消息
        full_messages.extend(self._compress_history())

        # 战略模式：注入计划摘要
        if self.mode == "strategic":
            plan_summary = self._get_plan_summary()
            if plan_summary:
                full_messages.append({
                    "role": "user",
                    "content": f"<current_plan>\n{plan_summary}\n</current_plan>"
                })

        return full_messages

    def _get_workspace_snapshot(self) -> str:
        """
        获取工作空间快照（缓存机制：仅第一次扫描）

        Returns:
            工作空间状态描述
        """
        if self._workspace_cache is None:
            self._workspace_cache = self._scan_workspace()

        if not self._workspace_cache:
            return ""

        return f"""当前工作空间状态：
- 目录：{self.workspace}
- 数据文件：{', '.join(self._workspace_cache.get('data_files', [])) or '无'}
- 脚本文件：{', '.join(self._workspace_cache.get('scripts', [])) or '无'}
- 输出文件：{', '.join(self._workspace_cache.get('outputs', [])) or '无'}
- 总文件数：{self._workspace_cache.get('total_files', 0)}"""

    def _scan_workspace(self) -> Dict:
        """
        扫描工作空间目录

        Returns:
            包含文件分类信息的字典
        """
        result = {
            "data_files": [],
            "scripts": [],
            "outputs": [],
            "total_files": 0
        }

        try:
            for root, dirs, files in os.walk(self.workspace):
                # 跳过隐藏目录和 __pycache__
                dirs[:] = [d for d in dirs if not d.startswith('.') and d != '__pycache__']

                for f in files:
                    if f.startswith('.'):
                        continue

                    result["total_files"] += 1
                    rel_path = os.path.relpath(os.path.join(root, f), self.workspace)

                    if f.endswith(('.csv', '.xlsx', '.json', '.txt')):
                        result["data_files"].append(rel_path)
                    elif f.endswith('.py'):
                        result["scripts"].append(rel_path)
                    elif f.endswith(('.png', '.jpg', '.pdf', '.html')):
                        result["outputs"].append(rel_path)
        except Exception as e:
            print(f"警告: 扫描工作空间失败: {e}")

        return result

    def _get_plan_summary(self) -> str:
        """
        从 plan.md 提取当前进度摘要

        Returns:
            计划摘要（仅当前阶段和问题）
        """
        if not os.path.exists(self.plan_file):
            return ""

        try:
            with open(self.plan_file, 'r', encoding='utf-8') as f:
                content = f.read()

            # 简化版：返回完整内容（未来可优化为仅提取关键部分）
            # TODO: 可以进一步优化，仅提取当前进行中的阶段和 Active Issues
            if len(content) > 1000:
                return content[:1000] + "\n...(计划已截断)"
            return content
        except Exception as e:
            return f"读取计划失败: {e}"

    def _compress_history(self) -> List[Dict]:
        """
        压缩历史消息（滑动窗口策略）

        Returns:
            压缩后的消息列表
        """
        # 如果消息不多，直接返回
        if len(self.messages) <= 12:
            return self.messages

        # 保留最近 10 条消息，旧消息汇总
        compressed = []

        # 保留第一条用户消息（初始任务）
        if self.messages and self.messages[0]["role"] == "user":
            compressed.append(self.messages[0])

        # 中间历史汇总（简化版：直接省略）
        # TODO: 未来可以使用 LLM 汇总中间历史
        if len(self.messages) > 12:
            compressed.append({
                "role": "user",
                "content": "<previous_work>\n已省略前期执行细节。最近 10 轮对话如下：\n</previous_work>"
            })

        # 保留最近 10 条
        compressed.extend(self.messages[-10:])

        return compressed

    def run(self, user_input: str, max_turns: int = 30) -> str:
        """
        主运行循环（响应式架构）

        Args:
            user_input: 用户输入
            max_turns: 最大轮次

        Returns:
            最终输出
        """
        print(f"\n{'='*60}")
        print(f"用户: {user_input}")
        print(f"{'='*60}\n")

        # 仅添加用户消息到历史（系统提示通过动态上下文注入）
        self.messages.append({
            "role": "user",
            "content": user_input
        })

        # 主循环（响应式）
        for turn in range(max_turns):
            print(f"\n--- 回合 {turn + 1} ---")

            # 调用 Kimi API（使用动态上下文）
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
        """调用 Kimi API（使用动态上下文和 system prompt）"""
        try:
            # 构建动态上下文
            full_messages = self._build_dynamic_context()

            # 调用 API（注入 system prompt）
            response = self.client.chat.completions.create(
                model=self.model,
                messages=full_messages,
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
        """定义可用工具（根据 mode 过滤）"""
        all_tools = [
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
            },
            # ===== 战略层新增工具 =====
            {
                "type": "function",
                "function": {
                    "name": "ExploreWorkspace",
                    "description": "探索工作空间目录结构，了解可用资源。初始化时调用。",
                    "parameters": {
                        "type": "object",
                        "properties": {},
                        "required": []
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "DelegateToTactical",
                    "description": "将具体执行任务委派给战术 Agent（上下文隔离）。用于：数据处理、统计计算、可视化、模型训练等需要 3-7 步的中等粒度任务。",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "task_id": {
                                "type": "string",
                                "description": "任务唯一标识（如 tactical_001）"
                            },
                            "objective": {
                                "type": "string",
                                "description": "清晰的任务目标（一句话描述）"
                            },
                            "context": {
                                "type": "object",
                                "properties": {
                                    "files": {
                                        "type": "array",
                                        "items": {"type": "string"},
                                        "description": "输入文件列表"
                                    },
                                    "required_output": {
                                        "type": "string",
                                        "description": "期望输出"
                                    },
                                    "constraints": {
                                        "type": "array",
                                        "items": {"type": "string"},
                                        "description": "约束条件（如超时、数据要求）"
                                    },
                                    "relevant_info": {
                                        "type": "string",
                                        "description": "相关背景信息"
                                    }
                                },
                                "description": "任务上下文（压缩的必要信息）"
                            },
                            "success_criteria": {
                                "type": "string",
                                "description": "如何验证任务完成"
                            }
                        },
                        "required": ["task_id", "objective", "context", "success_criteria"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "GetUserConfirmation",
                    "description": "请求用户确认或输入。Agent 会暂停等待用户通过 input() 提供答案。用于重大决策点。",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "question": {
                                "type": "string",
                                "description": "问题描述"
                            },
                            "options": {
                                "type": "array",
                                "items": {"type": "string"},
                                "description": "选项列表（可选）"
                            },
                            "reason": {
                                "type": "string",
                                "description": "为什么需要确认"
                            }
                        },
                        "required": ["question"]
                    }
                }
            }
        ]

        # 根据 mode 过滤工具
        if self.mode == "tactical":
            # 战术层：仅保留基础执行工具
            tactical_tool_names = {"ReadFile", "WriteFile", "RunCommand"}
            return [tool for tool in all_tools
                    if tool["function"]["name"] in tactical_tool_names]
        else:
            # 战略层：所有工具
            return all_tools

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
            # 新增：战略层工具
            elif tool_name == "ExploreWorkspace":
                return self._tool_explore_workspace()
            elif tool_name == "DelegateToTactical":
                return self._tool_delegate_to_tactical(tool_args)
            elif tool_name == "GetUserConfirmation":
                return self._tool_get_user_confirmation(tool_args)
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

    # ===== 新增：战略层工具实现 =====

    def _tool_explore_workspace(self) -> str:
        """探索工作空间目录（调用缓存机制）"""
        # 重新扫描以获取最新状态
        self._workspace_cache = self._scan_workspace()

        result = self._workspace_cache
        return f"""✓ 工作空间探索完成

数据文件 ({len(result['data_files'])}):
{chr(10).join('- ' + f for f in result['data_files'][:10])}
{'...(省略 ' + str(len(result['data_files']) - 10) + ' 个)' if len(result['data_files']) > 10 else ''}

脚本文件 ({len(result['scripts'])}):
{chr(10).join('- ' + f for f in result['scripts'][:5])}
{'...(省略 ' + str(len(result['scripts']) - 5) + ' 个)' if len(result['scripts']) > 5 else ''}

输出文件 ({len(result['outputs'])}):
{chr(10).join('- ' + f for f in result['outputs'][:5])}
{'...(省略 ' + str(len(result['outputs']) - 5) + ' 个)' if len(result['outputs']) > 5 else ''}

总文件数: {result['total_files']}"""

    def _tool_delegate_to_tactical(self, params: Dict) -> str:
        """委派任务给战术 SubAgent（上下文隔离）"""
        task_id = params.get("task_id", "tactical_task")
        objective = params["objective"]
        context = params.get("context", {})
        success_criteria = params.get("success_criteria", "任务完成")

        print(f"\n{'='*60}")
        print(f"🎯 启动战术 Agent: {task_id}")
        print(f"   目标: {objective}")
        print(f"{'='*60}\n")

        # 创建战术 Agent（新实例，上下文隔离）
        tactical = PlanKimiAgent(api_key=self.api_key, mode="tactical")

        # 压缩任务描述（<500 tokens）
        tactical_prompt = f"""执行战术任务：

目标：{objective}

成功标准：{success_criteria}

上下文信息：
{json.dumps(context, ensure_ascii=False, indent=2)}

要求：
- 专注此任务，3-7 步完成
- 无法完成时诚实报告原因并建议替代方案
- 只返回结果，不要解释详细过程
"""

        # 执行战术任务（限制 10 轮）
        try:
            result = tactical.run(tactical_prompt, max_turns=10)

            print(f"\n{'='*60}")
            print(f"✓ 战术任务完成: {task_id}")
            print(f"{'='*60}\n")

            # 返回压缩的结果摘要
            return f"""战术任务执行完成

任务ID: {task_id}
状态: 成功
结果摘要:
{result[:500] if len(result) > 500 else result}
"""
        except Exception as e:
            return f"""战术任务执行失败

任务ID: {task_id}
状态: 失败
错误: {str(e)}
建议: 检查任务定义和上下文是否完整
"""

    def _tool_get_user_confirmation(self, params: Dict) -> str:
        """请求用户确认/输入（暂停等待）"""
        question = params["question"]
        options = params.get("options", [])
        reason = params.get("reason", "")

        print(f"\n{'='*60}")
        print(f"需要您的确认")
        print(f"{'='*60}")
        print(f"\n问题：{question}")
        if reason:
            print(f"原因：{reason}\n")

        if options:
            print("选项：")
            for i, opt in enumerate(options, 1):
                print(f"{i}. {opt}")
            print()

        # 等待用户输入
        try:
            answer = input("请输入您的选择: ").strip()
            return f"用户选择：{answer}"
        except (EOFError, KeyboardInterrupt):
            return "用户取消输入"

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
