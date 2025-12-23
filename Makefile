.PHONY: quick baseline eval-quick eval-baseline setup-datasets help

# Stage 2 快速测试（5个任务）
quick:
	python test/run_benchmark.py --mode quick --agent dynamic

# Stage 2 Baseline 测试（59个任务）
baseline:
	python test/run_benchmark.py --mode baseline --agent dynamic

# Stage 1 快速测试（对比）
quick-stage1:
	python test/run_benchmark.py --mode quick --agent minimal

# 评估 Quick 结果
eval-quick:
	python test/evaluate_results.py --dataset quick --output-dir output_dir_dynamic

# 评估 Baseline 结果
eval-baseline:
	python test/evaluate_results.py --dataset test --output-dir output_dir_dynamic

# 生成训练集/验证集划分
setup-datasets:
	python test/setup_datasets.py

# SubAgent示例
example-subagent-multi:
	@echo "运行 SubAgent 多文件分析示例..."
	python examples/subagent_multi_file.py

example-subagent-recursion:
	@echo "运行 SubAgent 递归深度示例..."
	python examples/subagent_recursion.py

# Stage 2/3 功能测试
test-dynamic:
	@echo "运行 Dynamic Plan Agent 单元测试..."
	python -m pytest test_dynamic_plan_agent.py -v

# 显示帮助
help:
	@echo "DA-Code Benchmark & Agent Testing 快捷命令:"
	@echo ""
	@echo "📊 DA-Code 基准测试:"
	@echo "  make quick          - Stage 2/3 快速测试（5个任务）"
	@echo "  make baseline       - Stage 2/3 Baseline 测试（59个任务）"
	@echo "  make quick-stage1   - Stage 1 快速测试（对比）"
	@echo ""
	@echo "📈 评估结果:"
	@echo "  make eval-quick     - 评估 Quick 结果"
	@echo "  make eval-baseline  - 评估 Baseline 结果"
	@echo ""
	@echo "🧪 单元测试:"
	@echo "  make test-dynamic   - 运行 Dynamic Plan Agent 单元测试"
	@echo ""
	@echo "🚀 SubAgent 示例 (Stage 3):"
	@echo "  make example-subagent-multi      - 批量文件分析示例"
	@echo "  make example-subagent-recursion  - 递归深度控制示例"
	@echo ""
	@echo "🗂️  数据集管理:"
	@echo "  make setup-datasets - 生成训练集/验证集划分"
