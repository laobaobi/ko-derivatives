"""读取 KO 市场参数，并用 20 步基准树演示 X 的两阶段定价。"""

from pathlib import Path
import pandas as pd
import numpy as np

# __file__ 是当前脚本的路径。
# resolve() 将它转换为绝对路径，parent 获取脚本所在的项目目录。
project_dir = Path(__file__).resolve().parent

# 从项目内的 data 目录读取文件，不再依赖个人桌面路径。
data_path = project_dir / "data" / "KO2015-2025.xlsx"

# 文件不存在时，给出明确提示，方便检查文件名和存放位置。
if not data_path.is_file():
    raise FileNotFoundError(f"找不到数据文件：{data_path}")

# header=None 表示不把第一行当作列名。
# 这样 DataFrame 的行号、列号可以直接对应 Excel 的位置。
summary = pd.read_excel(
    data_path,
    sheet_name="参数汇总",
    header=None,
    engine="openpyxl",
)

# iloc 的行号和列号从 0 开始：
# Excel 第 55 行对应索引 54，B 列对应索引 1。
# B55:B58 依次是年化波动率、连续股息率、连续利率和不复权现货价。
# 这些值由 Excel 预处理得到，Python 直接读取工作簿已保存的结果。
sigma = float(summary.iloc[54, 1])
q = float(summary.iloc[55, 1])
r = float(summary.iloc[56, 1])
s0 = float(summary.iloc[57, 1])

# 百分号格式只影响屏幕显示，不改变变量中的原始数值。
# 例如 sigma 实际保存约 0.182194，而不是 18.2194。
print(f"现货价格 S0：{s0:.6f} 美元")
print(f"年化波动率 sigma：{sigma:.6%}")
print(f"连续股息率 q：{q:.6%}")
print(f"连续无风险利率 r：{r:.6%}")
print(f"风险中性持有收益 r-q：{r - q:.6%}")

# T 是衍生品 X 的到期期限，单位为年。
# n 是从今天到 T 的时间步数，题目要求至少为 20。
T = 1.0
n = 20

# 每一步的时间长度，单位也是年。
dt = T / n

# 持有收益决定每一步的增长部分；
# 波动率乘以时间平方根，决定上下分支的变动幅度。
growth = (r - q) * dt
movement = sigma * np.sqrt(dt)

# 上涨因子和下跌因子都包含持有收益。
u = np.exp(growth + movement)
d = np.exp(growth - movement)

# 由 p*u + (1-p)*d = exp((r-q)*dt) 解出定价用的上涨权重。
p = (np.exp(growth) - d) / (u - d)

# 未来一步支付折算到当前节点时使用的折现因子。
discount = np.exp(-r * dt)

print("\n股票树的单步参数：")
print(f"每步时间 dt：{dt:.6f} 年")
print(f"上涨因子 u：{u:.6f}")
print(f"下跌因子 d：{d:.6f}")
print(f"风险中性上涨概率 p：{p:.6f}")
print(f"单步折现因子：{discount:.6f}")

# 展示从今天出发，第一步的两个可能股价。
print(f"第一步上涨后的股价：{s0 * u:.6f} 美元")
print(f"第一步下跌后的股价：{s0 * d:.6f} 美元")

# 检查概率是否合法。
if not 0 < p < 1:
    raise ValueError("风险中性概率必须位于 0 和 1 之间。")

# 用计算得到的 p 回代，检查浮点计算是否满足风险中性增长条件。
expected_growth = p * u + (1 - p) * d
target_growth = np.exp((r - q) * dt)

if not np.isclose(expected_growth, target_growth, rtol=1e-12, atol=1e-12):
    raise ValueError("股票树没有满足风险中性增长条件。")

print("检查通过：概率合法，风险中性增长条件成立。")

# C 是 X 到期后，底层期权剩余的期限，单位为年。
C = 0.5
extra_steps = round(C / dt)

# 确认 T+C 正好落在网格上，避免四舍五入悄悄改变到期日。
if not np.isclose(extra_steps * dt, C, rtol=0, atol=1e-12):
    raise ValueError("请调整 n，使底层期权到期日落在树的时间网格上。")

total_steps = n + extra_steps

# 外层列表按时间步保存各层；每层的股价按上涨次数从少到多排列。
stock_tree = []
for i in range(total_steps + 1):
    up_moves = np.arange(i + 1)   # 可能上涨 0 到 i 次
    down_moves = i - up_moves   # 每条路径一共走 i 步
    prices = s0 * u**up_moves * d**down_moves
    stock_tree.append(prices)

# 打印前 3 层，核对起点、单步分支和第 2 步的重组结果。
for i in range(3):
    print(f"第 {i} 层股价：{stock_tree[i].round(6)}")

# 第 0 层是今天，所以 30 个时间步对应 31 层。
print(f"X 到期（第 {n} 层）：{len(stock_tree[n])} 个节点")
print(f"底层期权到期（第 {total_steps} 层）："
      f"{len(stock_tree[total_steps])} 个节点")

# K2、K3 与 S 的 3/2 次方比较，基准两门槛分列在 S0^(3/2) 两侧。
# H 限制任一底层期权的行权收益，单位是美元。
K2 = 550.0
K3 = 600.0
H = 100.0

def inner_value_at_T(strike, american=False):
    """计算底层期权在 T 层各节点的价值，默认使用欧式行权规则。"""
    # 在 T+C，两种期权都按同一个公式计算到期支付。
    values = np.clip(stock_tree[total_steps] ** 1.5 - strike, 0.0, H)

    # i 是回推后所在的层。最后一次 i=n，也就是 X 到期的 T 层。
    for i in range(total_steps - 1, n - 1, -1):
        # 下一层 j 是下跌子节点，j+1 是上涨子节点。切片把它们逐个对齐。
        # 加权并折现一小步，得到当前层的继续持有价值。
        continuation = discount * ((1 - p) * values[:-1] + p * values[1:])

        if american:
            # 立即行权要用当前层的股价，并与继续持有价值逐节点比较。
            exercise = np.clip(stock_tree[i] ** 1.5 - strike, 0.0, H)
            values = np.maximum(exercise, continuation)
        else:
            values = continuation

    return values


# 先取两份欧式底层期权的节点价值，用于演示 T 层上的支付输入。
v1_k2 = inner_value_at_T(K2)
v1_k3 = inner_value_at_T(K3)

# 选取 T 层的中间节点，在同一个股价下比较两份期权的价值。
middle = n // 2
print(f"\nT 层节点数：K2 对应 {len(v1_k2)} 个，K3 对应 {len(v1_k3)} 个")
print(f"T 层中间节点股价：{stock_tree[n][middle]:.6f} 美元")
print(f"K2 = {K2:g} 时的欧式底层期权价值：{v1_k2[middle]:.6f} 美元")
print(f"K3 = {K3:g} 时的欧式底层期权价值：{v1_k3[middle]:.6f} 美元")

# K1 是 X 支付公式中的门槛。N 只作用于第一个候选支付。
K1 = 30.0
N = 1

def price_x(*, american):
    """计算 X 今天的价格。american 控制底层期权的行权方式。"""
    # 先求两份底层期权在 T 层各个股价节点上的价值。
    v1_k2 = inner_value_at_T(K2, american=american)
    v1_k3 = inner_value_at_T(K3, american=american)

    # 在每个节点比较两个候选支付和零。N 只作用于第一项。
    branch_1 = N * (v1_k2 - K1)
    branch_2 = v1_k3 - K1
    values = np.maximum(np.maximum(branch_1, branch_2), 0.0)

    # X 的支付日固定在 T。从 T 回推 n 步时，两种情形都只加权和折现。
    for _ in range(n):
        values = discount * ((1 - p) * values[:-1] + p * values[1:])

    # 第 0 层只剩一个节点，这就是 X 今天的价格。
    return float(values[0])


# 同一个函数调用两次，分别选择欧式和美式底层。
print(f"X 今天的价格（欧式底层）：{price_x(american=False):.6f} 美元")
print(f"X 今天的价格（美式底层）：{price_x(american=True):.6f} 美元")
