"""
Analysis and Visualization Module for Satellite Quantum Error Correction
Framework: NumPy, Pandas, Matplotlib

Computes analytical benchmarks (P_L = 3p^2 - 2p^3), statistical metrics (MAE, RMSE, R^2),
and generates high-resolution figures comparing theory against Monte Carlo simulations.
"""

import sys
import os
from typing import Dict, Any
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

# Ensure UTF-8 output on Windows consoles
if sys.stdout.encoding and sys.stdout.encoding.lower() != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass


def theoretical_logical_error(p: np.ndarray | float) -> np.ndarray | float:
    """
    Theoretical logical error rate for the 3-qubit bit-flip code:
        P_L = 3p^2(1 - p) + p^3 = 3p^2 - 2p^3
    Derived from probability of >= 2 bit flips across 3 independent channel qubits.
    """
    p_arr = np.asarray(p, dtype=float)
    return 3.0 * (p_arr ** 2) * (1.0 - p_arr) + (p_arr ** 3)


def theoretical_success_rate(p: np.ndarray | float) -> np.ndarray | float:
    """Theoretical transmission success rate: S(p) = 1 - P_L."""
    return 1.0 - theoretical_logical_error(p)


def theoretical_error_reduction(p: np.ndarray | float) -> np.ndarray | float:
    """
    Theoretical percentage error reduction achieved by the code over unencoded link:
        Reduction(%) = ((p - P_L) / p) * 100% = (1 - p)(1 - 2p) * 100%
    """
    p_arr = np.asarray(p, dtype=float)
    return np.where(p_arr > 1e-12, (1.0 - p_arr) * (1.0 - 2.0 * p_arr) * 100.0, 100.0)


def evaluate_simulation_accuracy(df: pd.DataFrame) -> Dict[str, float]:
    """Computes statistical goodness-of-fit metrics (MAE, RMSE, Max Deviation, R^2)."""
    y_sim = df["encoded_error_sim"].values
    y_th = df["encoded_error_theoretical"].values
    residuals = y_sim - y_th

    mae = float(np.mean(np.abs(residuals)))
    rmse = float(np.sqrt(np.mean(residuals ** 2)))
    max_dev = float(np.max(np.abs(residuals)))

    ss_res = np.sum(residuals ** 2)
    ss_tot = np.sum((y_sim - np.mean(y_sim)) ** 2)
    r2 = 1.0 - (ss_res / ss_tot) if ss_tot > 0 else 1.0

    return {
        "MAE": mae,
        "RMSE": rmse,
        "Max_Deviation": max_dev,
        "R2_Score": float(r2)
    }


def print_summary_table(df: pd.DataFrame) -> None:
    """Displays a formatted summary table comparing simulated and theoretical error rates."""
    print("\n" + "=" * 115)
    print(" " * 28 + "EXPERIMENTAL SUMMARY TABLE: SATELLITE QUANTUM LINK QEC")
    print("=" * 115)
    header = (
        f"{'p (Physical)':<12} | "
        f"{'Unenc Err':<10} | "
        f"{'Theo Err':<10} | "
        f"{'Sim Err':<10} | "
        f"{'Residual':<10} | "
        f"{'Unenc Succ':<11} | "
        f"{'Encod Succ':<11} | "
        f"{'Theo Reduc(%)':<14} | "
        f"{'Sim Reduc(%)':<14}"
    )
    print(header)
    print("-" * 115)

    for _, row in df.iterrows():
        p_val = row["physical_error_p"]
        unenc_err = row["unencoded_error_sim"]
        theo_err = row["encoded_error_theoretical"]
        sim_err = row["encoded_error_sim"]
        residual = sim_err - theo_err
        unenc_succ = row["unencoded_success_sim"]
        enc_succ = row["encoded_success_sim"]
        theo_red = row["error_reduction_percent_theoretical"]
        sim_red = row["error_reduction_percent_sim"]

        line = (
            f"{p_val:<12.2f} | "
            f"{unenc_err:<10.4f} | "
            f"{theo_err:<10.4f} | "
            f"{sim_err:<10.4f} | "
            f"{residual:<+10.4f} | "
            f"{unenc_succ*100:<10.2f}% | "
            f"{enc_succ*100:<10.2f}% | "
            f"{theo_red:<13.2f}% | "
            f"{sim_red:<13.2f}%"
        )
        print(line)

    print("=" * 115)
    metrics = evaluate_simulation_accuracy(df)
    print(f"Goodness-of-Fit (N={len(df)} points): MAE={metrics['MAE']:.6f} | RMSE={metrics['RMSE']:.6f} | Max Dev={metrics['Max_Deviation']:.6f} | R^2={metrics['R2_Score']:.6f}")
    print("=" * 115 + "\n")


def generate_all_plots(df: pd.DataFrame, sample_experiment: Dict[str, Any], output_dir: str = "plots") -> Dict[str, str]:
    """Generates the four core experimental plots and saves them at 300 DPI."""
    os.makedirs(output_dir, exist_ok=True)
    generated_plots = {}

    plt.rcParams.update({
        'font.sans-serif': ['DejaVu Sans', 'Arial', 'Helvetica'],
        'axes.edgecolor': '#CBD5E0',
        'axes.linewidth': 1.2,
        'grid.color': '#E2E8F0',
        'grid.linestyle': '--',
        'grid.alpha': 0.7,
        'legend.frameon': True,
        'legend.facecolor': '#FFFFFF',
        'legend.edgecolor': '#CBD5E0'
    })

    p = df["physical_error_p"].values
    p_fine = np.linspace(p.min(), p.max(), 200)
    y_fine_th = theoretical_logical_error(p_fine)
    shots = sample_experiment.get("shots", 10000)

    # 1. Error Rate Comparison: Physical p vs Logical Error P_L
    fig, ax = plt.subplots(figsize=(9, 6), dpi=300)
    ax.plot(p, df["unencoded_error_sim"], color='#E53E3E', linestyle='--', marker='s', markersize=4, label='Unencoded Link ($P = p$)', alpha=0.9, lw=1.8)
    ax.plot(p_fine, y_fine_th, color='#2B6CB0', linestyle='-', lw=2.5, label=r'Theoretical Curve: $P_L = 3p^2 - 2p^3$')
    ax.plot(p, df["encoded_error_sim"], color='#319795', linestyle='none', marker='o', markersize=6, label='Monte Carlo Simulated Logical Error (Qiskit Aer)', zorder=5)

    # 95% Confidence interval band (+/- 1.96 * sigma)
    se = np.sqrt(y_fine_th * (1.0 - y_fine_th) / shots)
    ax.fill_between(p_fine, np.maximum(0, y_fine_th - 2 * se), y_fine_th + 2 * se, color='#63B3ED', alpha=0.25, label=r'Monte Carlo $95\%$ Confidence Interval ($\pm 1.96\sigma$)')

    # Mid-range benchmark callout
    idx_ann = np.abs(p - 0.15).argmin()
    ax.annotate(
        f"At p = {p[idx_ann]:.2f}:\n• Unencoded Err: {df['unencoded_error_sim'].iloc[idx_ann]:.4f}\n• Simulated $P_L$: {df['encoded_error_sim'].iloc[idx_ann]:.4f}\n• Theory $P_L$: {df['encoded_error_theoretical'].iloc[idx_ann]:.4f}\n• Error Reduction: {df['error_reduction_percent_sim'].iloc[idx_ann]:.1f}%",
        xy=(p[idx_ann], df["encoded_error_sim"].iloc[idx_ann]),
        xytext=(p.min() + (p.max() - p.min()) * 0.10, df["unencoded_error_sim"].max() * 0.70),
        arrowprops=dict(facecolor='#1A365D', arrowstyle='->', lw=1.5),
        bbox=dict(boxstyle="round,pad=0.5", facecolor="#EBF8FF", edgecolor="#3182CE", lw=1.2),
        fontsize=9.5
    )

    ax.set_title("Physical vs. Logical Error Probability in Satellite Quantum Link", fontsize=14, fontweight='bold', pad=14, color='#1A365D')
    ax.set_xlabel("Physical Channel Bit-Flip Error Probability ($p$)", fontsize=12, labelpad=10)
    ax.set_ylabel("Logical Error Probability ($P_L$)", fontsize=12, labelpad=10)
    ax.set_xlim(p.min() - 0.01, p.max() + 0.01)
    ax.set_ylim(-0.005, max(df["unencoded_error_sim"].max(), df["encoded_error_sim"].max()) * 1.08)
    ax.grid(True)
    ax.legend(loc='upper left', fontsize=9.5)
    plt.tight_layout()
    p1_path = os.path.join(output_dir, "01_error_rate_comparison.png")
    fig.savefig(p1_path)
    plt.close()
    generated_plots["01_error_rate_comparison"] = p1_path

    # 2. Transmission Success Rate Comparison
    fig, ax = plt.subplots(figsize=(9, 6), dpi=300)
    ax.plot(p, df["unencoded_success_sim"] * 100, color='#E53E3E', linestyle='--', marker='^', markersize=4, label='Unencoded Transmission ($1 - p$)', lw=1.8)
    ax.plot(p_fine, (1.0 - y_fine_th) * 100, color='#2F855A', linestyle='-', lw=2.5, label=r'Theoretical QEC Success ($1 - P_L$)')
    ax.plot(p, df["encoded_success_sim"] * 100, color='#276749', linestyle='none', marker='o', markersize=6, label='Simulated 3-Qubit QEC Success', zorder=5)
    ax.fill_between(p, df["unencoded_success_sim"] * 100, df["encoded_success_sim"] * 100, color='#C6F6D5', alpha=0.45, label='Fidelity Enhancement Gain')

    min_succ = min(df["unencoded_success_sim"].min(), df["encoded_success_sim"].min()) * 100
    ax.set_title("Transmission Success Rate vs. Channel Error Probability", fontsize=14, fontweight='bold', pad=14, color='#1A365D')
    ax.set_xlabel("Physical Channel Bit-Flip Error Probability ($p$)", fontsize=12, labelpad=10)
    ax.set_ylabel("Transmission Success Rate (%)", fontsize=12, labelpad=10)
    ax.set_xlim(p.min() - 0.01, p.max() + 0.01)
    ax.set_ylim(max(0, min_succ - 4), 102)
    ax.grid(True)
    ax.legend(loc='lower left', fontsize=10)
    plt.tight_layout()
    p2_path = os.path.join(output_dir, "02_success_rate_comparison.png")
    fig.savefig(p2_path)
    plt.close()
    generated_plots["02_success_rate_comparison"] = p2_path

    # 3. Percentage Error Reduction
    fig, ax = plt.subplots(figsize=(9, 6), dpi=300)
    ax.plot(p_fine, theoretical_error_reduction(p_fine), color='#805AD5', linestyle='-', lw=2.5, label=r'Theoretical Reduction: $(1 - p)(1 - 2p) \times 100\%$')
    ax.plot(p, df["error_reduction_percent_sim"], color='#44337A', linestyle='none', marker='D', markersize=6, label='Simulated Reduction (Monte Carlo)', zorder=5)
    ax.axhline(50, color='#CBD5E0', linestyle='--', lw=1, label='50% Error Reduction Threshold')

    # Selected callout points
    callouts = [cp for cp in [0.05, 0.10, 0.15, 0.20, 0.25, 0.30] if p.min() - 1e-4 <= cp <= p.max() + 1e-4]
    for cp in callouts:
        c_idx = np.abs(p - cp).argmin()
        c_red = df["error_reduction_percent_sim"].iloc[c_idx]
        ax.scatter([p[c_idx]], [c_red], color='#D69E2E', s=55, zorder=6)
        ax.annotate(f"p={p[c_idx]:.2f}\n{c_red:.1f}%", xy=(p[c_idx], c_red), xytext=(p[c_idx], c_red + 4), ha='center', fontsize=8.5, fontweight='bold', color='#2D3748')

    min_red = df["error_reduction_percent_sim"].min()
    ax.set_title("Quantum Error Correction Efficacy: Error Reduction (%)", fontsize=14, fontweight='bold', pad=14, color='#1A365D')
    ax.set_xlabel("Physical Channel Bit-Flip Error Probability ($p$)", fontsize=12, labelpad=10)
    ax.set_ylabel("Error Reduction Achieved (%)", fontsize=12, labelpad=10)
    ax.set_xlim(p.min() - 0.01, p.max() + 0.01)
    ax.set_ylim(max(0, min_red - 8), 105)
    ax.grid(True)
    ax.legend(loc='lower left', fontsize=10)
    plt.tight_layout()
    p3_path = os.path.join(output_dir, "03_error_reduction.png")
    fig.savefig(p3_path)
    plt.close()
    generated_plots["03_error_reduction"] = p3_path

    # 4. Measurement Results & Syndrome Distribution Breakdown
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(13, 5.5), dpi=300)
    p_sample = sample_experiment.get("p", 0.10)
    unenc_counts = sample_experiment.get("unencoded_counts", {})
    enc_counts = sample_experiment.get("encoded_counts", {})
    syndrome_counts = sample_experiment.get("syndrome_distribution", {})

    unenc_0, unenc_1 = unenc_counts.get("0", 0), unenc_counts.get("1", 0)
    enc_0 = sum(count for k, count in enc_counts.items() if k.split()[0] == '0')
    enc_1 = sum(count for k, count in enc_counts.items() if k.split()[0] == '1')

    categories = ['Logical |0⟩ (Success)', 'Logical |1⟩ (Error)']
    x = np.arange(len(categories))
    width = 0.35

    bars1 = ax1.bar(x - width/2, [unenc_0, unenc_1], width, label='Unencoded Link', color=['#48BB78', '#F56565'], alpha=0.85, edgecolor='#2D3748', lw=1.2)
    bars2 = ax1.bar(x + width/2, [enc_0, enc_1], width, label='3-Qubit Repetition Code', color=['#2F855A', '#9B2C2C'], alpha=0.95, edgecolor='#2D3748', lw=1.2)

    for bar in list(bars1) + list(bars2):
        h = bar.get_height()
        ax1.text(bar.get_x() + bar.get_width()/2., h + 100, f'{h:,}', ha='center', va='bottom', fontsize=9, fontweight='bold')

    ax1.set_title(f"Transmission Outcomes (p = {p_sample:.2f}, N = {shots:,})", fontsize=12, fontweight='bold', pad=12, color='#1A365D')
    ax1.set_xticks(x)
    ax1.set_xticklabels(categories, fontsize=10)
    ax1.set_ylabel("Shot Counts", fontsize=11)
    ax1.set_ylim(0, shots * 1.15)
    ax1.legend(loc='upper right', fontsize=9.5)
    ax1.grid(axis='y')

    # Ancilla syndrome histogram
    synd_labels = ['00\n(No Error)', '01\n(Q0 Error)', '11\n(Q1 Error)', '10\n(Q2 Error)']
    synd_vals = [syndrome_counts.get(k, 0) for k in ['00', '01', '11', '10']]
    bars3 = ax2.bar(synd_labels, synd_vals, color=['#3182CE', '#38B2AC', '#4FD1C5', '#81E6D9'], edgecolor='#2D3748', lw=1.2, width=0.55)

    for bar in bars3:
        h = bar.get_height()
        pct = (h / shots) * 100.0
        ax2.text(bar.get_x() + bar.get_width()/2., h + (shots * 0.015), f'{h:,}\n({pct:.1f}%)', ha='center', va='bottom', fontsize=8.5, fontweight='bold')

    ax2.set_title("Syndrome Parity Distribution ($s_1 s_0$)", fontsize=12, fontweight='bold', pad=12, color='#1A365D')
    ax2.set_xlabel("Measured Parity Syndrome ($s_1 s_0$)", fontsize=11, labelpad=8)
    ax2.set_ylabel("Syndrome Detection Counts", fontsize=11)
    ax2.set_ylim(0, shots * 1.15)
    ax2.grid(axis='y')

    plt.suptitle("Quantum Measurement Profiling & Error Correction Verification", fontsize=14, fontweight='bold', y=0.98, color='#1A365D')
    plt.tight_layout()
    p4_path = os.path.join(output_dir, "04_measurement_results.png")
    fig.savefig(p4_path)
    plt.close()
    generated_plots["04_measurement_results"] = p4_path

    return generated_plots
