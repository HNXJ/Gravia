import subprocess
import sys
from pathlib import Path
from typing import Tuple

def run_autopsy(script_path: str) -> Tuple[bool, str]:
    """
    Executes a generated Python script and captures its output/errors.
    Specifically designed to catch JAX tracer leaks and compilation errors.
    """
    print(f"[THETA AUTOPSY] Executing {script_path}...")
    
    try:
        # Run script as a separate process to capture stderr
        result = subprocess.run(
            [sys.executable, script_path],
            capture_output=True,
            text=True,
            timeout=60  # Prevent infinite loops in biophysical ODEs
        )
        
        if result.returncode == 0:
            print("✅ Execution Successful.")
            return True, result.stdout
        else:
            print("❌ Execution Failed.")
            return False, result.stderr
            
    except subprocess.TimeoutExpired:
        return False, "TIMEOUT: Script exceeded 60s execution limit."
    except Exception as e:
        return False, f"SYSTEM_ERROR: {str(e)}"

if __name__ == "__main__":
    if len(sys.argv) > 1:
        success, output = run_autopsy(sys.argv[1])
        if not success:
            print("\n--- ERROR TRACEBACK ---")
            print(output)
            sys.exit(1)
        else:
            print("\n--- OUTPUT ---")
            print(output)
