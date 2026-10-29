"""
Quantum Circuit Implementation: 3-Qubit Bit-Flip Code for Satellite Links
Framework: Qiskit 2.x & Qiskit Aer

Implements encoding, atmospheric bit-flip channel noise, non-destructive
ancilla syndrome extraction, dynamic classical feedforward correction,
and logical decoding.
"""

import sys
import os
from typing import List, Optional, Dict
import matplotlib.pyplot as plt

# Ensure UTF-8 output across Windows consoles
if sys.stdout.encoding and sys.stdout.encoding.lower() != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

from qiskit import QuantumCircuit, QuantumRegister, ClassicalRegister, transpile
from qiskit_aer import AerSimulator
from qiskit_aer.noise import NoiseModel, pauli_error


def create_unencoded_circuit(error_prob: float = 0.0, inject_error: bool = False) -> QuantumCircuit:
    """
    Constructs an unencoded baseline link: a single physical qubit |0> passes
    through the channel and is measured directly at the receiver ground station.
    """
    qr = QuantumRegister(1, name='data')
    cr = ClassicalRegister(1, name='meas')
    qc = QuantumCircuit(qr, cr, name="Unencoded_Satellite_Link")

    # Channel noise: explicit Pauli-X for deterministic demo, or identity gate for Aer noise model
    if inject_error:
        qc.x(qr[0])
    else:
        qc.id(qr[0])

    qc.measure(qr[0], cr[0])
    return qc


def create_bitflip_code_circuit(
    error_prob: float = 0.0,
    error_qubits: Optional[List[int]] = None,
    include_barriers: bool = True
) -> QuantumCircuit:
    """
    Constructs the 3-qubit bit-flip repetition code circuit:
    - 3 data qubits (q0, q1, q2) storing the logical qubit state.
    - 2 ancilla qubits (a0, a1) for non-destructive syndrome extraction.
    - 2 classical syndrome bits (s0, s1) for parity outcomes.
    - 1 classical measurement bit for final recovered logical state.
    """
    qr_data = QuantumRegister(3, name='data')
    qr_ancilla = QuantumRegister(2, name='ancilla')
    cr_syndrome = ClassicalRegister(2, name='syndrome')
    cr_out = ClassicalRegister(1, name='recovered_bit')
    qc = QuantumCircuit(qr_data, qr_ancilla, cr_syndrome, cr_out, name="3Qubit_BitFlip_QEC")

    # 1. Encoding: Distribute logical state |0> -> |000> using entanglement without cloning
    qc.cx(qr_data[0], qr_data[1])
    qc.cx(qr_data[0], qr_data[2])
    if include_barriers:
        qc.barrier(label='1. Encoding')

    # 2. Satellite Channel: Stochastic or deterministic bit-flip (Pauli-X) noise
    if error_qubits is not None:
        for q_idx in error_qubits:
            if 0 <= q_idx < 3:
                qc.x(qr_data[q_idx])
    else:
        for i in range(3):
            qc.id(qr_data[i])
    if include_barriers:
        qc.barrier(label='2. Channel')

    # 3. Syndrome Extraction: Non-destructively measure stabilizers Z0Z1 and Z1Z2 onto ancillas
    # Parity check 1: a0 = q0 ^ q1
    qc.cx(qr_data[0], qr_ancilla[0])
    qc.cx(qr_data[1], qr_ancilla[0])

    # Parity check 2: a1 = q1 ^ q2
    qc.cx(qr_data[1], qr_ancilla[1])
    qc.cx(qr_data[2], qr_ancilla[1])

    qc.measure(qr_ancilla[0], cr_syndrome[0])
    qc.measure(qr_ancilla[1], cr_syndrome[1])
    if include_barriers:
        qc.barrier(label='3. Parity Readout')

    # 4. Dynamic Classical Feedforward: Apply conditional X gate based on syndrome bits (s1, s0)
    # s0=1, s1=0 (syndrome '01') -> Qubit 0 flipped
    with qc.if_test((cr_syndrome[0], 1)):
        with qc.if_test((cr_syndrome[1], 0)):
            qc.x(qr_data[0])

    # s0=1, s1=1 (syndrome '11') -> Qubit 1 flipped
    with qc.if_test((cr_syndrome[0], 1)):
        with qc.if_test((cr_syndrome[1], 1)):
            qc.x(qr_data[1])

    # s0=0, s1=1 (syndrome '10') -> Qubit 2 flipped
    with qc.if_test((cr_syndrome[0], 0)):
        with qc.if_test((cr_syndrome[1], 1)):
            qc.x(qr_data[2])

    if include_barriers:
        qc.barrier(label='4. Correction')

    # 5. Decoding: Uncompute entanglement back to q0 and measure recovered logical qubit
    qc.cx(qr_data[0], qr_data[1])
    qc.cx(qr_data[0], qr_data[2])
    qc.measure(qr_data[0], cr_out[0])

    return qc


def build_bitflip_noise_model(p: float) -> NoiseModel:
    """Creates an Aer NoiseModel applying Pauli-X bit-flip errors with probability p."""
    noise_model = NoiseModel()
    if p > 0.0:
        p_clamped = min(max(p, 0.0), 1.0)
        error = pauli_error([('X', p_clamped), ('I', 1.0 - p_clamped)])
        noise_model.add_all_qubit_quantum_error(error, ['id'])
    return noise_model


def run_deterministic_demonstrations(seed: int = 42) -> List[Dict]:
    """Validates the 4 canonical single-qubit error cases plus the double-error failure limit."""
    cases = [
        {"name": "Case 0: No Error", "errors": [], "expected_syndrome": "00", "expected_bit": "0"},
        {"name": "Case 1: Error on Qubit 0", "errors": [0], "expected_syndrome": "01", "expected_bit": "0"},
        {"name": "Case 2: Error on Qubit 1", "errors": [1], "expected_syndrome": "11", "expected_bit": "0"},
        {"name": "Case 3: Error on Qubit 2", "errors": [2], "expected_syndrome": "10", "expected_bit": "0"},
        {"name": "Case 4: Double Error (Q0 & Q1)", "errors": [0, 1], "expected_syndrome": "10", "expected_bit": "1 (Failure)"},
    ]

    sim = AerSimulator()
    results = []

    for case in cases:
        qc = create_bitflip_code_circuit(error_qubits=case["errors"], include_barriers=True)
        t_qc = transpile(qc, sim, optimization_level=0)
        job = sim.run(t_qc, shots=100, seed_simulator=seed)
        counts = job.result().get_counts()

        # Parse outcome format: 'recovered_bit syndrome' (e.g. '0 01')
        top_outcome = max(counts.items(), key=lambda x: x[1])[0]
        parts = top_outcome.split()
        recovered_bit = parts[0]
        syndrome_bits = parts[1] if len(parts) > 1 else "N/A"

        # Little-endian bit extraction: s0 is rightmost bit, s1 is leftmost bit
        s0_val = syndrome_bits[-1] if len(syndrome_bits) >= 2 else "0"
        s1_val = syndrome_bits[-2] if len(syndrome_bits) >= 2 else "0"

        corrected_qubit = "None"
        if s0_val == '1' and s1_val == '0':
            corrected_qubit = "Qubit 0"
        elif s0_val == '1' and s1_val == '1':
            corrected_qubit = "Qubit 1"
        elif s0_val == '0' and s1_val == '1':
            corrected_qubit = "Qubit 2"

        results.append({
            "case_name": case["name"],
            "injected_errors": case["errors"],
            "raw_syndrome": syndrome_bits,
            "corrected_target": corrected_qubit,
            "recovered_bit": recovered_bit,
            "success": (recovered_bit == '0'),
            "counts": counts
        })

    return results


def explain_quantum_gates() -> str:
    """Returns a concise summary of the gates used and their roles in the QEC protocol."""
    return """
Summary of Quantum Gates in 3-Qubit Repetition Code:
1. CNOT Gate (Controlled-NOT):
   - Encoding: Creates entangled state |000> without violating the No-Cloning Theorem.
   - Syndrome Extraction: Measures two-qubit parities (Z0Z1 and Z1Z2) onto ancilla qubits non-destructively.
   - Decoding: Inverts the encoding step to recover the logical state on qubit 0.
2. Pauli-X Gate (Quantum NOT):
   - Channel: Models atmospheric polarization rotation bit-flip errors.
   - Correction: Applies dynamic recovery operation based on classical syndrome measurement.
3. Dynamic Classical Feedback (if_test):
   - Executes mid-circuit feedforward correction conditioned on ancilla parity measurements.
"""


def save_circuit_diagrams(output_dir: str = "plots") -> str:
    """Renders and saves the quantum circuit diagram at high resolution."""
    os.makedirs(output_dir, exist_ok=True)
    qc = create_bitflip_code_circuit(error_qubits=[1], include_barriers=True)
    circuit_path = os.path.join(output_dir, "00_quantum_circuit_bitflip.png")

    try:
        fig = qc.draw(output='mpl', style='iqp', scale=0.85)
        plt.title("3-Qubit Bit-Flip Repetition Code Circuit for Satellite Communication Link",
                  fontsize=12, pad=12, fontweight='bold', color='#1A365D')
        plt.tight_layout()
        plt.savefig(circuit_path, dpi=300, bbox_inches='tight')
        plt.close()
    except Exception:
        # Fallback to text drawing if matplotlib backend encounters issues
        text_drawing = qc.draw(output='text')
        circuit_path = os.path.join(output_dir, "00_quantum_circuit_bitflip.txt")
        with open(circuit_path, 'w', encoding='utf-8') as f:
            f.write(str(text_drawing))

    return circuit_path
