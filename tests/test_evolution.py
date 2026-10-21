import sys
import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE_DIR)

if __name__ == "__main__":
    # Mock JARVIS globals needed for evolution
    import jarvis
    jarvis.SELF_PATCH_AVAILABLE = True

    from jarvis_evolution import run_evolution_scan_operation

    print("Running Evolution Scan...")
    result = run_evolution_scan_operation()
    print("Result:")
    print(result)

    print("\nChecking TOOLS_DEFINITION length:")
    print(len(jarvis.TOOLS_DEFINITION))
