"""
DA-Code 评估脚本
比较 Agent 输出与 Gold 标准答案
"""

import os
import sys
import json
import re
import pandas as pd
from typing import Tuple

# 路径配置
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
GOLD_DIR = os.path.join(PROJECT_ROOT, "agent_workspace/da-code/da_code/gold")
WORKSPACE = os.path.join(PROJECT_ROOT, "agent_workspace")


def extract_json_from_output(output: str) -> dict:
    """从 Agent 输出中提取 JSON"""
    # 尝试多种模式匹配 JSON
    patterns = [
        r'```json\s*([\s\S]*?)\s*```',  # ```json ... ```
        r'```\s*([\s\S]*?)\s*```',       # ``` ... ```
        r'\{[\s\S]*?"[^"]+"\s*:[\s\S]*?\}',  # 直接 JSON
    ]

    for pattern in patterns:
        matches = re.findall(pattern, output)
        if matches:
            for match in matches:
                try:
                    # 清理并解析
                    json_str = match.strip()
                    if not json_str.startswith('{'):
                        continue
                    return json.loads(json_str)
                except:
                    continue

    return None


def compare_json(pred: dict, gold: dict) -> Tuple[bool, str]:
    """比较两个 JSON 对象"""
    if pred is None:
        return False, "无法从输出中提取 JSON"

    # 标准化比较
    def normalize(obj):
        if isinstance(obj, dict):
            return {k.lower().strip(): normalize(v) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [normalize(x) for x in obj]
        elif isinstance(obj, str):
            return obj.lower().strip()
        elif isinstance(obj, float):
            return round(obj, 2)
        return obj

    pred_norm = normalize(pred)
    gold_norm = normalize(gold)

    # 检查键是否匹配
    if set(pred_norm.keys()) != set(gold_norm.keys()):
        return False, f"键不匹配: pred={set(pred_norm.keys())}, gold={set(gold_norm.keys())}"

    # 检查值是否匹配
    for key in gold_norm:
        if pred_norm.get(key) != gold_norm[key]:
            return False, f"值不匹配 [{key}]: pred={pred_norm.get(key)}, gold={gold_norm[key]}"

    return True, "完全匹配"


def compare_csv(pred_path: str, gold_path: str) -> Tuple[bool, str]:
    """比较两个 CSV 文件"""
    if not os.path.exists(pred_path):
        return False, f"预测文件不存在: {pred_path}"

    try:
        pred_df = pd.read_csv(pred_path)
        gold_df = pd.read_csv(gold_path)

        # 比较形状
        if pred_df.shape != gold_df.shape:
            return False, f"形状不匹配: pred={pred_df.shape}, gold={gold_df.shape}"

        # 比较列名
        if list(pred_df.columns) != list(gold_df.columns):
            return False, f"列名不匹配: pred={list(pred_df.columns)}, gold={list(gold_df.columns)}"

        # 比较数值（允许小误差）
        for col in pred_df.columns:
            if pred_df[col].dtype in ['float64', 'int64']:
                if not (abs(pred_df[col] - gold_df[col]) < 0.01).all():
                    return False, f"列 {col} 数值不匹配"
            else:
                if not (pred_df[col] == gold_df[col]).all():
                    return False, f"列 {col} 值不匹配"

        return True, "CSV 完全匹配"
    except Exception as e:
        return False, f"CSV 比较错误: {e}"


def evaluate_task(task_result: dict) -> dict:
    """评估单个任务"""
    task_id = task_result['task_id']
    output = task_result['output']
    workspace = task_result['workspace']

    gold_path = os.path.join(GOLD_DIR, task_id)

    # 检查是否有 gold 答案
    if not os.path.exists(gold_path):
        return {
            "task_id": task_id,
            "has_gold": False,
            "correct": None,
            "reason": "无 Gold 答案"
        }

    # 根据任务类型评估
    if task_id.startswith("di-text"):
        # 文本输出任务 - 比较 JSON
        gold_file = os.path.join(gold_path, "result.json")
        if os.path.exists(gold_file):
            with open(gold_file, 'r') as f:
                gold_json = json.load(f)

            pred_json = extract_json_from_output(output)
            correct, reason = compare_json(pred_json, gold_json)
        else:
            correct, reason = False, "Gold 文件不存在"

    elif task_id.startswith("dm-csv") or task_id.startswith("data-sa"):
        # CSV 输出任务
        gold_files = os.listdir(gold_path)
        csv_files = [f for f in gold_files if f.endswith('.csv')]

        if csv_files:
            gold_csv = os.path.join(gold_path, csv_files[0])
            pred_csv = os.path.join(workspace, csv_files[0])
            correct, reason = compare_csv(pred_csv, gold_csv)
        else:
            correct, reason = False, "无 Gold CSV 文件"

    elif task_id.startswith("ml-"):
        # ML 任务 - 检查是否生成了 result.csv
        pred_csv = os.path.join(workspace, "result.csv")
        if os.path.exists(pred_csv):
            correct, reason = True, "生成了结果文件（无Gold对比）"
        else:
            correct, reason = False, "未生成 result.csv"

    elif task_id.startswith("plot-"):
        # 可视化任务 - 检查是否生成了图片
        pred_png = os.path.join(workspace, "result.png")
        if os.path.exists(pred_png):
            correct, reason = True, "生成了图片（需人工评判）"
        else:
            correct, reason = False, "未生成 result.png"

    else:
        correct, reason = False, f"未知任务类型: {task_id}"

    return {
        "task_id": task_id,
        "has_gold": True,
        "correct": correct,
        "reason": reason
    }


def main():
    """主函数"""
    # 读取测试结果
    import glob
    result_files = glob.glob(os.path.join(PROJECT_ROOT, "logs/dacode_test_*.json"))

    if not result_files:
        print("未找到测试结果文件")
        return

    # 使用最新的结果文件
    latest_result = max(result_files)
    print(f"评估文件: {os.path.basename(latest_result)}")
    print("=" * 60)

    with open(latest_result, 'r') as f:
        test_results = json.load(f)

    # 评估每个任务
    evaluations = []
    for task_result in test_results:
        eval_result = evaluate_task(task_result)
        evaluations.append(eval_result)

    # 打印结果
    print(f"\n{'任务ID':<20} {'有Gold':<8} {'正确':<8} {'原因'}")
    print("-" * 80)

    correct_count = 0
    total_with_gold = 0

    for eval_result in evaluations:
        has_gold = "✓" if eval_result['has_gold'] else "-"
        if eval_result['correct'] is None:
            correct_str = "-"
        elif eval_result['correct']:
            correct_str = "✓"
            correct_count += 1
        else:
            correct_str = "✗"

        if eval_result['has_gold']:
            total_with_gold += 1

        print(f"{eval_result['task_id']:<20} {has_gold:<8} {correct_str:<8} {eval_result['reason']}")

    # 打印摘要
    print("\n" + "=" * 60)
    print("评估摘要")
    print("=" * 60)
    print(f"总任务数: {len(evaluations)}")
    print(f"有 Gold 答案: {total_with_gold}")
    print(f"正确数: {correct_count}")
    if total_with_gold > 0:
        accuracy = correct_count / total_with_gold * 100
        print(f"准确率: {accuracy:.1f}% ({correct_count}/{total_with_gold})")


if __name__ == "__main__":
    main()
