#!/usr/bin/env python3
"""Plot ShopFix demo matrix results (excludes intent_opposition)."""

from __future__ import annotations

import argparse
import json
import subprocess
from pathlib import Path

import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
from matplotlib.lines import Line2D
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_JSON = ROOT / "experiments" / "results" / "shopfix_demo_matrix_20260517_091231.json"
RESULTS_DIR = ROOT / "experiments" / "results"
OUT_DIR = ROOT / "experiments" / "charts"
GUARDRAIL_ACCENT = "#7c3aed"

# Demo-friendly palette
BASELINE = "#94a3b8"
HELM = "#0ea5e9"
WIN = "#10b981"
LOSS = "#f43f5e"
ACCENT = "#8b5cf6"
GRID = "#e2e8f0"
BG = "#fafafa"


def _style() -> None:
    plt.rcParams.update(
        {
            "figure.facecolor": BG,
            "axes.facecolor": "white",
            "axes.edgecolor": GRID,
            "axes.labelcolor": "#334155",
            "axes.titleweight": "bold",
            "axes.titlesize": 13,
            "axes.labelsize": 11,
            "xtick.color": "#64748b",
            "ytick.color": "#64748b",
            "grid.color": GRID,
            "grid.alpha": 0.8,
            "font.family": "sans-serif",
            "font.sans-serif": ["Helvetica Neue", "Arial", "DejaVu Sans"],
            "legend.frameon": True,
            "legend.facecolor": "white",
            "legend.edgecolor": GRID,
        }
    )


def _load(path: Path) -> list[dict]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    rows = payload["rows"]
    return [r for r in rows if r.get("suite") != "intent_opposition" and not r["id"].startswith("opposition")]


def load_guardrail_trials(results_dir: Path | None = None) -> list[dict]:
    directory = results_dir or RESULTS_DIR
    return [
        json.loads(p.read_text(encoding="utf-8"))
        for p in sorted(directory.glob("shopfix_guardrail_*.json"))
    ]


def _guardrail_row(trial: dict, label: str) -> dict:
    c = trial["comparison"]
    return {
        "label": label,
        "cost_savings_pct": c.get("cost_savings_pct", 0),
        "wall_savings_pct": c.get("time_savings_pct", 0),
        "baseline_cost": c.get("baseline_cost_usd", 0),
        "helm_cost": c.get("helm_cost_usd", 0),
        "baseline_sec": c.get("baseline_resolution_time_ms", 0) / 1000,
        "helm_sec": c.get("helm_resolution_time_ms", 0) / 1000,
        "baseline_calls": trial.get("baseline", {}).get("haiku_calls", 2),
        "helm_calls": trial.get("helm", {}).get("guardrail_calls", 1),
        "blocked_rule": trial.get("helm", {}).get("blocked_rule", ""),
    }


def _guardrail_median(trials: list[dict]) -> dict:
    rows = [_guardrail_row(t, f"t{i+1}") for i, t in enumerate(trials)]
    if not rows:
        return {}
    return {
        "cost_savings_pct": int(np.median([r["cost_savings_pct"] for r in rows])),
        "wall_savings_pct": int(np.median([r["wall_savings_pct"] for r in rows])),
        "baseline_cost": float(np.median([r["baseline_cost"] for r in rows])),
        "helm_cost": float(np.median([r["helm_cost"] for r in rows])),
        "baseline_sec": float(np.median([r["baseline_sec"] for r in rows])),
        "helm_sec": float(np.median([r["helm_sec"] for r in rows])),
        "baseline_calls": 2,
        "helm_calls": 1,
        "blocked_rule": rows[0]["blocked_rule"],
        "n_trials": len(rows),
    }


def _filter(rows: list[dict], **kw) -> list[dict]:
    out = rows
    for k, v in kw.items():
        if isinstance(v, str) and v.endswith("*"):
            out = [r for r in out if r.get(k, "").startswith(v[:-1])]
        else:
            out = [r for r in out if r.get(k) == v]
    return sorted(out, key=lambda r: r["agent_count"])


def _save(fig: plt.Figure, name: str) -> Path:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    path = OUT_DIR / name
    fig.savefig(path, dpi=160, bbox_inches="tight", facecolor=fig.get_facecolor())
    plt.close(fig)
    return path


def plot_contention_savings(rows: list[dict]) -> Path:
    """Cost & wall savings % by agent count (std); winner-only overlay at N=4,6."""
    std = _filter(rows, kind="live", id="contention_std*")
    nr = {r["agent_count"]: r for r in _filter(rows, kind="live", id="contention_no_reassign*")}

    ns = [r["agent_count"] for r in std]
    x = np.arange(len(ns))
    w = 0.32

    fig, ax = plt.subplots(figsize=(9, 5))
    ax.axhline(0, color="#cbd5e1", linewidth=1, zorder=0)

    bars = [
        ax.bar(x - w / 2, [r["cost_savings_pct"] for r in std], w, label="Cost (std)", color=WIN, edgecolor="white"),
        ax.bar(x + w / 2, [r["wall_savings_pct"] for r in std], w, label="Wall (std)", color=HELM, edgecolor="white"),
    ]
    for b in bars:
        for rect in b:
            h = rect.get_height()
            ax.annotate(
                f"{h:+.0f}%",
                xy=(rect.get_x() + rect.get_width() / 2, h),
                xytext=(0, 3 if h >= 0 else -12),
                textcoords="offset points",
                ha="center",
                va="bottom" if h >= 0 else "top",
                fontsize=9,
                color="#334155",
            )

    # Winner-only markers where measured (N=4,6)
    for i, n in enumerate(ns):
        if n not in nr:
            continue
        r = nr[n]
        ax.scatter(i - w / 2, r["cost_savings_pct"], s=120, marker="D", color="#047857", zorder=5)
        ax.scatter(i + w / 2, r["wall_savings_pct"], s=120, marker="D", color="#1d4ed8", zorder=5)
        ax.annotate(f"{r['cost_savings_pct']:+.0f}%", (i - w / 2, r["cost_savings_pct"]), textcoords="offset points", xytext=(0, 10), ha="center", fontsize=8, color="#047857")
        ax.annotate(f"{r['wall_savings_pct']:+.0f}%", (i + w / 2, r["wall_savings_pct"]), textcoords="offset points", xytext=(0, 10), ha="center", fontsize=8, color="#1d4ed8")

    ax.set_xticks(x)
    ax.set_xticklabels([f"N={n}" for n in ns])
    ax.set_ylabel("Helm savings vs baseline (%)")
    ax.set_title("Contention — duplicate work (live AWS)")
    ax.yaxis.set_major_formatter(mticker.FuncFormatter(lambda v, _: f"{v:+.0f}%"))
    h, lab = ax.get_legend_handles_labels()
    if nr:
        h += [
            Line2D([0], [0], marker="D", color="w", markerfacecolor="#047857", markersize=8, label="Cost (winner-only)"),
            Line2D([0], [0], marker="D", color="w", markerfacecolor="#1d4ed8", markersize=8, label="Wall (winner-only)"),
        ]
        lab += ["Cost (winner-only)", "Wall (winner-only)"]
    ax.legend(h, lab, loc="upper left", ncol=2, fontsize=9)
    ax.grid(axis="y", linestyle="--")
    ax.set_ylim(bottom=min(-20, min(r["wall_savings_pct"] for r in std) - 8))

    fig.text(0.5, 0.01, "Bars = std (dedup + reassign)  |  diamonds = winner-only at N=4,6", ha="center", fontsize=9, color="#64748b")
    return _save(fig, "01_contention_savings.png")


def plot_contention_cost_wall(rows: list[dict]) -> Path:
    """Side-by-side absolute cost and wall for contention_std."""
    data = _filter(rows, kind="live", id="contention_std*")
    ns = [r["agent_count"] for r in data]
    x = np.arange(len(ns))
    w = 0.35

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(10, 4.5), sharex=True)

    for ax, key, ylab, fmt in [
        (ax1, "baseline_usd", "Cost (USD)", "${:.3f}"),
        (ax2, "baseline_sec", "Wall time (s)", "{:.1f}s"),
    ]:
        helm_key = "helm_usd" if "usd" in key else "helm_sec"
        b1 = ax.bar(x - w / 2, [r[key] for r in data], w, label="Baseline", color=BASELINE, edgecolor="white")
        b2 = ax.bar(x + w / 2, [r[helm_key] for r in data], w, label="Helm", color=HELM, edgecolor="white")
        ax.set_xticks(x)
        ax.set_xticklabels([f"N={n}" for n in ns])
        ax.set_ylabel(ylab)
        ax.legend(loc="upper right", fontsize=9)
        ax.grid(axis="y", linestyle="--")
        for bars in (b1, b2):
            for rect in bars:
                v = rect.get_height()
                ax.annotate(
                    fmt.format(v),
                    xy=(rect.get_x() + rect.get_width() / 2, v),
                    xytext=(0, 3),
                    textcoords="offset points",
                    ha="center",
                    fontsize=8,
                    color="#475569",
                )

    ax1.set_title("Cost")
    ax2.set_title("Wall clock")
    fig.suptitle("Contention E2E — baseline vs Helm (std config)", y=1.02)
    fig.tight_layout()
    return _save(fig, "02_contention_absolute.png")


def plot_agents_executed(rows: list[dict]) -> Path:
    """Agents run: baseline always N vs Helm executed (std + winner-only at N=4,6)."""
    std = _filter(rows, kind="live", id="contention_std*")
    nr = {r["agent_count"]: r for r in _filter(rows, kind="live", id="contention_no_reassign*")}

    fig, (ax_std, ax_nr) = plt.subplots(1, 2, figsize=(11, 4.5), gridspec_kw={"width_ratios": [2, 1]})

    def _panel(ax, data: list[dict], title: str) -> None:
        ns = [r["agent_count"] for r in data]
        x = np.arange(len(ns))
        w = 0.35
        ax.bar(x - w / 2, ns, w, label="Baseline", color=BASELINE, edgecolor="white")
        ax.bar(x + w / 2, [r["helm_agents_executed"] for r in data], w, label="Helm", color=HELM, edgecolor="white")
        for i, r in enumerate(data):
            sk = r.get("helm_agents_skipped", 0)
            skipped = sk if isinstance(sk, int) else len(sk)
            if skipped:
                ax.annotate(f"−{skipped} skipped", xy=(x[i] + w / 2, r["helm_agents_executed"]), xytext=(0, 6), textcoords="offset points", ha="center", fontsize=8, color=WIN, fontweight="bold")
        ax.set_xticks(x)
        ax.set_xticklabels([f"N={n}" for n in ns])
        ax.set_ylabel("Agent implementations")
        ax.set_title(title)
        ax.legend(loc="upper left", fontsize=9)
        ax.grid(axis="y", linestyle="--")
        ax.set_ylim(0, max(ns) + 1.5)

    _panel(ax_std, std, "Std — dedup + reassign")
    _panel(ax_nr, [nr[n] for n in sorted(nr)], "Winner-only (N=4,6)")
    fig.suptitle("Fewer Helm agents than baseline (contention)", y=1.02)
    fig.tight_layout()
    return _save(fig, "03_contention_agents.png")


def plot_merge_fleet(rows: list[dict]) -> Path:
    """Merge phase wall savings when multiple files conflict."""
    data = _filter(rows, kind="merge_fleet")
    ns = [r["agent_count"] for r in data]
    walls = [r["wall_savings_pct"] for r in data]
    costs = [r["cost_savings_pct"] for r in data]

    fig, ax = plt.subplots(figsize=(8, 5))
    colors = [WIN if w > 0 else LOSS for w in walls]
    bars = ax.bar([f"N={n}" for n in ns], walls, color=colors, edgecolor="white", width=0.55)

    for rect, n, w in zip(bars, ns, walls):
        files = "auth" if n < 6 else "auth + listings"
        ax.annotate(
            f"{w:+.0f}%\n({files})",
            xy=(rect.get_x() + rect.get_width() / 2, w),
            xytext=(0, 4),
            textcoords="offset points",
            ha="center",
            va="bottom",
            fontsize=10,
            fontweight="bold",
            color="#334155",
        )

    ax.axhline(0, color="#cbd5e1", linewidth=1)
    ax.set_ylabel("Merge-phase wall savings (%)")
    ax.set_title("Parallel per-file merge-fix (merge fleet benchmark)")
    ax.yaxis.set_major_formatter(mticker.FuncFormatter(lambda v, _: f"{v:+.0f}%"))
    ax.grid(axis="y", linestyle="--")

    cost_note = ", ".join(f"N={n}: {c:+d}% cost" for n, c in zip(ns, costs))
    fig.text(0.5, 0.01, f"Haiku cost ~flat ({cost_note})", ha="center", fontsize=9, color="#64748b")
    return _save(fig, "04_merge_fleet_wall.png")


def plot_phase_breakdown(rows: list[dict]) -> Path:
    """Stacked phase times for contention at N=4,6,8."""
    picks = [r for r in _filter(rows, kind="live", id="contention_std*") if r["agent_count"] in (4, 6, 8)]
    labels = [f"N={r['agent_count']}\nHelm" for r in picks]
    phases = ["coord", "agents", "merge_verify"]
    colors = ["#f59e0b", HELM, "#a78bfa"]

    fig, ax = plt.subplots(figsize=(8, 5))
    x = np.arange(len(picks))
    bottom = np.zeros(len(picks))

    for phase, color in zip(phases, colors):
        vals = [r.get("helm_phases", {}).get(phase, 0) for r in picks]
        ax.bar(x, vals, bottom=bottom, label=phase.replace("_", " "), color=color, edgecolor="white", width=0.5)
        bottom += np.array(vals)

    for i, r in enumerate(picks):
        total = r["helm_sec"]
        ax.text(i, total + 0.15, f"{total:.1f}s", ha="center", fontsize=10, fontweight="bold", color="#334155")

    ax.set_xticks(x)
    ax.set_xticklabels(labels)
    ax.set_ylabel("Seconds")
    ax.set_title("Helm phase breakdown (contention, std)")
    ax.legend(loc="upper right")
    ax.grid(axis="y", linestyle="--")
    return _save(fig, "05_contention_phases.png")


def plot_guardrail_savings(trials: list[dict]) -> Path | None:
    """Per-trial cost & wall savings (3 live runs)."""
    if not trials:
        return None
    rows = [_guardrail_row(t, f"Run {i+1}") for i, t in enumerate(trials)]
    x = np.arange(len(rows))
    w = 0.35

    fig, ax = plt.subplots(figsize=(9, 5))
    ax.axhline(0, color="#cbd5e1", linewidth=1)
    b1 = ax.bar(x - w / 2, [r["cost_savings_pct"] for r in rows], w, label="Cost", color=WIN, edgecolor="white")
    b2 = ax.bar(x + w / 2, [r["wall_savings_pct"] for r in rows], w, label="Wall", color=GUARDRAIL_ACCENT, edgecolor="white")
    for bars in (b1, b2):
        for rect in bars:
            h = rect.get_height()
            ax.annotate(
                f"{h:+.0f}%",
                xy=(rect.get_x() + rect.get_width() / 2, h),
                xytext=(0, 4),
                textcoords="offset points",
                ha="center",
                fontsize=10,
                fontweight="bold",
                color="#334155",
            )

    med = _guardrail_median(trials)
    ax.set_xticks(x)
    ax.set_xticklabels([r["label"] for r in rows])
    ax.set_ylabel("Helm savings vs baseline (%)")
    ax.set_title("Guardrails on ShopFix auth.py — live AWS (3 trials)")
    ax.yaxis.set_major_formatter(mticker.FuncFormatter(lambda v, _: f"{v:+.0f}%"))
    ax.legend(loc="upper right")
    ax.grid(axis="y", linestyle="--")
    fig.text(
        0.5,
        0.01,
        f"Median: +{med['cost_savings_pct']}% cost, +{med['wall_savings_pct']}% wall  |  "
        f"rule={med.get('blocked_rule', 'reverses_recent_decision')}",
        ha="center",
        fontsize=9,
        color="#64748b",
    )
    return _save(fig, "06_guardrail_savings.png")


def plot_guardrail_absolute(trials: list[dict]) -> Path | None:
    """Median trial: baseline (2x Haiku) vs Helm (1x guardrail)."""
    if not trials:
        return None
    med = _guardrail_median(trials)
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(10, 4.5))

    for ax, b_val, h_val, ylab, fmt in [
        (ax1, med["baseline_cost"], med["helm_cost"], "Cost (USD)", "${:.4f}"),
        (ax2, med["baseline_sec"], med["helm_sec"], "Wall time (s)", "{:.1f}s"),
    ]:
        bars = ax.bar(
            ["Baseline\n(2 Haiku edits)", "Helm\n(block + resolve)"],
            [b_val, h_val],
            color=[BASELINE, GUARDRAIL_ACCENT],
            edgecolor="white",
            width=0.55,
        )
        ax.set_ylabel(ylab)
        ax.grid(axis="y", linestyle="--")
        for rect in bars:
            v = rect.get_height()
            ax.annotate(
                fmt.format(v),
                xy=(rect.get_x() + rect.get_width() / 2, v),
                xytext=(0, 4),
                textcoords="offset points",
                ha="center",
                fontsize=10,
                color="#475569",
            )

    ax1.set_title("Cost (median of 3)")
    ax2.set_title("Wall clock (median of 3)")
    fig.suptitle("ShopFix guardrail — destructive path vs preflight block", y=1.02)
    fig.tight_layout()
    return _save(fig, "07_guardrail_absolute.png")


def plot_guardrail_calls(trials: list[dict]) -> Path | None:
    """Bedrock calls: baseline runs 2 agent edits, Helm runs 1 guardrail."""
    if not trials:
        return None
    fig, ax = plt.subplots(figsize=(7, 4.5))
    labels = ["Baseline\n(no guardrail)", "Helm\n(guardrail)"]
    calls = [2, 1]
    colors = [BASELINE, GUARDRAIL_ACCENT]
    bars = ax.bar(labels, calls, color=colors, edgecolor="white", width=0.5)
    for rect, n in zip(bars, calls):
        ax.annotate(
            str(n),
            xy=(rect.get_x() + rect.get_width() / 2, n),
            xytext=(0, 6),
            textcoords="offset points",
            ha="center",
            fontsize=14,
            fontweight="bold",
        )
    ax.set_ylabel("Bedrock calls")
    ax.set_title("Fewer calls when delete is blocked upfront")
    ax.set_ylim(0, 2.8)
    ax.grid(axis="y", linestyle="--")
    fig.text(
        0.5,
        0.01,
        "Baseline: destructive edit on auth.py + rebuild  |  Helm: preflight block + 1 Haiku resolution",
        ha="center",
        fontsize=9,
        color="#64748b",
    )
    return _save(fig, "08_guardrail_calls.png")


def plot_guardrail_headline(trials: list[dict]) -> Path | None:
    """Single slide: median savings bars."""
    if not trials:
        return None
    med = _guardrail_median(trials)
    fig, ax = plt.subplots(figsize=(7, 5))
    metrics = ["Cost savings", "Wall savings"]
    vals = [med["cost_savings_pct"], med["wall_savings_pct"]]
    colors = [WIN, GUARDRAIL_ACCENT]
    bars = ax.barh(metrics, vals, color=colors, height=0.5, edgecolor="white")
    ax.axvline(0, color="#cbd5e1", linewidth=1)
    ax.set_xlabel("Helm vs baseline (%)")
    for rect, v in zip(bars, vals):
        ax.text(v + 2, rect.get_y() + rect.get_height() / 2, f"+{v}%", va="center", fontsize=14, fontweight="bold")
    ax.set_xlim(0, max(vals) + 15)
    ax.set_title("Guardrails — ShopFix backend/app/routers/auth.py")
    ax.grid(axis="x", linestyle="--")
    fig.text(
        0.5,
        0.02,
        f"{med['n_trials']} live trials  |  blocks delete (reverses_recent_decision)  |  ~${med['helm_cost']:.4f} vs ~${med['baseline_cost']:.4f}",
        ha="center",
        fontsize=9,
        color="#64748b",
    )
    return _save(fig, "09_guardrail_headline.png")


def plot_dashboard(rows: list[dict], guardrail_trials: list[dict] | None = None) -> Path:
    """Single slide: best metrics summary."""
    fig = plt.figure(figsize=(12, 7))
    fig.patch.set_facecolor(BG)
    gs = fig.add_gridspec(2, 2, hspace=0.35, wspace=0.28)

    # 1 — contention wall std
    ax1 = fig.add_subplot(gs[0, 0])
    std = _filter(rows, kind="live", id="contention_std*")
    ns = [r["agent_count"] for r in std]
    ax1.plot(ns, [r["wall_savings_pct"] for r in std], "o-", color=HELM, linewidth=2.5, markersize=10, label="Wall Δ%")
    ax1.plot(ns, [r["cost_savings_pct"] for r in std], "s--", color=WIN, linewidth=2, markersize=8, label="Cost Δ%")
    ax1.axhline(0, color="#cbd5e1", linewidth=1)
    ax1.set_xticks(ns)
    ax1.set_xlabel("Agents")
    ax1.set_ylabel("Savings %")
    ax1.set_title("Contention (std)")
    ax1.legend(fontsize=8)
    ax1.grid(True, linestyle="--", alpha=0.7)

    # 2 — merge fleet
    ax2 = fig.add_subplot(gs[0, 1])
    mf = _filter(rows, kind="merge_fleet")
    ns_m = [r["agent_count"] for r in mf]
    ax2.bar([str(n) for n in ns_m], [r["wall_savings_pct"] for r in mf], color=HELM, edgecolor="white", width=0.6)
    ax2.axhline(0, color="#cbd5e1", linewidth=1)
    ax2.set_xlabel("Agents")
    ax2.set_ylabel("Merge wall savings %")
    ax2.set_title("Merge fleet")

    # 3 — guardrails or winner-only
    ax3 = fig.add_subplot(gs[1, 0])
    if guardrail_trials:
        med = _guardrail_median(guardrail_trials)
        ax3.barh(
            ["Cost", "Wall"],
            [med["cost_savings_pct"], med["wall_savings_pct"]],
            color=[WIN, GUARDRAIL_ACCENT],
            height=0.4,
            edgecolor="white",
        )
        ax3.set_xlabel("Savings %")
        ax3.set_title("Guardrails (auth.py)")
        ax3.axvline(0, color="#cbd5e1", linewidth=1)
        for i, v in enumerate([med["cost_savings_pct"], med["wall_savings_pct"]]):
            ax3.text(v + 2, i, f"+{v}%", va="center", fontsize=10, fontweight="bold")
    else:
        nr = _filter(rows, kind="live", id="contention_no_reassign*")
        ns_nr = [r["agent_count"] for r in nr]
        ax3.barh([f"N={n}" for n in ns_nr], [r["cost_savings_pct"] for r in nr], color=WIN, height=0.45, edgecolor="white")
        ax3.set_xlabel("Cost savings %")
        ax3.set_title("Winner-only (max cost win)")
        ax3.axvline(0, color="#cbd5e1", linewidth=1)
        for i, r in enumerate(nr):
            ax3.text(r["cost_savings_pct"] + 1, i, f"+{r['cost_savings_pct']}%", va="center", fontsize=10, fontweight="bold")

    # 4 — headline callouts
    ax4 = fig.add_subplot(gs[1, 1])
    ax4.axis("off")
    best_wall = max(std, key=lambda r: r["wall_savings_pct"])
    best_merge = max(mf, key=lambda r: r["wall_savings_pct"])
    lines = [
        ("Headlines (live AWS)", 14, "#0f172a", "bold"),
        ("", 6, BG, "normal"),
        (f"Contention N={best_wall['agent_count']}: {best_wall['wall_savings_pct']:+.0f}% wall, {best_wall['cost_savings_pct']:+.0f}% cost", 11, "#334155", "normal"),
        (f"Merge fleet N={best_merge['agent_count']}: {best_merge['wall_savings_pct']:+.0f}% merge wall", 11, "#334155", "normal"),
        ("", 6, BG, "normal"),
    ]
    if not guardrail_trials:
        nr = _filter(rows, kind="live", id="contention_no_reassign*")
        if nr:
            best_cost_nr = max(nr, key=lambda r: r["cost_savings_pct"])
            lines.insert(
                4,
                (
                    f"Winner-only N={best_cost_nr['agent_count']}: {best_cost_nr['cost_savings_pct']:+.0f}% cost, {best_cost_nr['wall_savings_pct']:+.0f}% wall",
                    11,
                    "#334155",
                    "normal",
                ),
            )
    if guardrail_trials:
        med = _guardrail_median(guardrail_trials)
        lines.append(
            (
                f"Guardrails auth: +{med['cost_savings_pct']}% cost, +{med['wall_savings_pct']}% wall (block delete)",
                11,
                GUARDRAIL_ACCENT,
                "normal",
            )
        )
    lines.extend(
        [
            ("Gate / disjoint: 0 dedup calls", 10, "#64748b", "normal"),
            ("Intent opposition: excluded from charts", 10, "#94a3b8", "italic"),
        ]
    )
    y = 0.95
    for text, size, color, weight in lines:
        kw: dict = {"fontsize": size, "color": color, "fontweight": weight, "va": "top"}
        if weight == "italic":
            kw["fontstyle"] = "italic"
            kw["fontweight"] = "normal"
        ax4.text(0.05, y, text, transform=ax4.transAxes, **kw)
        y -= 0.14 if size > 8 else 0.06

    fig.suptitle("ShopFix + Helm — four pillars (live AWS)", fontsize=15, fontweight="bold", y=0.98)
    return _save(fig, "00_dashboard.png")


def _write_index(paths: list[Path], json_path: Path, *, has_guardrail: bool) -> None:
    md = OUT_DIR / "README.md"
    lines = [
        "# ShopFix demo charts",
        "",
        "Generated from demo matrix (intent opposition excluded).",
        "",
        f"Source: `{json_path.relative_to(ROOT)}`",
        "",
        "| Chart | Use in demo |",
        "|-------|-------------|",
        "| [00_dashboard.png](00_dashboard.png) | Single-slide overview |",
        "| [01_contention_savings.png](01_contention_savings.png) | Cost + wall % by N |",
        "| [02_contention_absolute.png](02_contention_absolute.png) | Absolute $ and seconds |",
        "| [03_contention_agents.png](03_contention_agents.png) | Fewer agents run |",
        "| [04_merge_fleet_wall.png](04_merge_fleet_wall.png) | Merge parallelism story |",
        "| [05_contention_phases.png](05_contention_phases.png) | Where time goes |",
    ]
    if has_guardrail:
        lines.extend(
            [
                "| [06_guardrail_savings.png](06_guardrail_savings.png) | Guardrail savings per trial |",
                "| [07_guardrail_absolute.png](07_guardrail_absolute.png) | Guardrail $ and seconds (median) |",
                "| [08_guardrail_calls.png](08_guardrail_calls.png) | 2 Haiku vs 1 guardrail call |",
                "| [09_guardrail_headline.png](09_guardrail_headline.png) | Guardrail one-slide |",
            ]
        )
    lines.extend(
        [
            "",
            "Regenerate:",
            "",
            "```bash",
            "python scripts/plot_shopfix_demo_matrix.py",
            "```",
            "",
        ]
    )
    md.write_text("\n".join(lines), encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--json", type=Path, default=DEFAULT_JSON)
    args = parser.parse_args()

    _style()
    rows = _load(args.json)
    guardrail_trials = load_guardrail_trials()
    paths: list[Path] = [
        plot_dashboard(rows, guardrail_trials),
        plot_contention_savings(rows),
        plot_contention_cost_wall(rows),
        plot_agents_executed(rows),
        plot_merge_fleet(rows),
        plot_phase_breakdown(rows),
    ]
    for fn in (
        plot_guardrail_savings,
        plot_guardrail_absolute,
        plot_guardrail_calls,
        plot_guardrail_headline,
    ):
        p = fn(guardrail_trials)
        if p:
            paths.append(p)
    _write_index(paths, args.json, has_guardrail=bool(guardrail_trials))
    for p in paths:
        print(f"Wrote {p}")
    print(f"Wrote {OUT_DIR / 'README.md'}")
    sync_script = ROOT / "scripts" / "sync_demo_charts.sh"
    if sync_script.is_file():
        subprocess.run(["bash", str(sync_script)], check=True, cwd=ROOT)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
