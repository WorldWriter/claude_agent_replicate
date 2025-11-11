# 最简Agent实现 - 数据挖掘系统

## 架构设计

基于 **Plan-Execute-Reflect** 循环的最简Agent实现（228行代码）

### 文件结构

```
agent_architecture/
├── llm_client.py    # LLM接口封装 (43行)
├── tools.py         # 工具函数集 (81行)
├── agent.py         # Agent核心 (78行)
├── main.py          # 程序入口 (26行)
└── .env             # 配置文件
```

## 快速开始

### 1. 安装依赖

```bash
pip install anthropic requests pandas matplotlib numpy python-dotenv
```

### 2. 配置API密钥

编辑 `.env` 文件：
- 如使用Anthropic Claude: 保持 `LLM_PROVIDER=anthropic`
- 如使用Kimi K2: 修改为 `LLM_PROVIDER=kimi`，并填写 `MOONSHOT_API_KEY`

### 3. 运行Agent

```bash
python main.py
```

## 核心功能

### Agent能力
- 自主规划任务步骤
- 动态选择和调用工具
- 反思执行结果并调整策略
- 最多10轮迭代完成任务

### 工具集
1. **read_csv_file**: 读取CSV并返回统计摘要
2. **analyze_data**: 执行pandas数据分析代码
3. **execute_python**: 执行任意Python代码
4. **visualize_data**: 生成matplotlib图表

### 日志输出

每轮迭代打印：
- `[PLAN]`: LLM生成的执行计划
- `[EXECUTE]`: 工具执行过程和结果
- `[REFLECT]`: 对结果的反思和下一步决策

## 任务示例

默认任务：分析 `data/full_gcp_data.csv`
1. 读取GCP成本数据
2. 成本异常检测
3. 多维度归因分析（按服务/地区/资源）
4. 生成可视化图表

## 自定义任务

修改 `main.py` 中的 `task` 变量：

```python
task = """
你的自定义任务描述
"""
```

## 架构特点

- **极简设计**: 不到230行实现完整Agent
- **模块化**: 清晰分离LLM、工具、逻辑
- **可扩展**: 易于添加新工具和能力
- **完整日志**: 所有步骤可追溯
