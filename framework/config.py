"""Pipeline configuration constants."""

# Basis sets
DEFAULT_BASIS = "cc-pvdz"
COMPARISON_BASIS = "sto-3g"

# Active space selection
OCCUPATION_LOWER = 0.02   # initial lower threshold (loosest)
OCCUPATION_UPPER = 1.98   # initial upper threshold (loosest)
MAX_ACTIVE_ORBITALS = 8   # hard cap on active orbitals

# Core electrons per atom type (for freeze-core)
CORE_ELECTRONS = {
    "H": 0,
    "He": 0,
    "Li": 2, "Be": 2, "B": 2, "C": 2, "N": 2, "O": 2, "F": 2, "Ne": 2,
    "Na": 10, "Mg": 10, "Al": 10, "Si": 10, "P": 10, "S": 10, "Cl": 10, "Ar": 10,
}

# Jordan-Wigner is default (matches existing QMProt data)
DEFAULT_MAPPING = "jordan_wigner"

# Dataset paths
DATASET_DIR = "framework/datasets"

# Hartree to eV conversion
HARTREE_TO_EV = 27.211386245988
# Bohr to Angstrom
BOHR_TO_ANGSTROM = 0.529177249
# Debye conversion
AU_TO_DEBYE = 2.541746473
