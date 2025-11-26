"""
DA-Code 官方评估脚本

使用方法:
  python test/evaluate_dacode_official.py --dataset train   # 训练集 (50个任务)
  python test/evaluate_dacode_official.py --dataset val     # 验证集 (50个任务)
  python test/evaluate_dacode_official.py --dataset test    # 测试集 (59个任务, Baseline)
  python test/evaluate_dacode_official.py --mode quick      # 快速测试 (5个任务, 兼容旧参数)
"""
import os, sys, json, argparse
from datetime import datetime

# 添加路径
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(PROJECT_ROOT, "agent_workspace/da-code"))

from da_agent.evaluators.evaluation import Evaluator

# 路径配置
OUTPUT_DIR = os.path.join(PROJECT_ROOT, "agent_workspace/output_dir")
GOLD_DIR = os.path.join(PROJECT_ROOT, "agent_workspace/da-code/da_code/gold")
EVAL_DIR = os.path.join(PROJECT_ROOT, "agent_workspace/da-code/da_code/configs/eval")
LOGS_DIR = os.path.join(PROJECT_ROOT, "logs")


def load_dataset_config():
    """加载数据集配置文件"""
    config_file = os.path.join(os.path.dirname(__file__), "dataset_tasks.json")
    with open(config_file) as f:
        return json.load(f)


def get_task_ids_legacy(mode):
    """获取任务列表 (兼容旧版 --mode 参数)"""
    config = load_dataset_config()
    if mode == 'quick':
        return config['datasets']['quick']['task_ids']
    else:  # baseline
        return config['datasets']['test']['task_ids']


def get_task_ids(dataset):
    """获取任务ID列表"""
    config = load_dataset_config()
    if dataset in ['train', 'val', 'test']:
        return config['datasets'][dataset]['task_ids']
    else:
        raise ValueError(f"未知的数据集: {dataset}")


def get_eval_config_file(dataset):
    """
    获取评估配置文件路径

    如果配置文件已存在（train/val），直接返回路径
    否则（test/quick）动态生成
    """
    if dataset in ['train', 'val']:
        # 训练集和验证集配置文件已经存在
        eval_file = os.path.join(EVAL_DIR, f"eval_{dataset}.jsonl")
        if os.path.exists(eval_file):
            return eval_file

    # test/quick 需要动态生成（兼容旧代码）
    return None


def create_eval_config(dataset, task_ids):
    """创建评估配置（仅用于test/quick）"""
    eval_all = os.path.join(EVAL_DIR, "eval_all.jsonl")

    # 读取所有配置
    all_configs = []
    with open(eval_all) as f:
        for line in f:
            if line.strip():
                all_configs.append(json.loads(line))

    # 过滤任务
    filtered = [c for c in all_configs if c['id'] in task_ids]

    # 保存
    output_file = os.path.join(EVAL_DIR, f"eval_{dataset}.jsonl")
    with open(output_file, 'w') as f:
        for c in filtered:
            f.write(json.dumps(c) + '\n')

    return output_file


def main():
    parser = argparse.ArgumentParser(
        description='DA-Code评估脚本 - 支持训练集/验证集/测试集',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  python test/evaluate_dacode_official.py --dataset train   # 50个训练任务
  python test/evaluate_dacode_official.py --dataset val     # 50个验证任务
  python test/evaluate_dacode_official.py --dataset test    # 59个测试任务
  python test/evaluate_dacode_official.py --mode quick      # 5个快速测试任务
        """
    )

    # 新参数: --dataset (推荐使用)
    parser.add_argument('--dataset', choices=['train', 'val', 'test'],
                       help='数据集选择: train(50), val(50), test(59)')

    # 旧参数: --mode (向后兼容)
    parser.add_argument('--mode', choices=['quick', 'baseline'],
                       help='[已弃用] 使用 --dataset 代替。quick=5任务, baseline=test')

    args = parser.parse_args()

    # 参数处理：优先使用 --dataset，否则使用 --mode
    if args.dataset:
        dataset = args.dataset
        task_ids = get_task_ids(dataset)
        print(f"\n{'='*60}")
        print(f"DA-Code 评估 - {dataset.upper()} 数据集")
        print(f"{'='*60}\n")
    elif args.mode:
        # 兼容旧参数
        print("⚠️  --mode 参数已弃用，请使用 --dataset train|val|test")
        dataset = 'test' if args.mode == 'baseline' else 'quick'
        task_ids = get_task_ids_legacy(args.mode)
        print(f"\n{'='*60}")
        print(f"DA-Code 评估 - {args.mode.upper()} 模式")
        print(f"{'='*60}\n")
    else:
        # 默认使用test数据集
        dataset = 'test'
        task_ids = get_task_ids('test')
        print(f"\n{'='*60}")
        print(f"DA-Code 评估 - TEST 数据集 (默认)")
        print(f"{'='*60}\n")

    # 获取或创建评估配置文件
    eval_json = get_eval_config_file(dataset)
    if eval_json is None:
        eval_json = create_eval_config(dataset, task_ids)

    print(f"✓ 数据集: {dataset}")
    print(f"✓ 任务数: {len(task_ids)}")
    print(f"✓ 配置文件: {eval_json}")
    print()

    # 运行评估
    evaluator = Evaluator(output_dir=OUTPUT_DIR, gold_dir=GOLD_DIR, timeout_seconds=300)
    results = evaluator.evaluate(env_config=eval_json)

    # 统计
    scores = [r['total_score'] for r in results]
    finished = [r['finished'] for r in results]
    avg_score = sum(scores) / len(scores)
    avg_finished = sum(finished) / len(finished)

    # 统计成功/部分成功/失败
    high_quality = sum(1 for s in scores if s >= 0.9)
    partial = sum(1 for s in scores if 0 < s < 0.9)
    failed = sum(1 for s in scores if s == 0)

    # 打印
    print(f"\n{'='*60}")
    print(f"评估结果 - {dataset.upper()} 数据集")
    print(f"{'='*60}")
    print(f"任务总数: {len(results)}")
    print(f"平均得分: {avg_score:.4f}")
    print(f"完成率:   {avg_finished:.2%}")
    print(f"")
    print(f"成功 (≥0.9分):     {high_quality:2d} / {len(results)} ({high_quality/len(results)*100:.1f}%)")
    print(f"部分成功 (0~0.9):  {partial:2d} / {len(results)} ({partial/len(results)*100:.1f}%)")
    print(f"失败 (0分):        {failed:2d} / {len(results)} ({failed/len(results)*100:.1f}%)")
    print(f"{'='*60}\n")

    # 保存
    os.makedirs(LOGS_DIR, exist_ok=True)
    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    result_file = os.path.join(LOGS_DIR, f"dacode_eval_{dataset}_{timestamp}.json")

    with open(result_file, 'w') as f:
        json.dump({
            'dataset': dataset,
            'num_tasks': len(results),
            'average_score': avg_score,
            'average_finished': avg_finished,
            'high_quality_count': high_quality,
            'partial_success_count': partial,
            'failed_count': failed,
            'results': results
        }, f, indent=2)

    print(f"✓ 结果已保存: {result_file}\n")


if __name__ == '__main__':
    main()
