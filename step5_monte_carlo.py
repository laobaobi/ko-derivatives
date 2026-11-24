"""MFE5130 g 项：用蒙特卡洛对照欧式底层对应的 X 树价。"""

from dataclasses import replace
from math import erfc, sqrt
from pathlib import Path

import numpy as np
import pandas as pd

from step3_validate_parameters import default_scenarios, load_market, price_x, x_payoff


def normal_cdf(values):
    """用标准库 erfc 计算正态分布函数，无需额外安装 SciPy。"""
    # Φ(z) = erfc(-z/√2)/2。fromiter 保持输入的路径顺序并返回 NumPy 数组。
    return np.fromiter(
        (0.5 * erfc(-value / sqrt(2.0)) for value in values),
        dtype=float,
        count=len(values),
    )


def european_inner(stock_at_T, strike, contract, market):
    """在每条模拟路径的 S_T 条件下解析计算还有 C 年的欧式 V1。"""
    alpha = 1.5
    sigma, q, r = (market[name] for name in ("sigma", "q", "r"))
    # 给定 S_T，计算剩余 C 年的对数股价均值和方差。-σ²/2 来自对数变换。
    variance = sigma**2 * contract.C
    stdev = sqrt(variance)
    log_mean = np.log(stock_at_T) + (r - q - 0.5 * sigma**2) * contract.C
    power_mean = np.exp(alpha * log_mean + 0.5 * alpha**2 * variance)

    def power_call(k):
        """给定 S_T，计算未折现的幂次看涨支付的条件期望。"""
        # 把 S^(3/2)>K 转成正态变量上的阈值，计算截断期望。
        z = (log_mean - np.log(k) / alpha) / stdev
        return power_mean * normal_cdf(z + alpha * stdev) - k * normal_cdf(z)

    # 封顶支付等于两份门槛分别为 K 与 K+H 的幂次看涨之差。
    inner = np.exp(-r * contract.C) * (power_call(strike) - power_call(strike + contract.h))
    # 消除在极端节点可能出现的浮点舍入越界。
    return np.clip(inner, 0.0, contract.h * np.exp(-r * contract.C))


def monte_carlo(market):
    """g：对 d(i) 的各组参数估计欧式底层对应的 X 价格。"""
    seed = 5130
    pairs = 250_000
    # 固定随机种子便于复现。将 Z 与 -Z 配对，共得到 50 万条路径。
    standard_normal = np.random.default_rng(seed).standard_normal(pairs)
    antithetic = np.concatenate((standard_normal, -standard_normal))
    s0, sigma, q, r = (market[name] for name in ("s0", "sigma", "q", "r"))
    # 不同情形共用随机数。只改变 n 的情形拥有同一个连续模型目标。
    estimates = {}
    rows = []
    for label, contract in default_scenarios():
        # 用相同的细网格作为对照。仅 n 不同的行可共享模拟值与细网格价。
        fine_contract = replace(contract, n=2560)
        if fine_contract not in estimates:
            drift = (r - q - 0.5 * sigma**2) * contract.T
            diffusion = sigma * sqrt(contract.T)
            stock_at_T = s0 * np.exp(drift + diffusion * antithetic)
            # X 在 T 支付。把两份还有 C 年的欧式底层价值代入 X，再折现 T 年。
            v1_k2 = european_inner(stock_at_T, contract.k2, contract, market)
            v1_k3 = european_inner(stock_at_T, contract.k3, contract, market)
            discounted_payoff = np.exp(-r * contract.T) * x_payoff(contract, v1_k2, v1_k3)

            # 一正一负两条路径组成一组。标准误按独立的组均值估计。
            pair_means = (discounted_payoff[:pairs] + discounted_payoff[pairs:]) / 2
            estimate = pair_means.mean()
            standard_error = pair_means.std(ddof=1) / sqrt(pairs)
            fine_price, _ = price_x(fine_contract, **market)
            estimates[fine_contract] = estimate, standard_error, fine_price

        estimate, standard_error, fine_price = estimates[fine_contract]
        tree_price, _ = price_x(contract, **market)
        # 95% 置信区间反映抽样误差。用原步数和细网格分别与该区间做对照。
        lower = estimate - 1.96 * standard_error
        upper = estimate + 1.96 * standard_error
        rows.append(dict(
            scenario=label, d_n=contract.n, d_European=tree_price,
            MC=estimate, standard_error=standard_error, CI95_low=lower, CI95_high=upper,
            MC_minus_d=estimate - tree_price, fine_n=fine_contract.n,
            fine_European=fine_price, MC_minus_fine=estimate - fine_price,
            d_in_MC_CI=lower <= tree_price <= upper,
            fine_in_MC_CI=lower <= fine_price <= upper, paths=2 * pairs, seed=seed,
        ))
    return pd.DataFrame(rows)


def main():
    """运行所有 d(i) 情形的欧式对照并写入 CSV。"""
    # 相对脚本位置定位数据和输出，在 VS Code 中直接运行也能找到文件。
    project_dir = Path(__file__).resolve().parent
    market = load_market(project_dir)
    output_dir = project_dir / "results"
    output_dir.mkdir(exist_ok=True)
    results = monte_carlo(market)
    output_file = output_dir / "g_monte_carlo.csv"
    results.to_csv(output_file, index=False, encoding="utf-8-sig")
    print(f"{output_file.name}: {len(results)} rows.")


if __name__ == "__main__":
    main()
