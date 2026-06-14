import os
from typing import List, Dict, Tuple, Optional

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MPL_CACHE_DIR = os.path.join(BASE_DIR, ".matplotlib_cache")
os.makedirs(MPL_CACHE_DIR, exist_ok=True)
os.environ["MPLCONFIGDIR"] = MPL_CACHE_DIR

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.font_manager as fm
import numpy as np
import pandas as pd

from .frequency_counter import DynastyFrequencyCounter


def _setup_chinese_font():
    font_candidates = [
        "SimHei",
        "Microsoft YaHei",
        "STHeiti",
        "WenQuanYi Micro Hei",
        "Noto Sans CJK SC",
        "Arial Unicode MS",
        "PingFang SC",
    ]

    available_fonts = [f.name for f in fm.fontManager.ttflist]

    for font_name in font_candidates:
        if font_name in available_fonts:
            plt.rcParams["font.sans-serif"] = [font_name]
            plt.rcParams["axes.unicode_minus"] = False
            return font_name

    plt.rcParams["font.sans-serif"] = ["DejaVu Sans"]
    plt.rcParams["axes.unicode_minus"] = False
    return None


_setup_chinese_font()


class CharVisualizer:
    def __init__(self, counter: DynastyFrequencyCounter, output_dir: str):
        self.counter = counter
        self.output_dir = output_dir
        os.makedirs(output_dir, exist_ok=True)

    def plot_char_trend(self, char: str, use_ratio: bool = True,
                       title: str = None, save_path: str = None) -> str:
        dynasties = self.counter.get_sorted_dynasties()

        if use_ratio:
            values = [self.counter.get_char_frequency_ratio(char, d) for d in dynasties]
            y_label = "使用频率 (频次/总字数)"
        else:
            values = [self.counter.get_dynasty_frequency(d, char) for d in dynasties]
            y_label = "使用频次"

        fig, ax = plt.subplots(figsize=(10, 6))

        ax.plot(dynasties, values, marker="o", linewidth=2, markersize=8,
                color="#2c3e50", markerfacecolor="#e74c3c", markeredgecolor="#e74c3c")

        for i, v in enumerate(values):
            if use_ratio:
                label = f"{v:.4f}"
            else:
                label = str(v)
            ax.annotate(label, (dynasties[i], v), textcoords="offset points",
                       xytext=(0, 10), ha="center", fontsize=9)

        if title is None:
            title = f"「{char}」字跨朝代使用频率变化"

        ax.set_title(title, fontsize=14, fontweight="bold", pad=20)
        ax.set_xlabel("朝代", fontsize=12)
        ax.set_ylabel(y_label, fontsize=12)
        ax.grid(True, alpha=0.3, linestyle="--")
        ax.tick_params(axis="x", rotation=45)

        plt.tight_layout()

        if save_path is None:
            save_path = os.path.join(
                self.output_dir,
                f"trend_{char}_{'ratio' if use_ratio else 'count'}.png"
            )

        plt.savefig(save_path, dpi=150, bbox_inches="tight")
        plt.close()

        return save_path

    def plot_multiple_chars_trend(self, chars: List[str], use_ratio: bool = True,
                                  title: str = None, save_path: str = None) -> str:
        dynasties = self.counter.get_sorted_dynasties()

        fig, ax = plt.subplots(figsize=(12, 7))

        colors = plt.cm.Set3(np.linspace(0, 1, len(chars)))

        for i, char in enumerate(chars):
            if use_ratio:
                values = [self.counter.get_char_frequency_ratio(char, d) for d in dynasties]
                y_label = "使用频率 (频次/总字数)"
            else:
                values = [self.counter.get_dynasty_frequency(d, char) for d in dynasties]
                y_label = "使用频次"

            ax.plot(dynasties, values, marker="o", linewidth=2, markersize=6,
                    label=f"「{char}」", color=colors[i])

        if title is None:
            title = "多汉字跨朝代使用频率变化对比"

        ax.set_title(title, fontsize=14, fontweight="bold", pad=20)
        ax.set_xlabel("朝代", fontsize=12)
        ax.set_ylabel(y_label, fontsize=12)
        ax.grid(True, alpha=0.3, linestyle="--")
        ax.legend(loc="best", fontsize=11)
        ax.tick_params(axis="x", rotation=45)

        plt.tight_layout()

        if save_path is None:
            save_path = os.path.join(
                self.output_dir,
                f"trend_multi_{'_'.join(chars)}_{'ratio' if use_ratio else 'count'}.png"
            )

        plt.savefig(save_path, dpi=150, bbox_inches="tight")
        plt.close()

        return save_path

    def plot_dynasty_top_chars(self, dynasty: str, top_n: int = 15,
                               category: str = None, title: str = None,
                               save_path: str = None) -> str:
        top_chars = self.counter.get_top_chars(dynasty, top_n=top_n, category=category)

        if not top_chars:
            return None

        chars = [item[0] for item in top_chars]
        counts = [item[1] for item in top_chars]

        fig, ax = plt.subplots(figsize=(10, 6))

        colors = plt.cm.Blues(np.linspace(0.4, 0.9, len(chars)))
        bars = ax.barh(chars[::-1], counts[::-1], color=colors)

        for bar, count in zip(bars, counts[::-1]):
            ax.text(bar.get_width() + max(counts) * 0.01, bar.get_y() + bar.get_height() / 2,
                    str(count), va="center", fontsize=9)

        if title is None:
            category_str = f"（{category}）" if category else ""
            title = f"{dynasty}代字频Top{top_n}{category_str}"

        ax.set_title(title, fontsize=14, fontweight="bold", pad=20)
        ax.set_xlabel("出现频次", fontsize=12)
        ax.grid(True, alpha=0.3, linestyle="--", axis="x")

        plt.tight_layout()

        if save_path is None:
            cat_suffix = f"_{category}" if category else ""
            save_path = os.path.join(
                self.output_dir,
                f"top_chars_{dynasty}{cat_suffix}.png"
            )

        plt.savefig(save_path, dpi=150, bbox_inches="tight")
        plt.close()

        return save_path

    def plot_dynasty_distribution(self, save_path: str = None) -> str:
        summary = self.counter.get_summary()
        dynasties = self.counter.get_sorted_dynasties()

        totals = [summary[d]["total_chars"] for d in dynasties]

        fig, ax = plt.subplots(figsize=(10, 6))

        colors = plt.cm.viridis(np.linspace(0.2, 0.8, len(dynasties)))
        bars = ax.bar(dynasties, totals, color=colors)

        for bar, total in zip(bars, totals):
            height = bar.get_height()
            ax.text(bar.get_x() + bar.get_width() / 2., height,
                    f"{total:,}", ha="center", va="bottom", fontsize=9)

        ax.set_title("各朝代古籍总字数分布", fontsize=14, fontweight="bold", pad=20)
        ax.set_xlabel("朝代", fontsize=12)
        ax.set_ylabel("总字数", fontsize=12)
        ax.grid(True, alpha=0.3, linestyle="--", axis="y")
        ax.tick_params(axis="x", rotation=45)

        plt.tight_layout()

        if save_path is None:
            save_path = os.path.join(self.output_dir, "dynasty_distribution.png")

        plt.savefig(save_path, dpi=150, bbox_inches="tight")
        plt.close()

        return save_path

    def plot_category_comparison(self, save_path: str = None) -> str:
        summary = self.counter.get_summary()
        dynasties = self.counter.get_sorted_dynasties()

        common_counts = [summary[d]["common_count"] for d in dynasties]
        rare_counts = [summary[d]["rare_count"] for d in dynasties]

        x = np.arange(len(dynasties))
        width = 0.35

        fig, ax = plt.subplots(figsize=(11, 6))

        bars1 = ax.bar(x - width/2, common_counts, width, label="通用字", color="#3498db")
        bars2 = ax.bar(x + width/2, rare_counts, width, label="生僻字", color="#e67e22")

        ax.set_xticks(x)
        ax.set_xticklabels(dynasties, rotation=45)
        ax.set_title("各朝代通用字与生僻字数量对比", fontsize=14, fontweight="bold", pad=20)
        ax.set_xlabel("朝代", fontsize=12)
        ax.set_ylabel("字数", fontsize=12)
        ax.legend()
        ax.grid(True, alpha=0.3, linestyle="--", axis="y")

        plt.tight_layout()

        if save_path is None:
            save_path = os.path.join(self.output_dir, "category_comparison.png")

        plt.savefig(save_path, dpi=150, bbox_inches="tight")
        plt.close()

        return save_path

    def plot_char_evolution_heatmap(self, chars: List[str], use_ratio: bool = True,
                                    title: str = None, save_path: str = None) -> str:
        dynasties = self.counter.get_sorted_dynasties()

        data = []
        for char in chars:
            if use_ratio:
                row = [self.counter.get_char_frequency_ratio(char, d) for d in dynasties]
            else:
                row = [self.counter.get_dynasty_frequency(d, char) for d in dynasties]
            data.append(row)

        data = np.array(data)

        fig, ax = plt.subplots(figsize=(max(8, len(dynasties) * 1.2), max(6, len(chars) * 0.6)))

        im = ax.imshow(data, cmap="YlOrRd", aspect="auto")

        ax.set_yticks(range(len(chars)))
        ax.set_yticklabels([f"「{c}」" for c in chars])
        ax.set_xticks(range(len(dynasties)))
        ax.set_xticklabels(dynasties, rotation=45, ha="right")

        for i in range(len(chars)):
            for j in range(len(dynasties)):
                val = data[i, j]
                if use_ratio:
                    text = f"{val:.4f}"
                else:
                    text = str(int(val))
                color = "white" if val > data.max() * 0.6 else "black"
                ax.text(j, i, text, ha="center", va="center", color=color, fontsize=8)

        cbar = plt.colorbar(im, ax=ax)
        cbar.set_label("使用频率" if use_ratio else "使用频次")

        if title is None:
            title = "汉字使用频率热力图"

        ax.set_title(title, fontsize=14, fontweight="bold", pad=20)

        plt.tight_layout()

        if save_path is None:
            save_path = os.path.join(
                self.output_dir,
                f"heatmap_{'_'.join(chars[:3])}_{'ratio' if use_ratio else 'count'}.png"
            )

        plt.savefig(save_path, dpi=150, bbox_inches="tight")
        plt.close()

        return save_path

    def generate_all_charts(self, target_chars: List[str] = None) -> Dict[str, str]:
        charts = {}

        charts["dynasty_distribution"] = self.plot_dynasty_distribution()
        charts["category_comparison"] = self.plot_category_comparison()

        dynasties = self.counter.get_sorted_dynasties()
        for dynasty in dynasties:
            chart_path = self.plot_dynasty_top_chars(dynasty, top_n=15)
            if chart_path:
                charts[f"top_{dynasty}"] = chart_path

        if target_chars:
            for char in target_chars:
                chart_path = self.plot_char_trend(char, use_ratio=True)
                charts[f"trend_{char}"] = chart_path

            if len(target_chars) >= 2:
                charts["multi_trend"] = self.plot_multiple_chars_trend(
                    target_chars, use_ratio=True
                )
                charts["heatmap"] = self.plot_char_evolution_heatmap(
                    target_chars, use_ratio=True
                )

        return charts


def create_visualizer(counter: DynastyFrequencyCounter = None,
                      output_dir: str = None) -> CharVisualizer:
    import sys
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from config.paths_config import FIGURES_OUTPUT_DIR

    if counter is None:
        from .frequency_counter import create_counter
        counter = create_counter()
    if output_dir is None:
        output_dir = FIGURES_OUTPUT_DIR

    return CharVisualizer(counter, output_dir)


if __name__ == "__main__":
    import sys
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from config.paths_config import ensure_dirs

    ensure_dirs()
    visualizer = create_visualizer()
    charts = visualizer.generate_all_charts(["之", "乎", "者", "也"])
    print(f"生成图表: {list(charts.keys())}")
