"""
Evaluation Constants Module

This module contains constants and patterns used for evaluation tasks,
specifically for MPI (Multi-dimensional Personality Inventory) assessments.
"""

# MPI Assessment Evaluation Format
MPI_AE_FORMAT = (
    "### EVALUATION FORMAT\n"
    "Choose exactly ONE option from (A/B/C/D/E).\n"
    "Output ONLY the single uppercase letter (A, B, C, D, or E) with no spaces, "
    "no punctuation, no explanations, no extra text."
)

# Strict validation regex for MPI-AE responses (only 1 letter A-E, minimal whitespace allowed)
MPI_AE_REGEX = r"^(?:\s*)?([ABCDE])(?:\s*)?$"

# Evaluation types
EVAL_TYPE_NONE = "none"
EVAL_TYPE_MPI_AE = "mpi_ae"

# Default values
DEFAULT_FORMAT_ID = "MPI-120"
DEFAULT_SEED = None
DEFAULT_STRICT_OUTPUT = True
