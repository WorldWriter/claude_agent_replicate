"""严格遵循伪代码的Agent实现 - Plan-Execute-Reflect"""
import json
import logging
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
from llm_client import LLMClient
from tools import TOOLS

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


@dataclass
class Step:
    """执行步骤"""
    type: str  # "tool", "think", "subagent"
    reasoning: str
    # for tool
    tool: Optional[str] = None
    args: Optional[Dict] = None
    # for subagent
    subagent_task: Optional[str] = None
    # for think
    thought: Optional[str] = None


@dataclass
class Plan:
    """执行计划"""
    steps: List[Step]
    summary: str


class SimpleAgent:
    """基于Plan-Execute-Reflect循环的Agent"""

    def __init__(self, llm_client: LLMClient, original_task: str = "", max_iterations=5, parent=None):
        self.llm = llm_client
        self.original_task = original_task  # 保存原始任务
        self.max_iterations = max_iterations
        self.context = []  # Agent执行历史（记录用）
        self.llm_messages = []  # LLM对话历史（API格式）
        self.data_cache = {}  # 数据缓存
        self.parent = parent  # 父Agent（如果是SubAgent）
        self.completed = False
        self.step_counter = 0

    def plan(self, current_context: str) -> Plan:
        """生成多步执行计划"""
        system_prompt = f"""我们在进行数据分析任务, 帮我生成一个逐步执行的任务计划.

**原始任务**：
{self.original_task}

**当前上下文**：
{current_context}

**可用工具**：
- read_csv_file(file_path, nrows): 读取CSV文件
- analyze_data(code, df): 执行pandas代码，df从缓存获取
- execute_python(code): 执行Python代码
- visualize_data(df, chart_type, x_col, y_col, title, output_path): 生成图表

**任务**：
生成一个多步骤的执行计划。每步可以是三种类型之一：

1. **tool**: 使用工具
2. **think**: 根据历史context 思考推理
3. **subagent**: 创建子Agent处理复杂子任务

JSON格式示例：
{{
  "summary": "数据分析计划",
  "steps": [
    {{"type": "tool", "tool": "read_csv_file", "args": {{"file_path": "data/full_gcp_data.csv", "nrows": 1000}}, "reasoning": "读取数据了解结构"}},
    {{"type": "tool", "tool": "analyze_data", "args": {{"code": "result = df.describe()", "df": "cached"}}, "reasoning": "统计分析"}},
    {{"type": "think", "thought": "分析当前数据特征", "reasoning": "理解数据分布"}},
    {{"type": "tool", "tool": "visualize_data", "args": {{"df": "cached", "chart_type": "hist", "y_col": "cost", "title": "成本分布", "output_path": "results/cost_dist.png"}}, "reasoning": "可视化成本分布"}}
  ]
}}
**重要**：
- 只返回一个有效的JSON对象，不要添加任何解释文字。
- 确保JSON格式正确，所有字符串用双引号
- 不要在JSON外添加任何文字说明

**目标**：
- 首先分析下用户的心理和核心诉求, 我们的语境是在互联网的成本分析, 我们希望尽量的减少成本浪费, 获取更多的业务收益
- 这个计划要针对用清晰,有效的.
- 后一步依赖前一步.
- 每一步的任务复杂度应该有个评级, 复杂的就调用sub-agent
"""

        messages = [{"role": "user", "content": system_prompt}]
        response = self.llm.call(messages, temperature=0.7, max_tokens=3000)
        logger.info(f"\n{'='*60}\n[PLAN] LLM生成的计划\n{'='*60}\n{response}\n{'='*60}")

        # 解析JSON - 增强容错性
        try:
            import re

            # 1. 清理响应文本
            cleaned = response.strip()
            # 移除markdown代码块
            cleaned = re.sub(r'```json\s*', '', cleaned)
            cleaned = re.sub(r'```\s*', '', cleaned)
            # 移除前后可能的解释性文本，只保留JSON
            json_match = re.search(r'\{[^{}]*"steps"[^{}]*\[.*?\]\s*\}', cleaned, re.DOTALL)

            if not json_match:
                # 尝试更宽松的匹配
                json_match = re.search(r'\{.*?\}', cleaned, re.DOTALL)

            if json_match:
                json_str = json_match.group()
                logger.info(f"[DEBUG] 提取的JSON字符串:\n{json_str[:500]}...")
                plan_dict = json.loads(json_str)
            else:
                logger.error(f"[PLAN ERROR] 无法提取JSON，原始响应:\n{response[:500]}...")
                raise ValueError("No JSON found in response")

            # 2. 解析steps
            steps = []
            for idx, step_data in enumerate(plan_dict.get("steps", [])):
                try:
                    step = Step(
                        type=step_data.get("type", "think"),
                        reasoning=step_data.get("reasoning", "未提供原因"),
                        tool=step_data.get("tool"),
                        args=step_data.get("args", {}),
                        subagent_task=step_data.get("subagent_task"),
                        thought=step_data.get("thought")
                    )
                    steps.append(step)
                except Exception as step_error:
                    logger.warning(f"[PLAN WARN] 解析步骤{idx+1}失败: {step_error}，跳过该步骤")
                    continue

            if not steps:
                raise ValueError("No valid steps parsed")

            return Plan(steps=steps, summary=plan_dict.get("summary", "执行计划"))

        except json.JSONDecodeError as e:
            logger.error(f"[PLAN ERROR] JSON解析失败: {e}")
            logger.error(f"[PLAN ERROR] 原始响应:\n{response}")
            # 返回简化计划
            return Plan(
                steps=[
                    Step(type="tool", tool="read_csv_file",
                         args={"file_path": "data/full_gcp_data.csv", "nrows": 1000},
                         reasoning="JSON解析失败，使用默认读取计划")
                ],
                summary="默认计划（解析失败回退）"
            )
        except Exception as e:
            logger.error(f"[PLAN ERROR] 解析计划失败: {e}")
            logger.error(f"[PLAN ERROR] 原始响应:\n{response}")
            return Plan(
                steps=[
                    Step(type="tool", tool="read_csv_file",
                         args={"file_path": "data/full_gcp_data.csv", "nrows": 1000},
                         reasoning="解析失败，使用默认读取计划")
                ],
                summary="默认计划（解析失败回退）"
            )

    def use_tool(self, tool_name: str, args: Dict) -> Any:
        """使用工具"""
        # 处理特殊参数
        if "df" in args and args["df"] == "cached":
            args["df"] = self.data_cache.get("df")

        result = TOOLS[tool_name](**args)

        # 缓存DataFrame
        if tool_name == "read_csv_file" and result.get("success"):
            import pandas as pd
            self.data_cache["df"] = pd.read_csv(args["file_path"])

        return result

    def think(self, thought: str) -> Dict:
        """纯思考推理"""
        prompt = f"请对以下内容进行思考和分析：\n{thought}\n\n基于当前上下文，给出你的分析结果。"
        messages = self.llm_messages + [{"role": "user", "content": prompt}]
        response = self.llm.call(messages, temperature=0.7, max_tokens=1000)

        # 更新LLM对话历史
        self.llm_messages.append({"role": "user", "content": prompt})
        self.llm_messages.append({"role": "assistant", "content": response})

        return {"type": "thought", "content": response}

    def spawn_subagent(self, task: str) -> Any:
        """创建子Agent处理复杂子任务"""
        logger.info(f"\n[SPAWN SUBAGENT] 创建子Agent处理任务: {task}")
        subagent = SimpleAgent(
            llm_client=self.llm,
            original_task=task,
            max_iterations=3,  # 子Agent迭代次数较少
            parent=self
        )
        result = subagent.run(task)
        return result

    def execute_step(self, step: Step, step_num: int, total_steps: int) -> Any:
        """执行单个步骤"""
        logger.info(f"\n{'='*60}\n[STEP {step_num}/{total_steps}] 类型: {step.type}\n原因: {step.reasoning}\n{'='*60}")

        if step.type == "tool":
            logger.info(f"[EXECUTE TOOL] {step.tool}({step.args})")
            result = self.use_tool(step.tool, step.args)
            logger.info(f"[RESULT] {result}")
            return result

        elif step.type == "think":
            logger.info(f"[EXECUTE THINK] {step.thought}")
            result = self.think(step.thought)
            logger.info(f"[RESULT] {result}")
            return result

        elif step.type == "subagent":
            logger.info(f"[EXECUTE SUBAGENT] 任务: {step.subagent_task}")
            result = self.spawn_subagent(step.subagent_task)
            logger.info(f"[SUBAGENT RESULT] {result}")
            return result

        else:
            logger.error(f"[ERROR] 未知步骤类型: {step.type}")
            return {"error": f"未知步骤类型: {step.type}"}

    def reflect(self, step_result: Any, step_num: int, total_steps: int, is_macro: bool = False) -> Dict:
        """双层反思机制"""
        if is_macro:
            # 宏观反思：对比原始任务
            prompt = f"""**宏观反思**

**原始任务**：
{self.original_task}

**当前已执行步骤**：{step_num}/{total_steps}

**最新结果**：
{json.dumps(step_result, ensure_ascii=False)[:500]}

**反思问题**：
1. 当前进展是否符合原始任务要求？
2. 是否偏离了用户的核心需求？
3. 已完成的部分是否满足预期质量？
4. 接下来应该继续执行还是调整方向？

请给出宏观评估，只返回JSON：
{{
  "on_track": true/false,
  "quality_met": true/false,
  "needs_adjustment": true/false,
  "suggestion": "建议"
}}
"""
        else:
            # 微观反思：评估当前步骤
            prompt = f"""**微观反思**

**当前步骤结果**：
{json.dumps(step_result, ensure_ascii=False)[:500]}

**反思问题**：
1. 这一步是否成功执行？
2. 输出是否符合预期？
3. 是否有错误或异常？
4. 下一步是否可以继续？

请给出微观评估，只返回JSON：
{{
  "success": true/false,
  "meets_expectation": true/false,
  "has_error": true/false,
  "can_continue": true/false,
  "issue": "问题描述（如果有）"
}}
"""

        # 不使用对话历史，独立评估
        messages = [{"role": "user", "content": prompt}]
        response = self.llm.call(messages, temperature=0.3, max_tokens=800)

        reflection_type = "MACRO-REFLECT" if is_macro else "MICRO-REFLECT"
        logger.info(f"\n[{reflection_type}]\n{response}\n")

        try:
            import re
            cleaned = response.strip().replace("```json", "").replace("```", "").strip()
            json_match = re.search(r'\{.*\}', cleaned, re.DOTALL)
            if json_match:
                reflection = json.loads(json_match.group())
            else:
                reflection = json.loads(cleaned)
            return reflection
        except:
            return {"parsed": False, "raw": response}

    def run(self, task: str) -> Dict:
        """主循环 - 严格遵循伪代码"""
        logger.info(f"\n{'#'*60}\n# 开始任务: {task}\n{'#'*60}")

        iteration = 0
        while not self.completed and iteration < self.max_iterations:
            iteration += 1
            logger.info(f"\n{'='*60}\n=== 第 {iteration}/{self.max_iterations} 轮迭代 ===\n{'='*60}")

            # 生成计划
            current_context = f"当前进展：已执行{iteration-1}轮\n上下文：{json.dumps(self.context[-3:], ensure_ascii=False)}"
            plan = self.plan(current_context)

            # 执行计划中的每一步
            for idx, step in enumerate(plan.steps, 1):
                self.step_counter += 1
                result = self.execute_step(step, idx, len(plan.steps))

                # 微观反思
                # micro_reflection = self.reflect(result, idx, len(plan.steps), is_macro=False)

                # 添加到上下文
                self.context.append({
                    "step": self.step_counter,
                    "type": step.type,
                    "result": result,
                    # "reflection": micro_reflection
                })

                # 如果微观反思发现问题，可以提前中断
                # if not micro_reflection.get("can_continue", True):
                #     logger.warning("[WARNING] 微观反思建议中断执行")
                #     break

            # 宏观反思（阶段性）
            macro_reflection = self.reflect(
                self.context[-1]["result"],
                len(plan.steps),
                len(plan.steps),
                is_macro=True
            )

            # 判断是否完成
            if macro_reflection.get("quality_met", False) and not macro_reflection.get("needs_adjustment", True):
                logger.info("\n[COMPLETE] 宏观反思确认任务完成")
                self.completed = True

        logger.info(f"\n{'#'*60}\n# 任务结束: {'完成' if self.completed else '达到最大迭代次数'}\n{'#'*60}")
        return {
            "completed": self.completed,
            "iterations": iteration,
            "context": self.context
        }
