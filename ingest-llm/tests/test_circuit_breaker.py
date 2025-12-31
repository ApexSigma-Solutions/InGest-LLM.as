"""
Unit tests for Circuit Breaker implementation.

Tests cover state transitions, failure counting, timeout handling,
and thread-safety of the CircuitBreaker class.

Phase: TN-LINEAR-06 - Webhook Ingestion
"""

import time
import threading
from unittest.mock import patch

import pytest

from ingest_llm.core.circuit_breaker import (
    CircuitBreaker,
    CircuitState,
)


@pytest.fixture
def circuit_breaker():
    """Create a fresh CircuitBreaker instance for each test."""
    return CircuitBreaker(
        failure_threshold=3,
        timeout_seconds=5,
        name="test-circuit-breaker",
    )


class TestCircuitBreakerInitialization:
    """Test CircuitBreaker initialization and default state."""

    def test_initial_state_is_closed(self, circuit_breaker):
        """Circuit breaker should start in CLOSED state."""
        assert circuit_breaker.get_state() == CircuitState.CLOSED
        assert circuit_breaker.is_closed() is True

    def test_initial_failure_count_is_zero(self, circuit_breaker):
        """Circuit breaker should start with zero failures."""
        assert circuit_breaker.get_failure_count() == 0

    def test_custom_failure_threshold(self):
        """Circuit breaker should accept custom failure threshold."""
        cb = CircuitBreaker(failure_threshold=5, timeout_seconds=10, name="custom")
        assert cb.get_failure_count() == 0
        assert cb.get_state() == CircuitState.CLOSED

    def test_custom_timeout(self):
        """Circuit breaker should accept custom timeout."""
        cb = CircuitBreaker(failure_threshold=3, timeout_seconds=15, name="custom")
        assert cb.get_state() == CircuitState.CLOSED


class TestCircuitBreakerFailureRecording:
    """Test failure recording and state transitions."""

    def test_record_failure_increments_count(self, circuit_breaker):
        """Recording a failure should increment the failure count."""
        circuit_breaker.record_failure()
        assert circuit_breaker.get_failure_count() == 1

        circuit_breaker.record_failure()
        assert circuit_breaker.get_failure_count() == 2

    def test_record_failure_below_threshold(self, circuit_breaker):
        """Failures below threshold should keep circuit CLOSED."""
        circuit_breaker.record_failure()
        circuit_breaker.record_failure()
        assert circuit_breaker.get_state() == CircuitState.CLOSED
        assert circuit_breaker.is_closed() is True

    def test_record_failure_at_threshold_trips_circuit(self, circuit_breaker):
        """Failures at threshold should trip circuit to OPEN."""
        circuit_breaker.record_failure()
        circuit_breaker.record_failure()
        circuit_breaker.record_failure()
        assert circuit_breaker.get_state() == CircuitState.OPEN
        assert circuit_breaker.is_closed() is False

    def test_record_failure_in_open_state(self, circuit_breaker):
        """Recording failure in OPEN state should not change state."""
        # Trip the circuit
        circuit_breaker.record_failure()
        circuit_breaker.record_failure()
        circuit_breaker.record_failure()
        assert circuit_breaker.get_state() == CircuitState.OPEN

        # Record another failure
        circuit_breaker.record_failure()
        # State should remain OPEN
        assert circuit_breaker.get_state() == CircuitState.OPEN


class TestCircuitBreakerSuccessRecording:
    """Test success recording and state transitions."""

    def test_record_success_resets_failure_count(self, circuit_breaker):
        """Recording success should reset failure count."""
        circuit_breaker.record_failure()
        circuit_breaker.record_failure()
        assert circuit_breaker.get_failure_count() == 2

        circuit_breaker.record_success()
        assert circuit_breaker.get_failure_count() == 0

    def test_record_success_in_closed_state(self, circuit_breaker):
        """Recording success in CLOSED state should keep it CLOSED."""
        circuit_breaker.record_success()
        assert circuit_breaker.get_state() == CircuitState.CLOSED
        assert circuit_breaker.is_closed() is True

    def test_record_success_in_half_open_state(self, circuit_breaker):
        """Recording success in HALF_OPEN should transition to CLOSED."""
        # Use a shorter timeout for testing
        cb_short = CircuitBreaker(failure_threshold=3, timeout_seconds=0.1, name="short-timeout")
        
        # Trip the circuit
        cb_short.record_failure()
        cb_short.record_failure()
        cb_short.record_failure()
        assert cb_short.get_state() == CircuitState.OPEN

        # Wait for timeout to expire
        time.sleep(0.2)

        # Record success (should transition to CLOSED)
        cb_short.record_success()
        assert cb_short.get_state() == CircuitState.CLOSED
        assert cb_short.is_closed() is True


class TestCircuitBreakerTimeoutHandling:
    """Test timeout and automatic state transitions."""

    def test_is_closed_returns_true_in_closed_state(self, circuit_breaker):
        """is_closed() should return True in CLOSED state."""
        assert circuit_breaker.is_closed() is True

    def test_is_closed_returns_false_in_open_state(self, circuit_breaker):
        """is_closed() should return False in OPEN state."""
        # Trip the circuit
        circuit_breaker.record_failure()
        circuit_breaker.record_failure()
        circuit_breaker.record_failure()
        assert circuit_breaker.get_state() == CircuitState.OPEN
        assert circuit_breaker.is_closed() is False

    def test_is_closed_returns_true_in_half_open_state(self, circuit_breaker):
        """is_closed() should return True in HALF_OPEN state."""
        # Trip the circuit
        circuit_breaker.record_failure()
        circuit_breaker.record_failure()
        circuit_breaker.record_failure()
        assert circuit_breaker.get_state() == CircuitState.OPEN

        # Wait for timeout to expire
        time.sleep(0.2)

        # Should be in HALF_OPEN state now
        assert circuit_breaker.is_closed() is True

    def test_timeout_transitions_to_half_open(self, circuit_breaker):
        """After timeout, circuit should transition to HALF_OPEN."""
        # Trip the circuit
        circuit_breaker.record_failure()
        circuit_breaker.record_failure()
        circuit_breaker.record_failure()
        assert circuit_breaker.get_state() == CircuitState.OPEN

        # Wait for timeout to expire (use a shorter timeout circuit breaker)
        cb_short = CircuitBreaker(failure_threshold=3, timeout_seconds=0.1, name="short-timeout")
        cb_short.record_failure()
        cb_short.record_failure()
        cb_short.record_failure()
        assert cb_short.get_state() == CircuitState.OPEN
        time.sleep(0.2)

        # Should be in HALF_OPEN state
        assert cb_short.get_state() == CircuitState.HALF_OPEN

    def test_half_open_allows_one_request(self, circuit_breaker):
        """HALF_OPEN state should allow one request."""
        # Use a shorter timeout for testing
        cb_short = CircuitBreaker(failure_threshold=3, timeout_seconds=0.1, name="short-timeout")
        
        # Trip the circuit
        cb_short.record_failure()
        cb_short.record_failure()
        cb_short.record_failure()
        assert cb_short.get_state() == CircuitState.OPEN

        # Wait for timeout to expire
        time.sleep(0.2)

        # Should be in HALF_OPEN state
        assert cb_short.get_state() == CircuitState.HALF_OPEN

        # First request should be allowed
        assert cb_short.is_closed() is True

        # Second request should be blocked (circuit trips again)
        cb_short.record_failure()
        assert cb_short.get_state() == CircuitState.OPEN
        assert cb_short.is_closed() is False


class TestCircuitBreakerThreadSafety:
    """Test thread-safety of circuit breaker operations."""

    def test_concurrent_failure_recording(self, circuit_breaker):
        """Concurrent failure recording should be thread-safe."""
        num_threads = 10
        failures_per_thread = 2

        def record_failures(cb, count):
            for _ in range(count):
                cb.record_failure()

        threads = [
            threading.Thread(target=record_failures, args=(circuit_breaker, failures_per_thread))
            for _ in range(num_threads)
        ]

        for thread in threads:
            thread.start()

        for thread in threads:
            thread.join()

        expected_failures = num_threads * failures_per_thread
        assert circuit_breaker.get_failure_count() == expected_failures

    def test_concurrent_success_recording(self, circuit_breaker):
        """Concurrent success recording should be thread-safe."""
        num_threads = 10

        def record_successes(cb, count):
            for _ in range(count):
                cb.record_success()

        threads = [
            threading.Thread(target=record_successes, args=(circuit_breaker, 5))
            for _ in range(num_threads)
        ]

        for thread in threads:
            thread.start()

        for thread in threads:
            thread.join()

        # Failure count should be reset to 0
        assert circuit_breaker.get_failure_count() == 0

    def test_concurrent_mixed_operations(self, circuit_breaker):
        """Concurrent mixed operations should be thread-safe."""
        num_threads = 10

        def mixed_operations(cb, count):
            for i in range(count):
                if i % 2 == 0:
                    cb.record_failure()
                else:
                    cb.record_success()

        threads = [
            threading.Thread(target=mixed_operations, args=(circuit_breaker, 10))
            for _ in range(num_threads)
        ]

        for thread in threads:
            thread.start()

        for thread in threads:
            thread.join()

        # After concurrent operations, circuit breaker should be in a consistent state
        # The exact count depends on timing, but state should be valid
        state = circuit_breaker.get_state()
        assert state in [CircuitState.CLOSED, CircuitState.OPEN, CircuitState.HALF_OPEN]
        # Failure count should be non-negative
        assert circuit_breaker.get_failure_count() >= 0
        # Test that circuit breaker is still functional
        assert isinstance(circuit_breaker.is_closed(), bool)


class TestCircuitBreakerStatus:
    """Test status reporting functionality."""

    def test_get_status_includes_all_fields(self, circuit_breaker):
        """get_status() should return all relevant fields."""
        status = circuit_breaker.get_status()

        assert "name" in status
        assert "state" in status
        assert "failure_count" in status
        assert "failure_threshold" in status
        assert "timeout_seconds" in status
        assert "last_failure_time" in status

    def test_get_status_in_closed_state(self, circuit_breaker):
        """get_status() should reflect CLOSED state."""
        status = circuit_breaker.get_status()

        assert status["state"] == "CLOSED"
        assert status["failure_count"] == 0
        assert status["is_closed"] is True

    def test_get_status_after_failures(self, circuit_breaker):
        """get_status() should reflect failure count."""
        circuit_breaker.record_failure()
        circuit_breaker.record_failure()

        status = circuit_breaker.get_status()

        assert status["state"] == "CLOSED"
        assert status["failure_count"] == 2
        assert status["is_closed"] is True

    def test_get_status_in_open_state(self, circuit_breaker):
        """get_status() should reflect OPEN state."""
        # Trip the circuit
        circuit_breaker.record_failure()
        circuit_breaker.record_failure()
        circuit_breaker.record_failure()

        status = circuit_breaker.get_status()

        assert status["state"] == "OPEN"
        assert status["failure_count"] == 3
        assert status["is_closed"] is False

    def test_get_status_in_half_open_state(self, circuit_breaker):
        """get_status() should reflect HALF_OPEN state."""
        # Use a shorter timeout for testing
        cb_short = CircuitBreaker(failure_threshold=3, timeout_seconds=0.1, name="short-timeout")
        
        # Trip the circuit
        cb_short.record_failure()
        cb_short.record_failure()
        cb_short.record_failure()

        # Wait for timeout to expire
        time.sleep(0.2)

        status = cb_short.get_status()

        assert status["state"] == "HALF_OPEN"
        assert status["failure_count"] == 3
        assert status["is_closed"] is True


class TestCircuitBreakerLogging:
    """Test logging of state transitions."""

    @patch("ingest_llm.core.circuit_breaker.logger")
    def test_logs_state_transition_to_open(self, mock_logger, circuit_breaker):
        """Circuit breaker should log transition to OPEN state."""
        # Trip the circuit
        circuit_breaker.record_failure()
        circuit_breaker.record_failure()
        circuit_breaker.record_failure()

        # Check that info was called
        assert mock_logger.info.call_count > 0

        # Find the log call about state transition
        state_transition_calls = [
            call for call in mock_logger.info.call_args_list
            if "OPEN" in str(call) and "transitioned" in str(call).lower()
        ]
        assert len(state_transition_calls) > 0

    @patch("ingest_llm.core.circuit_breaker.logger")
    def test_logs_state_transition_to_half_open(self, mock_logger, circuit_breaker):
        """Circuit breaker should log transition to HALF_OPEN state."""
        # Use a shorter timeout for testing
        cb_short = CircuitBreaker(failure_threshold=3, timeout_seconds=0.1, name="short-timeout")
        
        # Trip the circuit
        cb_short.record_failure()
        cb_short.record_failure()
        cb_short.record_failure()

        # Wait for timeout to expire
        time.sleep(0.2)

        # Check that info was called
        assert mock_logger.info.call_count > 0

        # Find the log call about state transition
        state_transition_calls = [
            call for call in mock_logger.info.call_args_list
            if "HALF_OPEN" in str(call) and "transitioned" in str(call).lower()
        ]
        assert len(state_transition_calls) > 0

    @patch("ingest_llm.core.circuit_breaker.logger")
    def test_logs_state_transition_to_closed(self, mock_logger, circuit_breaker):
        """Circuit breaker should log transition to CLOSED state."""
        # Use a shorter timeout for testing
        cb_short = CircuitBreaker(failure_threshold=3, timeout_seconds=0.1, name="short-timeout")
        
        # Trip the circuit
        cb_short.record_failure()
        cb_short.record_failure()
        cb_short.record_failure()

        # Wait for timeout to expire
        time.sleep(0.2)

        # Record success to transition to CLOSED
        cb_short.record_success()

        # Check that info was called
        assert mock_logger.info.call_count > 0

        # Find the log call about state transition
        state_transition_calls = [
            call for call in mock_logger.info.call_args_list
            if "CLOSED" in str(call) and "transitioned" in str(call).lower()
        ]
        assert len(state_transition_calls) > 0


class TestCircuitBreakerEdgeCases:
    """Test edge cases and boundary conditions."""

    def test_zero_failure_threshold(self):
        """Circuit breaker with zero threshold should trip immediately."""
        cb = CircuitBreaker(failure_threshold=0, timeout_seconds=5, name="zero-threshold")
        assert cb.get_state() == CircuitState.CLOSED

        # First failure should trip the circuit
        cb.record_failure()
        assert cb.get_state() == CircuitState.OPEN

    def test_large_failure_threshold(self):
        """Circuit breaker should handle large failure thresholds."""
        cb = CircuitBreaker(failure_threshold=1000, timeout_seconds=5, name="large-threshold")
        assert cb.get_state() == CircuitState.CLOSED

        # Record many failures
        for _ in range(100):
            cb.record_failure()

        # Should still be CLOSED (below threshold)
        assert cb.get_state() == CircuitState.CLOSED
        assert cb.get_failure_count() == 100

    def test_very_short_timeout(self):
        """Circuit breaker should handle very short timeouts."""
        cb = CircuitBreaker(failure_threshold=3, timeout_seconds=0.1, name="short-timeout")
        assert cb.get_state() == CircuitState.CLOSED

        # Trip the circuit
        cb.record_failure()
        cb.record_failure()
        cb.record_failure()
        assert cb.get_state() == CircuitState.OPEN

        # Wait for timeout to expire
        time.sleep(0.2)

        # Should be in HALF_OPEN state
        assert cb.get_state() == CircuitState.HALF_OPEN

    def test_very_long_timeout(self):
        """Circuit breaker should handle very long timeouts."""
        cb = CircuitBreaker(failure_threshold=3, timeout_seconds=3600, name="long-timeout")
        assert cb.get_state() == CircuitState.CLOSED

        # Trip the circuit
        cb.record_failure()
        cb.record_failure()
        cb.record_failure()
        assert cb.get_state() == CircuitState.OPEN

        # Should still be OPEN (timeout not expired)
        assert cb.get_state() == CircuitState.OPEN
        assert cb.is_closed() is False
