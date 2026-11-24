"""MFE5130 e 项：固定市场和合约条件，检查 KO 衍生品 X 的树价收敛。"""

from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd

from step3_validate_parameters import Contract, load_market, price_x


def convergence(market):
    """e：分别固定 N=1、N=-1 的合约，观察网格加密后的报价。"""
    rows = []
    for sign in (1, -1):
        # 每种 N 都固定 T=1、C=0.5，因此内层需 n/2 步，总步数为 3n/2。
        for n in (20, 40, 80, 160, 320, 640, 1280, 2560, 5120):
            contract = Contract(n=n, sign=sign)
            european, american = price_x(contract, **market)
            rows.append(dict(N=sign, n=n, total_steps=n * 3 // 2,
                             European=european, American=american))

    results = pd.DataFrame(rows)
    for style in ("European", "American"):
        group = results.groupby("N")[style]
        # 分组后的 diff() 计算同一个 N 内的相邻价差，每组第一行留空。
        # transform("last") 将同组的 5120 步价格对齐到每一行，作为数值参照。
        results[f"{style}_change"] = group.diff()
        results[f"{style}_gap_to_5120"] = results[style] - group.transform("last")
    return results


def plot_convergence(results, output_file):
    """为两种底层样式分别绘图，比较相对于细网格的带符号价差。"""
    # 两个面板共用纵轴范围，便于比较欧式和美式的网格波动。
    fig, axes = plt.subplots(1, 2, figsize=(10, 4), layout="constrained", sharey=True)
    for ax, style in zip(axes, ("European", "American"), strict=True):
        for sign, group in results.groupby("N", sort=False):
            ax.plot(group["n"], group[f"{style}_gap_to_5120"], marker="o", label=f"N = {sign}")
        ax.axhline(0, color="0.4", linewidth=0.8)
        # 步数每翻一倍，横轴前进相同距离。零线代表与参照价格相等。
        ax.set_xscale("log", base=2)
        ax.set_xticks([20, 80, 320, 1280, 5120], labels=["20", "80", "320", "1280", "5120"])
        ax.set(title=f"{style} underlying", xlabel="Outer tree steps (n)")
        ax.grid(axis="y", alpha=0.25)
        ax.legend()
    axes[0].set_ylabel("Tree price minus 5120-step price (USD)")
    fig.suptitle("KO derivative X: tree convergence")
    fig.savefig(output_file, dpi=180)
    plt.close(fig)


def main():
    """读取项目输入，生成 e 项收敛表和收敛图。"""
    # 相对脚本位置定位数据和输出，在 VS Code 中直接运行也能找到文件。
    project_dir = Path(__file__).resolve().parent
    market = load_market(project_dir)
    output_dir = project_dir / "results"
    output_dir.mkdir(exist_ok=True)
    results = convergence(market)
    output_file = output_dir / "e_convergence.csv"
    results.to_csv(output_file, index=False, encoding="utf-8-sig")
    plot_convergence(results, output_dir / "e_convergence.png")
    print(f"{output_file.name}: {len(results)} rows.")


if __name__ == "__main__":
    main()
