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


class MinimalKimiAgent:
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

        # 模型配置
        self.model = os.getenv("LLM_MODEL", "kimi-k2-turbo-preview")

        # 工作目录
        self.workspace = "agent_workspace"
        os.makedirs(self.workspace, exist_ok=True)

    def run(self, user_input: str, max_turns: int = 10) -> str:
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
                    "description": "读取文件内容",
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
            if tool_name == "ReadFile":
                return self._tool_read_file(tool_args["path"])
            elif tool_name == "WriteFile":
                return self._tool_write_file(tool_args["path"], tool_args["content"])
            elif tool_name == "RunCommand":
                return self._tool_run_command(tool_args["command"])
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
        try:
            with open(path, 'r', encoding='utf-8') as f:
                content = f.read()
            return f"成功读取文件 {path} ({len(content)} 字符)\n\n{content}"
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
            # 执行命令，设置60秒超时
            result = subprocess.run(
                command,
                shell=True,
                capture_output=True,
                text=True,
                timeout=60,  # 60秒超时
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

            for i, msg in enumerate(self.messages, 1):
                role = msg["role"]
                content = msg.get("content", "")

                if role == "user":
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

            # 写入json文件（原始消息）
            json_file = log_file.replace('.txt', '.json')
            with open(json_file, 'w', encoding='utf-8') as f:
                json.dump(self.messages, f, ensure_ascii=False, indent=2, default=str)

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

    agent = MinimalKimiAgent()
    result = agent.run("创建一个 test.txt 文件，内容是 'Hello Kimi Agent!'")
    print(f"\n最终结果: {result}")


def example_multi_step():
    """示例2: 多步骤任务"""
    print("\n" + "="*60)
    print("示例: 多步骤任务")
    print("="*60)

    agent = MinimalKimiAgent()
    result = agent.run("""
    请完成以下任务:
    1. 找下当前的工作目录下有什么? 找到data/full_gcp_data.csv
    2. 写个python 脚本,并运行(当前已经有相关脚本, 可直接运行). 该脚本的功能是读取data/full_gcp_data.csv 文件, 并打印出文件的行数和列数.
    3. 以及该文件的列头是什么, 每列的基本的情况是什么? 
    4. 然后根据上面的结果, 统计下 2022年1月和2月的各个指标值的增长情况;
    5. 根据以上的指标的增长, 给出一个可行决策的建议, 用以节省成本
    """)
    print(f"\n最终结果: {result}")



if __name__ == "__main__":
    # 检查 API Key
    load_dotenv()
    if not os.getenv("MOONSHOT_API_KEY"):
        print("❌ 请在 .env 文件中设置 MOONSHOT_API_KEY")
        exit(1)

    # 运行示例
    example_multi_step()
