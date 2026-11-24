# KO 复合衍生品定价

本项目以可口可乐股票（KO）为标的，用前向重组二叉树对复合衍生品 $X$ 定价。d 项比较合约参数变化，e 项检验树价随步数加密的稳定性。报告为 MFE5130 课程项目 f 项，另附 g 项蒙特卡洛对照和 h 项 Delta、Gamma 程序及结果。

## 最终报告

- [PDF 报告](reports/ko-pricing-report.pdf)
- [Word 可编辑版（.doc）](reports/ko-pricing-report.doc)

报告第 3 节包含 d 项两组 $N$ 的参数扫描、报价表和四张敏感性图。第 4 节列出 e 项的完整收敛序列，第 5 节汇总参数敏感性、固定行权方式时改变 $N$ 的报价差异，以及 $X$ 的基准定价。

## 基准结果

估值日为 2025 年 12 月 31 日。合约基准为 $K_1=30$、$K_2=550$、$K_3=600$、$H=100$、$T=1$ 年、$C=0.5$ 年。以下价格为估值日的美元现值。

| $N$ | 5120 步欧式底层 | 5120 步美式底层 | 欧式从 2560 到 5120 步的变化 | 美式从 2560 到 5120 步的变化 |
| --- | ---: | ---: | ---: | ---: |
| $+1$ | 20.833639 | 31.376900 | +0.0035 | −0.0148 |
| $-1$ | 22.907944 | 31.302270 | +0.0022 | +0.0351 |

固定其他基准参数和底层行权方式，将 $N$ 从 $+1$ 改为 $-1$，欧式报价增加 2.0743 美元，美式报价减少 0.0746 美元。5120 步报价用作数值参照，表中的差额衡量两档网格之间的变化。

## 在 VS Code 运行

在 VS Code 打开仓库根目录，使用 PowerShell 和 Python 3.12 或以上版本。依赖由 [pyproject.toml](pyproject.toml) 声明。

~~~powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -e .
~~~

将原始工作簿放到 `data/KO2015-2025.xlsx`。课程工作簿和配套说明留在本地，仓库提供已计算的报价和报告。脚本从工作簿的「参数汇总」读取 B55 至 B58，依次为年化波动率 $\sigma$、连续股息率 $q$、连续无风险利率 $r$ 和不复权现货价 $S_0$。程序读取已保存的单元格结果，按 `KO使用说明.pdf` 的口径处理过的数据可直接使用。

~~~powershell
# 检查解释器、依赖和输入工作簿
.\.venv\Scripts\python.exe step1_check.py

# 演示 20 步基准定价
.\.venv\Scripts\python.exe step2_read_parameters.py

# d 项代表性情形及自选外层执行价
.\.venv\Scripts\python.exe step3_validate_parameters.py
.\.venv\Scripts\python.exe step3_validate_parameters.py --k1 25.5 35

# d 项两种 N、两种底层行权方式的单参数曲线
.\.venv\Scripts\python.exe step3_plot_sensitivity_by_sign.py

# e 项收敛检验
.\.venv\Scripts\python.exe step4_convergence.py

# g 项蒙特卡洛对照和 h 项 Delta、Gamma
.\.venv\Scripts\python.exe step5_monte_carlo.py
.\.venv\Scripts\python.exe step6_greeks.py
~~~

分组绘图脚本使用 Windows 自带的宋体。`step3_plot_sensitivity.py` 提供分组脚本共用的取点和扫描函数，也可单独运行以生成早期合并视图。

## 定价方法

底层在 $T+C$ 到期，行权收益为 $g_K(S)=\min\{H,\max(S^{3/2}-K,0)\}$。程序先将门槛分别为 $K_2$ 和 $K_3$ 的两份底层回推至 $T$。欧式底层取折现持有价值，美式底层在允许行权的节点取即时行权与持有价值的较大者。

记两份底层在 $T$ 的价值为 $V_2$、$V_3$，则 $X$ 的到期支付为 $\max\{N(V_2-K_1),V_3-K_1,0\}$。程序再将该支付折现回估值日。模型采用恒定波动率、连续股息率和连续无风险利率。$n$ 是从估值日到 $T$ 的外层步数。步长为 $T/n$，底层剩余期限 $C$ 也对齐到同一时间网格。

- **d 项。** 代表性报价表以 20 步为基准。密集扫描分别固定 $N=+1$ 和 $N=-1$，依次改变 $K_1$、$K_2$、$K_3$、$H$、$T$、$C$ 或 $n$。除步数面板外统一采用 640 步。见[代表性报价](results/d_scenarios.csv)、[$N=-1$ 的代表性报价](results/d_scenarios_n_minus1.csv)和[826 行逐点报价](results/d_sensitivity_by_sign.csv)。
- **e 项。** 两种 $N$ 分别取 20 至 5120 的九个递增外层步数。`change` 是相邻两档报价的差，`gap_to_5120` 是与同一合约、同一行权方式的 5120 步报价之差。见[收敛表](results/e_convergence.csv)和[收敛图](results/e_convergence.png)。
- **g 项。** 用 25 万组对偶样本模拟 $S_T$，解析计算各模拟点的欧式底层价值，再估计 $X$ 的价格和抽样置信区间。见[蒙特卡洛结果](results/g_monte_carlo.csv)。
- **h 项。** 固定其余输入，分别按现货价的 0.5%、1% 和 2% 上下扰动现货，用中心差分估算 Delta 和 Gamma。见[敏感度结果](results/h_greeks.csv)。

| d 项敏感性图 | 欧式底层 | 美式底层 |
| --- | --- | --- |
| $N=+1$ | [欧式曲线](results/d_plus_european.png) | [美式曲线](results/d_plus_american.png) |
| $N=-1$ | [欧式曲线](results/d_minus_european.png) | [美式曲线](results/d_minus_american.png) |
