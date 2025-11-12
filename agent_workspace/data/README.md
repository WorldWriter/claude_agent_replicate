# 成本异常检测数据分析Agent - 数据集集合
## 备选集1

| 名称    | 简要说明         | 链接                   |
| ---------- | ------------------------ | ----------------------- |
| **AutonLab / TimeSeries-PILE**                   | 来自多个领域（健康、工程、金融等），包含大量时序，适合做 forecast + anomaly detection 验证。([Hugging Face][1]) | [https://huggingface.co/datasets/AutonLab/Timeseries-PILE](https://huggingface.co/datasets/AutonLab/Timeseries-PILE) ([Hugging Face][1])                                     |
| **aegean-ai / engine-anomaly-detection-dataset** | 引擎相关异常检测数据集，有明确异常与时间成分，可能可用于你做“指标某天异常后回落 /不回落”的类型。([Hugging Face][2])            | [https://huggingface.co/datasets/aegean-ai/engine-anomaly-detection-dataset](https://huggingface.co/datasets/aegean-ai/engine-anomaly-detection-dataset) ([Hugging Face][2]) |

[1]: https://huggingface.co/datasets/AutonLab/Timeseries-PILE?utm_source=chatgpt.com "AutonLab/Timeseries-PILE · Datasets at Hugging Face"
[2]: https://huggingface.co/datasets/aegean-ai/engine-anomaly-detection-dataset/tree/main?utm_source=chatgpt.com "aegean-ai/engine-anomaly-detection-dataset at main"


## 备选集2
1. GCP Cloud Billing Cost（云账单字段齐全，天然适合做成本异常与切片归因）
https://huggingface.co/datasets/sairamn/gcp-cloud-billing-cost
 
2. Monash Time-Series Forecasting Repo（含 kaggle_web_traffic 子集：14万+维基页面日序列，可按“页面/项目/国家”等维度切片后做异常→归因链路）
https://huggingface.co/datasets/Monash-University/monash_tsf
 （其中 kaggle_web_traffic* 配置） 

3. Favorita Store Sales（门店×品类×日期的经典分层序列，做“异常日→州/店/品类贡献拆解”手到擒来）
https://huggingface.co/datasets/t4tiana/store-sales-time-series-forecasting


4. Time-series PILE（跨行业时序大合集，练检测器与稳健基线，之后把逻辑迁到你的成本表）
https://huggingface.co/datasets/AutonLab/Timeseries-PILE
 

5. Engine Anomaly Detection（有明确异常标签的工业时序，先把“尖峰/持续异常”分型打磨好，再移植到成本域）
https://huggingface.co/datasets/aegean-ai/engine-anomaly-detection-dataset
