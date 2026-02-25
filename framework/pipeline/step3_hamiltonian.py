"""Step 3: Build qubit Hamiltonian using OpenFermion.

Takes geometry + active space info and produces a QubitHamiltonian
compatible with the VQE framework.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional

from .geometry import MoleculeGeometry
from .step1_orbitals import OrbitalDiagnostics
from .step2_active_space import ActiveSpaceResult


@dataclass
class PipelineHamiltonian:
    """Result of Hamiltonian construction."""
    qubit_hamiltonian: object = None  # framework QubitHamiltonian
    openfermion_qubit_op: object = None  # OpenFermion QubitOperator
    n_qubits: int = 0
    n_terms: int = 0
    # Pauli terms dict
    terms: Dict[str, complex] = field(default_factory=dict)

    def summary(self) -> str:
        lines = [
            "=" * 60,
            "QUBIT HAMILTONIAN",
            "=" * 60,
            f"Number of qubits:  {self.n_qubits}",
            f"Number of terms:   {self.n_terms}",
        ]
        if self.n_terms <= 20:
            lines.append("")
            lines.append("Terms (showing all):")
            for pauli, coeff in sorted(self.terms.items(), key=lambda x: -abs(x[1])):
                lines.append(f"  {coeff:+.8f}  {pauli}")
        else:
            lines.append("")
            lines.append("Top 10 terms by magnitude:")
            sorted_terms = sorted(self.terms.items(), key=lambda x: -abs(x[1]))
            for pauli, coeff in sorted_terms[:10]:
                lines.append(f"  {coeff:+.8f}  {pauli}")
            lines.append(f"  ... and {self.n_terms - 10} more terms")
        lines.append("=" * 60)
        return "\n".join(lines)


def build_qubit_hamiltonian(
    geometry: MoleculeGeometry,
    active_space: ActiveSpaceResult,
    diagnostics: OrbitalDiagnostics,
) -> PipelineHamiltonian:
    """Build qubit Hamiltonian via OpenFermion + PySCF.

    Uses the same pattern as generate_gln_hamiltonian_active_space.py:
    MolecularData -> run_pyscf -> get_molecular_hamiltonian -> jordan_wigner.

    Args:
        geometry: Molecular geometry.
        active_space: Validated active space from Step 2.
        diagnostics: Orbital diagnostics from Step 1.

    Returns:
        PipelineHamiltonian with OpenFermion and framework-compatible formats.
    """
    from openfermion import MolecularData, jordan_wigner
    from openfermionpyscf import run_pyscf

    from framework.core.hamiltonian_loader import Molecule, QubitHamiltonian

    result = PipelineHamiltonian()

    # Set up MolecularData
    of_geometry = geometry.to_openfermion_geometry()
    mol_data = MolecularData(
        geometry=of_geometry,
        basis=diagnostics.mol.basis if diagnostics.mol else "cc-pvdz",
        multiplicity=geometry.multiplicity,
        charge=geometry.charge,
        description=f"{geometry.name}_active_space",
    )

    # Run PySCF through OpenFermion interface
    mol_data = run_pyscf(mol_data, run_scf=True, run_mp2=True, run_fci=False)

    # Get molecular Hamiltonian with active space reduction
    occupied_indices = diagnostics.core_orbital_indices
    active_indices = diagnostics.proposed_active_indices

    molecular_hamiltonian = mol_data.get_molecular_hamiltonian(
        occupied_indices=occupied_indices,
        active_indices=active_indices,
    )

    # Jordan-Wigner transformation
    qubit_op = jordan_wigner(molecular_hamiltonian)

    # Extract terms as {pauli_string: coefficient}
    terms = {}
    n_qubits = 2 * active_space.n_active_orbitals
    for term, coeff in qubit_op.terms.items():
        if abs(coeff) < 1e-12:
            continue
        # Convert OpenFermion term tuple to Pauli string
        pauli_str = _term_to_pauli_string(term, n_qubits)
        terms[pauli_str] = complex(coeff)

    result.openfermion_qubit_op = qubit_op
    result.n_qubits = n_qubits
    result.n_terms = len(terms)
    result.terms = terms

    # Build framework-compatible QubitHamiltonian
    molecule = Molecule(
        name=geometry.name,
        formula=geometry.formula,
        n_atoms=geometry.n_atoms,
        n_electrons=geometry.n_electrons,
        n_qubits=n_qubits,
        basis=diagnostics.mol.basis if diagnostics.mol else "cc-pvdz",
        charge=geometry.charge,
        multiplicity=geometry.multiplicity,
    )

    qh = QubitHamiltonian(
        molecule=molecule,
        terms=terms,
        n_qubits=n_qubits,
        hf_energy=diagnostics.hf_energy,
        mp2_energy=diagnostics.mp2_energy,
        casci_energy=active_space.casci_energy,
        n_active_electrons=active_space.n_active_electrons,
        n_active_orbitals=active_space.n_active_orbitals,
        frozen_core_orbitals=diagnostics.core_orbital_indices,
        active_orbitals=diagnostics.proposed_active_indices,
        mapping="jordan_wigner",
    )
    result.qubit_hamiltonian = qh

    return result


def _term_to_pauli_string(term: tuple, n_qubits: int) -> str:
    """Convert OpenFermion term tuple to Pauli string.

    OpenFermion terms are tuples like ((0, 'X'), (1, 'Z')) meaning X0 Z1.
    We convert to a string like "XZII..." of length n_qubits.
    """
    pauli_list = ["I"] * n_qubits
    for qubit_idx, pauli in term:
        if qubit_idx < n_qubits:
            pauli_list[qubit_idx] = pauli
    return "".join(pauli_list)
