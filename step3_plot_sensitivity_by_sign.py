"""用相同取点比较两种 N 和两种底层行权方式。"""

from dataclasses import replace
from pathlib import Path

from matplotlib import font_manager
from matplotlib.ticker import NullFormatter
import numpy as np
import pandas as pd

from step3_plot_sensitivity import BASE, plt, sweep
from step3_validate_parameters import load_market


LABELS = {
    "K1": r"外层门槛 $K_1$（美元）",
    "K2": r"第一份底层门槛 $K_2$",
    "K3": r"第二份底层门槛 $K_3$",
    "H": r"底层支付上限 $H$（美元）",
    "T": r"外层到期 $T$（年）",
    "C": r"底层剩余期限 $C$（年）",
    "n": r"外层步数 $n$（对数刻度）",
}
STYLES = ("European", "American")


def verify_grids(data):
    """同一参数的两组报价必须使用完全相同的网格。"""
    counts = dict(zip(LABELS, (61, 63, 63, 61, 61, 61, 43), strict=True))
    for key, expected in counts.items():
        plus = data.loc[(data.parameter == key) & (data.N == 1)]
        minus = data.loc[(data.parameter == key) & (data.N == -1)]
        if len(plus) != expected or not np.array_equal(plus.value.to_numpy(), minus.value.to_numpy()):
            raise ValueError(f"{key} 的两组网格不一致。")
        if sum(plus.is_baseline) != 1 or sum(minus.is_baseline) != 1:
            raise ValueError(f"{key} 的基准点有缺失或重复。")


def draw(data, sign, style, output_file):
    """为一组 N 和行权方式绘图，各参数坐标范围由四组数据共同决定。"""
    fig = plt.figure(figsize=(7.6, 4.55))
    grid = fig.add_gridspec(3, 3)
    fig.subplots_adjust(left=.090, right=.984, bottom=.11, top=.967, hspace=.78, wspace=.38)
    for index, (key, label) in enumerate(LABELS.items()):
        ax = fig.add_subplot(grid[2, :] if key == "n" else grid[index // 3, index % 3])
        all_cases = data[data.parameter == key]
        group = all_cases[all_cases.N == sign]
        baseline = group[group.is_baseline]
        low, high = all_cases[list(STYLES)].stack().agg(["min", "max"])
        pad = .075 * (high - low)
        ax.plot(group.value, group[style], color="black", linewidth=1.05)
        ax.axvline(baseline.value.iloc[0], color="#AAAAAA", linewidth=.6)
        ax.scatter(baseline.value, baseline[style], s=22, facecolors="white",
                   edgecolors="black", linewidths=.85, zorder=4)
        ax.set_ylim(low - pad, high + pad)
        ax.set_xlabel(label, fontsize=9)
        if index % 3 == 0:
            ax.set_ylabel(r"$X$（美元）", fontsize=8.5)
        ax.spines[["top", "right"]].set_visible(False)
        ax.grid(axis="y", linewidth=.45, color="#D9D9D9")
        ax.tick_params(labelsize=8, length=3)
        if key == "n":
            ax.set_xscale("log", base=2)
            ax.set_xticks([20, 40, 80, 160, 320, 640],
                          labels=["20", "40", "80", "160", "320", "640"])
            ax.xaxis.set_minor_formatter(NullFormatter())
    fig.savefig(output_file, dpi=260, facecolor="white")
    plt.close(fig)


def main():
    project_dir = Path(__file__).resolve().parent
    results = project_dir / "results"
    results.mkdir(exist_ok=True)
    market = load_market(project_dir)

    # 逐组由同一个取点函数生成数据。N 的比较单独做，图内只扫七个其他参数。
    rows = [sweep(market, replace(BASE, sign=sign)).query("parameter != 'N'") for sign in (1, -1)]
    data = pd.concat(rows, ignore_index=True)
    verify_grids(data)
    data.to_csv(results / "d_sensitivity_by_sign.csv", index=False, encoding="utf-8-sig")

    font = Path("C:/Windows/Fonts/simsun.ttc")
    font_manager.fontManager.addfont(str(font))
    plt.rcParams.update({"font.family":font_manager.FontProperties(fname=font).get_name(),
                         "axes.unicode_minus":False,"mathtext.fontset":"stix"})
    for sign, tag in ((1,"plus"),(-1,"minus")):
        for style in STYLES:
            draw(data, sign, style, results / f"d_{tag}_{style.lower()}.png")
    print(f"{len(data)} rows; four charts generated.")


if __name__ == "__main__":
    main()
