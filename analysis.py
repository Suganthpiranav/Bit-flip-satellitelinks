"""
================================================================================
analysis.py
================================================================================
Project: Bit-Flip Code for Satellite Links: Quantum Error Correction Simulation
Author: B.Tech Computer Science Student Project
Framework: NumPy, Pandas, Matplotlib, SciPy

This module provides the analytical foundation, statistical evaluations,
summary reporting, and graph generation routines for comparing theoretical
predictions against empirical Monte Carlo quantum circuit simulations.

Key Mathematical Models:
1. Physical error channel: Independent bit-flip probability p.
2. Unencoded transmission error rate: P_unencoded = p.
3. 3-qubit repetition code logical error rate:
   P_logical(p) = 3 * p^2 * (1 - p) + p^3 = 3p^2 - 2p^3.
4. Error reduction percentage:
   Reduction(%) = ((P_unencoded - P_logical) / P_unencoded) * 100%
                = (1 - p)(1 - 2p) * 100%.
5. Monte Carlo standard error:
   SE = sqrt(P_theory * (1 - P_theory) / N_shots).
================================================================================
"""

import sys
import os
from typing import Dict, Tuple, Optional, Any
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.ticker import PercentFormatter

# Ensure UTF-8 output on Windows consoles
if sys.stdout.encoding and sys.stdout.encoding.lower() != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass


def theoretical_logical_error(p: np.ndarray | float) -> np.ndarray | float:
    """
    Computes theoretical logical error rate for the 3-qubit bit-flip code.
    
    Formula:
        P(logical error) = 3 * p^2 * (1 - p) + p^3 = 3p^2 - 2p^3
        
    Derivation:
        - Repetition code can correct at most 1 bit flip among 3 qubits.
        - Logical error occurs when 2 or 3 qubits suffer bit flips.
        - Probability of exactly 2 flips: C(3,2) * p^2 * (1 - p) = 3 * p^2 * (1 - p)
        - Probability of exactly 3 flips: C(3,3) * p^3 = p^3
        - Summing disjoint events yields: 3p^2(1 - p) + p^3.
    """
    p_arr = np.asarray(p, dtype=float)
    return 3.0 * (p_arr ** 2) * (1.0 - p_arr) + (p_arr ** 3)


def theoretical_success_rate(p: np.ndarray | float) -> np.ndarray | float:
    """
    Computes theoretical transmission success rate (1 - P_logical).
    """
    return 1.0 - theoretical_logical_error(p)


def theoretical_error_reduction(p: np.ndarray | float) -> np.ndarray | float:
    """
    Computes theoretical percentage error reduction achieved by the code.
    
    Reduction(%) = ((p - P_logical) / p) * 100%
                 = (1 - 3p + 2p^2) * 100%
                 = (1 - p)(1 - 2p) * 100%
    """
    p_arr = np.asarray(p, dtype=float)
    # Handle p = 0 boundary condition cleanly
    reduction = np.where(p_arr > 1e-12, (1.0 - p_arr) * (1.0 - 2.0 * p_arr) * 100.0, 100.0)
    return reduction


def evaluate_simulation_accuracy(df: pd.DataFrame) -> Dict[str, float]:
    """
    Computes statistical goodness-of-fit metrics comparing empirical
    Monte Carlo simulation results against analytical theoretical predictions.
    
    Parameters:
        df (pd.DataFrame): Dataframe containing simulation and theoretical values.
        
    Returns:
        Dict[str, float]: Dictionary of metrics (MAE, RMSE, Max Residual, R^2).
    """
    y_sim = df["encoded_error_sim"].values
    y_th = df["encoded_error_theoretical"].values
    
    residuals = y_sim - y_th
    mae = float(np.mean(np.abs(residuals)))
    rmse = float(np.sqrt(np.mean(residuals ** 2)))
    max_dev = float(np.max(np.abs(residuals)))
    
    # Coefficient of determination R^2
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
    """
    Prints a formatted, publication-style ASCII summary table comparing
    physical error, theoretical logical error, simulated logical error,
    success rates, and error reduction percentages.
    """
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
    print(f"Simulation Goodness-of-Fit Metrics (N={len(df)} points):")
    print(f"  • Mean Absolute Error (MAE) : {metrics['MAE']:.6f}")
    print(f"  • Root Mean Squared Error (RMSE): {metrics['RMSE']:.6f}")
    print(f"  • Max Sample Deviation (Max Dev): {metrics['Max_Deviation']:.6f}")
    print(f"  • R-Squared (R² Accuracy Score) : {metrics['R2_Score']:.6f}")
    print("=" * 115 + "\n")


def generate_all_plots(
    df: pd.DataFrame,
    sample_experiment: Dict[str, Any],
    output_dir: str = "plots"
) -> Dict[str, str]:
    """
    Generates and saves the 4 required analytical graphs with publication aesthetics:
    
    1. 01_error_rate_comparison.png:
       Physical error rate p vs logical error rate (Unencoded vs Encoded Sim vs Theory).
    2. 02_success_rate_comparison.png:
       Channel error probability vs transmission success rate.
    3. 03_error_reduction.png:
       Percentage error reduction achieved by the 3-qubit repetition code.
    4. 04_measurement_results.png:
       Measurement counts and syndrome breakdown for a representative experiment.
       
    Parameters:
        df (pd.DataFrame): Simulation results table.
        sample_experiment (dict): Sample detailed counts data at e.g. p=0.05.
        output_dir (str): Folder path to save images.
        
    Returns:
        Dict[str, str]: Mapping of plot identifier to saved file path.
    """
    os.makedirs(output_dir, exist_ok=True)
    generated_plots = {}
    
    # Configure global styling for crisp presentation
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
    
    # =========================================================================
    # PLOT 1: ERROR RATE COMPARISON (Physical p vs Logical Error)
    # =========================================================================
    fig, ax = plt.subplots(figsize=(9, 6), dpi=300)
    
    # Baseline: No correction (Unencoded P = p)
    ax.plot(p, df["unencoded_error_sim"], color='#E53E3E', linestyle='--',
            marker='s', markersize=4, label='Unencoded Link (No-QEC Baseline, $P = p$)', alpha=0.9, lw=1.8)
    
    # Theoretical 3-Qubit Repetition Code: P_L = 3p^2 - 2p^3
    p_fine = np.linspace(p.min(), p.max(), 200)
    y_fine_th = theoretical_logical_error(p_fine)
    ax.plot(p_fine, y_fine_th, color='#2B6CB0', linestyle='-',
            lw=2.5, label=r'Theoretical Curve: $P_L = 3p^2 - 2p^3$')
    
    # Simulated 3-Qubit Repetition Code (Monte Carlo)
    ax.plot(p, df["encoded_error_sim"], color='#319795', linestyle='none',
            marker='o', markersize=6, label='Monte Carlo Simulated Logical Error (Qiskit Aer)', zorder=5)
    
    # Theoretical Error Bounds (95% Confidence / 2-sigma band)
    shots = sample_experiment.get("shots", 10000)
    se = np.sqrt(y_fine_th * (1.0 - y_fine_th) / shots)
    ax.fill_between(p_fine, np.maximum(0, y_fine_th - 2 * se), y_fine_th + 2 * se,
                    color='#63B3ED', alpha=0.25, label=r'Monte Carlo $95\%$ Confidence Interval ($\pm 1.96\sigma$)')
    
    # Annotate mid-range benchmark (e.g. p = 0.15 or 0.20)
    target_annotate = 0.15 if 0.15 in p else p[len(p)//2]
    idx_ann = np.abs(p - target_annotate).argmin()
    ax.annotate(
        f"At p = {p[idx_ann]:.2f}:\n• Unencoded Err: {df['unencoded_error_sim'].iloc[idx_ann]:.4f}\n• Simulated $P_L$: {df['encoded_error_sim'].iloc[idx_ann]:.4f}\n• Theory $P_L$: {df['encoded_error_theoretical'].iloc[idx_ann]:.4f}\n• Error Reduction: {df['error_reduction_percent_sim'].iloc[idx_ann]:.1f}%",
        xy=(p[idx_ann], df["encoded_error_sim"].iloc[idx_ann]),
        xytext=(p.min() + (p.max() - p.min()) * 0.10, df["unencoded_error_sim"].max() * 0.70),
        arrowprops=dict(facecolor='#1A365D', arrowstyle='->', lw=1.5),
        bbox=dict(boxstyle="round,pad=0.5", facecolor="#EBF8FF", edgecolor="#3182CE", lw=1.2),
        fontsize=9.5, fontweight='medium'
    )
    
    ax.set_title("Physical vs. Logical Error Probability in Satellite Quantum Link",
                 fontsize=14, fontweight='bold', pad=14, color='#1A365D')
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
    
    # =========================================================================
    # PLOT 2: SUCCESS RATE COMPARISON
    # =========================================================================
    fig, ax = plt.subplots(figsize=(9, 6), dpi=300)
    
    # Unencoded Success Rate
    ax.plot(p, df["unencoded_success_sim"] * 100, color='#E53E3E', linestyle='--',
            marker='^', markersize=4, label='Unencoded Transmission ($1 - p$)', lw=1.8)
    
    # Theoretical Encoded Success Rate
    y_fine_succ = (1.0 - y_fine_th) * 100
    ax.plot(p_fine, y_fine_succ, color='#2F855A', linestyle='-',
            lw=2.5, label=r'Theoretical QEC Success ($1 - P_L$)')
    
    # Simulated Encoded Success Rate
    ax.plot(p, df["encoded_success_sim"] * 100, color='#276749', linestyle='none',
            marker='o', markersize=6, label='Simulated 3-Qubit QEC Success', zorder=5)
    
    # Shaded reliability gain region
    ax.fill_between(p, df["unencoded_success_sim"] * 100, df["encoded_success_sim"] * 100,
                    color='#C6F6D5', alpha=0.45, label='Fidelity Enhancement Gain')
    
    min_succ = min(df["unencoded_success_sim"].min(), df["encoded_success_sim"].min()) * 100
    ax.set_title("Transmission Success Rate vs. Channel Error Probability",
                 fontsize=14, fontweight='bold', pad=14, color='#1A365D')
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
    
    # =========================================================================
    # PLOT 3: PERCENTAGE ERROR REDUCTION
    # =========================================================================
    fig, ax = plt.subplots(figsize=(9, 6), dpi=300)
    
    # Theoretical Reduction Curve
    y_fine_red = theoretical_error_reduction(p_fine)
    ax.plot(p_fine, y_fine_red, color='#805AD5', linestyle='-', lw=2.5,
            label=r'Theoretical Reduction: $(1 - p)(1 - 2p) \times 100\%$')
    
    # Simulated Reduction Points
    ax.plot(p, df["error_reduction_percent_sim"], color='#44337A', linestyle='none',
            marker='D', markersize=6, label='Simulated Reduction (Monte Carlo)', zorder=5)
    
    # Horizontal reference lines
    ax.axhline(50, color='#CBD5E0', linestyle='--', lw=1, label='50% Error Reduction Threshold')
    
    # Key callout points within the swept range
    candidate_callouts = [0.05, 0.10, 0.15, 0.20, 0.25, 0.30]
    callouts = [cp for cp in candidate_callouts if (cp >= p.min() - 1e-4 and cp <= p.max() + 1e-4)]
    for cp in callouts:
        c_idx = np.abs(p - cp).argmin()
        c_red = df["error_reduction_percent_sim"].iloc[c_idx]
        ax.scatter([p[c_idx]], [c_red], color='#D69E2E', s=55, zorder=6)
        ax.annotate(f"p={p[c_idx]:.2f}\n{c_red:.1f}%", xy=(p[c_idx], c_red),
                    xytext=(p[c_idx], c_red + 4),
                    ha='center', fontsize=8.5, fontweight='bold', color='#2D3748')
                    
    min_red = df["error_reduction_percent_sim"].min()
    ax.set_title("Quantum Error Correction Efficacy: Error Reduction (%)",
                 fontsize=14, fontweight='bold', pad=14, color='#1A365D')
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
    
    # =========================================================================
    # PLOT 4: MEASUREMENT RESULTS & SYNDROME BREAKDOWN
    # =========================================================================
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(13, 5.5), dpi=300)
    
    p_sample = sample_experiment.get("p", 0.05)
    shots_sample = sample_experiment.get("shots", 10000)
    unenc_counts = sample_experiment.get("unencoded_counts", {"0": 9500, "1": 500})
    enc_counts = sample_experiment.get("encoded_counts", {})
    syndrome_counts = sample_experiment.get("syndrome_distribution", {})
    
    # Panel A: Unencoded Raw Bit Outcomes vs Corrected Logical Bit Outcomes
    unenc_0 = unenc_counts.get("0", 0)
    unenc_1 = unenc_counts.get("1", 0)
    
    # Parse final decoded logical bit from encoded experiment
    enc_0 = sum(count for k, count in enc_counts.items() if k.split()[0] == '0')
    enc_1 = sum(count for k, count in enc_counts.items() if k.split()[0] == '1')
    
    categories = ['Logical |0⟩ (Success)', 'Logical |1⟩ (Error)']
    x = np.arange(len(categories))
    width = 0.35
    
    bars1 = ax1.bar(x - width/2, [unenc_0, unenc_1], width, label='Unencoded Channel',
                    color=['#48BB78', '#F56565'], alpha=0.85, edgecolor='#2D3748', lw=1.2)
    bars2 = ax1.bar(x + width/2, [enc_0, enc_1], width, label='3-Qubit QEC Repetition Code',
                    color=['#2F855A', '#9B2C2C'], alpha=0.95, edgecolor='#2D3748', lw=1.2)
    
    # Add count labels above bars
    for bar in bars1:
        h = bar.get_height()
        ax1.text(bar.get_x() + bar.get_width()/2., h + 100, f'{h:,}',
                 ha='center', va='bottom', fontsize=9, fontweight='bold')
    for bar in bars2:
        h = bar.get_height()
        ax1.text(bar.get_x() + bar.get_width()/2., h + 100, f'{h:,}',
                 ha='center', va='bottom', fontsize=9, fontweight='bold')
                 
    ax1.set_title(f"Channel Transmission Outcomes (p = {p_sample:.2f}, N = {shots_sample:,})",
                  fontsize=12, fontweight='bold', pad=12, color='#1A365D')
    ax1.set_xticks(x)
    ax1.set_xticklabels(categories, fontsize=10, fontweight='medium')
    ax1.set_ylabel("Shot Counts (Trials)", fontsize=11)
    ax1.set_ylim(0, shots_sample * 1.15)
    ax1.legend(loc='upper right', fontsize=9.5)
    ax1.grid(axis='y')
    
    # Panel B: Syndrome Detection Distribution Breakdown
    # Syndromes: 00 (No error), 01 (Q0 flipped), 11 (Q1 flipped), 10 (Q2 flipped)
    synd_labels = ['00\n(No Error)', '01\n(Q0 Error)', '11\n(Q1 Error)', '10\n(Q2 Error)']
    synd_keys = ['00', '01', '11', '10']
    synd_vals = [syndrome_counts.get(k, 0) for k in synd_keys]
    
    colors_synd = ['#3182CE', '#38B2AC', '#4FD1C5', '#81E6D9']
    bars3 = ax2.bar(synd_labels, synd_vals, color=colors_synd, edgecolor='#2D3748', lw=1.2, width=0.55)
    
    for bar in bars3:
        h = bar.get_height()
        pct = (h / shots_sample) * 100.0
        ax2.text(bar.get_x() + bar.get_width()/2., h + (shots_sample * 0.015),
                 f'{h:,}\n({pct:.1f}%)', ha='center', va='bottom', fontsize=8.5, fontweight='bold')
                 
    ax2.set_title("Syndrome Measurement Distribution ($s_1 s_0$)",
                  fontsize=12, fontweight='bold', pad=12, color='#1A365D')
    ax2.set_xlabel("Measured Parity Syndrome ($s_1 s_0$)", fontsize=11, labelpad=8)
    ax2.set_ylabel("Syndrome Detection Counts", fontsize=11)
    ax2.set_ylim(0, shots_sample * 1.15)
    ax2.grid(axis='y')
    
    plt.suptitle("Quantum Measurement Profiling & Error Correction Verification",
                 fontsize=14, fontweight='bold', y=0.98, color='#1A365D')
    plt.tight_layout()
    p4_path = os.path.join(output_dir, "04_measurement_results.png")
    fig.savefig(p4_path)
    plt.close()
    generated_plots["04_measurement_results"] = p4_path
    
    return generated_plots
