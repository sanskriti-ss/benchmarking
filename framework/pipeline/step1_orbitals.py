"""Step 1: Hartree-Fock + MP2 orbital analysis and diagnostics.

Runs HF and MP2 calculations, computes natural orbital occupations,
and proposes an active space based on occupation thresholds.
"""

from dataclasses import dataclass, field
from typing import List, Optional, Tuple
import numpy as np

from .geometry import MoleculeGeometry


@dataclass
class OrbitalDiagnostics:
    """Results from orbital analysis."""
    # HF results
    hf_energy: float = 0.0
    hf_converged: bool = False
    n_basis_functions: int = 0
    n_molecular_orbitals: int = 0
    orbital_energies: Optional[np.ndarray] = None

    # MP2 results
    mp2_energy: float = 0.0           # Total MP2 energy
    mp2_correlation: float = 0.0      # MP2 correlation energy (mp2 - hf)
    natural_occupations: Optional[np.ndarray] = None

    # Diagnostics
    homo_lumo_gap_ev: float = 0.0
    dipole_moment_debye: float = 0.0

    # Active space proposal
    n_core_orbitals: int = 0
    core_orbital_indices: List[int] = field(default_factory=list)
    proposed_active_indices: List[int] = field(default_factory=list)
    proposed_n_active_electrons: int = 0
    proposed_n_active_orbitals: int = 0

    # Basis comparison (optional)
    hf_energy_minimal: Optional[float] = None  # STO-3G HF for comparison

    # PySCF objects (not serializable, used by later steps)
    mol: object = None
    mf: object = None
    mp2_obj: object = None
    mo_coeff: Optional[np.ndarray] = None

    @property
    def n_qubits_proposed(self) -> int:
        """Number of qubits for proposed active space (2 * n_active_orbitals)."""
        return 2 * self.proposed_n_active_orbitals

    def summary(self) -> str:
        """Human-readable summary."""
        lines = [
            "=" * 60,
            "ORBITAL ANALYSIS DIAGNOSTICS",
            "=" * 60,
            f"Basis functions:       {self.n_basis_functions}",
            f"Molecular orbitals:    {self.n_molecular_orbitals}",
            "",
            f"HF energy:             {self.hf_energy:.10f} Ha",
            f"HF converged:          {self.hf_converged}",
            f"MP2 total energy:      {self.mp2_energy:.10f} Ha",
            f"MP2 correlation:       {self.mp2_correlation:.10f} Ha",
            "",
            f"HOMO-LUMO gap:         {self.homo_lumo_gap_ev:.4f} eV",
            f"Dipole moment:         {self.dipole_moment_debye:.4f} Debye",
            "",
            f"Core orbitals frozen:  {self.n_core_orbitals}",
            f"Proposed active space: ({self.proposed_n_active_electrons}e, {self.proposed_n_active_orbitals}o)",
            f"Qubits needed:         {self.n_qubits_proposed}",
        ]
        if self.natural_occupations is not None:
            lines.append("")
            lines.append("Natural orbital occupations (active region):")
            for i in self.proposed_active_indices:
                if i < len(self.natural_occupations):
                    lines.append(f"  MO {i:3d}: {self.natural_occupations[i]:.6f}")
        if self.hf_energy_minimal is not None:
            lines.append("")
            lines.append(f"STO-3G HF energy:      {self.hf_energy_minimal:.10f} Ha")
            lines.append(f"Basis set improvement:  {self.hf_energy - self.hf_energy_minimal:.6f} Ha")
        lines.append("=" * 60)
        return "\n".join(lines)


def run_orbital_analysis(
    geometry: MoleculeGeometry,
    basis: str = "cc-pvdz",
    run_basis_comparison: bool = False,
) -> OrbitalDiagnostics:
    """Run HF + MP2 and propose active space.

    Args:
        geometry: Molecular geometry.
        basis: Basis set for the main calculation.
        run_basis_comparison: If True, also run STO-3G HF for comparison.

    Returns:
        OrbitalDiagnostics with all results and proposed active space.
    """
    from pyscf import gto, scf, mp as pyscf_mp
    from framework.config import (
        CORE_ELECTRONS, OCCUPATION_LOWER, OCCUPATION_UPPER,
        MAX_ACTIVE_ORBITALS, HARTREE_TO_EV,
    )

    diag = OrbitalDiagnostics()

    # Build molecule
    mol = gto.Mole()
    mol.atom = geometry.to_pyscf_atom_list()
    mol.basis = basis
    mol.charge = geometry.charge
    mol.spin = geometry.spin
    mol.build()

    diag.n_basis_functions = mol.nao_nr()
    diag.n_molecular_orbitals = mol.nao_nr()
    diag.mol = mol

    # Run RHF
    mf = scf.RHF(mol)
    mf.kernel()
    diag.hf_energy = float(mf.e_tot)
    diag.hf_converged = bool(mf.converged)
    diag.orbital_energies = mf.mo_energy
    diag.mo_coeff = mf.mo_coeff
    diag.mf = mf

    if not mf.converged:
        print("WARNING: HF did not converge!")

    # HOMO-LUMO gap
    n_occ = mol.nelectron // 2
    homo = mf.mo_energy[n_occ - 1]
    lumo = mf.mo_energy[n_occ]
    diag.homo_lumo_gap_ev = float((lumo - homo) * HARTREE_TO_EV)

    # Dipole moment
    dip = mf.dip_moment(verbose=0)
    diag.dipole_moment_debye = float(np.linalg.norm(dip))

    # Run MP2
    mp2_obj = pyscf_mp.MP2(mf)
    mp2_obj.kernel()
    diag.mp2_energy = float(mp2_obj.e_tot)
    diag.mp2_correlation = float(mp2_obj.e_corr)
    diag.mp2_obj = mp2_obj

    # Natural orbital occupations from MP2 1-RDM
    rdm1_mo = mp2_obj.make_rdm1()
    nat_occ, nat_orb = np.linalg.eigh(rdm1_mo)
    # eigh returns ascending order; we want descending
    nat_occ = nat_occ[::-1]
    diag.natural_occupations = nat_occ

    # Freeze core: count core orbitals from atom types
    n_core = 0
    for atom in geometry.atoms:
        n_core += CORE_ELECTRONS.get(atom, 0) // 2  # orbitals, not electrons
    diag.n_core_orbitals = n_core
    diag.core_orbital_indices = list(range(n_core))

    # Propose active space: rank non-core orbitals by how far their
    # occupation deviates from integer (2.0 or 0.0) — the most
    # fractional orbitals carry the most correlation and belong in
    # the active space.  Then cap at MAX_ACTIVE_ORBITALS.
    candidate_indices = []
    for i in range(n_core, len(nat_occ)):
        if OCCUPATION_LOWER < nat_occ[i] < OCCUPATION_UPPER:
            candidate_indices.append(i)

    if len(candidate_indices) == 0:
        # Fallback: HOMO-2 … LUMO+2
        start = max(n_core, n_occ - 3)
        end = min(len(nat_occ), n_occ + 3)
        candidate_indices = list(range(start, end))

    if len(candidate_indices) > MAX_ACTIVE_ORBITALS:
        # Score each orbital: distance of its occupation from the
        # nearest integer (2 or 0).  Larger distance = more correlated.
        def _correlation_score(idx):
            occ = nat_occ[idx]
            return min(abs(occ - 2.0), abs(occ - 0.0))

        candidate_indices.sort(key=_correlation_score, reverse=True)
        candidate_indices = sorted(candidate_indices[:MAX_ACTIVE_ORBITALS])

    active_indices = candidate_indices

    diag.proposed_active_indices = active_indices
    diag.proposed_n_active_orbitals = len(active_indices)
    # Active electrons = total electrons in active orbitals
    # (total electrons - 2 * core orbitals)
    n_active_e = mol.nelectron - 2 * n_core
    # But cap to the number of active orbitals * 2
    n_active_e = min(n_active_e, 2 * len(active_indices))
    diag.proposed_n_active_electrons = n_active_e

    # Optional basis comparison
    if run_basis_comparison:
        mol_min = gto.Mole()
        mol_min.atom = geometry.to_pyscf_atom_list()
        mol_min.basis = "sto-3g"
        mol_min.charge = geometry.charge
        mol_min.spin = geometry.spin
        mol_min.build()
        mf_min = scf.RHF(mol_min)
        mf_min.kernel()
        diag.hf_energy_minimal = float(mf_min.e_tot)

    return diag
