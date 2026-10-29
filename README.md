# Bit-Flip Code for Satellite Links: Quantum Error Correction Simulation

**Academic Project** | 3rd-Year B.Tech Computer Science & Engineering  
**Domain:** Quantum Computing, Quantum Information Theory & Satellite Communications  
**Simulation Framework:** Python 3.10+ / 3.12+, Qiskit 2.6+, Qiskit Aer 0.18+, NumPy, Pandas, Matplotlib  

---

## 🛰️ 1. Project Overview & Motivation

Free-space optical (FSO) satellite quantum communication links (e.g., ground-to-satellite uplink and satellite-to-ground downlink) form the physical backbone for global **Quantum Key Distribution (QKD)** networks and the **Quantum Internet** (demonstrated by missions like China's *Micius* satellite and ESA's *Eagle-1*).

When single-photon polarization states ($|H\rangle \equiv |0\rangle$ and $|V\rangle \equiv |1\rangle$) propagate through the atmosphere and space:
1. **Atmospheric Turbulence & Birefringence:** Variations in atmospheric refractive index induce stochastic rotations of the photon polarization angle, producing **bit-flip errors** ($|0\rangle \leftrightarrow |1\rangle$).
2. **Thermal & Background Radiative Noise:** Solar photons and detector noise induce false detection events.

In classical communications, repeaters and amplifiers simply re-transmit signals. In quantum communication, however, the **No-Cloning Theorem** ($U|\psi\rangle|0\rangle \neq |\psi\rangle|\psi\rangle$) forbids copying arbitrary quantum states. Hence, **Quantum Error Correction (QEC)** is mandatory: logical information is encoded non-locally into entangled multi-qubit states, and syndrome ancilla qubits extract parity information non-destructively.

This project implements, validates, and simulates a **3-qubit bit-flip repetition code** protecting a transmitted logical qubit against bit-flip errors across a parameterized satellite channel swept from **$p = 0.05$ to $p = 0.30$** (inclusive, $\Delta p = 0.01$, with $\ge 10,000$ shots per point).

---

## 🔬 2. Quantum Circuit Architecture & Syndrome Parity Detection

The 3-qubit repetition code encodes $1$ logical qubit ($q_0$) into $3$ data qubits ($q_0, q_1, q_2$) using $2$ ancilla qubits ($a_0, a_1$) to measure syndrome parities without collapsing data superpositions.

### Quantum Circuit Layout
The high-resolution circuit diagram is saved to `plots/00_quantum_circuit_bitflip.png`.

```
        ┌───────────┐    ┌─────────────────┐    ┌────────────────────┐    ┌────────────┐    ┌─────────┐    ┌─┐
data_0: ┤ Tx: Init  ├──■──┤ Satellite Noise ├─■──┤                    ├────┼─[X if s=01]─┼────┤ Dec: CX ├──■─┤M├
        └───────────┘┌─┴─┐└─────────────────┘│  │                    │    │            │    └────┬────┘  │ └╥┘
data_1: ─────────────┤ X ├───────────────────┼──┼──■──────────────■──┼────┼─[X if s=11]─┼─────────┼────■─┼──╫─
                     └───┘                   │  │  │              │  │    │            │         │    │  │  ╫ 
data_2: ─────────────────────────────────────┼──┼──┼──────────────┼──┼─■──┼─[X if s=10]─┼─────────■────┼──┼──╫─
                                             │  │  │              │  │ │  │            │              │  │  ╫ 
                                           ┌─┴─┐│  │              │  │ │  │            │              │  │  ╫ 
anc_0:  ───────────────────────────────────┤ X ├┴──┼──────────────┼──┼─┼──┤ Measure s0 ├──────────────┼──┼──╫─
                                           └───┘   │              │  │ │  └─────┬──────┘              │  │  ╫ 
                                                 ┌─┴─┐          ┌─┴─┐│ │        │                     │  │  ╫ 
anc_1:  ─────────────────────────────────────────┤ X ├──────────┤ X ├┴─┼────────┼──────────Measure s1─┤──┼──╫─
                                                 └───┘          └───┘  │        │               │     │  │  ╫ 
syndrome: 2/═══════════════════════════════════════════════════════════╧════════╧═══════════════╧═════╪══╪══╬═
                                                                       0        0               1     │  │  ║ 
recovered: 1/═════════════════════════════════════════════════════════════════════════════════════════╧══╧══╩═
                                                                                                      0
```

### Circuit Stages & Verification of Correction Logic

1. **Encoding (Transmitter):**
   $$\text{CNOT}(q_0, q_1), \quad \text{CNOT}(q_0, q_2) \implies |0\rangle_L = |000\rangle$$
   Entangles the 3 data qubits without cloning.
2. **Satellite Noise Channel:**
   Independent stochastic Pauli-$X$ bit flips with physical error probability $p \in [0.05, 0.30]$.
3. **Syndrome Extraction (Ancilla Parity Measurement):**
   - Ancilla $a_0$ measures the two-qubit stabilizer parity $Z_0 Z_1$ ($q_0 \oplus q_1$) via CNOTs targeting $a_0$.
   - Ancilla $a_1$ measures the two-qubit stabilizer parity $Z_1 Z_2$ ($q_1 \oplus q_2$) via CNOTs targeting $a_1$.
   - Measurements of $a_0 \to s_0$ and $a_1 \to s_1$ extract error information **without projecting the logical data state**.
4. **Active Dynamic Correction (Receiver Classical Feedforward):**
   The classical bits $(s_1, s_0)$ trigger single-qubit recovery gates:

| Injected Channel Error | Codeword at Rx | Parity $s_0 = q_0 \oplus q_1$ | Parity $s_1 = q_1 \oplus q_2$ | Syndrome ($s_1 s_0$) | Corrective Action | Recovered Logical Bit | Verification |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **No Error** | $\|000\rangle$ | $0$ | $0$ | `00` | None (Identity) | $\|0\rangle$ | Verified (Success) |
| **Bit flip on $q_0$** | $\|100\rangle$ | $1$ | $0$ | `01` | Apply $X(q_0)$ | $\|0\rangle$ | Verified (Success) |
| **Bit flip on $q_1$** | $\|010\rangle$ | $1$ | $1$ | `11` | Apply $X(q_1)$ | $\|0\rangle$ | Verified (Success) |
| **Bit flip on $q_2$** | $\|001\rangle$ | $0$ | $1$ | `10` | Apply $X(q_2)$ | $\|0\rangle$ | Verified (Success) |
| **Double flip ($q_0, q_1$)** | $\|110\rangle$ | $0$ | $1$ | `10` | Misidentifies as $q_2 \implies X(q_2) \to \|111\rangle$ | $\|1\rangle$ | Verified (Failure Mode) |

5. **Decoding & Readout:**
   Inverse CNOTs disentangle the data qubits back to $q_0$, and measurement reads the recovered logical bit.

---

## 📐 3. Mathematical Model & Theoretical Derivation

### Theoretical Logical Error Probability
For independent bit-flip errors occurring with probability $p$:
- A single error on any one of the 3 data qubits is detected and fully corrected.
- A logical error occurs if and only if **2 or 3 qubits** suffer bit flips simultaneously:
  - Probability of exactly 2 bit flips: $\binom{3}{2} p^2 (1 - p) = 3p^2(1 - p)$
  - Probability of exactly 3 bit flips: $\binom{3}{3} p^3 = p^3$

Summing these disjoint events yields the exact theoretical logical error probability $P_L$:
$$P_L = 3p^2(1 - p) + p^3 = 3p^2 - 3p^3 + p^3 = \mathbf{3p^2 - 2p^3}$$

### Unencoded Baseline vs. Encoded Comparison
- **Unencoded Link Error:** $P_{\text{unencoded}} = p$
- **Break-Even Threshold Condition:**
  $$P_L < P_{\text{unencoded}} \iff 3p^2 - 2p^3 < p \iff p(2p^2 - 3p + 1) > 0 \iff (2p - 1)(p - 1) > 0$$
  Since $p \in (0, 0.5)$, the 3-qubit code strictly outperforms the unencoded link for all $p < 0.50$ (50%).
- **Percentage Error Reduction:**
  $$\text{Reduction}(\%) = \left(\frac{p - P_L}{p}\right) \times 100\% = \frac{p - (3p^2 - 2p^3)}{p} \times 100\% = (1 - p)(1 - 2p) \times 100\%$$

---

## 🔬 4. Actual Experimental Results ($p \in [0.05, 0.30]$, 10,000 Shots / Point)

The experiment was run across 26 discrete probability levels ($p = 0.05, 0.06, \dots, 0.30$) with $10,000$ Monte Carlo shots per probability ($260,000$ total circuit executions).

Results are saved in `results/bitflip_results.csv`:

| $p$ (Physical) | Unencoded Error (Sim) | Theoretical $P_L$ ($3p^2-2p^3$) | Simulated Logical Error | Residual (Sim - Theo) | Unencoded Success | Encoded Success | Theoretical Reduction | Simulated Reduction |
| :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **0.05** | 0.0480 | 0.0073 | 0.0085 | +0.0012 | 95.20% | 99.15% | 85.50% | 82.29% |
| **0.06** | 0.0592 | 0.0104 | 0.0115 | +0.0011 | 94.08% | 98.85% | 82.72% | 80.57% |
| **0.07** | 0.0695 | 0.0140 | 0.0154 | +0.0014 | 93.05% | 98.46% | 79.98% | 77.84% |
| **0.08** | 0.0776 | 0.0182 | 0.0198 | +0.0016 | 92.24% | 98.02% | 77.28% | 74.48% |
| **0.09** | 0.0924 | 0.0228 | 0.0243 | +0.0015 | 90.76% | 97.57% | 74.62% | 73.70% |
| **0.10** | 0.1007 | 0.0280 | 0.0298 | +0.0018 | 89.93% | 97.02% | 72.00% | 70.41% |
| **0.11** | 0.1100 | 0.0336 | 0.0365 | +0.0029 | 89.00% | 96.35% | 69.42% | 66.82% |
| **0.12** | 0.1203 | 0.0397 | 0.0430 | +0.0033 | 87.97% | 95.70% | 66.88% | 64.26% |
| **0.13** | 0.1305 | 0.0463 | 0.0493 | +0.0030 | 86.95% | 95.07% | 64.38% | 62.22% |
| **0.14** | 0.1365 | 0.0533 | 0.0557 | +0.0024 | 86.35% | 94.43% | 61.92% | 59.19% |
| **0.15** | 0.1466 | 0.0607 | 0.0637 | +0.0030 | 85.34% | 93.63% | 59.50% | 56.55% |
| **0.16** | 0.1628 | 0.0686 | 0.0731 | +0.0045 | 83.72% | 92.69% | 57.12% | 55.10% |
| **0.17** | 0.1725 | 0.0769 | 0.0812 | +0.0043 | 82.75% | 91.88% | 54.78% | 52.93% |
| **0.18** | 0.1809 | 0.0855 | 0.0895 | +0.0040 | 81.91% | 91.05% | 52.48% | 50.53% |
| **0.19** | 0.1899 | 0.0946 | 0.1000 | +0.0054 | 81.01% | 90.00% | 50.22% | 47.34% |
| **0.20** | 0.1960 | 0.1040 | 0.1099 | +0.0059 | 80.40% | 89.01% | 48.00% | 43.93% |
| **0.21** | 0.2204 | 0.1138 | 0.1199 | +0.0061 | 77.96% | 88.01% | 45.82% | 45.60% |
| **0.22** | 0.2166 | 0.1239 | 0.1323 | +0.0084 | 78.34% | 86.77% | 43.68% | 38.92% |
| **0.23** | 0.2333 | 0.1344 | 0.1440 | +0.0096 | 76.67% | 85.60% | 41.58% | 38.28% |
| **0.24** | 0.2444 | 0.1452 | 0.1539 | +0.0087 | 75.56 | 84.61% | 39.52% | 37.03% |
| **0.25** | 0.2526 | 0.1562 | 0.1642 | +0.0080 | 74.74% | 83.58% | 37.50% | 35.00% |
| **0.26** | 0.2604 | 0.1676 | 0.1754 | +0.0078 | 73.96% | 82.46% | 35.52% | 32.64% |
| **0.27** | 0.2748 | 0.1793 | 0.1874 | +0.0081 | 72.52% | 81.26% | 33.58% | 31.80% |
| **0.28** | 0.2753 | 0.1913 | 0.1991 | +0.0078 | 72.47% | 80.09% | 31.68% | 27.68% |
| **0.29** | 0.2889 | 0.2035 | 0.2106 | +0.0071 | 71.11% | 78.94% | 29.82% | 27.10% |
| **0.30** | 0.2983 | 0.2160 | 0.2242 | +0.0082 | 70.17% | 77.58% | 28.00% | 24.84% |

### Statistical Goodness-of-Fit
- **Mean Absolute Error (MAE):** `0.004883` (~0.49%)
- **Root Mean Squared Error (RMSE):** `0.005608` (~0.56%)
- **Max Absolute Deviation:** `0.009634` (< 1.0%)
- **R² Fit Score:** `0.992942` (Extreme correlation with theoretical physics)

---

## 📈 5. Plots & Interpretation (in `plots/`)

1. **`01_error_rate_comparison.png` (Required Core Plot):**
   - **X-axis:** Physical bit-flip probability $p$ ($0.05$ to $0.30$).
   - **Y-axis:** Logical error probability ($P_L$).
   - **Curves:** 
     - Solid blue line: Theoretical curve $P_L = 3p^2 - 2p^3$.
     - Teal circle markers: Monte Carlo simulated logical error ($10,000$ shots per point).
     - Red dashed line: Unencoded baseline ($P = p$).
     - Shaded blue band: $95\%$ confidence interval ($\pm 1.96\sigma$).
   - **Interpretation:** The simulated points track the quadratic theoretical curve across all 26 points. At $p = 0.05$, QEC suppresses errors from $4.8\%$ to $0.85\%$; at $p = 0.30$, errors are suppressed from $29.8\%$ to $22.4\%$.
2. **`02_success_rate_comparison.png`:**
   - Compares transmission success rates ($1 - \text{error}$). Encoded transmission maintains $\ge 99.1\%$ success at $p=0.05$ and $77.6\%$ success at $p=0.30$ (vs. $70.2\%$ unencoded).
3. **`03_error_reduction.png`:**
   - Plots percentage error reduction vs. $p$, confirming $(1-p)(1-2p) \times 100\%$, decaying from $\sim 82.3\%$ at $p=0.05$ to $\sim 24.8\%$ at $p=0.30$.
4. **`04_measurement_results.png`:**
   - Detailed shot breakdown at $p = 0.10$, showing syndrome distribution ($s_1 s_0 = \text{'00'}, \text{'01'}, \text{'11'}, \text{'10'}$) and logical bit recovery.

---

## ⚠️ 6. Idealized Model vs. Realistic Satellite Optical Link (Crucial Distinction)

For academic and scientific rigor, the distinction between this simulation and an operational satellite deployment must be clearly understood:

### A. Assumptions of the Idealized Bit-Flip Model (This Simulation)
1. **Pauli-X Noise Only:** Assumes quantum errors consist strictly of discrete bit flips $|0\rangle \leftrightarrow |1\rangle$.
2. **Independent & Identically Distributed (i.i.d.):** Each data qubit experiences noise independently without spatial or temporal crosstalk.
3. **Noiseless Ancilla Operations:** Assumes CNOT syndrome extraction gates and measurements are instantaneous, noiseless, and $100\%$ reliable.
4. **Zero Photon Loss:** Assumes all transmitted qubits arrive intact at the receiver (no erasure channel).

### B. Physical Reality of Satellite Quantum Communication Channels
1. **Arbitrary Quantum State Rotations (Phase-Flip Vulnerability):**
   Atmospheric turbulence and optical birefringence induce continuous polarization phase rotations. General noise is a superposition $\alpha I + \beta X + \gamma Y + \delta Z$. **The 3-qubit repetition code has distance $d=1$ against Pauli-Z (phase flips)**: a single phase-flip error destroys the logical state completely without being detected.
2. **Dominant Photon Diffraction & Absorption (Erasure):**
   In real low-Earth orbit (LEO) satellite-to-ground links (e.g. 500–1200 km), geometric beam divergence and atmospheric scattering cause **20 dB to 40 dB of loss** (only 1 in 100 to 1 in 10,000 photons is collected). In reality, photon loss dominates over depolarization bit flips.
3. **Atmospheric Turbulence & Scintillation:**
   Turbulent eddies cause beam wander, beam broadening, and wavefront deformation, causing dynamic signal fading.
4. **Background Solar Radiance & Dark Counts:**
   During daylight or twilight passes, solar background photons inject false coincidence counts, limiting the signal-to-noise ratio (SNR).
5. **Requirement for Full Quantum Repeaters:**
   A real satellite quantum internet node requires full 2D stabilizer codes (e.g. **Steane [[7,1,3]] code**, **Shor 9-qubit code**, or **Surface codes**) paired with quantum memory buffers, entanglement purification, and adaptive optics.

---

## 🚀 7. Execution Guide

```powershell
# Run the complete simulation with default settings (p: 0.05 to 0.30, 10,000 shots)
python main.py

# Run only the deterministic canonical case demonstrations (fast viva demo)
python main.py --demo-only

# Run with custom parameters
python main.py --p-min 0.05 --p-max 0.30 --p-step 0.01 --shots 15000 --seed 42
```