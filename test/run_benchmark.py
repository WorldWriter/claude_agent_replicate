"""
DA-Code Benchmark 测试脚本（支持 Minimal & Dynamic Agent）
支持增量测试：自动发现所有任务，跳过已测试任务

测试模式:
- quick: 测试 5 个快速验证任务（每类任务各1个）
- baseline: 测试 baseline 59 个任务（git clone 时包含的 gold 任务）
- all: 测试所有有 gold 答案的任务（需要先下载完整数据集）
"""

import os
import sys
import json
import shutil
import glob
import argparse
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime

# 添加父目录到路径以导入 agent
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from dynamic_plan_agent import DynamicPlanAgent
from minimal_kimi_agent import MinimalKimiAgent

# 路径配置 (相对于项目根目录)
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DA_CODE_DIR = os.path.join(PROJECT_ROOT, "agent_workspace/da-code/da_code")
SOURCE_DIR = os.path.join(DA_CODE_DIR, "source")
GOLD_DIR = os.path.join(DA_CODE_DIR, "gold")
CONFIG_FILE = os.path.join(DA_CODE_DIR, "configs/task/all.jsonl")
WORKSPACE_ROOT = os.path.join(PROJECT_ROOT, "agent_workspace")
LOGS_DIR = os.path.join(PROJECT_ROOT, "logs")
DATASET_TASKS_FILE = os.path.join(os.path.dirname(__file__), "dataset_tasks.json")

AGENT_CONFIGS = {
    "dynamic": {
        "name": "Dynamic Plan Agent (Stage 2)",
        "cls": DynamicPlanAgent,
        "default_max_turns": 20,
        "workspace_root": os.path.join(PROJECT_ROOT, "agent_workspace/output_dir_dynamic"),
        "workspace_pattern": "{task_id}",
        "log_prefix": "dacode_dynamic",
        "eval_output_dir": "output_dir_dynamic",
    },
    "minimal": {
        "name": "MinimalKimiAgent (Stage 1)",
        "cls": MinimalKimiAgent,
        "default_max_turns": 15,
        "workspace_root": WORKSPACE_ROOT,
        "workspace_pattern": "dacode_{task_id}",
        "log_prefix": "dacode_test",
        "eval_output_dir": None,
    },
}


def load_baseline_tasks(mode: str = 'baseline') -> list:
    """
    加载任务列表

    Args:
        mode: 'baseline' (59个任务) 或 'quick' (5个任务)
    """
    if not os.path.exists(DATASET_TASKS_FILE):
        print(f"警告: 数据集配置文件不存在: {DATASET_TASKS_FILE}")
        return []

    with open(DATASET_TASKS_FILE, 'r', encoding='utf-8') as f:
        config = json.load(f)

        if mode == 'quick':
            return config['datasets']['quick']['task_ids']
        else:  # baseline
            return config['datasets']['test']['task_ids']


def discover_all_tasks() -> list:
    """从 gold 目录发现所有有标准答案的任务"""
    if not os.path.exists(GOLD_DIR):
        print(f"警告: Gold 目录不存在: {GOLD_DIR}")
        return []

    tasks = [d for d in os.listdir(GOLD_DIR) if os.path.isdir(os.path.join(GOLD_DIR, d))]
    tasks.sort()  # 按字母顺序排序
    return tasks


def load_previous_results(log_prefix: str) -> dict:
    """加载之前的测试结果，返回 {task_id: result} 字典"""
    previous_results = {}

    if not os.path.exists(LOGS_DIR):
        return previous_results

    pattern = os.path.join(LOGS_DIR, f"{log_prefix}_*.json")
    result_files = [
        f for f in glob.glob(pattern)
        if "_merged_" not in os.path.basename(f)
    ]

    if not result_files:
        return previous_results

    # 加载所有结果文件
    for result_file in result_files:
        try:
            with open(result_file, 'r', encoding='utf-8') as f:
                results = json.load(f)
                for result in results:
                    task_id = result.get('task_id')
                    if task_id:
                        # 如果同一个任务有多次测试，保留最新的
                        previous_results[task_id] = result
        except Exception as e:
            print(f"警告: 加载结果文件失败 {result_file}: {e}")

    return previous_results


def get_tasks_to_test(all_tasks: list, previous_results: dict) -> list:
    """获取需要测试的任务列表（排除已测试的）"""
    tested_tasks = set(previous_results.keys())
    tasks_to_test = [task for task in all_tasks if task not in tested_tasks]
    return tasks_to_test


def load_task_config(task_id: str) -> dict:
    """加载任务配置"""
    with open(CONFIG_FILE, 'r') as f:
        for line in f:
            task = json.loads(line)
            if task['id'] == task_id:
                return task
    return None


def get_agent_config(agent_name: str) -> dict:
    if agent_name not in AGENT_CONFIGS:
        raise ValueError(f"未知 agent: {agent_name}")
    return AGENT_CONFIGS[agent_name]


def build_workspace_path(agent_name: str, task_id: str) -> str:
    cfg = get_agent_config(agent_name)
    workspace_name = cfg["workspace_pattern"].format(task_id=task_id)
    return os.path.join(cfg["workspace_root"], workspace_name)


def prepare_workspace(task_id: str, agent_name: str) -> str:
    """准备工作目录，复制数据文件到输出目录"""
    source_path = os.path.join(SOURCE_DIR, task_id)
    task_workspace = build_workspace_path(agent_name, task_id)

    # 清理并创建工作目录
    if os.path.exists(task_workspace):
        shutil.rmtree(task_workspace)
    os.makedirs(os.path.dirname(task_workspace), exist_ok=True)
    shutil.copytree(source_path, task_workspace)

    return task_workspace


def build_prompt(task_config: dict, task_workspace: str) -> str:
    """构建 Agent 提示词"""
    task_id = task_config['id']
    instruction = task_config['instruction']
    task_type = task_config['type']

    # 读取 README 获取数据描述
    readme_path = os.path.join(task_workspace, "README.md")
    readme_content = ""
    if os.path.exists(readme_path):
        with open(readme_path, 'r') as f:
            readme_content = f.read()

    # 列出工作目录中的文件
    files = os.listdir(task_workspace)
    files_str = "\n".join([f"- {f}" for f in files])

    # 检测 sample 文件并生成格式提示
    sample_files = [f for f in files if f.startswith('sample_')]
    config_files = [f for f in files if f.endswith(('.yaml', '.yml'))]

    format_hint = ""
    if sample_files:
        format_hint += f"""
## ⚠️ 输出格式要求 (重要!)
工作目录中存在样本文件: {', '.join(sample_files)}
你的输出必须**完全匹配**样本文件的格式:
- 相同的列名和列顺序
- 相同的数值精度(小数位数)
- 只包含样本中出现的列，不要添加额外列
- 先读取样本文件了解格式，再生成结果
"""

    if config_files:
        format_hint += f"""
## 配置文件
工作目录中存在配置文件: {', '.join(config_files)}
对于可视化任务，必须读取配置文件获取: figsize、颜色、字体等参数
"""

    # 任务类型特定提示
    type_hints = {
        "data-insight": """
## 数据洞察任务注意事项
- CSV 数值可能带逗号千分位符，使用 `pd.read_csv(file, thousands=',')`
- 结果要做合理性检查（如人口密度最高应该是小国如Monaco 38000+，不是Palestinian 847）
- 如果发现结果不合理，检查数据解析是否正确
- 输出格式严格按照 sample 文件
""",
        "data-manipulation": """
## 数据处理任务注意事项
- 金融收益计算要仔细理解题意：等权重、市值加权、原始权重的区别
- 累积收益一般从第一个交易日开始计算，不是从0开始
- 注意检查计算结果的合理性（日收益率通常在 -10%~+10%）
- 投资组合权重之和应为 1.0 (100%)
""",
        "statistical-analysis": """
## 统计分析任务注意事项
- p-value 保留原始精度，不要 round 到 0
- 如果 p-value 很小 (< 0.0001)，使用科学记数法: `f'{p:.2e}'`
- 或保留足够位数: `f'{p:.15f}'`
- p-value 为 0.0 几乎总是错误的！检查精度处理
""",
        "ml-regression": """
## 机器学习任务注意事项
- 输出列名必须与 README/sample 完全一致，包括空格和括号
- 不要简化列名，直接复制原始格式
- 例如: "Biogas Generation Estimate (cu-ft/day)" 不能改成 "biogas_generation_estimate"
""",
        "ml-classification": """
## 分类任务注意事项
- 输出列名必须与 README/sample 完全一致
- 分类结果格式要与 sample 匹配（整数/字符串/布尔值）
""",
        "plot-bindplot": """
## 可视化任务注意事项
- 必须读取 .yaml 配置文件获取绑定参数
- 图表尺寸、颜色、字体等必须与配置一致
""",
        "plot-bindbar": """
## 可视化任务注意事项
- 必须读取 .yaml 配置文件获取绑定参数
- 图表尺寸、颜色、字体等必须与配置一致
""",
    }

    # 获取任务类型特定提示（支持部分匹配）
    type_specific_hint = ""
    for type_key, hint in type_hints.items():
        if task_type.startswith(type_key) or type_key in task_type:
            type_specific_hint = hint
            break

    # 如果没有精确匹配，尝试更宽泛的类别
    if not type_specific_hint:
        if "insight" in task_type or "di-" in task_id:
            type_specific_hint = type_hints["data-insight"]
        elif "manipulation" in task_type or "dm-" in task_id:
            type_specific_hint = type_hints["data-manipulation"]
        elif "statistical" in task_type or "sa-" in task_id:
            type_specific_hint = type_hints["statistical-analysis"]
        elif "regression" in task_type or "ml-regression" in task_id:
            type_specific_hint = type_hints["ml-regression"]
        elif "classification" in task_type or "ml-classification" in task_id:
            type_specific_hint = type_hints["ml-classification"]
        elif "plot" in task_type:
            type_specific_hint = type_hints.get("plot-bindplot", "")

    prompt = f"""## 任务: {task_id}
类型: {task_type}

## 数据文件
工作目录: {task_workspace}
文件列表:
{files_str}
{format_hint}{type_specific_hint}
## 数据说明
{readme_content[:2000] if readme_content else "请先阅读 README.md 了解数据"}

## 任务要求
{instruction}

## 执行要求
1. 首先读取 README.md 和所有数据文件，理解任务
2. 如果存在 sample_*.* 文件，必须先读取了解输出格式要求
3. 如果存在 .yaml/.yml 配置文件，必须读取获取参数
4. 编写 Python 代码完成任务
5. **关键**: 输出的列名必须与 README/sample 中的写法**完全一致**，不要简化或修改列名!
   - 错误示例: 把 "Biogas Generation Estimate (cu-ft/day)" 改成 "biogas_generation_estimate"
   - 正确做法: 直接复制原始列名，包括空格、括号、大小写
6. 按照以上的任务要求, 结果生成文件，请保存到当前工作目录, 一般保存为result.(csv|json|txt)文件

请开始执行任务。
"""
    return prompt


def run_test(task_id: str, agent_name: str, max_turns: int, verify_agent: bool = False) -> dict:
    """运行单个测试"""
    print(f"\n{'='*60}")
    print(f"测试任务: {task_id}")
    print(f"{'='*60}")

    # 加载任务配置
    task_config = load_task_config(task_id)
    if not task_config:
        return {
            "task_id": task_id,
            "status": "error",
            "message": "任务配置未找到"
        }

    # 准备工作目录
    task_workspace = prepare_workspace(task_id, agent_name)

    # 构建提示词
    prompt = build_prompt(task_config, task_workspace)

    # 创建 Agent 并运行
    agent_cls = get_agent_config(agent_name)["cls"]
    agent = agent_cls()
    # 临时修改工作目录
    original_workspace = getattr(agent, "workspace", None)
    if hasattr(agent, "workspace"):
        agent.workspace = task_workspace
    # 启用验证 Agent（如果支持）
    if verify_agent and hasattr(agent, "_enable_verification_agent"):
        agent._enable_verification_agent = True

    try:
        result = agent.run(prompt, max_turns=max_turns)
        status = "completed"
    except Exception as e:
        result = str(e)
        status = "error"
    finally:
        if hasattr(agent, "workspace"):
            agent.workspace = original_workspace

    return {
        "task_id": task_id,
        "type": task_config['type'],
        "hardness": task_config['hardness'],
        "status": status,
        "output": result,
        "workspace": task_workspace
    }


def main():
    """主函数 - 多 Agent 测试入口"""
    parser = argparse.ArgumentParser(
        description='DA-Code Benchmark - 多 Agent 测试脚本'
    )
    parser.add_argument(
        '--agent',
        type=str,
        default='dynamic',
        choices=sorted(AGENT_CONFIGS.keys()),
        help='选择执行 Agent: dynamic=Dynamic Plan Agent | minimal=MinimalKimiAgent'
    )
    parser.add_argument(
        '--mode',
        type=str,
        default='quick',
        choices=['quick', 'baseline', 'all'],
        help='测试模式: quick (5个快速验证任务) | baseline (59个基准任务) | all (所有有gold的任务)'
    )
    parser.add_argument(
        '--max-turns',
        type=int,
        help='每个任务的最大轮次 (默认: 根据 agent 选择自动设置)'
    )
    parser.add_argument(
        '--force',
        action='store_true',
        help='强制重新运行所有任务（忽略已有测试结果，兼容旧用法）'
    )
    parser.add_argument(
        '--resume',
        action='store_true',
        help='续跑模式：跳过已有日志记录中完成的任务，从断点继续'
    )
    parser.add_argument(
        '--task',
        type=str,
        help='只运行指定的单个任务（如: plot-bar-005），忽略 --mode 参数'
    )
    parser.add_argument(
        '--output-dir',
        type=str,
        help='自定义输出目录名（相对于 agent_workspace/），覆盖默认值'
    )
    parser.add_argument(
        '--workers',
        type=int,
        default=1,
        help='并行 worker 数量（默认: 1 串行；建议 3-5）'
    )
    parser.add_argument(
        '--verify-agent',
        action='store_true',
        help='启用 Fresh-Context 验证 Agent（VerifyResult PASS 后独立验证输出格式）'
    )
    args = parser.parse_args()

    agent_cfg = get_agent_config(args.agent)
    # 允许 --output-dir 覆盖 workspace_root 和 eval_output_dir
    if args.output_dir:
        agent_cfg = dict(agent_cfg)
        agent_cfg["workspace_root"] = os.path.join(WORKSPACE_ROOT, args.output_dir)
        agent_cfg["eval_output_dir"] = args.output_dir
        AGENT_CONFIGS[args.agent] = agent_cfg
    log_prefix = agent_cfg["log_prefix"]

    max_turns = args.max_turns or agent_cfg["default_max_turns"]
    dataset_map = {'quick': 'quick', 'baseline': 'test', 'all': 'test'}
    eval_dataset = dataset_map.get(args.mode, 'test')
    eval_output_dir = agent_cfg.get("eval_output_dir")
    eval_command = None
    if eval_output_dir:
        eval_command = f"python test/evaluate_results.py --dataset {eval_dataset} --output-dir {eval_output_dir}"

    print("=" * 60)
    print(f"DA-Code Benchmark 测试 - {agent_cfg['name']} - {args.mode.upper()} 模式")
    print("=" * 60)
    print(f"Agent: {args.agent}")
    print(f"日志前缀: {log_prefix}")
    print(f"最大轮次: {max_turns}")

    # 1. 根据模式选择任务列表
    if args.task:
        # 单任务模式
        all_tasks = [args.task]
        print(f"\n模式: 单任务测试")
        print(f"任务ID: {args.task}")
    elif args.mode == 'quick':
        all_tasks = load_baseline_tasks(mode='quick')
        print(f"\n模式: 快速测试（每类任务各1个）")
        print(f"任务来源: {DATASET_TASKS_FILE}")
        print(f"预期准确率: 100% (5/5) - 这5个任务在Stage 1测试中全部成功")
    elif args.mode == 'baseline':
        all_tasks = load_baseline_tasks(mode='baseline')
        print(f"\n模式: Baseline 测试")
        print(f"任务来源: {DATASET_TASKS_FILE}")
        print(f"Stage 1 Baseline 准确率: 23.7% (14/59)")
    else:  # all
        all_tasks = discover_all_tasks()
        print(f"\n模式: 全量测试")
        print(f"任务来源: {GOLD_DIR}")

    print(f"任务总数: {len(all_tasks)}")

    # 2. 加载之前的测试结果
    if args.resume:
        previous_results = load_previous_results(log_prefix)
        print(f"\n▶️  续跑模式: 已跳过 {len(previous_results)} 个已完成任务")
    else:
        if args.force:
            # 删除该 agent 的历史日志 JSON（非 merged），重置记录
            pattern = os.path.join(LOGS_DIR, f"{log_prefix}_*.json")
            old_logs = [f for f in glob.glob(pattern) if "_merged_" not in os.path.basename(f)]
            for f in old_logs:
                os.remove(f)
            if old_logs:
                print(f"\n⚠️  强制模式: 已清除 {len(old_logs)} 个历史日志，从头开始")
            else:
                print(f"\n⚠️  强制模式: 无历史日志，从头开始")
        previous_results = {}

    # 3. 获取需要测试的任务
    tasks_to_test = get_tasks_to_test(all_tasks, previous_results)
    print(f"待测试任务数: {len(tasks_to_test)}")

    if not tasks_to_test:
        print("\n所有任务都已测试完成！")
        print("=" * 60)
        if eval_command:
            print(f"提示: 请运行官方评估脚本:")
            print(f"  {eval_command}")
        else:
            print("提示: 请使用 test/evaluate_results.py 对输出目录进行评估。")
        print("=" * 60)
        return

    # 显示待测试任务列表
    print("\n待测试任务:")
    for i, task in enumerate(tasks_to_test, 1):
        print(f"  {i}. {task}")

    print("\n" + "=" * 60)
    print(f"开始测试 {len(tasks_to_test)} 个任务")
    print("=" * 60)

    # 4. 执行测试（每完成一个任务立即追加保存）
    new_results = []
    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    os.makedirs(LOGS_DIR, exist_ok=True)
    new_result_file = os.path.join(LOGS_DIR, f"{log_prefix}_{timestamp}.json")
    log_lock = threading.Lock()
    completed_count = 0

    def run_and_save(task_id):
        nonlocal completed_count
        result = run_test(task_id, agent_name=args.agent, max_turns=max_turns,
                         verify_agent=args.verify_agent)
        with log_lock:
            completed_count += 1
            new_results.append(result)
            print(f"\n[{completed_count}/{len(tasks_to_test)}] ✓ {task_id} 状态: {result['status']}")
            with open(new_result_file, 'w', encoding='utf-8') as f:
                json.dump(new_results, f, ensure_ascii=False, indent=2)
        return result

    workers = args.workers
    if workers > 1:
        print(f"\n⚡ 并行模式: {workers} workers")
        with ThreadPoolExecutor(max_workers=workers) as executor:
            futures = {executor.submit(run_and_save, task_id): task_id for task_id in tasks_to_test}
            for future in as_completed(futures):
                try:
                    future.result()
                except Exception as e:
                    task_id = futures[future]
                    print(f"\n❌ {task_id} 异常: {e}")
    else:
        for i, task_id in enumerate(tasks_to_test, 1):
            print(f"\n[{i}/{len(tasks_to_test)}] 开始测试 {task_id}")
            result = run_and_save(task_id)

    # 5. 合并结果（之前的 + 新的）
    all_results = list(previous_results.values()) + new_results

    # 6. 保存最终结果

    # 保存完整的合并结果
    merged_result_file = os.path.join(LOGS_DIR, f"{log_prefix}_merged_{timestamp}.json")
    with open(merged_result_file, 'w', encoding='utf-8') as f:
        json.dump(all_results, f, ensure_ascii=False, indent=2)

    # 7. 打印摘要
    print("\n" + "=" * 60)
    print(f"测试摘要 - {agent_cfg['name']}")
    print("=" * 60)

    # 本次测试摘要
    completed_new = sum(1 for r in new_results if r['status'] == 'completed')
    print(f"\n本次测试:")
    print(f"  完成: {completed_new}/{len(new_results)}")
    print(f"  结果保存: {new_result_file}")

    # 总体摘要
    completed_all = sum(1 for r in all_results if r['status'] == 'completed')
    print(f"\n总体进度:")
    print(f"  完成: {completed_all}/{len(all_results)}")
    print(f"  合并结果: {merged_result_file}")

    # 显示所有任务状态
    print(f"\n所有任务状态:")
    for r in sorted(all_results, key=lambda x: x['task_id']):
        status_icon = "✓" if r['status'] == 'completed' else "✗"
        print(f"  {status_icon} {r['task_id']} ({r.get('hardness', 'N/A')})")

    print("\n" + "=" * 60)
    print(f"测试完成 - {agent_cfg['name']}")
    print("=" * 60)
    print(f"输出目录根路径: {agent_cfg['workspace_root']}")
    if eval_command:
        print("\n下一步: 运行官方评估脚本")
        print(f"  {eval_command}")
    else:
        print("\n下一步: 请根据 README 使用 test/evaluate_results.py 进行评估")
    print("=" * 60)


if __name__ == "__main__":
    main()
