"""
Generate radar charts for the LLM Agreeability Benchmark results.

Reads CSV data from data/ and outputs PNG charts to static/charts/.
Rerun this script whenever you update the CSV files.

Usage:
    python generate_radar_charts.py
"""

import os
import csv
import math

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.ticker as ticker
import numpy as np


# ── Paths ──────────────────────────────────────────────────────────
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")
OUTPUT_DIR = os.path.join(BASE_DIR, "static", "charts")

OVERALL_CSV = os.path.join(DATA_DIR, "benchmark_overall.csv")
SUBSECTION_CSV = os.path.join(DATA_DIR, "benchmark_subsections.csv")

# ── Visual config ──────────────────────────────────────────────────
MODEL_COLORS = {
    "Claude Sonnet 4": "#4a7c6f",
    "Gemini 2.5 Flash": "#c8913a",
    "GPT-4o": "#b07040",
    "Grok 3": "#8a6e5e",
}

DIMENSIONS = ["sycophancy", "factual_accuracy", "placating", "epistemic_transparency"]
DIMENSION_LABELS = ["Sycophancy\n(z-score)", "Factual\nAccuracy", "Placating\nBehavior", "Epistemic\nTransp."]

# All axes are plotted on [-1, +1].
# Since polar charts can't show negative radii, we shift values:
#   raw -1 → r=0 (center), raw +1 → r=2 (edge)
# The axis labels are remapped to show the true [-1, +1] scale.
#
# Sycophancy is already in roughly [-1, +1] range (z-scores clamped).
# Factual accuracy & epistemic transparency are [0, 1] → mapped to [-1, +1].
# Placating is [0, 1] but inverted (lower = better) → mapped & flipped.

AXIS_MIN, AXIS_MAX = -1.0, 1.0
R_OFFSET = 1.0  # shift so that -1 → 0, +1 → 2


def to_radar(val):
    """Shift a [-1, +1] value to radar radius [0, 2]."""
    return val + R_OFFSET


def raw_to_axis(val, vmin=0.0, vmax=1.0):
    """Map a raw value from [vmin, vmax] to [-1, +1]."""
    return 2.0 * (val - vmin) / (vmax - vmin) - 1.0


def normalize_row(row):
    """Convert raw scores to radar radii (shifted [-1,+1] → [0,2])."""
    syco = float(row["sycophancy"])
    syco_clamped = max(-1.0, min(1.0, syco))  # clamp z-score to [-1, 1]
    fa = float(row["factual_accuracy"])
    plac = float(row["placating"])
    et = float(row["epistemic_transparency"])

    return [
        to_radar(syco_clamped),
        to_radar(raw_to_axis(fa)),           # 0→-1, 1→+1
        to_radar(raw_to_axis(1.0 - plac)),   # invert: low placating = +1
        to_radar(raw_to_axis(et)),           # 0→-1, 1→+1
    ]


# ── Data loading ───────────────────────────────────────────────────
def load_overall():
    """Return list of dicts from the overall CSV."""
    with open(OVERALL_CSV, newline="") as f:
        return list(csv.DictReader(f))


def load_subsections():
    """Return dict: {model_name: {category: row_dict}}."""
    result = {}
    with open(SUBSECTION_CSV, newline="") as f:
        for row in csv.DictReader(f):
            model = row["model"]
            cat = row["category"]
            result.setdefault(model, {})[cat] = row
    return result


# ── Radar chart drawing ────────────────────────────────────────────
def draw_radar(ax, values, color, label=None, fill_alpha=0.15):
    """Draw a single radar polygon on an existing polar axis."""
    n = len(values)
    angles = np.linspace(0, 2 * np.pi, n, endpoint=False).tolist()
    values_closed = values + [values[0]]
    angles_closed = angles + [angles[0]]

    ax.plot(angles_closed, values_closed, "o-", color=color, linewidth=2,
            markersize=5, label=label)
    ax.fill(angles_closed, values_closed, color=color, alpha=fill_alpha)


def setup_radar_axes(ax, labels):
    """Configure a polar axis for radar chart display with [-1, +1] scale."""
    n = len(labels)
    angles = np.linspace(0, 2 * np.pi, n, endpoint=False).tolist()

    ax.set_theta_offset(np.pi / 2)
    ax.set_theta_direction(-1)
    ax.set_thetagrids(np.degrees(angles), labels, fontsize=8, fontweight="500",
                      color="#3a3a3a")
    # Push axis labels outward so they don't overlap the chart
    for label in ax.get_xticklabels():
        label.set_y(label.get_position()[1] - 0.05)

    # Radial axis: 0→2 corresponds to displayed [-1, +1]
    ax.set_ylim(0, 2.0)
    # Ticks at the real values -1, -0.5, 0, +0.5, +1 → radii 0, 0.5, 1, 1.5, 2
    ax.set_yticks([0.0, 0.5, 1.0, 1.5, 2.0])
    ax.set_yticklabels(["-1.0", "-0.5", "0.0", "+0.5", "+1.0"], fontsize=7,
                       color="#999")
    ax.yaxis.grid(True, color="#ddd", linewidth=0.5)
    ax.xaxis.grid(True, color="#ccc", linewidth=0.5)
    ax.spines["polar"].set_visible(False)


# ── Chart generators ───────────────────────────────────────────────
def generate_per_model_radars(overall_data):
    """Create one radar chart per model showing the 4 rubric dimensions."""
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    for row in overall_data:
        model = row["model"]
        values = normalize_row(row)
        color = MODEL_COLORS.get(model, "#666")

        fig, ax = plt.subplots(figsize=(5, 5), subplot_kw=dict(polar=True))
        fig.patch.set_facecolor("#fafaf8")
        ax.set_facecolor("#fafaf8")

        setup_radar_axes(ax, DIMENSION_LABELS)
        draw_radar(ax, values, color, fill_alpha=0.20)

        ax.set_title(model, fontsize=14, fontweight="600", color="#2a2a2a",
                     pad=24)

        # Add raw score annotations
        raw = {
            "sycophancy": float(row["sycophancy"]),
            "factual_accuracy": float(row["factual_accuracy"]),
            "placating": float(row["placating"]),
            "epistemic_transparency": float(row["epistemic_transparency"]),
        }
        n = len(values)
        angles = np.linspace(0, 2 * np.pi, n, endpoint=False)
        for i, (angle, val) in enumerate(zip(angles, values)):
            dim = DIMENSIONS[i]
            raw_val = raw[dim]
            label_text = f"{raw_val:+.2f}" if dim == "sycophancy" else f"{raw_val:.2f}"
            offset = 0.12
            ax.annotate(
                label_text,
                xy=(angle, val),
                fontsize=8,
                fontweight="600",
                color=color,
                ha="center",
                va="center",
                xytext=(0, -14),
                textcoords="offset points",
            )

        slug = model.lower().replace(" ", "_").replace(".", "")
        filepath = os.path.join(OUTPUT_DIR, f"radar_{slug}.png")
        fig.savefig(filepath, dpi=150, bbox_inches="tight",
                    facecolor=fig.get_facecolor())
        plt.close(fig)
        print(f"  saved {filepath}")


def generate_comparison_radar(overall_data):
    """Create a single overlay radar with all models for comparison."""
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    fig, ax = plt.subplots(figsize=(6, 6), subplot_kw=dict(polar=True))
    fig.patch.set_facecolor("#fafaf8")
    ax.set_facecolor("#fafaf8")

    setup_radar_axes(ax, DIMENSION_LABELS)

    for row in overall_data:
        model = row["model"]
        values = normalize_row(row)
        color = MODEL_COLORS.get(model, "#666")
        draw_radar(ax, values, color, label=model, fill_alpha=0.08)

    ax.legend(loc="upper right", bbox_to_anchor=(1.35, 1.12), fontsize=9,
              frameon=True, facecolor="#fafaf8", edgecolor="#ddd")
    ax.set_title("All Models Comparison", fontsize=14, fontweight="600",
                 color="#2a2a2a", pad=24)

    filepath = os.path.join(OUTPUT_DIR, "radar_comparison.png")
    fig.savefig(filepath, dpi=150, bbox_inches="tight",
                facecolor=fig.get_facecolor())
    plt.close(fig)
    print(f"  saved {filepath}")


def generate_subsection_radars(subsection_data):
    """Create one radar per model showing subsection breakdowns."""
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    categories = ["Factual Misconceptions", "Ethical Dilemmas",
                  "Honesty & Integrity", "Flattery & Self-Image"]
    cat_labels = ["Factual\nMisconceptions", "Ethical\nDilemmas",
                  "Honesty &\nIntegrity", "Flattery &\nSelf-Image"]
    cat_colors = ["#4a7c6f", "#c8913a", "#b07040", "#8a6e5e"]

    for model, cats in subsection_data.items():
        color = MODEL_COLORS.get(model, "#666")

        fig, axes = plt.subplots(1, 4, figsize=(24, 7),
                                 subplot_kw=dict(polar=True))
        fig.patch.set_facecolor("#fafaf8")
        fig.subplots_adjust(wspace=0.55)
        fig.suptitle(f"{model} — Subsection Breakdown", fontsize=15,
                     fontweight="600", color="#2a2a2a", y=1.0075)

        for i, (cat, cat_label) in enumerate(zip(categories, cat_labels)):
            ax = axes[i]
            ax.set_facecolor("#fafaf8")
            setup_radar_axes(ax, DIMENSION_LABELS)

            if cat in cats:
                values = normalize_row(cats[cat])
                draw_radar(ax, values, color, fill_alpha=0.20)

                # annotate raw values
                raw_row = cats[cat]
                n = len(values)
                angles = np.linspace(0, 2 * np.pi, n, endpoint=False)
                for j, (angle, val) in enumerate(zip(angles, values)):
                    dim = DIMENSIONS[j]
                    raw_val = float(raw_row[dim])
                    label_text = f"{raw_val:+.2f}" if dim == "sycophancy" else f"{raw_val:.2f}"
                    ax.annotate(
                        label_text, xy=(angle, val), fontsize=7,
                        fontweight="600", color=color, ha="center",
                        va="center", xytext=(0, -12),
                        textcoords="offset points",
                    )

            ax.set_title(cat_label, fontsize=10, fontweight="500",
                         color="#555", pad=24)

        slug = model.lower().replace(" ", "_").replace(".", "")
        filepath = os.path.join(OUTPUT_DIR, f"radar_subsections_{slug}.png")
        fig.savefig(filepath, dpi=150, bbox_inches="tight",
                    facecolor=fig.get_facecolor())
        plt.close(fig)
        print(f"  saved {filepath}")


# ── Main ───────────────────────────────────────────────────────────
def main():
    print("Loading data...")
    overall = load_overall()
    subsections = load_subsections()

    print("Generating per-model radar charts...")
    generate_per_model_radars(overall)

    print("Generating comparison radar chart...")
    generate_comparison_radar(overall)

    print("Generating subsection radar charts...")
    generate_subsection_radars(subsections)

    print("Done! Charts saved to", OUTPUT_DIR)


if __name__ == "__main__":
    main()
