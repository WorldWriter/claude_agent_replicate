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

# 显示帮助
help:
	@echo "DA-Code Benchmark 快捷命令:"
	@echo ""
	@echo "运行测试:"
	@echo "  make quick          - Stage 2 快速测试（5个任务）"
	@echo "  make baseline       - Stage 2 Baseline 测试（59个任务）"
	@echo "  make quick-stage1   - Stage 1 快速测试（对比）"
	@echo ""
	@echo "评估结果:"
	@echo "  make eval-quick     - 评估 Quick 结果"
	@echo "  make eval-baseline  - 评估 Baseline 结果"
	@echo ""
	@echo "数据集管理:"
	@echo "  make setup-datasets - 生成训练集/验证集划分"
