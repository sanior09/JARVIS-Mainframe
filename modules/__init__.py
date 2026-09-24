"""
J.A.R.V.I.S. Core Modules & Subsystems Package
Automatically configures sys.path so all modules can resolve each other and root utilities.
"""
import sys
import os

_MODULES_DIR = os.path.dirname(os.path.abspath(__file__))
_ROOT_DIR = os.path.dirname(_MODULES_DIR)

if _ROOT_DIR not in sys.path:
    sys.path.insert(0, _ROOT_DIR)
if _MODULES_DIR not in sys.path:
    sys.path.insert(0, _MODULES_DIR)
