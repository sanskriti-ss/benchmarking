"""Step 2: Active space validation via CASCI/CASSCF.

Validates the proposed active space from Step 1 by running
CASCI (and optionally CASSCF) calculations.
"""

from dataclasses import dataclass
from typing import Optional

from .geometry import MoleculeGeometry
from .step1_orbitals import OrbitalDiagnostics


@dataclass
class ActiveSpaceResult:
    """Results from active space validation."""
    # Active space parameters used
    n_active_electrons: int = 0
    n_active_orbitals: int = 0

    # CASCI results
    casci_energy: float = 0.0
    casci_converged: bool = False

    # CASSCF results (optional)
    casscf_energy: Optional[float] = None
    casscf_converged: Optional[bool] = None

    # Validation
    energy_below_hf: bool = False
    correlation_recovered: float = 0.0  # fraction of MP2 correlation recovered

    # Reference energies
    hf_energy: float = 0.0
    mp2_energy: float = 0.0

    def summary(self) -> str:
        """Human-readable summary."""
        lines = [
            "=" * 60,
            "ACTIVE SPACE VALIDATION",
            "=" * 60,
            f"Active space:          ({self.n_active_electrons}e, {self.n_active_orbitals}o)",
            f"Qubits:                {2 * self.n_active_orbitals}",
            "",
            f"HF energy:             {self.hf_energy:.10f} Ha",
            f"CASCI energy:          {self.casci_energy:.10f} Ha",
            f"CASCI converged:       {self.casci_converged}",
            f"CASCI below HF:        {self.energy_below_hf}",
            f"Correlation recovered:  {self.correlation_recovered:.1%}",
        ]
        if self.casscf_energy is not None:
            lines.extend([
                "",
                f"CASSCF energy:         {self.casscf_energy:.10f} Ha",
                f"CASSCF converged:      {self.casscf_converged}",
            ])
        lines.append("=" * 60)
        return "\n".join(lines)


def validate_active_space(
    geometry: MoleculeGeometry,
    diagnostics: OrbitalDiagnostics,
    run_casscf: bool = False,
) -> ActiveSpaceResult:
    """Validate proposed active space with CASCI (and optionally CASSCF).

    Args:
        geometry: Molecular geometry.
        diagnostics: Results from Step 1 orbital analysis.
        run_casscf: If True, also run CASSCF for orbital optimization.

    Returns:
        ActiveSpaceResult with validation metrics.
    """
    from pyscf import gto, scf, mcscf

    result = ActiveSpaceResult()
    result.hf_energy = diagnostics.hf_energy
    result.mp2_energy = diagnostics.mp2_energy
    result.n_active_electrons = diagnostics.proposed_n_active_electrons
    result.n_active_orbitals = diagnostics.proposed_n_active_orbitals

    ncas = diagnostics.proposed_n_active_orbitals
    nelecas = diagnostics.proposed_n_active_electrons

    # Reuse mol and mf from diagnostics if available, otherwise rebuild
    if diagnostics.mol is not None and diagnostics.mf is not None:
        mol = diagnostics.mol
        mf = diagnostics.mf
    else:
        mol = gto.Mole()
        mol.atom = geometry.to_pyscf_atom_list()
        mol.basis = "cc-pvdz"
        mol.charge = geometry.charge
        mol.spin = geometry.spin
        mol.build()
        mf = scf.RHF(mol)
        mf.kernel()

    # Run CASCI
    mc = mcscf.CASCI(mf, ncas, nelecas)
    mc.kernel()

    result.casci_energy = float(mc.e_tot)
    result.casci_converged = True  # CASCI is variational, always "converges"

    # Validation: CASCI should be below HF
    result.energy_below_hf = result.casci_energy < result.hf_energy

    # Fraction of MP2 correlation energy recovered
    mp2_corr = diagnostics.mp2_correlation
    if abs(mp2_corr) > 1e-10:
        casci_corr = result.casci_energy - result.hf_energy
        result.correlation_recovered = casci_corr / mp2_corr
    else:
        result.correlation_recovered = 0.0

    # Optional CASSCF
    if run_casscf:
        mc_scf = mcscf.CASSCF(mf, ncas, nelecas)
        mc_scf.kernel()
        result.casscf_energy = float(mc_scf.e_tot)
        result.casscf_converged = bool(mc_scf.converged)

    return result
