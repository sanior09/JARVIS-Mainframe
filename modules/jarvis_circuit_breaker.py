import time
import logging
from enum import Enum
from typing import Callable, Any

logger = logging.getLogger("CircuitBreaker")
if not logger.handlers:
    h = logging.StreamHandler()
    h.setFormatter(logging.Formatter("%(asctime)s [CIRCUIT-BREAKER] %(message)s"))
    logger.addHandler(h)
    logger.setLevel(logging.INFO)

class CircuitState(Enum):
    CLOSED = "CLOSED"       
    OPEN = "OPEN"           
    HALF_OPEN = "HALF_OPEN" 

class CircuitOpenException(Exception):
    pass

class APICircuitBreaker:
    def __init__(self, failure_threshold: int = 3, recovery_timeout: int = 60):
        """
        :param failure_threshold: Number of consecutive failures before tripping to OPEN.
        :param recovery_timeout: Seconds to wait in OPEN state before trying HALF_OPEN.
        """
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.state = CircuitState.CLOSED
        self.failure_count = 0
        self.last_failure_time = 0.0

    def call(self, func: Callable, *args, **kwargs) -> Any:
        if self.state == CircuitState.OPEN:
            if time.time() - self.last_failure_time > self.recovery_timeout:
                logger.info("Circuit switching to HALF_OPEN. Testing endpoint...")
                self.state = CircuitState.HALF_OPEN
            else:
                remaining = int(self.recovery_timeout - (time.time() - self.last_failure_time))
                raise CircuitOpenException(f"Circuit is OPEN. Fast-failing. Cooldown: {remaining}s")

        try:
            result = func(*args, **kwargs)
            if self.state == CircuitState.HALF_OPEN:
                logger.info("Endpoint recovered. Circuit switching to CLOSED.")
                self.reset()
            return result
        except Exception as e:
            self._handle_failure(e)
            raise e

    def _handle_failure(self, error: Exception):
        
        err_str = str(error).lower()
        if any(code in err_str for code in ["429", "503", "502", "504", "rate limit", "timeout", "connection"]):
            self.failure_count += 1
            self.last_failure_time = time.time()
            logger.warning(f"Endpoint failure recorded ({self.failure_count}/{self.failure_threshold}): {error}")
            
            if self.state in [CircuitState.CLOSED, CircuitState.HALF_OPEN] and self.failure_count >= self.failure_threshold:
                self.state = CircuitState.OPEN
                logger.error(f"CIRCUIT BREAKER TRIPPED! State is now OPEN for {self.recovery_timeout} seconds.")
        else:
            
            pass

    def reset(self):
        self.state = CircuitState.CLOSED
        self.failure_count = 0
        self.last_failure_time = 0.0

groq_breaker = APICircuitBreaker(failure_threshold=3, recovery_timeout=15)
