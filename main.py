"""
Main Execution Script: 3-Qubit Quantum Error Correction Simulation for Satellite Links
Framework: Qiskit 2.x & Qiskit Aer

Orchestrates deterministic case validation, Monte Carlo noise simulation across
error probabilities p in [0.05, 0.30], CSV export, and publication-grade plot generation.
"""

import sys
import os
import argparse
import time
from typing import Dict, Any

# Ensure UTF-8 output on Windows consoles
if sys.stdout.encoding and sys.stdout.encoding.lower() != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

import numpy as np
import pandas as pd
from qiskit import transpile
from qiskit_aer import AerSimulator

from quantum_circuit import (
    create_unencoded_circuit,
    create_bitflip_code_circuit,
    build_bitflip_noise_model,
    run_deterministic_demonstrations,
    explain_quantum_gates,
    save_circuit_diagrams
)
from analysis import (
    theoretical_logical_error,
    theoretical_success_rate,
    theoretical_error_reduction,
    print_summary_table,
    generate_all_plots
)


def run_single_probability_simulation(
    p: float,
    shots: int,
    simulator: AerSimulator,
    seed: int
) -> Dict[str, Any]:
    """
    Executes unencoded baseline and 3-qubit QEC circuits under bit-flip noise rate p.
    Returns measurement counts, logical error rates, and theoretical comparisons.
    """
    noise_model = build_bitflip_noise_model(p)

    # 1. Unencoded baseline transmission: single qubit subject to error rate p
    qc_unenc = create_unencoded_circuit(error_prob=p)
    t_qc_unenc = transpile(qc_unenc, simulator, optimization_level=0)
    job_unenc = simulator.run(t_qc_unenc, shots=shots, noise_model=noise_model, seed_simulator=seed)
    counts_unenc = job_unenc.result().get_counts()

    unenc_errors = counts_unenc.get("1", 0)
    unenc_error_rate = unenc_errors / shots
    unenc_success_rate = 1.0 - unenc_error_rate

    # 2. 3-qubit repetition code: encoding, noisy channel, syndrome extraction, dynamic correction
    qc_enc = create_bitflip_code_circuit(error_prob=p, include_barriers=False)
    t_qc_enc = transpile(qc_enc, simulator, optimization_level=0)
    job_enc = simulator.run(t_qc_enc, shots=shots, noise_model=noise_model, seed_simulator=seed + 1000)
    counts_enc = job_enc.result().get_counts()

    # Parse classical readout: 'recovered_bit syndrome' (e.g., '0 01')
    enc_errors = sum(count for outcome, count in counts_enc.items() if outcome.split()[0] == '1')
    enc_error_rate = enc_errors / shots
    enc_success_rate = 1.0 - enc_error_rate

    # Tally syndrome detection statistics
    syndrome_distribution = {"00": 0, "01": 0, "11": 0, "10": 0}
    for outcome, count in counts_enc.items():
        parts = outcome.split()
        if len(parts) > 1:
            synd = parts[1]
            syndrome_distribution[synd] = syndrome_distribution.get(synd, 0) + count

    # Analytical benchmarks: P_L = 3p^2 - 2p^3
    theo_err = float(theoretical_logical_error(p))
    theo_succ = float(theoretical_success_rate(p))
    theo_red = float(theoretical_error_reduction(p))

    sim_red = ((unenc_error_rate - enc_error_rate) / unenc_error_rate) * 100.0 if unenc_error_rate > 1e-12 else 100.0
    std_error = np.sqrt(theo_err * (1.0 - theo_err) / shots)

    return {
        "p": p,
        "unenc_counts": counts_unenc,
        "enc_counts": counts_enc,
        "syndrome_distribution": syndrome_distribution,
        "unencoded_error_sim": unenc_error_rate,
        "unencoded_success_sim": unenc_success_rate,
        "encoded_error_sim": enc_error_rate,
        "encoded_success_sim": enc_success_rate,
        "encoded_error_theoretical": theo_err,
        "encoded_success_theoretical": theo_succ,
        "error_reduction_percent_sim": sim_red,
        "error_reduction_percent_theoretical": theo_red,
        "monte_carlo_std_error": std_error
    }


def main():
    parser = argparse.ArgumentParser(
        description="3-Qubit Bit-Flip Quantum Error Correction Simulation for Satellite Links"
    )
    parser.add_argument("--shots", type=int, default=10000,
                        help="Number of Monte Carlo trials per probability (default: 10,000)")
    parser.add_argument("--p-min", type=float, default=0.05,
                        help="Minimum physical bit-flip probability (default: 0.05)")
    parser.add_argument("--p-max", type=float, default=0.30,
                        help="Maximum physical bit-flip probability (default: 0.30)")
    parser.add_argument("--p-step", type=float, default=0.01,
                        help="Probability increment step (default: 0.01)")
    parser.add_argument("--seed", type=int, default=42,
                        help="Random seed for deterministic reproducibility (default: 42)")
    parser.add_argument("--demo-only", action="store_true",
                        help="Run only the deterministic canonical case demonstrations")
    parser.add_argument("--results-dir", type=str, default="results",
                        help="Directory to store CSV experimental results (default: results)")
    parser.add_argument("--plots-dir", type=str, default="plots",
                        help="Directory to store output graphs (default: plots)")
    args = parser.parse_args()

    base_dir = os.path.dirname(os.path.abspath(__file__))
    results_path = os.path.join(base_dir, args.results_dir)
    plots_path = os.path.join(base_dir, args.plots_dir)
    os.makedirs(results_path, exist_ok=True)
    os.makedirs(plots_path, exist_ok=True)

    print("\n" + "=" * 80)
    print("  Bit-Flip Code for Satellite Links: Quantum Error Correction Simulation")
    print("  Framework: Qiskit 2.x & Qiskit Aer")
    print("=" * 80)

    # 1. Gate explanation and high-resolution circuit diagram generation
    print(explain_quantum_gates())
    save_circuit_diagrams(plots_path)

    # 2. Deterministic validation of single-qubit errors and syndrome diagnosis
    print("\n[Step 1] Running Deterministic Validation Cases...")
    demos = run_deterministic_demonstrations(seed=args.seed)
    print("-" * 80)
    print(f"{'Experiment Case':<32} | {'Syndrome (s1s0)':<16} | {'Target Corrected':<18} | {'Status'}")
    print("-" * 80)
    for d in demos:
        status_str = "SUCCESS (Bit |0> Restored)" if d["success"] else "FAIL (Uncorrectable >1 error)"
        print(f"{d['case_name']:<32} | {d['raw_syndrome']:<16} | {d['corrected_target']:<18} | {status_str}")
    print("-" * 80)

    if args.demo_only:
        return

    # 3. Monte Carlo channel simulation across parameter sweep
    p_values = np.round(np.arange(args.p_min, args.p_max + args.p_step / 2.0, args.p_step), 4)
    print(f"\n[Step 2] Executing Monte Carlo Sweep across {len(p_values)} points (N={args.shots:,} shots/point)...")

    simulator = AerSimulator()
    sim_records = []
    sample_data = {}
    start_time = time.time()

    for idx, p in enumerate(p_values):
        t0 = time.time()
        res = run_single_probability_simulation(
            p=float(p),
            shots=args.shots,
            simulator=simulator,
            seed=args.seed + idx * 7
        )
        sim_records.append(res)

        # Retain sample distribution at representative error rate p=0.10
        if np.isclose(p, 0.10, atol=1e-3):
            sample_data = {
                "p": float(p),
                "shots": args.shots,
                "unencoded_counts": res["unenc_counts"],
                "encoded_counts": res["enc_counts"],
                "syndrome_distribution": res["syndrome_distribution"]
            }

        elapsed = time.time() - t0
        print(f"  • Progress [{idx+1:2d}/{len(p_values):2d}] p={p:4.2f} | Unenc Err: {res['unencoded_error_sim']:6.4f} | QEC Err: {res['encoded_error_sim']:6.4f} | Reduc: {res['error_reduction_percent_sim']:5.1f}% ({elapsed:.2f}s)")

    print(f"\n[INFO] Simulation completed in {time.time() - start_time:.2f} seconds.")

    # 4. Save results to CSV
    df = pd.DataFrame([{
        "physical_error_p": r["p"],
        "unencoded_error_sim": r["unencoded_error_sim"],
        "unencoded_success_sim": r["unencoded_success_sim"],
        "encoded_error_sim": r["encoded_error_sim"],
        "encoded_error_theoretical": r["encoded_error_theoretical"],
        "encoded_success_sim": r["encoded_success_sim"],
        "encoded_success_theoretical": r["encoded_success_theoretical"],
        "error_reduction_percent_sim": r["error_reduction_percent_sim"],
        "error_reduction_percent_theoretical": r["error_reduction_percent_theoretical"],
        "monte_carlo_std_error": r["monte_carlo_std_error"]
    } for r in sim_records])

    csv_file_path = os.path.join(results_path, "bitflip_results.csv")
    df.to_csv(csv_file_path, index=False)
    print(f"[Step 3] Experimental data written to: {csv_file_path}")

    # 5. Render publication-grade figures
    if not sample_data:
        sample_data = {
            "p": sim_records[len(sim_records)//2]["p"],
            "shots": args.shots,
            "unencoded_counts": sim_records[len(sim_records)//2]["unenc_counts"],
            "encoded_counts": sim_records[len(sim_records)//2]["enc_counts"],
            "syndrome_distribution": sim_records[len(sim_records)//2]["syndrome_distribution"]
        }
    generate_all_plots(df, sample_data, plots_path)
    print(f"[Step 4] Plots successfully saved to: {plots_path}")

    # 6. Display formatted experimental comparison table
    print_summary_table(df)


if __name__ == "__main__":
    main()
