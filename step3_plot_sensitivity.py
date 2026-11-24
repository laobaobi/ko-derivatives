"""为 d 项绘制八个单参数定价曲线。"""

from dataclasses import asdict, replace
from pathlib import Path

import matplotlib
import numpy as np
import pandas as pd

# 使用文件绘图后端，运行脚本即可保存 PNG。
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.ticker import FixedLocator, NullFormatter, ScalarFormatter

from step3_validate_parameters import Contract, load_market, price_x


# 统一用 640 步作为扫参基准，减少较粗网格带来的价格抖动。
BASE = Contract(n=640)
PANELS = {
    "k1": (r"$K_1$", "Outer strike (USD)"),
    "k2": (r"$K_2$", "First underlying strike"),
    "k3": (r"$K_3$", "Second underlying strike"),
    "h": (r"$H$", "Underlying payoff cap (USD)"),
    "sign": (r"$N$", "Sign of first payoff branch"),
    "T": (r"$T$", "X maturity (years)"),
    "C": (r"$C$", "Remaining underlying maturity (years)"),
    "n": (r"$n$", "Outer tree steps (log scale)"),
}


def parameter_grids(base):
    """生成六组稠密连续参数，以及 N 和 n 的合法离散取值。"""
    # 加入精确基准值，确保每个面板都有同一基准交易可供核对。
    continuous = {
        "k1": np.linspace(10, 60, 61),
        "k2": np.linspace(475, 650, 61),
        "k3": np.linspace(475, 650, 61),
        "h": np.linspace(50, 150, 61),
    }
    grids = {
        name: np.unique(np.append(values, getattr(base, name))).tolist()
        for name, values in continuous.items()
    }
    # 当两个底层门槛相等时，N=1 的有效支付分支切换。保留精确的折点。
    grids["k2"] = sorted(set(grids["k2"]) | {base.k3})
    grids["k3"] = sorted(set(grids["k3"]) | {base.k2})
    # T 在 0.5 至 2 年间取点。先确定整数内层步数 m，再取 T=nC/m。
    # 这样只改变 T，既固定 n 和 C，又能让 T+C 正好落在网格上。
    target_T = np.linspace(0.5, 2.0, 61)
    inner_steps = np.unique(np.rint(base.n * base.C / target_T).astype(int))
    grids["T"] = sorted((base.n * base.C / inner_steps).tolist())

    # C 直接选为时间步长的整数倍。基准网格每 0.0125 年取一个点。
    dt = base.T / base.n
    inner_steps = np.arange(160, 641, 8)
    grids["C"] = (inner_steps * dt).tolist()
    grids["sign"] = [-1, 1]

    # C/T=1/2 时，n 必须是偶数。补入 d 项原来比较的 20、40、80 步。
    n_values = (2 * np.rint(np.geomspace(20, 640, 42) / 2)).astype(int)
    grids["n"] = np.unique(np.append(n_values, [20, 40, 80, base.n])).tolist()
    return grids


def sweep(market, base):
    """每次复制基准合约并替换一项，记录完整合约和两种价格。"""
    rows = []
    for key, values in parameter_grids(base).items():
        for value in values:
            # 每个取点从同一基准出发，只覆盖当前参数，避免上一轮的改动累积。
            contract = replace(base, **{key: value})
            european, american = price_x(contract, **market)
            rows.append({
                "parameter": "N" if key == "sign" else key if key in ("T", "C", "n") else key.upper(),
                "value": value,
                "is_baseline": value == getattr(base, key),
                **asdict(contract),
                "European": european,
                "American": american,
            })
    return pd.DataFrame(rows).rename(
        columns={"k1": "K1", "k2": "K2", "k3": "K3", "h": "H", "sign": "N"},
    )


def plot_panels(results, keys, base, title, output_file):
    """绘制四个面板。空心点是共同的基准交易。"""
    fig, axes = plt.subplots(2, 2, figsize=(11.6, 7.6))
    fig.subplots_adjust(left=0.09, right=0.97, bottom=0.10, top=0.82, wspace=0.30, hspace=0.47)
    fig.suptitle(title, x=0.09, y=0.966, ha="left", fontsize=18, fontweight="bold")
    fig.text(0.09, 0.914, "One parameter changes per panel. Open markers show the common baseline.",
             fontsize=10.5, color="#475569")
    handles = []
    for ax, key in zip(axes.flat, keys, strict=True):
        symbol, description = PANELS[key]
        label = "N" if key == "sign" else key if key in ("T", "C", "n") else key.upper()
        group = results.loc[results["parameter"] == label]
        # 每个面板中，空心点对应其余面板共用的基准报价。
        baseline = group.loc[group["is_baseline"]]
        for style, color, linestyle, marker in (
            ("European", "#18588C", "-", "o"),
            ("American", "#AB471F", "--", "s"),
        ):
            line, = ax.plot(group["value"], group[style], color=color, linestyle=linestyle,
                            linewidth=1.8, marker=marker if key == "sign" else None,
                            label=f"{style} underlying")
            if ax is axes.flat[0]:
                handles.append(line)
            ax.scatter(baseline["value"], baseline[style], facecolor="white", edgecolor=color,
                       marker=marker, s=44, linewidth=1.5, zorder=3)
        ax.axvline(getattr(base, key), color="#CBD5E1", linewidth=1.0, zorder=0)
        ax.set(title=f"{symbol}   {description}", ylabel="X value (USD)")
        ax.title.set_ha("left")
        ax.title.set_position((0, 1.0))
        ax.grid(axis="y", color="#E2E8F0", linewidth=0.7)
        ax.spines[["top", "right"]].set_visible(False)
        # N 的中间值不在题目定义域内。只标出两个合法取点。
        if key == "sign":
            ax.set_xticks([-1, 1])
        # 对数横轴使 20 到 40 与 320 到 640 的间距相同，便于观察步数翻倍。
        if key == "n":
            ax.set_xscale("log", base=2)
            ax.xaxis.set_major_locator(FixedLocator([20, 40, 80, 160, 320, 640]))
            ax.xaxis.set_major_formatter(ScalarFormatter())
            ax.xaxis.set_minor_formatter(NullFormatter())
    fig.legend(handles=handles, loc="upper left", bbox_to_anchor=(0.083, 0.892),
               ncols=2, frameon=False)
    fig.text(0.09, 0.025, "Baseline: K1=30, K2=550, K3=600, H=100, N=+1, T=1, C=0.5, n=640.",
             color="#475569", fontsize=9)
    fig.savefig(output_file, dpi=180, facecolor="white")
    plt.close(fig)


def main():
    """保存可复核的取点价格表，并生成两张四面板图。"""
    project_dir = Path(__file__).resolve().parent
    output_dir = project_dir / "results"
    output_dir.mkdir(exist_ok=True)
    results = sweep(load_market(project_dir), BASE)
    results.to_csv(output_dir / "d_sensitivity_curves.csv", index=False, encoding="utf-8-sig")
    plot_panels(results, ("k1", "k2", "k3", "h"), BASE,
                "Derivative X: strikes and payoff cap", output_dir / "d_sensitivity_strikes_cap.png")
    plot_panels(results, ("sign", "T", "C", "n"), BASE,
                "Derivative X: payoff sign, maturities and tree steps", output_dir / "d_sensitivity_terms_steps.png")
    print(f"Saved eight sensitivity panels and {len(results)} rows under {output_dir}.")


if __name__ == "__main__":
    main()
