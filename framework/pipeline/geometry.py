"""Geometry loading for molecular systems.

Supports loading from QMProt H5 files, manual specification,
and hardcoded fallbacks for testing.
"""

from dataclasses import dataclass, field
from typing import List, Optional, Tuple
import numpy as np


@dataclass
class MoleculeGeometry:
    """Molecular geometry specification."""
    atoms: List[str]              # Element symbols, e.g. ["C", "H", "O"]
    coords: np.ndarray            # Shape (n_atoms, 3) in Angstroms
    charge: int = 0
    spin: int = 0                 # 2S (number of unpaired electrons)
    name: str = ""
    formula: str = ""

    @property
    def n_atoms(self) -> int:
        return len(self.atoms)

    @property
    def n_electrons(self) -> int:
        """Total electrons (before accounting for charge)."""
        from framework.config import CORE_ELECTRONS
        atomic_numbers = {
            "H": 1, "He": 2, "Li": 3, "Be": 4, "B": 5, "C": 6,
            "N": 7, "O": 8, "F": 9, "Ne": 10, "Na": 11, "Mg": 12,
            "Al": 13, "Si": 14, "P": 15, "S": 16, "Cl": 17, "Ar": 18,
        }
        return sum(atomic_numbers.get(a, 0) for a in self.atoms) - self.charge

    @property
    def multiplicity(self) -> int:
        return self.spin + 1

    def to_pyscf_atom_string(self) -> str:
        """Convert to PySCF atom specification string."""
        lines = []
        for atom, coord in zip(self.atoms, self.coords):
            lines.append(f"{atom}  {coord[0]:.8f}  {coord[1]:.8f}  {coord[2]:.8f}")
        return "; ".join(lines)

    def to_pyscf_atom_list(self) -> List[Tuple[str, Tuple[float, float, float]]]:
        """Convert to PySCF atom list format."""
        return [(atom, tuple(coord)) for atom, coord in zip(self.atoms, self.coords)]

    def to_openfermion_geometry(self) -> List[Tuple[str, Tuple[float, float, float]]]:
        """Convert to OpenFermion geometry format (same as PySCF list)."""
        return self.to_pyscf_atom_list()


def load_geometry_from_h5(path: str) -> MoleculeGeometry:
    """Load molecular geometry from a QMProt-format H5 file.

    Expected H5 structure:
        /symbols   - dataset of element symbols (bytes or str)
        /coordinates - dataset of shape (n_atoms, 3) in Angstroms
    """
    import h5py

    with h5py.File(path, "r") as f:
        # Handle both byte-string and regular string datasets
        if "symbols" in f:
            symbols_raw = f["symbols"][:]
            atoms = [s.decode("utf-8") if isinstance(s, bytes) else str(s)
                     for s in symbols_raw]
        elif "atoms" in f:
            symbols_raw = f["atoms"][:]
            atoms = [s.decode("utf-8") if isinstance(s, bytes) else str(s)
                     for s in symbols_raw]
        else:
            raise KeyError("H5 file must contain 'symbols' or 'atoms' dataset")

        if "coordinates" in f:
            coords = np.array(f["coordinates"][:])
        elif "coords" in f:
            coords = np.array(f["coords"][:])
        else:
            raise KeyError("H5 file must contain 'coordinates' or 'coords' dataset")

    name = path.split("/")[-1].replace(".h5", "")
    formula = _compute_formula(atoms)

    return MoleculeGeometry(
        atoms=atoms,
        coords=coords,
        charge=0,
        spin=0,
        name=name,
        formula=formula,
    )


def get_glycine_geometry() -> MoleculeGeometry:
    """Hardcoded glycine (Gly) geometry for testing.

    Glycine: C2H5NO2, 10 atoms, 40 electrons.
    Geometry from NIST CCCBDB (optimized at B3LYP/cc-pVTZ).
    Coordinates in Angstroms.
    """
    atoms = ["N", "C", "C", "O", "O", "H", "H", "H", "H", "H"]
    coords = np.array([
        [-1.2127,  0.2078,  0.0000],  # N
        [ 0.0000,  0.8563,  0.0000],  # C (alpha)
        [ 1.1968, -0.0853,  0.0000],  # C (carbonyl)
        [ 1.0876, -1.3085,  0.0000],  # O (carbonyl)
        [ 2.3765,  0.5429,  0.0000],  # O (hydroxyl)
        [-1.2687,  1.1820,  0.0000],  # H (on N)
        [-2.0661,  0.6839,  0.0000],  # H (on N)
        [ 0.0576,  1.5037,  0.8789],  # H (on C-alpha)
        [ 0.0576,  1.5037, -0.8789],  # H (on C-alpha)
        [ 3.1101, -0.0830,  0.0000],  # H (on O-hydroxyl)
    ])

    return MoleculeGeometry(
        atoms=atoms,
        coords=coords,
        charge=0,
        spin=0,
        name="glycine",
        formula="C2H5NO2",
    )


def _compute_formula(atoms: List[str]) -> str:
    """Compute molecular formula from atom list (Hill system)."""
    from collections import Counter
    counts = Counter(atoms)
    # Hill system: C first, H second, then alphabetical
    parts = []
    for element in ["C", "H"]:
        if element in counts:
            parts.append(f"{element}{counts.pop(element) if counts[element] > 1 else ''}")
    for element in sorted(counts.keys()):
        parts.append(f"{element}{counts[element] if counts[element] > 1 else ''}")
    return "".join(parts)
