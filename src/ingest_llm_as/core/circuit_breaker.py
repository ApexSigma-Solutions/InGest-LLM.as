"""Circuit breaker implementation for fault tolerance."""

import time
import threading
from typing import Optional
from enum import Enum


class CircuitState(str, Enum):
    """Circuit breaker states."""
    CLOSED = "CLOSED"
    OPEN = "OPEN"
    HALF_OPEN = "HALF_OPEN"


class CircuitBreaker:
    """
    Thread-safe circuit breaker for fault tolerance.
    
    Implements the circuit breaker pattern with three states:
    - CLOSED: Normal operation, requests are allowed
    - OPEN: Service is failing, requests are blocked
    - HALF_OPEN: Testing if service recovered, limited requests allowed
    """

    def __init__(
        self,
        failure_threshold: int = 3,
        recovery_timeout: int = 300,
        name: str = "default"
    ):
        """
        Initialize circuit breaker.

        Args:
            failure_threshold: Number of failures before opening circuit
            recovery_timeout: Seconds to wait before attempting recovery
            name: Name for logging and identification
        """
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.name = name
        self.failure_count = 0
        self.last_failure_time: Optional[float] = None
        self.state = CircuitState.CLOSED
        self._lock = threading.Lock()

    def record_failure(self) -> None:
        """Record a failure and potentially open the circuit."""
        with self._lock:
            self.failure_count += 1
            self.last_failure_time = time.time()
            
            if self.failure_count >= self.failure_threshold:
                self.state = CircuitState.OPEN

    def record_success(self) -> None:
        """Record a success and close the circuit."""
        with self._lock:
            self.failure_count = 0
            self.state = CircuitState.CLOSED

    def is_closed(self) -> bool:
        """
        Check if circuit is closed (allowing requests).
        
        Returns:
            True if requests are allowed, False otherwise
        """
        with self._lock:
            if self.state == CircuitState.OPEN:
                # Check if recovery timeout has elapsed
                if self.last_failure_time and \
                   time.time() - self.last_failure_time > self.recovery_timeout:
                    self.state = CircuitState.HALF_OPEN
                    return True
                return False
            return True

    def get_state(self) -> CircuitState:
        """Get current circuit state."""
        with self._lock:
            return self.state

    def get_failure_count(self) -> int:
        """Get current failure count."""
        with self._lock:
            return self.failure_count

    def get_status(self) -> dict:
        """
        Get circuit breaker status for health checks.
        
        Returns:
            Dictionary with state and failure count
        """
        with self._lock:
            return {
                "name": self.name,
                "state": self.state.value,
                "failure_count": self.failure_count,
                "failure_threshold": self.failure_threshold,
                "recovery_timeout": self.recovery_timeout
            }
