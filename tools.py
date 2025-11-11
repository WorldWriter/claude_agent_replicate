"""Agent工具集 - 文件读取、数据分析、Python执行、可视化"""
import os
import json
import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
from io import StringIO


def read_csv_file(file_path, nrows=None):
    """读取CSV文件并返回摘要统计"""
    try:
        df = pd.read_csv(file_path, nrows=nrows)
        summary = {
            "shape": df.shape,
            "columns": df.columns.tolist(),
            "dtypes": df.dtypes.astype(str).to_dict(),
            "head": df.head(5).to_dict('records'),
            "describe": df.describe().to_dict()
        }
        return {"success": True, "data": summary, "df_stored": True}
    except Exception as e:
        return {"success": False, "error": str(e)}


def analyze_data(code, df=None):
    """执行pandas数据分析代码"""
    try:
        local_vars = {"df": df, "pd": pd, "np": np}
        exec(code, {}, local_vars)
        result = local_vars.get("result", "执行成功，无返回值")
        return {"success": True, "result": str(result)}
    except Exception as e:
        return {"success": False, "error": str(e)}


def execute_python(code):
    """执行任意Python代码"""
    try:
        output = StringIO()
        local_vars = {"pd": pd, "np": np, "plt": plt}
        exec(code, local_vars)
        result = local_vars.get("result", "执行成功")
        return {"success": True, "result": str(result)}
    except Exception as e:
        return {"success": False, "error": str(e)}


def visualize_data(df, chart_type, x_col=None, y_col=None, title="", output_path="results/chart.png"):
    """生成数据可视化图表"""
    try:
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        plt.figure(figsize=(10, 6))

        if chart_type == "hist":
            df[y_col].hist(bins=30)
        elif chart_type == "scatter":
            plt.scatter(df[x_col], df[y_col])
        elif chart_type == "line":
            df.plot(x=x_col, y=y_col, kind='line')
        elif chart_type == "bar":
            df.groupby(x_col)[y_col].mean().plot(kind='bar')

        plt.title(title)
        plt.tight_layout()
        plt.savefig(output_path)
        plt.close()
        return {"success": True, "path": output_path}
    except Exception as e:
        return {"success": False, "error": str(e)}


# 工具注册表
TOOLS = {
    "read_csv_file": read_csv_file,
    "analyze_data": analyze_data,
    "execute_python": execute_python,
    "visualize_data": visualize_data
}
