"""MFE5130 d 项：批量计算欧式、美式底层对应的衍生品 X 价格。"""

import argparse
from dataclasses import asdict, dataclass, replace
from pathlib import Path

import numpy as np
import pandas as pd


@dataclass(frozen=True)
class Contract:
    """一组合同条款及树的步数。T 和 C 的单位为年。"""

    k1: float = 30.0
    k2: float = 550.0
    k3: float = 600.0
    h: float = 100.0
    sign: int = 1  # 题目中的 N，只作用于第一个候选支付
    T: float = 1.0
    C: float = 0.5
    n: int = 20  # 从今天到 X 到期的步数


def positive_number(text):
    """检查终端传入的 K1 是否为有限的正数。"""
    try:
        value = float(text)
    except ValueError as error:
        raise argparse.ArgumentTypeError("K1 必须是数字，例如 25.5。") from error
    if not np.isfinite(value) or value <= 0:
        raise argparse.ArgumentTypeError("K1 必须是有限的正数。")
    return value


def load_market(project_dir):
    """读取 Excel 参数汇总 B55:B58 中的定价输入。"""
    data_path = project_dir / "data" / "KO2015-2025.xlsx"
    summary = pd.read_excel(data_path, sheet_name="参数汇总", header=None)
    # pandas 的行列位置从零开始。四个单元格分别是年化 σ、连续 q、连续 r 和实际收盘价。
    sigma, q, r, s0 = summary.iloc[54:58, 1].to_numpy(dtype=float)
    return dict(sigma=sigma, q=q, r=r, s0=s0)


def x_payoff(contract, v1_k2, v1_k3):
    """在 T 用两份 V1 的节点价值计算 X 的支付。"""
    # 当 N=-1 时，第一项变成 K1-V1。第二项始终是 V1-K1。
    branch_1 = contract.sign * (v1_k2 - contract.k1)
    branch_2 = v1_k3 - contract.k1
    return np.maximum(np.maximum(branch_1, branch_2), 0.0)


def price_x(contract, *, sigma, q, r, s0):
    """在同一股票树上计算欧式、美式底层对应的 X 价格。"""
    dt = contract.T / contract.n
    extra_steps = round(contract.C / dt)
    # T 与 T+C 均须落在树的时间网格上，避免改变合同到期日。
    if extra_steps < 1 or not np.isclose(extra_steps * dt, contract.C, rtol=0, atol=1e-12):
        raise ValueError("请调整 n，使 C 是时间步长 T/n 的整数倍。")
    total_steps = contract.n + extra_steps

    # 股票的风险中性预期增长用 r-q，期权的未来现金用无风险利率 r 折现。
    growth = (r - q) * dt
    movement = sigma * np.sqrt(dt)
    u = np.exp(growth + movement)
    d = np.exp(growth - movement)
    p = (np.exp(growth) - d) / (u - d)
    discount = np.exp(-r * dt)
    if not 0 < p < 1:
        raise ValueError("风险中性概率必须在 0 和 1 之间。")

    def stock_layer(i):
        """按需要生成一层股价，使加密网格时无需存储整棵树。"""
        # 第 j 个节点有 j 次上涨和 i-j 次下跌。将 u^j*d^(i-j) 合并到一个指数中。
        up_moves = np.arange(i + 1)
        return s0 * np.exp(i * growth + (2 * up_moves - i) * movement)

    terminal_stock = stock_layer(total_steps)

    def roll_back(values):
        """将下一层的节点价值按风险中性概率加权并折现。"""
        # 对当前层 j，下跌子节点是下一层 j，上涨子节点是下一层 j+1。
        return discount * ((1 - p) * values[:-1] + p * values[1:])

    def inner_at_T(strike, *, american):
        """把给定门槛的 V1 从 T+C 回推到 T。"""
        # np.clip(x, 0, H) 表示低于零时取零，高于 H 时取 H。
        values = np.clip(terminal_stock ** 1.5 - strike, 0.0, contract.h)
        for i in range(total_steps - 1, contract.n - 1, -1):
            values = roll_back(values)
            if american:
                # 美式 V1 在当前节点比较立即行权与继续持有。
                exercise = np.clip(stock_layer(i) ** 1.5 - strike, 0.0, contract.h)
                values = np.maximum(values, exercise)
        return values

    # 共用同一套股价节点，返回顺序固定为欧式、美式。
    prices = []
    for american in (False, True):
        v1_k2 = inner_at_T(contract.k2, american=american)
        v1_k3 = inner_at_T(contract.k3, american=american)
        # 在 T 逐节点计算 X 的到期支付。N 只改变第一项的方向。
        values = x_payoff(contract, v1_k2, v1_k3)

        # X 在 T 支付，外层只做风险中性折现。
        for _ in range(contract.n):
            values = roll_back(values)
        prices.append(float(values[0]))

    return tuple(prices)


def default_scenarios():
    """每组只改变一个参数，便于与基准合约直接比较。"""
    base = Contract()
    changes = {
        "k1": (20.0, 40.0),
        "k2": (500.0, 600.0),
        "k3": (500.0, 650.0),
        "h": (60.0, 140.0),
        "sign": (-1,),
        "T": (0.5, 2.0),
        "C": (0.25, 1.0),
        "n": (40, 80),
    }
    labels = {"k1": "K1", "k2": "K2", "k3": "K3", "h": "H", "sign": "N"}
    scenarios = [("Base", base)]
    for field, values in changes.items():
        for value in values:
            label = f"{labels.get(field, field)}={value:g}"
            # replace 创建新对象，仅覆盖这一轮正在比较的字段。
            scenarios.append((label, replace(base, **{field: value})))
    return scenarios


def main():
    """运行 d 项情形比较，或用 --k1 单独试算指定门槛。"""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--k1", type=positive_number, nargs="+",
        help="只比较指定的 K1。省略此选项时运行完整 d 项并导出 CSV。",
    )
    args = parser.parse_args()
    project_dir = Path(__file__).resolve().parent

    market = load_market(project_dir)

    if args.k1 is None:
        scenarios = default_scenarios()
    else:
        scenarios = [(f"K1={k1:g}", Contract(k1=k1)) for k1 in args.k1]

    rows = []
    for label, contract in scenarios:
        european, american = price_x(contract, **market)
        rows.append({
            "scenario": label,
            **asdict(contract),
            "European": european,
            "American": american,
            "American_minus_European": american - european,
        })

    # 保留完整精度保存；终端只把价格显示到小数点后六位。
    results = pd.DataFrame(rows).rename(
        columns={"k1": "K1", "k2": "K2", "k3": "K3", "h": "H", "sign": "N"},
    )
    price_columns = ("European", "American", "American_minus_European")
    print(results.to_string(index=False, formatters={name: "{:.6f}".format for name in price_columns}))
    if args.k1 is None:
        output_dir = project_dir / "results"
        output_dir.mkdir(exist_ok=True)
        output_file = output_dir / "d_scenarios.csv"
        results.to_csv(output_file, index=False, encoding="utf-8-sig")
        print(f"结果已保存到 {output_file}")


# 直接运行才执行批量定价，供 e、g、h 导入时只加载函数。
if __name__ == "__main__":
    main()
