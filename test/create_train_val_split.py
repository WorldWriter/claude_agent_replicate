#!/usr/bin/env python3
"""
分层随机抽样生成训练集和验证集

策略：
1. 从500个任务中排除59个baseline测试集任务，得到441个可用任务
2. 双重分层：按任务类别 × 难度分层
3. 难度分布：Easy 33%, Medium 33%, Hard 33%（折中方案）
4. 训练集50个，验证集50个
"""

import json
import random
from collections import defaultdict
from pathlib import Path
from typing import List, Dict, Tuple

# 设置随机种子确保可复现
RANDOM_SEED = 42
random.seed(RANDOM_SEED)

# 文件路径
BASE_DIR = Path(__file__).parent.parent
EVAL_DIR = BASE_DIR / "agent_workspace/da-code/da_code/configs/eval"
DATASET_FILE = BASE_DIR / "test/dataset_tasks.json"
ALL_TASKS_FILE = EVAL_DIR / "eval_all.jsonl"
OUTPUT_TRAIN_FILE = EVAL_DIR / "eval_train.jsonl"
OUTPUT_VAL_FILE = EVAL_DIR / "eval_val.jsonl"

# 目标难度分布（用户要求的折中方案）
TARGET_DIFFICULTY_DIST = {
    "Easy": 0.33,
    "Medium": 0.33,
    "Hard": 0.34  # 补齐到100%
}

# 训练集和验证集大小
TRAIN_SIZE = 50
VAL_SIZE = 50


def load_all_tasks() -> List[Dict]:
    """加载所有500个任务"""
    tasks = []
    with open(ALL_TASKS_FILE, 'r', encoding='utf-8') as f:
        for line in f:
            task = json.loads(line.strip())
            tasks.append(task)
    print(f"✓ 加载 {len(tasks)} 个任务从 eval_all.jsonl")
    return tasks


def load_baseline_task_ids() -> set:
    """加载baseline测试集的59个任务ID"""
    # 尝试从 dataset_tasks.json 加载
    if DATASET_FILE.exists():
        with open(DATASET_FILE, 'r', encoding='utf-8') as f:
            data = json.load(f)
        baseline_ids = set(data['datasets']['test']['task_ids'])
        print(f"✓ 加载 {len(baseline_ids)} 个baseline测试集任务ID (从 dataset_tasks.json)")
    else:
        # 降级方案：如果新文件不存在，创建空的测试集
        print("⚠️  dataset_tasks.json 不存在，将创建新的数据集划分")
        baseline_ids = set()
    return baseline_ids


def filter_available_tasks(all_tasks: List[Dict], baseline_ids: set) -> List[Dict]:
    """过滤得到可用任务（排除baseline）"""
    available = [task for task in all_tasks if task['id'] not in baseline_ids]
    print(f"✓ 过滤后可用任务: {len(available)} 个 (500 - {len(baseline_ids)} = {len(available)})")
    return available


def stratify_tasks(tasks: List[Dict]) -> Dict[Tuple[str, str], List[Dict]]:
    """
    按 (task_category, hardness) 双重分层

    返回: {(category, hardness): [task1, task2, ...]}
    """
    strata = defaultdict(list)
    for task in tasks:
        category = task['config']['task']
        hardness = task['config']['hardness']
        strata[(category, hardness)].append(task)

    print(f"\n✓ 分层统计 ({len(strata)} 个层):")
    for (cat, hard), task_list in sorted(strata.items()):
        print(f"  {cat:25s} × {hard:6s}: {len(task_list):3d} 个任务")

    return strata


def calculate_target_counts(total_size: int) -> Dict[str, int]:
    """计算每个难度级别的目标数量"""
    targets = {}
    for hardness, ratio in TARGET_DIFFICULTY_DIST.items():
        targets[hardness] = int(total_size * ratio)

    # 确保总和等于total_size
    diff = total_size - sum(targets.values())
    if diff > 0:
        targets["Hard"] += diff

    return targets


def stratified_sample(
    strata: Dict[Tuple[str, str], List[Dict]],
    total_size: int,
    name: str
) -> Tuple[List[Dict], Dict]:
    """
    分层随机抽样

    参数:
        strata: 分层后的任务字典
        total_size: 目标样本数（50）
        name: 数据集名称（"训练集" 或 "验证集"）

    返回:
        (抽样任务列表, 统计信息)
    """
    # 第一步：按难度分配配额
    difficulty_targets = calculate_target_counts(total_size)
    print(f"\n{name}难度分配目标: {difficulty_targets}")

    # 第二步：在每个难度内，按类别比例分配
    sampled_tasks = []
    stats = defaultdict(lambda: defaultdict(int))

    for hardness in ["Easy", "Medium", "Hard"]:
        target_count = difficulty_targets[hardness]

        # 获取该难度下所有类别的任务
        tasks_by_category = defaultdict(list)
        total_tasks = 0
        for (cat, hard), task_list in strata.items():
            if hard == hardness:
                tasks_by_category[cat] = task_list
                total_tasks += len(task_list)

        if total_tasks == 0:
            print(f"  ⚠️  {hardness} 难度无可用任务，跳过")
            continue

        # 按类别比例分配配额
        allocated = 0
        for cat in sorted(tasks_by_category.keys()):
            task_list = tasks_by_category[cat]
            ratio = len(task_list) / total_tasks
            quota = int(target_count * ratio)

            # 确保不超过可用任务数
            quota = min(quota, len(task_list))

            if quota > 0:
                samples = random.sample(task_list, quota)
                sampled_tasks.extend(samples)
                stats[cat][hardness] = quota
                allocated += quota

                # 从原列表中移除已抽样的任务（避免重复抽样）
                for s in samples:
                    task_list.remove(s)

        # 如果还没达到目标，补充随机抽样
        remaining = target_count - allocated
        if remaining > 0:
            # 从所有剩余任务中随机补充
            remaining_tasks = []
            for task_list in tasks_by_category.values():
                remaining_tasks.extend(task_list)

            if len(remaining_tasks) >= remaining:
                extra_samples = random.sample(remaining_tasks, remaining)
                sampled_tasks.extend(extra_samples)
                for s in extra_samples:
                    cat = s['config']['task']
                    hard = s['config']['hardness']
                    stats[cat][hard] += 1

    return sampled_tasks, dict(stats)


def save_tasks(tasks: List[Dict], output_file: Path):
    """保存任务配置到jsonl文件"""
    with open(output_file, 'w', encoding='utf-8') as f:
        for task in tasks:
            f.write(json.dumps(task, ensure_ascii=False) + '\n')
    print(f"✓ 保存 {len(tasks)} 个任务到 {output_file.name}")


def print_statistics(train_tasks: List[Dict], val_tasks: List[Dict],
                     train_stats: Dict, val_stats: Dict):
    """打印详细统计信息"""
    print("\n" + "="*70)
    print("数据集划分完成统计")
    print("="*70)

    def count_by_category(tasks):
        counts = defaultdict(int)
        for task in tasks:
            counts[task['config']['task']] += 1
        return dict(counts)

    def count_by_hardness(tasks):
        counts = defaultdict(int)
        for task in tasks:
            counts[task['config']['hardness']] += 1
        return dict(counts)

    print(f"\n训练集: {len(train_tasks)} 个任务")
    print("  类别分布:")
    for cat, count in sorted(count_by_category(train_tasks).items()):
        print(f"    {cat:25s}: {count:2d} ({count/len(train_tasks)*100:.1f}%)")
    print("  难度分布:")
    for hard, count in sorted(count_by_hardness(train_tasks).items()):
        print(f"    {hard:6s}: {count:2d} ({count/len(train_tasks)*100:.1f}%)")

    print(f"\n验证集: {len(val_tasks)} 个任务")
    print("  类别分布:")
    for cat, count in sorted(count_by_category(val_tasks).items()):
        print(f"    {cat:25s}: {count:2d} ({count/len(val_tasks)*100:.1f}%)")
    print("  难度分布:")
    for hard, count in sorted(count_by_hardness(val_tasks).items()):
        print(f"    {hard:6s}: {count:2d} ({count/len(val_tasks)*100:.1f}%)")

    # 验证无重叠
    train_ids = {task['id'] for task in train_tasks}
    val_ids = {task['id'] for task in val_tasks}
    overlap = train_ids & val_ids
    print(f"\n验证:")
    print(f"  训练集 ∩ 验证集 = {len(overlap)} (应为0) {'✓' if len(overlap) == 0 else '✗ 错误！'}")


def save_metadata(train_tasks: List[Dict], val_tasks: List[Dict],
                 baseline_ids: set, train_stats: Dict, val_stats: Dict):
    """更新 dataset_tasks.json 文件"""
    # 加载现有配置或创建新配置
    if DATASET_FILE.exists():
        with open(DATASET_FILE, 'r', encoding='utf-8') as f:
            config = json.load(f)
    else:
        # 创建新的配置结构
        config = {
            "project": "DA-Code Agent Architecture Research",
            "dataset_version": "v1.0",
            "total_tasks_available": 500,
            "datasets": {
                "quick": {
                    "description": "快速测试配置 - 每类任务各选1个（共5个）",
                    "note": "选择标准：(1) 覆盖5种主要任务类型 (2) 优先选择baseline测试中已成功的任务 (3) 适合快速验证Agent改进效果",
                    "expected_accuracy": "100% (5/5) - 这5个任务在baseline测试中全部成功",
                    "size": 5,
                    "task_ids": [
                        "di-text-001", "dm-csv-050", "ml-regression-011",
                        "data-sa-001", "plot-bar-005"
                    ]
                }
            },
            "usage": {
                "quick_test": "python test/evaluate_dacode_official.py --mode quick",
                "train_eval": "python test/evaluate_dacode_official.py --dataset train",
                "val_eval": "python test/evaluate_dacode_official.py --dataset val",
                "test_eval": "python test/evaluate_dacode_official.py --dataset test",
                "regenerate": "python test/create_train_val_split.py"
            },
            "files": {
                "this_file": "test/dataset_tasks.json",
                "split_script": "test/create_train_val_split.py",
                "eval_script": "test/evaluate_dacode_official.py",
                "detailed_report": "docs/dataset_split_report.md",
                "train_config": "agent_workspace/da-code/da_code/configs/eval/eval_train.jsonl",
                "val_config": "agent_workspace/da-code/da_code/configs/eval/eval_val.jsonl",
                "test_config": "agent_workspace/da-code/da_code/configs/eval/eval_baseline.jsonl"
            }
        }

    # 计算难度分布
    def count_difficulty(tasks):
        dist = {"Easy": 0, "Medium": 0, "Hard": 0}
        for task in tasks:
            hardness = task['config']['hardness']
            dist[hardness] += 1
        return dist

    train_difficulty = count_difficulty(train_tasks)
    val_difficulty = count_difficulty(val_tasks)

    # 更新配置
    config["split_date"] = "2025-11-22"
    config["total_tasks_allocated"] = len(train_tasks) + len(val_tasks) + len(baseline_ids)
    config["total_tasks_reserved"] = 500 - config["total_tasks_allocated"]

    config["sampling_config"] = {
        "random_seed": RANDOM_SEED,
        "strategy": "双重分层随机抽样 (任务类别 × 难度)",
        "target_difficulty_distribution": TARGET_DIFFICULTY_DIST
    }

    # 更新训练集
    config["datasets"]["train"] = {
        "description": "训练集 - 用于提示工程优化、策略开发",
        "size": len(train_tasks),
        "difficulty_distribution": train_difficulty,
        "config_file": "agent_workspace/da-code/da_code/configs/eval/eval_train.jsonl",
        "task_ids": [task['id'] for task in train_tasks],
        "statistics": train_stats
    }

    # 更新验证集
    config["datasets"]["val"] = {
        "description": "验证集 - 用于超参数调优、策略验证",
        "size": len(val_tasks),
        "difficulty_distribution": val_difficulty,
        "config_file": "agent_workspace/da-code/da_code/configs/eval/eval_val.jsonl",
        "task_ids": [task['id'] for task in val_tasks],
        "statistics": val_stats
    }

    # 更新测试集（如果有baseline）
    if baseline_ids:
        if "test" not in config["datasets"]:
            config["datasets"]["test"] = {}
        config["datasets"]["test"]["task_ids"] = sorted(list(baseline_ids))
        config["datasets"]["test"]["size"] = len(baseline_ids)

    # 更新验证信息
    config["verification"] = {
        "train_val_overlap": len(set([task['id'] for task in train_tasks]) &
                                  set([task['id'] for task in val_tasks])),
        "train_test_overlap": len(set([task['id'] for task in train_tasks]) & baseline_ids),
        "val_test_overlap": len(set([task['id'] for task in val_tasks]) & baseline_ids),
        "note": "所有数据集完全独立，无任务交集"
    }

    # 保存
    with open(DATASET_FILE, 'w', encoding='utf-8') as f:
        json.dump(config, f, ensure_ascii=False, indent=2)

    print(f"\n✓ 更新元数据到 {DATASET_FILE.name}")


def main():
    print("="*70)
    print("DA-Code 数据集划分 - 训练集/验证集生成")
    print("="*70)

    # 1. 加载数据
    all_tasks = load_all_tasks()
    baseline_ids = load_baseline_task_ids()

    # 2. 过滤可用任务
    available_tasks = filter_available_tasks(all_tasks, baseline_ids)

    # 3. 分层
    strata = stratify_tasks(available_tasks)

    # 4. 抽样训练集
    print(f"\n{'='*70}")
    print("开始抽样训练集")
    print(f"{'='*70}")
    train_tasks, train_stats = stratified_sample(strata, TRAIN_SIZE, "训练集")

    # 5. 从strata中移除已抽样的训练集任务
    train_ids = {task['id'] for task in train_tasks}
    for key in strata:
        strata[key] = [task for task in strata[key] if task['id'] not in train_ids]

    # 6. 抽样验证集
    print(f"\n{'='*70}")
    print("开始抽样验证集")
    print(f"{'='*70}")
    val_tasks, val_stats = stratified_sample(strata, VAL_SIZE, "验证集")

    # 7. 保存文件
    print(f"\n{'='*70}")
    print("保存配置文件")
    print(f"{'='*70}")
    save_tasks(train_tasks, OUTPUT_TRAIN_FILE)
    save_tasks(val_tasks, OUTPUT_VAL_FILE)
    save_metadata(train_tasks, val_tasks, baseline_ids, train_stats, val_stats)

    # 8. 打印统计
    print_statistics(train_tasks, val_tasks, train_stats, val_stats)

    print("\n" + "="*70)
    print("✓ 完成！")
    print("="*70)
    print(f"输出文件:")
    print(f"  - {OUTPUT_TRAIN_FILE}")
    print(f"  - {OUTPUT_VAL_FILE}")
    print(f"  - {DATASET_FILE}")


if __name__ == "__main__":
    main()
