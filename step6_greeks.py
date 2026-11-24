"""MFE5130 h 项：估计 KO 衍生品 X 的股票 Delta 和 Gamma。"""

from pathlib import Path

import numpy as np
import pandas as pd

from step3_validate_parameters import Contract, load_market, price_x


def greeks(market):
    """h：固定合约和市场中的其他输入，以中心差分估计 X 的 Greeks。"""
    s0 = market["s0"]
    rows = []
    for n in (1280, 5120):
        # 同一网格的基准价只算一次，并复用于该网格下的三个扰动幅度。
        contract = Contract(n=n)
        center = np.array(price_x(contract, **market))
        for bump_pct in (0.005, 0.01, 0.02):
            bump = s0 * bump_pct
            # 用字典合并复制市场输入，只覆盖 s0，保持 σ、q、r 不变。
            down = np.array(price_x(contract, **(market | {"s0": s0 - bump})))
            up = np.array(price_x(contract, **(market | {"s0": s0 + bump})))
            # Delta 是一阶中心差分。Gamma 是二阶中心差分，对网格误差更敏感。
            deltas = (up - down) / (2 * bump)
            gammas = (up - 2 * center + down) / bump**2
            # 定价器返回顺序为欧式、美式。保存三次价格，方便核对差分。
            for i, style in enumerate(("European", "American")):
                rows.append(dict(
                    style=style, n=n, bump_pct=bump_pct, bump_USD=bump, S0=s0,
                    X_down=down[i], X_base=center[i], X_up=up[i],
                    Delta=deltas[i], Gamma=gammas[i],
                ))
    return pd.DataFrame(rows)


def main():
    """运行基准合约的股价敏感度实验并写入 CSV。"""
    # 相对脚本位置定位数据和输出，在 VS Code 中直接运行也能找到文件。
    project_dir = Path(__file__).resolve().parent
    market = load_market(project_dir)
    output_dir = project_dir / "results"
    output_dir.mkdir(exist_ok=True)
    results = greeks(market)
    output_file = output_dir / "h_greeks.csv"
    results.to_csv(output_file, index=False, encoding="utf-8-sig")
    print(f"{output_file.name}: {len(results)} rows.")


if __name__ == "__main__":
    main()
