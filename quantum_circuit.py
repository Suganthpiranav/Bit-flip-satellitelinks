"""
================================================================================
quantum_circuit.py
================================================================================
Project: Bit-Flip Code for Satellite Links: Quantum Error Correction Simulation
Author: B.Tech Computer Science Student Project
Framework: Qiskit 2.x & Qiskit Aer

This module implements the quantum circuit primitives for the 3-qubit bit-flip
repetition code tailored for simulating noisy satellite quantum communication
channels (downlink/uplink free-space optical quantum links).

Key Components:
1. Unencoded transmission circuit (raw physical qubit).
2. 3-qubit repetition code circuit with syndrome ancillas and dynamic correction.
3. Satellite channel noise modeling (Aer NoiseModel with Pauli-X bit-flip channel).
4. Deterministic single-qubit error injection circuits for faculty demonstration.
5. Circuit diagram generation and gate explanation utility.
================================================================================
"""

import sys
import os
from typing import List, Optional, Tuple, Dict
import matplotlib.pyplot as plt

# Ensure UTF-8 output on Windows consoles
if sys.stdout.encoding and sys.stdout.encoding.lower() != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

from qiskit import QuantumCircuit, QuantumRegister, ClassicalRegister, transpile
from qiskit_aer import AerSimulator
from qiskit_aer.noise import NoiseModel, pauli_error


def create_unencoded_circuit(error_prob: float = 0.0,
                             inject_error: bool = False) -> QuantumCircuit:
    """
    Constructs an unencoded baseline quantum transmission circuit.
    
    A single qubit represents the logical bit |0>. It passes through
    the noisy satellite channel (identity gate subject to bit-flip noise)
    and is measured at the receiver ground station.
    
    Parameters:
        error_prob (float): Bit-flip probability p.
        inject_error (bool): If True, explicitly injects a Pauli-X gate for demo.
        
    Returns:
        QuantumCircuit: The unencoded transmission circuit.
    """
    qr = QuantumRegister(1, name='data')
    cr = ClassicalRegister(1, name='meas')
    qc = QuantumCircuit(qr, cr, name="Unencoded_Satellite_Link")
    
    # Transmitter (Satellite): Prepare logical state |0> (default ground state)
    qc.barrier(label='Tx: Prepare |0>')
    
    # Satellite Channel
    if inject_error:
        qc.x(qr[0])
    else:
        # id gate acts as the physical medium subject to Aer noise model
        qc.id(qr[0])
    qc.barrier(label='Satellite Channel')
    
    # Receiver (Ground Station): Direct Measurement
    qc.measure(qr[0], cr[0])
    return qc


def create_bitflip_code_circuit(
    error_prob: float = 0.0,
    error_qubits: Optional[List[int]] = None,
    include_barriers: bool = True
) -> QuantumCircuit:
    """
    Constructs the complete 3-qubit bit-flip Quantum Error Correction circuit.
    
    Circuit Architecture:
    - 3 Data Qubits (q0, q1, q2) representing the logical qubit.
    - 2 Ancilla Qubits (a0, a1) for non-destructive syndrome parity extraction.
    - 2 Syndrome Classical Bits (s0, s1) to store parity measurement outcomes.
    - 1 Output Classical Bit (m0) to record the final decoded logical bit.
    
    Stages:
    1. Encoding: |0>_L = |000> via two CNOT gates.
    2. Satellite Channel: Independent Pauli-X bit flips on data qubits.
    3. Syndrome Extraction: Non-destructive Z0Z1 and Z1Z2 parity checks.
    4. Active Correction: Dynamic feedforward Pauli-X based on syndrome bits.
    5. Decoding & Measurement: Disentangling CNOTs and readout of logical state.
    
    Parameters:
        error_prob (float): Physical bit-flip probability for noise model.
        error_qubits (list[int], optional): Deterministic qubit indices to flip (e.g. [0], [1], [2]).
        include_barriers (bool): Whether to insert visual stage-separating barriers.
        
    Returns:
        QuantumCircuit: The fully constructed QEC circuit.
    """
    qr_data = QuantumRegister(3, name='data')
    qr_ancilla = QuantumRegister(2, name='ancilla')
    cr_syndrome = ClassicalRegister(2, name='syndrome')
    cr_out = ClassicalRegister(1, name='recovered_bit')
    
    qc = QuantumCircuit(qr_data, qr_ancilla, cr_syndrome, cr_out, name="3Qubit_BitFlip_QEC")
    
    # -------------------------------------------------------------------------
    # STAGE 1: ENCODING (Satellite Transmitter)
    # -------------------------------------------------------------------------
    # Logical state |0>_L = |000>
    # q0 is the source qubit. CNOT(q0, q1) and CNOT(q0, q2) replicate the state.
    qc.cx(qr_data[0], qr_data[1])
    qc.cx(qr_data[0], qr_data[2])
    
    if include_barriers:
        qc.barrier(label='1. Encoding: |0> -> |000>')
        
    # -------------------------------------------------------------------------
    # STAGE 2: SATELLITE PROPAGATION CHANNEL (Atmospheric Noise)
    # -------------------------------------------------------------------------
    # Photons travel through free space / atmospheric channel.
    if error_qubits is not None:
        for q_idx in error_qubits:
            if 0 <= q_idx < 3:
                qc.x(qr_data[q_idx])
    else:
        # Identity gates serve as physical interaction targets for Aer NoiseModel
        for i in range(3):
            qc.id(qr_data[i])
            
    if include_barriers:
        qc.barrier(label='2. Satellite Channel')
        
    # -------------------------------------------------------------------------
    # STAGE 3: SYNDROME EXTRACTION (Ground Station Receiver)
    # -------------------------------------------------------------------------
    # Ancilla a0 checks parity of q0 and q1: Z0 * Z1
    qc.cx(qr_data[0], qr_ancilla[0])
    qc.cx(qr_data[1], qr_ancilla[0])
    
    # Ancilla a1 checks parity of q1 and q2: Z1 * Z2
    qc.cx(qr_data[1], qr_ancilla[1])
    qc.cx(qr_data[2], qr_ancilla[1])
    
    # Measure ancilla qubits into syndrome classical register
    qc.measure(qr_ancilla[0], cr_syndrome[0])
    qc.measure(qr_ancilla[1], cr_syndrome[1])
    
    if include_barriers:
        qc.barrier(label='3. Syndrome Readout')
        
    # -------------------------------------------------------------------------
    # STAGE 4: ACTIVE ERROR CORRECTION (Classical Feedforward)
    # -------------------------------------------------------------------------
    # Syndrome mapping (s0 = cr_syndrome[0], s1 = cr_syndrome[1]):
    # s0=1, s1=0 -> Error on data[0] -> Apply X on data[0]
    # s0=1, s1=1 -> Error on data[1] -> Apply X on data[1]
    # s0=0, s1=1 -> Error on data[2] -> Apply X on data[2]
    # s0=0, s1=0 -> No error detected
    with qc.if_test((cr_syndrome[0], 1)):
        with qc.if_test((cr_syndrome[1], 0)):
            qc.x(qr_data[0])
            
    with qc.if_test((cr_syndrome[0], 1)):
        with qc.if_test((cr_syndrome[1], 1)):
            qc.x(qr_data[1])
            
    with qc.if_test((cr_syndrome[0], 0)):
        with qc.if_test((cr_syndrome[1], 1)):
            qc.x(qr_data[2])
            
    if include_barriers:
        qc.barrier(label='4. Correction')
        
    # -------------------------------------------------------------------------
    # STAGE 5: DECODING AND LOGICAL READOUT
    # -------------------------------------------------------------------------
    # Invert the encoding CNOTs to restore single-qubit format
    qc.cx(qr_data[0], qr_data[1])
    qc.cx(qr_data[0], qr_data[2])
    
    # Measure the recovered logical qubit
    qc.measure(qr_data[0], cr_out[0])
    
    return qc


def build_bitflip_noise_model(p: float) -> NoiseModel:
    """
    Builds a Qiskit Aer NoiseModel representing independent bit-flip channel.
    
    Each identity gate ('id') experiences a Pauli-X bit flip with probability p,
    and identity (no error) with probability (1 - p).
    
    Parameters:
        p (float): Error probability in [0.0, 1.0].
        
    Returns:
        NoiseModel: Configured Aer noise model.
    """
    noise_model = NoiseModel()
    if p > 0.0:
        p_clamped = min(max(p, 0.0), 1.0)
        error = pauli_error([('X', p_clamped), ('I', 1.0 - p_clamped)])
        noise_model.add_all_qubit_quantum_error(error, ['id'])
    return noise_model


def run_deterministic_demonstrations(seed: int = 42) -> List[Dict]:
    """
    Executes and validates the 4 canonical single-qubit error cases:
    - Case 0: No error (channel undisturbed)
    - Case 1: Error on Qubit 0
    - Case 2: Error on Qubit 1
    - Case 3: Error on Qubit 2
    Plus an educational Case 4: Double error on Qubits 0 and 1 (failure demonstration).
    
    Returns:
        List[Dict]: Detailed demonstration records for presentation.
    """
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
        
        # Most frequent outcome string
        top_outcome = max(counts.items(), key=lambda x: x[1])[0]
        # Format: 'recovered_bit syndrome' e.g. '0 01'
        parts = top_outcome.split()
        recovered_bit = parts[0]
        syndrome_bits = parts[1] if len(parts) > 1 else "N/A"
        
        # In Qiskit, ClassicalRegister(2, 'syndrome') prints as s[1]s[0]
        s0_val = syndrome_bits[-1] if len(syndrome_bits) >= 2 else "0"
        s1_val = syndrome_bits[-2] if len(syndrome_bits) >= 2 else "0"
        
        corrected_qubit = "None"
        if s0_val == '1' and s1_val == '0':
            corrected_qubit = "Qubit 0"
        elif s0_val == '1' and s1_val == '1':
            corrected_qubit = "Qubit 1"
        elif s0_val == '0' and s1_val == '1':
            corrected_qubit = "Qubit 2"
            
        success = (recovered_bit == '0')
        
        results.append({
            "case_name": case["name"],
            "injected_errors": case["errors"],
            "s0 (q0^q1)": s0_val,
            "s1 (q1^q2)": s1_val,
            "raw_syndrome": syndrome_bits,
            "corrected_target": corrected_qubit,
            "recovered_bit": recovered_bit,
            "success": success,
            "counts": counts,
            "circuit": qc
        })
        
    return results


def explain_quantum_gates() -> str:
    """
    Returns an academic explanation of every quantum gate used in the simulation.
    """
    explanation = """
================================================================================
EXPLANATION OF QUANTUM GATES IN THE 3-QUBIT SATELLITE QEC CIRCUIT
================================================================================

1. CNOT Gate (Controlled-NOT / CX):
   - Action: Flips the target qubit if and only if the control qubit is |1>.
   - Matrix: [[1, 0, 0, 0],
              [0, 1, 0, 0],
              [0, 0, 0, 1],
              [0, 0, 1, 0]]
   - Purpose in Encoding: Encodes logical |0> into entangled 3-qubit state |000>
     without violating the No-Cloning Theorem. It creates quantum entanglement,
     not independent clones.
   - Purpose in Syndrome Extraction: Computes non-destructive two-qubit parity
     (Z0 * Z1 and Z1 * Z2) onto ancilla qubits without collapsing data superpositions.
   - Purpose in Decoding: Disentangles the corrected codewords back to single-qubit space.

2. Pauli-X Gate (Quantum NOT Gate):
   - Action: Inverts state amplitudes: X|0> = |1>, X|1> = |0>.
   - Matrix: [[0, 1],
              [1, 0]]
   - Role in Channel: Models atmospheric polarization rotation / scattering
     that flips qubit states during satellite downlink/uplink transmission.
   - Role in Correction: Corrective unitary transformation triggered dynamically
     to invert the flipped qubit back to its original state.

3. Identity Gate (I / id):
   - Action: Leaves the qubit unchanged.
   - Matrix: [[1, 0],
              [0, 1]]
   - Role in Simulation: Serves as a transparent propagation placeholder where
     the Aer stochastic noise model injects bit-flip errors with probability p.

4. Dynamic Classical Control (if_test / c_if):
   - Action: Conditionally applies a quantum gate based on classical syndrome bits.
   - Role: Implements feedback error correction based on the non-destructive
     syndrome lookup table.
================================================================================
"""
    return explanation


def save_circuit_diagrams(output_dir: str = "plots") -> str:
    """
    Draws and saves high-resolution circuit diagrams of the QEC architecture.
    
    Parameters:
        output_dir (str): Destination directory for plots.
        
    Returns:
        str: Absolute path to the saved circuit diagram.
    """
    os.makedirs(output_dir, exist_ok=True)
    qc = create_bitflip_code_circuit(error_qubits=[1], include_barriers=True)
    circuit_path = os.path.join(output_dir, "00_quantum_circuit_bitflip.png")
    
    try:
        fig = qc.draw(output='mpl', style='iqp', scale=0.85)
        plt.title("3-Qubit Bit-Flip Repetition Code Circuit for Satellite Communication Link",
                  fontsize=13, pad=15, fontweight='bold', color='#1A365D')
        plt.tight_layout()
        plt.savefig(circuit_path, dpi=300, bbox_inches='tight')
        plt.close()
        print(f"[INFO] Circuit diagram saved to: {circuit_path}")
    except Exception as e:
        print(f"[WARNING] Could not save MPL circuit diagram ({e}). Falling back to text drawing.")
        text_drawing = qc.draw(output='text')
        txt_path = os.path.join(output_dir, "00_quantum_circuit_bitflip.txt")
        with open(txt_path, 'w', encoding='utf-8') as f:
            f.write(str(text_drawing))
        print(f"[INFO] Text circuit diagram saved to: {txt_path}")
        return txt_path
        
    return circuit_path


if __name__ == "__main__":
    print(explain_quantum_gates())
    demos = run_deterministic_demonstrations()
    for d in demos:
        print(f"{d['case_name']:<30} | Syndrome (s1s0): {d['raw_syndrome']} | Corrected: {d['corrected_target']:<8} | Recovered: {d['recovered_bit']} | Success: {d['success']}")
    save_circuit_diagrams("plots")
