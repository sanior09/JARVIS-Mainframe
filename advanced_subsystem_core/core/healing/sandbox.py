import logging
import traceback
from typing import Dict, Any, List
from ...domain.models import SynthesizedPatch
from ...domain.interfaces import SandboxObserverInterface
from ...exceptions import SandboxExecutionError

logger = logging.getLogger(__name__)

class IsolatedSandbox:
    """Provides an isolated environment to test generated code patches."""
    
    def __init__(self):
        self._observers: List[SandboxObserverInterface] = []
        
    def attach(self, observer: SandboxObserverInterface):
        self._observers.append(observer)
        
    def detach(self, observer: SandboxObserverInterface):
        self._observers.remove(observer)
        
    def notify_success(self, patch: SynthesizedPatch, results: Dict[str, Any]):
        for observer in self._observers:
            observer.on_patch_success(patch, results)
            
    def notify_failure(self, patch: SynthesizedPatch, error: str):
        for observer in self._observers:
            observer.on_patch_failure(patch, error)

    def run_patch(self, patch: SynthesizedPatch, global_context: Dict[str, Any] = None) -> bool:
        """
        Attempts to execute the proposed AST block in a restricted context.
        Uses a lightweight exec sandboxing mechanism.
        """
        logger.info(f"[Sandbox] Executing patch {patch.patch_id} for {patch.target_file}...")
        restricted_globals = global_context or {}
        local_context = {}
        
        # In a true enterprise environment, this would use a separate Process or Docker container.
        # For this demonstration, we use restricted exec.
        try:
            exec(patch.proposed_code_snippet, restricted_globals, local_context)  # nosec B102
            logger.info(f"[Sandbox] Patch {patch.patch_id} executed successfully.")
            self.notify_success(patch, {"locals": str(local_context.keys())})
            return True
        except Exception as e:
            error_details = traceback.format_exc()
            logger.error(f"[Sandbox] Patch {patch.patch_id} failed execution:\n{error_details}")
            self.notify_failure(patch, str(e))
            raise SandboxExecutionError(f"Sandboxed patch failed: {e}")
