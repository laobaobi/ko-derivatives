"""检查 VS Code 实际使用的 Python、依赖库和项目输入。"""

import sys
from pathlib import Path

import numpy as np
import pandas as pd
import matplotlib

# 用解释器的绝对路径确认是否从项目的 .venv 运行。
print("当前 Python：", sys.executable)
print("NumPy 版本：", np.__version__)
print("Pandas 版本：", pd.__version__)
print("Matplotlib 版本：", matplotlib.__version__)

# 与定价脚本使用同一个项目内的工作簿路径。
data_path = Path(__file__).resolve().parent / "data" / "KO2015-2025.xlsx"

print("数据文件是否存在：", data_path.is_file())
