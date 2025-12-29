"""Unit tests for Circuit Breaker."""

import time
import threading
import pytest
from src.ingest_llm_as.core.circuit_breaker import CircuitBreaker, CircuitState


def test_circuit_breaker_initial_state():
    """Test circuit breaker starts in CLOSED state."""
    cb = CircuitBreaker(failure_threshold=3, recovery_timeout=300)
    assert cb.get_state() == CircuitState.CLOSED
    assert cb.is_closed() is True
    assert cb.get_failure_count() == 0


def test_circuit_breaker_records_failures():
    """Test circuit breaker tracks failure count."""
    cb = CircuitBreaker(failure_threshold=3, recovery_timeout=300)
    
    cb.record_failure()
    assert cb.get_failure_count() == 1
    assert cb.get_state() == CircuitState.CLOSED
    
    cb.record_failure()
    assert cb.get_failure_count() == 2
    assert cb.get_state() == CircuitState.CLOSED


def test_circuit_breaker_opens_after_threshold():
    """Test circuit breaker opens after threshold failures."""
    cb = CircuitBreaker(failure_threshold=3, recovery_timeout=300)
    
    cb.record_failure()
    cb.record_failure()
    cb.record_failure()
    
    assert cb.get_state() == CircuitState.OPEN
    assert cb.is_closed() is False


def test_circuit_breaker_resets_on_success():
    """Test circuit breaker resets failure count on success."""
    cb = CircuitBreaker(failure_threshold=3, recovery_timeout=300)
    
    cb.record_failure()
    cb.record_failure()
    assert cb.get_failure_count() == 2
    
    cb.record_success()
    assert cb.get_failure_count() == 0
    assert cb.get_state() == CircuitState.CLOSED


def test_circuit_breaker_recovery_after_timeout():
    """Test circuit breaker enters HALF_OPEN after timeout."""
    cb = CircuitBreaker(failure_threshold=2, recovery_timeout=1)
    
    # Open the circuit
    cb.record_failure()
    cb.record_failure()
    assert cb.get_state() == CircuitState.OPEN
    assert cb.is_closed() is False
    
    # Wait for recovery timeout
    time.sleep(1.1)
    
    # Should now allow requests (HALF_OPEN)
    assert cb.is_closed() is True


def test_circuit_breaker_thread_safety():
    """Test circuit breaker is thread-safe."""
    cb = CircuitBreaker(failure_threshold=100, recovery_timeout=300)
    failures = []
    
    def record_failures():
        for _ in range(50):
            cb.record_failure()
    
    threads = [threading.Thread(target=record_failures) for _ in range(4)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    
    # Should have recorded 200 failures total (4 threads * 50 each)
    assert cb.get_failure_count() == 200


def test_circuit_breaker_get_status():
    """Test circuit breaker status reporting."""
    cb = CircuitBreaker(failure_threshold=3, recovery_timeout=300, name="test-cb")
    
    status = cb.get_status()
    assert status["name"] == "test-cb"
    assert status["state"] == "CLOSED"
    assert status["failure_count"] == 0
    assert status["failure_threshold"] == 3
    assert status["recovery_timeout"] == 300
    
    cb.record_failure()
    cb.record_failure()
    cb.record_failure()
    
    status = cb.get_status()
    assert status["state"] == "OPEN"
    assert status["failure_count"] == 3
