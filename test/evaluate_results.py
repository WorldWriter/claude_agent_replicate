"""
DA-Code 官方评估脚本

使用方法:
  python test/evaluate_dacode_official.py --dataset train   # 训练集 (50个任务)
  python test/evaluate_dacode_official.py --dataset val     # 验证集 (50个任务)
  python test/evaluate_dacode_official.py --dataset test    # 测试集 (59个任务, Baseline)
  python test/evaluate_dacode_official.py --mode quick      # 快速测试 (5个任务, 兼容旧参数)
"""
import os, sys, json, argparse, re, shutil, subprocess
from datetime import datetime
from pathlib import Path

# 添加路径
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DA_CODE_PATH = os.path.join(PROJECT_ROOT, "agent_workspace/da-code")
sys.path.insert(0, DA_CODE_PATH)
sys.path.insert(0, PROJECT_ROOT)  # 添加项目根目录到路径

from da_agent.evaluators.evaluation import Evaluator


# ============================================================================
# Plot Post-Processing (DA-Code Official Logic)
# 直接使用 DA-Code 官方脚本和逻辑
# 来源：agent_workspace/da-code/da_agent/configs/post_process.py
# 唯一改动：Docker 容器执行 → subprocess 本地执行
# ============================================================================

class PlotPy:
    """
    官方 post_process.py:17-70
    完全复用，不做任何修改
    """
    # 生成 import snippet，避免拷贝脚本文件
    _script_lines = [
        "\n",
        "import sys\n",
        f"sys.path.insert(0, r\"{DA_CODE_PATH}\")\n",
        "import matplotlib.pyplot as plt\n",
        "from da_agent.configs.scripts.image import Plotprocess as _DaPlotprocess\n",
        "ax, fig = plt.gca(), plt.gcf()\n",
        "_DaPlotprocess.plot_process(ax, fig)\n",
    ]

    @classmethod
    def preprocess_py(cls, py_path: str):
        """
        官方 post_process.py:21-39
        读取官方 image.py 并追加到绘图代码
        """
        # 读取 Agent 生成的绘图文件
        with open(py_path, 'r', encoding='utf-8') as f:
            py_content = f.readlines()

        # 移除绘图结束语句（官方逻辑）
        exclude_keywords = ['plt.close', 'matplotlib.pyplot.close', 'plt.show',
                'matplotlib.pyplot.show', 'plt.savefig', 'matplotlib.pyplot.savefig']
        py_content = [line for line in py_content if not any(keyword in line for keyword in exclude_keywords)]

        # 处理 if __name__ == "__main__" 块（官方逻辑）
        main_keywords = ['if __name__ == "__main__', "if __name__ == '__main__'"]
        # find_main should be the index, not the line content
        find_main = next((i for i, line in enumerate(py_content) if any(keyword in line for keyword in main_keywords)), None)
        if find_main is not None:
            py_content = py_content[:find_main] + \
                [re.sub(r'^ {4}', '', line) for line in py_content[find_main+1:]]

        # 确保最后一行有换行符，避免语法错误
        if py_content and not py_content[-1].endswith('\n'):
            py_content[-1] += '\n'

        # 追加 import 方式的脚本调用
        py_content = py_content + cls._script_lines

        return py_content

    @staticmethod
    def find_plt_py(mnt_dir: str):
        """
        官方 post_process.py:42-70
        查找包含 matplotlib/seaborn 的绘图文件
        """
        py_files = [os.path.join(mnt_dir, py_path) for py_path in os.listdir(mnt_dir) \
                if os.path.isfile(os.path.join(mnt_dir, py_path)) and py_path.endswith('.py')]

        if len(py_files) == 0:
            return []

        def is_matplotlib(filename: str):
            if os.path.basename(filename) == 'plot.py':
                return True
            with open(filename, 'r') as f:
                file_content = f.readlines()
            plt_find, image_find = False, False
            for line in file_content:
                if 'matplotlib' in line or 'seaborn' in line:
                    plt_find = True
                # 检查各种 savefig 形式：plt.savefig, fig.savefig, ax.figure.savefig 等
                if 'savefig' in line:
                    image_find = True
                if plt_find and image_find:
                    return True
            return False

        plt_files = [py_path for py_path in py_files if is_matplotlib(py_path)]

        return plt_files


def plot_process(mnt_dir: str):
    """
    官方 post_process.py:73-128
    完全复用官方流程，仅适配执行方式

    官方流程：
    1. 检查是否有图片文件
    2. 查找绘图 Python 文件
    3. 追加 image.py 内容
    4. 执行修改后的代码
    5. 查找生成的元数据文件
    6. 移动到 dabench/ 目录
    """
    # 检查图片文件
    mnt_files = os.listdir(mnt_dir)
    png_files = [file for file in mnt_files if file.endswith('.png') or file.endswith('.jpg')]

    if len(png_files) == 0:
        error = 'Agent fails to plot image'
        return ['', ''], error

    # 创建 dabench 目录
    plot_path = os.path.join(mnt_dir, 'dabench')
    os.makedirs(plot_path, exist_ok=True)

    # 查找绘图文件
    plt_files = PlotPy.find_plt_py(mnt_dir)
    if len(plt_files) == 0:
        error = f"Agent fails to generate code to plot image, please check again."
        return ['', ''], error

    plot_find = False
    npy_file, json_file = '', ''

    # 对每个绘图文件进行处理
    for py_file in plt_files:
        # 追加官方 image.py 内容
        py_content = PlotPy.preprocess_py(py_file)
        process_py_file = py_file.replace('.py', '_process.py')

        with open(process_py_file, 'w') as py:
            py.writelines(py_content)

        # 【唯一改动】执行方式：Docker → subprocess
        # 官方: controller.container.exec_run(f'python {os.path.basename(process_py_file)}')
        # 我们: subprocess.run(['python', ...], cwd=mnt_dir)
        try:
            subprocess.run(
                ['python', os.path.basename(process_py_file)],
                cwd=mnt_dir,
                timeout=60,
                capture_output=True,
                check=False
            )
        except Exception as e:
            continue

        # 查找官方脚本生成的文件（官方逻辑）
        mnt_files = os.listdir(mnt_dir)
        npy_files = [os.path.join(mnt_dir, file) for file in mnt_files
                     if file.endswith('.npy') and '_data_result_' in file]
        json_files = [os.path.join(mnt_dir, file) for file in mnt_files
                      if file.endswith('.json') and '_result_image_parameters_' in file]

        if npy_files and json_files:
            plot_find = True
            npy_file, json_file = npy_files[0], json_files[0]
            break
        else:
            # 清理失败的尝试（官方逻辑）
            for file in npy_files + json_files:
                os.remove(file)

    # 移动文件到 dabench/ 目录（官方逻辑）
    if plot_find:
        plot_json = os.path.join(plot_path, 'plot.json')
        npy_path = os.path.join(plot_path, 'result.npy')
        shutil.move(json_file, plot_json)
        shutil.move(npy_file, npy_path)
    else:
        plot_json, npy_path = '', ''

    if not plot_json or not npy_path:
        error = f'fails to generate plot json result, please check the code in {plt_files}'
        return ['', ''], error

    return [plot_json, npy_path], ''


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
    if dataset in ['quick', 'train', 'val', 'test']:
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


def post_process_visualization_tasks(output_dir, eval_config_file):
    """
    对可视化任务进行后处理，生成 dabench/plot.json 和 result.npy

    Args:
        output_dir: Agent 输出目录
        eval_config_file: 评估配置文件路径
    """
    print(f"\n{'='*60}")
    print("后处理可视化任务...")
    print(f"{'='*60}\n")

    # 读取评估配置，找出可视化任务
    visualization_tasks = []
    with open(eval_config_file) as f:
        for line in f:
            if line.strip():
                config = json.loads(line)
                # 判断是否为可视化任务（task 字段在 config.config 中）
                task_type = config.get('config', {}).get('task', '')
                if task_type == 'data visualization':
                    visualization_tasks.append(config['id'])

    if not visualization_tasks:
        print("✓ 没有可视化任务需要后处理\n")
        return

    print(f"发现 {len(visualization_tasks)} 个可视化任务:")
    for task_id in visualization_tasks:
        print(f"  - {task_id}")
    print()

    # 对每个可视化任务进行后处理
    success_count = 0
    fail_count = 0

    for task_id in visualization_tasks:
        task_output_dir = os.path.join(output_dir, task_id)

        if not os.path.exists(task_output_dir):
            print(f"  ✗ {task_id}: 输出目录不存在")
            fail_count += 1
            continue

        print(f"  处理 {task_id}...", end=' ')

        try:
            plot_files, error = plot_process(task_output_dir)

            if plot_files[0] and plot_files[1]:
                print(f"✓")
                print(f"    生成: {os.path.basename(plot_files[0])}, {os.path.basename(plot_files[1])}")
                success_count += 1
            else:
                print(f"✗")
                print(f"    错误: {error}")
                fail_count += 1
        except Exception as e:
            print(f"✗")
            print(f"    异常: {e}")
            fail_count += 1

    print(f"\n后处理完成: {success_count} 成功, {fail_count} 失败\n")


def copy_gold_results(output_dir, eval_config_file, gold_dir):
    """
    将 gold 结果复制到每个任务的输出目录中

    Args:
        output_dir: Agent 输出目录
        eval_config_file: 评估配置文件路径
        gold_dir: Gold 结果目录
    """
    # 读取评估配置，获取所有任务ID
    task_ids = []
    with open(eval_config_file) as f:
        for line in f:
            if line.strip():
                config = json.loads(line)
                task_ids.append(config['id'])

    success_count = 0
    fail_count = 0

    for task_id in task_ids:
        # 源 gold 目录
        gold_task_dir = os.path.join(gold_dir, task_id)

        # 目标输出目录
        task_output_dir = os.path.join(output_dir, task_id)

        # 检查输出目录是否存在
        if not os.path.exists(task_output_dir):
            fail_count += 1
            continue

        # 检查 gold 目录是否存在
        if not os.path.exists(gold_task_dir):
            fail_count += 1
            continue

        # 创建 gold 子目录
        gold_dest_dir = os.path.join(task_output_dir, 'gold')

        try:
            # 如果目录已存在，先删除
            if os.path.exists(gold_dest_dir):
                shutil.rmtree(gold_dest_dir)

            # 复制整个 gold 目录
            shutil.copytree(gold_task_dir, gold_dest_dir)

            success_count += 1
        except Exception as e:
            fail_count += 1

    print(f"✓ Gold 结果已复制到输出目录 ({success_count} 成功, {fail_count} 失败)")


def main():
    parser = argparse.ArgumentParser(
        description='DA-Code评估脚本 - 支持训练集/验证集/测试集',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  python test/evaluate_results.py --dataset train   # 50个训练任务
  python test/evaluate_results.py --dataset val     # 50个验证任务
  python test/evaluate_results.py --dataset test    # 59个测试任务
  python test/evaluate_results.py --mode quick      # 5个快速测试任务
        """
    )

    # 新参数: --dataset (推荐使用)
    parser.add_argument('--dataset', choices=['quick', 'train', 'val', 'test'],
                       help='数据集选择: quick(5), train(50), val(50), test(59)')

    # 旧参数: --mode (向后兼容)
    parser.add_argument('--mode', choices=['quick', 'baseline'],
                       help='[已弃用] 使用 --dataset 代替。quick=5任务, baseline=test')

    # 输出目录参数
    parser.add_argument('--output-dir', type=str, default='output_dir',
                       help='输出目录名称 (默认: output_dir, Dynamic Agent使用: output_dir_dynamic)')

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

    # 构建输出目录完整路径
    output_dir = os.path.join(PROJECT_ROOT, "agent_workspace", args.output_dir)

    # 获取或创建评估配置文件
    eval_json = get_eval_config_file(dataset)
    if eval_json is None:
        eval_json = create_eval_config(dataset, task_ids)

    print(f"✓ 数据集: {dataset}")
    print(f"✓ 任务数: {len(task_ids)}")
    print(f"✓ 配置文件: {eval_json}")
    print(f"✓ 输出目录: {output_dir}")
    print()

    # 【新增】可视化任务后处理
    post_process_visualization_tasks(output_dir, eval_json)

    # 运行评估
    evaluator = Evaluator(output_dir=output_dir, gold_dir=GOLD_DIR, timeout_seconds=300)
    try:
        results = evaluator.evaluate(env_config=eval_json)
    except Exception as e:
        print(f"评估过程中发生错误: {e}")
        import traceback
        traceback.print_exc()
        results = []

    # 检查是否有结果
    if not results:
        print(f"\n{'='*60}")
        print(f"评估失败 - 没有成功评估的任务")
        print(f"{'='*60}")
        print(f"请检查输出目录结构和文件格式")
        print(f"输出目录: {output_dir}")
        return

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
    print(f"{'='*60}")
    
    # 打印详细任务列表
    print(f"\n任务详情:")
    for r in results:
        score = r['total_score']
        task_id = r['id']  # 评估器返回的是 'id' 而不是 'task_id'
        
        # 根据得分确定状态和图标
        if score >= 0.9:
            status = "✓ 成功"
        elif score > 0:
            status = "⚠ 部分"
        else:
            status = "✗ 失败"
        
        print(f"  {status} {task_id:20s} (得分: {score:.4f})")
    
    print(f"{'='*60}\n")

    # 【新增】复制 Gold 结果到输出目录
    copy_gold_results(output_dir, eval_json, GOLD_DIR)

    # 保存
    os.makedirs(LOGS_DIR, exist_ok=True)
    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    # 从输出目录名提取标识符
    output_dir_name = args.output_dir.replace('output_dir', '').replace('_', '') or 'stage1'
    result_file = os.path.join(LOGS_DIR, f"dacode_eval_{dataset}_{output_dir_name}_{timestamp}.json")

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
