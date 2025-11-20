"""
DA-Code Benchmark 测试脚本
使用 MinimalKimiAgent 测试 DA-Code 数据集
支持增量测试：自动发现所有任务，跳过已测试任务

测试模式:
- baseline: 测试 baseline 59 个任务（git clone 时包含的 gold 任务）
- all: 测试所有有 gold 答案的任务（需要先下载完整数据集）
"""

import os
import sys
import json
import shutil
import glob
import argparse
from datetime import datetime

# 添加父目录到路径以导入 minimal_kimi_agent
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from minimal_kimi_agent import MinimalKimiAgent

# 路径配置 (相对于项目根目录)
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DA_CODE_DIR = os.path.join(PROJECT_ROOT, "agent_workspace/da-code/da_code")
SOURCE_DIR = os.path.join(DA_CODE_DIR, "source")
GOLD_DIR = os.path.join(DA_CODE_DIR, "gold")
CONFIG_FILE = os.path.join(DA_CODE_DIR, "configs/task/all.jsonl")
WORKSPACE = os.path.join(PROJECT_ROOT, "agent_workspace")
LOGS_DIR = os.path.join(PROJECT_ROOT, "logs")
BASELINE_TASKS_FILE = os.path.join(os.path.dirname(__file__), "baseline_tasks.json")


def load_baseline_tasks() -> list:
    """加载 baseline 59 个任务列表"""
    if not os.path.exists(BASELINE_TASKS_FILE):
        print(f"警告: Baseline 任务配置文件不存在: {BASELINE_TASKS_FILE}")
        return []

    with open(BASELINE_TASKS_FILE, 'r', encoding='utf-8') as f:
        config = json.load(f)
        return config.get("baseline_59_tasks", [])


def discover_all_tasks() -> list:
    """从 gold 目录发现所有有标准答案的任务"""
    if not os.path.exists(GOLD_DIR):
        print(f"警告: Gold 目录不存在: {GOLD_DIR}")
        return []

    tasks = [d for d in os.listdir(GOLD_DIR) if os.path.isdir(os.path.join(GOLD_DIR, d))]
    tasks.sort()  # 按字母顺序排序
    return tasks


def load_previous_results() -> dict:
    """加载之前的测试结果，返回 {task_id: result} 字典"""
    previous_results = {}

    if not os.path.exists(LOGS_DIR):
        return previous_results

    # 查找所有测试结果文件
    result_files = glob.glob(os.path.join(LOGS_DIR, "dacode_test_*.json"))

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


def prepare_workspace(task_id: str) -> str:
    """准备工作目录，复制数据文件"""
    source_path = os.path.join(SOURCE_DIR, task_id)
    task_workspace = os.path.join(WORKSPACE, f"dacode_{task_id}")

    # 清理并创建工作目录
    if os.path.exists(task_workspace):
        shutil.rmtree(task_workspace)
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

    prompt = f"""## 任务: {task_id}
类型: {task_type}

## 数据文件
工作目录: {task_workspace}
文件列表:
{files_str}

## 数据说明
{readme_content[:2000] if readme_content else "请先阅读 README.md 了解数据"}

## 任务要求
{instruction}

## 执行要求
1. 首先读取并理解数据文件
2. 编写 Python 代码完成任务
3. 将结果按要求的格式输出
4. 如果需要生成文件，请保存到当前工作目录

请开始执行任务。
"""
    return prompt


def run_test(task_id: str, max_turns: int = 15) -> dict:
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
    task_workspace = prepare_workspace(task_id)

    # 构建提示词
    prompt = build_prompt(task_config, task_workspace)

    # 创建 Agent 并运行
    agent = MinimalKimiAgent()
    # 临时修改工作目录
    original_workspace = agent.workspace
    agent.workspace = task_workspace

    try:
        result = agent.run(prompt, max_turns=max_turns)
        status = "completed"
    except Exception as e:
        result = str(e)
        status = "error"
    finally:
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
    """主函数 - 增量测试模式"""
    # 解析命令行参数
    parser = argparse.ArgumentParser(description='DA-Code Benchmark 测试脚本')
    parser.add_argument(
        '--mode',
        type=str,
        default='baseline',
        choices=['baseline', 'all'],
        help='测试模式: baseline (59个基准任务) 或 all (所有有gold的任务)'
    )
    parser.add_argument(
        '--max-turns',
        type=int,
        default=15,
        help='每个任务的最大轮次 (默认: 15)'
    )
    args = parser.parse_args()

    print("=" * 60)
    print(f"DA-Code Benchmark 测试 - {args.mode.upper()} 模式")
    print("=" * 60)

    # 1. 根据模式选择任务列表
    if args.mode == 'baseline':
        all_tasks = load_baseline_tasks()
        print(f"\n模式: Baseline 测试")
        print(f"任务来源: {BASELINE_TASKS_FILE}")
    else:
        all_tasks = discover_all_tasks()
        print(f"\n模式: 全量测试")
        print(f"任务来源: {GOLD_DIR}")

    print(f"发现任务总数: {len(all_tasks)}")

    # 2. 加载之前的测试结果
    previous_results = load_previous_results()
    print(f"已测试任务数: {len(previous_results)}")

    # 3. 获取需要测试的任务
    tasks_to_test = get_tasks_to_test(all_tasks, previous_results)
    print(f"待测试任务数: {len(tasks_to_test)}")

    if not tasks_to_test:
        print("\n所有任务都已测试完成！")
        print("=" * 60)
        return

    # 显示待测试任务列表
    print("\n待测试任务:")
    for i, task in enumerate(tasks_to_test, 1):
        print(f"  {i}. {task}")

    print("\n" + "=" * 60)
    print(f"开始测试 {len(tasks_to_test)} 个任务")
    print("=" * 60)

    # 4. 执行测试
    new_results = []
    for i, task_id in enumerate(tasks_to_test, 1):
        print(f"\n[{i}/{len(tasks_to_test)}] 开始测试 {task_id}")

        result = run_test(task_id, max_turns=args.max_turns)
        new_results.append(result)

        print(f"状态: {result['status']}")

    # 5. 合并结果（之前的 + 新的）
    all_results = list(previous_results.values()) + new_results

    # 6. 保存新测试结果
    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    os.makedirs(LOGS_DIR, exist_ok=True)

    # 保存本次新增的测试结果
    new_result_file = os.path.join(LOGS_DIR, f"dacode_test_{timestamp}.json")
    with open(new_result_file, 'w', encoding='utf-8') as f:
        json.dump(new_results, f, ensure_ascii=False, indent=2)

    # 保存完整的合并结果
    merged_result_file = os.path.join(LOGS_DIR, f"dacode_test_merged_{timestamp}.json")
    with open(merged_result_file, 'w', encoding='utf-8') as f:
        json.dump(all_results, f, ensure_ascii=False, indent=2)

    # 7. 打印摘要
    print("\n" + "=" * 60)
    print("测试摘要")
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
    print("Baseline 测试完成！")
    print("下一步: 运行 python test/evaluate_dacode.py 查看评估结果")
    print("=" * 60)


if __name__ == "__main__":
    main()
