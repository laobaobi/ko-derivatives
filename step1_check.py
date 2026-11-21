import sys
from pathlib import Path

import numpy as np
import pandas as pd
import matplotlib

print("当前 Python：", sys.executable)
print("NumPy 版本：", np.__version__)
print("Pandas 版本：", pd.__version__)
print("Matplotlib 版本：", matplotlib.__version__)

data_path = Path("C:/Users/86183/Desktop/KO2015-2025.xlsx")

print("数据文件是否存在：", data_path.exists())