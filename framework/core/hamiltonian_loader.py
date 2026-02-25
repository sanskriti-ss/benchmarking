"""Core dataclasses for molecules and qubit Hamiltonians.

These are the output formats that the pipeline produces, compatible with
downstream VQE algorithms.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple
import numpy as np


@dataclass
class Molecule:
    """Molecular metadata."""
    name: str
    formula: str
    n_atoms: int
    n_electrons: int
    n_qubits: int
    basis: str
    charge: int = 0
    multiplicity: int = 1
    description: str = ""


@dataclass
class QubitHamiltonian:
    """Qubit Hamiltonian ready for VQE.

    Stores the Hamiltonian as a dict of Pauli strings to coefficients,
    plus molecular metadata and energies for validation.
    """
    molecule: Molecule
    # {pauli_string: coefficient} e.g. {"IIIZ": 0.5, "XXII": -0.3}
    terms: Dict[str, complex] = field(default_factory=dict)
    n_qubits: int = 0
    # Reference energies for validation
    hf_energy: Optional[float] = None
    fci_energy: Optional[float] = None
    mp2_energy: Optional[float] = None
    casci_energy: Optional[float] = None
    # Active space info
    n_active_electrons: Optional[int] = None
    n_active_orbitals: Optional[int] = None
    frozen_core_orbitals: Optional[List[int]] = None
    active_orbitals: Optional[List[int]] = None
    # Mapping used
    mapping: str = "jordan_wigner"

    @property
    def n_terms(self) -> int:
        return len(self.terms)

    def to_dict(self) -> dict:
        """Serialize to dictionary."""
        return {
            "molecule": {
                "name": self.molecule.name,
                "formula": self.molecule.formula,
                "n_atoms": self.molecule.n_atoms,
                "n_electrons": self.molecule.n_electrons,
                "n_qubits": self.molecule.n_qubits,
                "basis": self.molecule.basis,
                "charge": self.molecule.charge,
                "multiplicity": self.molecule.multiplicity,
            },
            "n_qubits": self.n_qubits,
            "n_terms": self.n_terms,
            "hf_energy": self.hf_energy,
            "fci_energy": self.fci_energy,
            "mp2_energy": self.mp2_energy,
            "casci_energy": self.casci_energy,
            "n_active_electrons": self.n_active_electrons,
            "n_active_orbitals": self.n_active_orbitals,
            "mapping": self.mapping,
        }
