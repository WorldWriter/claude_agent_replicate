这是根据我们之前的讨论，为您整理的关于 **Data Agent / Code Agent** 相关数据集的完整清单。

为了方便您针对 **“数据异常检测与归因 Agent”** 进行选型，我特别增加了一列 **“对您项目的适配度”** 并按此排序。

### **核心基准测试集 (Benchmarks)**

这些主要用于**评估**您的 Agent 聪明程度和代码能力。

| 数据集名称 | 核心特性 | 推出时间 | 优点 (Pros) | 缺点/局限 (Cons) | 您的项目适配度 | Hugging Face / 资源链接 |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **DSBench** | **端到端数据科学**<br>(End-to-End) | 2024.02 | **最硬核**。涵盖规划、清洗、建模全流程，最接近真实的“归因分析”工作流。 | 难度极高，环境配置复杂，包含大量机器学习任务而非纯分析。 | ⭐⭐⭐⭐⭐<br>(架构参考首选) | [GitHub (主)](https://www.google.com/search?q=https://github.com/LiZhe2004/DSBench)<br>*(HF暂无官方托管)* |
| **Spider 2.0** | **企业级 Text-to-SQL**<br>(Enterprise SQL) | 2024.10 | **真实环境**。涉及云数据库 (BigQuery)、海量宽表和外部文档，考察 SQL 检索能力。 | 仅限 SQL，不涉及 Python 分析（如 Pandas/Plotting），难以做复杂的归因逻辑。 | ⭐⭐⭐⭐<br>(SQL查询能力) | [xlangai/spider2-lite](https://huggingface.co/datasets/xlangai/spider2-lite) |
| **DABStep** | **多步推理 + 文档**<br>(Multi-step Reasoning) | 2025 | **混合模态**。必须结合 Markdown 文档规则和 CSV 数据才能解题，模拟“查阅业务手册排查问题”。 | 偏重金融/费率计算，更像是在做“审计”而非“异常归因”。 | ⭐⭐⭐⭐<br>(文档理解能力) | [adyen/DABstep](https://huggingface.co/datasets/adyen/DABstep) |
| **DA-Code** | **代码片段生成**<br>(Code Snippets) | 2024.10 | **基本功**。专注于标准库 (Pandas/Sklearn) 的具体操作，任务粒度细。 | 缺乏宏观的“解决问题”视角，只是在写代码片段。 | ⭐⭐⭐<br>(基础代码能力) | [Luo2003/DA-Code](https://huggingface.co/datasets/Luo2003/DA-Code) |
| **DABench**<br>*(InfiAgent)* | **Text-to-Pandas**<br>(QA focused) | 2024.01 | **问答型**。适合测试“Chat BI”类功能，格式统一。 | 题目较简单，多为单步计算，缺乏深度分析。 | ⭐⭐⭐<br>(基础问答) | [InfiAgent/DAEval](https://www.google.com/search?q=https://huggingface.co/datasets/InfiAgent/DAEval) |
| **DataBench** | **表格问答**<br>(Table QA) | \~2024 | **语义理解**。侧重于阅读表格回答问题，而非写代码。 | **不涉及代码生成**，无法测试 Agent 的执行能力。 | ⭐<br>(不推荐) | [cardiffnlp/databench](https://huggingface.co/datasets/cardiffnlp/databench) |

-----

| 数据集名称        | 对应论文/项目全名                                                                 | 发表 / 接收会议                                     | 会议级别 & 影响力简评                                           | 备注 |
|-------------------|------------------------------------------------------------------------------------|----------------------------------------------------|------------------------------------------------------------------|------|
| DSBench           | DSBench: How Far Are Data Science Agents from Becoming Data Science Experts?      | **ICLR 2025 Poster** :contentReference[oaicite:0]{index=0} | ICLR 顶会，poster 论文；引用数、话题热度都在明显上升，算当前 data-science-agent 方向的主力基准之一。 | 和你想做的“端到端归因 / Agent”关系非常近，可当核心背景引用。 |
| Spider 2.0        | Spider 2.0: Evaluating Language Models on Real-World Enterprise Text-to-SQL Workflows | **ICLR 2025 Oral** :contentReference[oaicite:1]{index=1} | ICLR 口头报告，含官网 + leaderboard，已经是 Text-to-SQL / enterprise workflow 里的“新一代标杆”。 | 在 SQL / enterprise workflow 圈子里话题度很高，适合当“真实企业场景难度”的典型例子。 |
| DABStep           | DABstep: Data Agent Benchmark for Multi-step Reasoning                            | **当前为 arXiv 预印本，暂无公开会议记录** :contentReference[oaicite:2]{index=2} | 工程质量高、Adyen + HF 联合推出，有 leaderboard 和 blog，但学术层面目前还是 preprint 阶段，影响力在发酵中。 | 更像工业界主导的 benchmark，适合你讲“多步推理 + 文档 + 数据分析”的最新趋势。 |
| DA-Code           | DA-Code: Agent Data Science Code Generation Benchmark for Large Language Models   | **EMNLP 2024 Main Conference** :contentReference[oaicite:3]{index=3} | EMNLP 顶会正会论文，专注 agent 式 data-science code generation，已被不少后续工作引用。 | 代码层面 benchmarking 很对你胃口，适合作为“细粒度 Pandas/SKLearn 能力”的对比基准。 |
| DABench (InfiAgent) | InfiAgent-DABench: Evaluating Agents on Data Analysis Tasks                     | **ICML 2024** :contentReference[oaicite:4]{index=4} | ICML 顶会论文，比较早期针对 data-analysis agent 的 benchmark，引用数已经破百，历史地位不错。 | 你要写“agent in data analysis”综述，基本绕不过去，可以和 DSBench/DABstep 同列比较。 |
| DataBench         | Question Answering over Tabular Data with DataBench: A Large-Scale Empirical Evaluation of LLMs | **LREC-COLING 2024**（数据集论文）:contentReference[oaicite:5]{index=5} | 偏 NLP 资源型会议，主打“大规模表格问答评测”；同时作为 **SemEval 2025 Task 8** 的基础数据集，赛事带了一波热度。 | 更偏 Table QA / language-to-table，不是代码/agent 主线，用来补全 related work 即可。 |


### **原始训练素材 (Raw Datasets for Attribution)**

这些不是现成的考题，而是**原材料**。您需要用这些数据来构建自己的“异常注入与归因”训练场。

| 数据集名称 | 领域 | 推荐理由 | 如何用于您的 Agent | 链接 |
| :--- | :--- | :--- | :--- | :--- |
| **M5 Forecasting** | 零售/时序 | **层级结构极佳**。<br>(State -\> Store -\> Category -\> Item)，非常适合训练“下钻归因”。 | **注入异常：** 修改底层 Item 销量。<br>**任务：** 让 Agent 从顶层 Total Sales 找出这个 Item。 | [Kaggle Link](https://www.kaggle.com/c/m5-forecasting-accuracy) |
| **SMD**<br>*(Server Machine Dataset)* | 运维/AIOps | **自带标注**。<br>包含大量真实的异常事件和多维指标。 | **训练：** 输入多维 CPU/Mem 指标，让 Agent 判断异常时间点及核心影响维度。 | [GitHub Link](https://github.com/NetManAIOps/OmniAnomaly) |
| **Rossmann Sales** | 零售/运营 | **外部因素丰富**。<br>包含节假日、促销、竞争对手距离等特征。 | **训练：** 让 Agent 归因销量波动是由于“周末”还是“促销结束”。 | [Kaggle Link](https://www.kaggle.com/c/rossmann-store-sales) |

### **给您的建议路径 (Next Steps)**

1.  **能力基座:** 使用 **Spider 2.0** (SQL部分) 和 **DA-Code** (Python部分) 来微调或测试您的基座模型，确保它懂基本的“数据方言”。
2.  **逻辑大脑:** 参考 **DSBench** 的 Agent 架构（Planning -\> Coding -\> Debugging），这是目前最科学的数据 Agent 设计范式。
3.  **实战演练:** 编写脚本对 **M5 Forecasting** 进行“下毒”（注入异常），生成属于您自己的、独一无二的归因测试集。这是目前开源界没有，但对企业应用价值最大的部分。