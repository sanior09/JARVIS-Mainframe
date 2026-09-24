import sys
import traceback
import logging
from typing import Any, Callable
from contextlib import ContextDecorator
from ...domain.models import FaultContext
from .synthesizer import TracebackASTAnalyzer
from .sandbox import IsolatedSandbox

logger = logging.getLogger(__name__)

class SelfHealingInterceptor(ContextDecorator):
    """
    Context Manager and Decorator that intercepts crashes, captures the fault context,
    synthesizes a patch via AST, and attempts to run it in a sandbox.
    """
    
    def __init__(self, sandbox: IsolatedSandbox, synthesizer: TracebackASTAnalyzer):
        self.sandbox = sandbox
        self.synthesizer = synthesizer
        
    def __enter__(self):
        logger.debug("[SelfHealingInterceptor] Execution context protected.")
        return self
        
    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type is None:
            return False # No exception
            
        logger.error(f"[SelfHealingInterceptor] Exception intercepted: {exc_type.__name__}: {exc_val}")
        
        # Extract the last frame where the error actually occurred
        tb_list = traceback.extract_tb(exc_tb)
        if not tb_list:
            return False
            
        last_frame = tb_list[-1]
        failing_file = last_frame.filename
        failing_line = last_frame.lineno
        
        # Construct Fault Context
        context = FaultContext(
            exception_type=exc_type.__name__,
            error_message=str(exc_val),
            traceback_lines=traceback.format_tb(exc_tb),
            failing_file=failing_file,
            failing_line_number=failing_line,
            local_vars_snapshot={} # Could use inspect framework here in a real scenario
        )
        
        try:
            # 1. Synthesize patch
            patch = self.synthesizer.synthesize_patch(context)
            
            # 2. Run in sandbox
            self.sandbox.run_patch(patch)
            
            # If successful, we theoretically could hot-reload the module here.
            logger.info("[SelfHealingInterceptor] Self-healing sequence complete.")
            
        except Exception as healing_err:
            logger.critical(f"[SelfHealingInterceptor] Self-healing completely failed: {healing_err}")
            
        # We still want the application to know it failed initially unless hot-reloaded
        return False
