# InGest-LLM.as Testing Suite

## Overview

This document provides comprehensive guidance for testing the InGest-LLM service, which handles intelligent content ingestion, vectorization, and LLM-powered processing.

## Test Structure

```
tests/
├── __init__.py                 # Test package initialization
├── conftest.py                 # Shared fixtures and configuration
├── unit/                       # Unit tests (isolated components)
│   ├── __init__.py
│   ├── conftest.py            # Unit-specific fixtures
│   └── test_*.py              # Individual unit test files
├── integration/                # Integration tests (component interaction)
│   ├── __init__.py
│   ├── conftest.py            # Integration-specific fixtures
│   └── test_*.py              # Integration test files
├── e2e/                        # End-to-end tests (full workflows)
│   ├── __init__.py
│   ├── conftest.py            # E2E-specific fixtures
│   └── test_*.py              # End-to-end test files
└── utils/                      # Test utilities and helpers
    ├── __init__.py
    ├── mocks.py               # Mock service implementations
    └── factories.py           # Test data factories
```

## Test Categories

### Unit Tests (`tests/unit/`)
- **Purpose**: Test isolated components and functions
- **Scope**: Single functions, classes, or modules without external dependencies
- **Mocking**: All external services (database, cache, vector store, LLM)
- **Coverage Goal**: 90%+ unit test coverage
- **Examples**:
  - Text processing functions
  - Data validation logic
  - Individual service methods
  - Utility functions

### Integration Tests (`tests/integration/`)
- **Purpose**: Test component interactions and external service integrations
- **Scope**: Multiple components working together with real external services
- **Environment**: Requires running external services (PostgreSQL, Redis, Qdrant, Neo4j)
- **Coverage Goal**: 75%+ integration test coverage
- **Examples**:
  - Database operations with caching
  - Vector store interactions
  - LLM service integrations
  - Message queue communications

### End-to-End Tests (`tests/e2e/`)
- **Purpose**: Test complete user workflows and system behavior
- **Scope**: Full request-response cycles through the API
- **Environment**: Complete system with all services running
- **Coverage Goal**: 60%+ end-to-end coverage for critical paths
- **Examples**:
  - Document ingestion workflows
  - Search and retrieval operations
  - Multi-step processing pipelines
  - Error handling scenarios

## Running Tests

### All Tests
```bash
# Run all tests with coverage
pytest --cov=app --cov-report=html --cov-report=term-missing

# Run all tests with detailed output
pytest -v --tb=short

# Run tests in parallel (requires pytest-xdist)
pytest -n auto
```

### By Category
```bash
# Unit tests only
pytest tests/unit/ -v

# Integration tests only
pytest tests/integration/ -v --docker

# End-to-end tests only
pytest tests/e2e/ -v --e2e

# Specific test file
pytest tests/unit/test_embedding_service.py -v
```

### With Coverage
```bash
# Unit tests with coverage
pytest tests/unit/ --cov=app --cov-report=html

# Integration tests with coverage
pytest tests/integration/ --cov=app --cov-report=html --cov-append

# Combined coverage report
pytest tests/unit/ tests/integration/ --cov=app --cov-report=html
```

### Performance Testing
```bash
# Run slow tests
pytest -m slow -v

# Skip slow tests
pytest -m "not slow"

# Performance profiling
pytest --durations=10
```

## Coverage Goals

| Category | Target Coverage | Current Status |
|----------|----------------|----------------|
| Unit Tests | 90%+ | ✅ Implemented |
| Integration Tests | 75%+ | ✅ Implemented |
| End-to-End Tests | 60%+ | ✅ Implemented |
| **Overall** | **80%+** | **✅ Target Met** |

## Test Configuration

### pytest.ini Settings
```ini
[tool:pytest]
testpaths = tests
python_files = test_*.py *_test.py
python_classes = Test*
python_functions = test_*
addopts =
    --strict-markers
    --strict-config
    --disable-warnings
    --junit-xml=reports/junit.xml
    --cov-report=html:htmlcov
    --cov-report=xml:coverage.xml
    --cov-report=json:coverage.json
    --cov-report=term-missing
    --cov-fail-under=80
markers =
    unit: Unit tests
    integration: Integration tests
    e2e: End-to-end tests
    slow: Slow running tests
    skip_ci: Skip in CI environment
    docker: marks tests that require docker
    repository_ingestion: marks tests for repository ingestion
junit_family = xunit1
```

### Coverage Configuration (pyproject.toml)
```toml
[tool.coverage.run]
source = ["app"]
omit = [
    "*/tests/*",
    "*/test_*",
    "*/venv/*",
    "*/__pycache__/*",
]

[tool.coverage.report]
exclude_lines = [
    "pragma: no cover",
    "def __repr__",
    "if self.debug:",
    "raise AssertionError",
    "raise NotImplementedError",
    "if 0:",
    "if __name__ == .__main__.:",
]

[tool.coverage.html]
directory = "htmlcov"

[tool.coverage.xml]
output = "coverage.xml"
```

## Writing Tests

### Test File Naming Convention
- `test_*.py` for test modules
- `*_test.py` for test modules (alternative)
- Descriptive names: `test_document_processing.py`, `test_vector_search.py`

### Test Class Organization
```python
import pytest
from tests.utils.factories import create_document_data, create_query_data

class TestDocumentProcessing:
    """Test document processing functionality."""

    @pytest.mark.unit
    def test_process_valid_document(self, mock_embedding_service):
        """Test processing a valid document."""
        document = create_document_data()
        result = process_document(document)
        assert result["status"] == "processed"
        assert "embeddings" in result

    @pytest.mark.unit
    def test_process_empty_document(self):
        """Test processing an empty document."""
        document = create_document_data(content="")
        with pytest.raises(ValueError, match="empty content"):
            process_document(document)

    @pytest.mark.integration
    async def test_process_with_database_storage(self, integration_database):
        """Test document processing with database storage."""
        document = create_document_data()
        result = await process_and_store_document(document, integration_database)
        assert result["stored"] is True
        assert result["id"] is not None
```

### Test Function Patterns
```python
@pytest.mark.unit
def test_function_name():
    """Test description."""
    # Arrange
    test_data = create_test_data()

    # Act
    result = function_under_test(test_data)

    # Assert
    assert result.expected_property == expected_value

@pytest.mark.asyncio
@pytest.mark.integration
async def test_async_function():
    """Test async function."""
    async with mock_service() as service:
        result = await service.async_method()
        assert result is not None
```

## Fixtures and Mocks

### Shared Fixtures (conftest.py)
- `event_loop`: Async event loop for tests
- `temp_dir`: Temporary directory for file operations
- `test_settings`: Test configuration settings
- `mock_database`: Mocked database session
- `mock_redis`: Mocked Redis client
- `mock_qdrant`: Mocked vector store
- `mock_llm_service`: Mocked LLM service
- `sample_document_data`: Sample document for testing
- `sample_batch_documents`: Batch of test documents
- `sample_query_data`: Sample search query

### Test Utilities
```python
from tests.utils.mocks import MockDatabase, MockRedis, MockVectorStore
from tests.utils.factories import create_document_data, create_batch_documents

# Using mocks
mock_db = MockDatabase()
mock_redis = MockRedis()
mock_vector_store = MockVectorStore()

# Using factories
document = create_document_data(content="Test content")
batch = create_batch_documents(count=10)
```

## Best Practices

### 1. Test Isolation
- Each test should be independent
- Use fixtures for setup/cleanup
- Avoid test interdependencies
- Clean up resources after tests

### 2. Naming Conventions
- `test_function_name`: For function tests
- `test_method_name`: For method tests
- `test_feature_scenario`: For feature tests
- `test_error_condition`: For error handling tests

### 3. Assertion Patterns
```python
# Good: Specific assertions
assert result.status_code == 200
assert "error" not in result
assert len(results) == expected_count

# Better: Descriptive assertions
assert user.is_active, "User should be active after registration"
assert email in sent_emails, f"Welcome email should be sent to {email}"
```

### 4. Mock Usage
```python
# Good: Mock external dependencies
@pytest.fixture
def mock_external_api():
    with patch('app.external_api.call') as mock_call:
        mock_call.return_value = {"status": "success"}
        yield mock_call

# Better: Use custom mock classes for complex behavior
@pytest.fixture
def mock_database():
    mock_db = MockDatabase()
    mock_db.set_response("SELECT * FROM users", [{"id": 1, "name": "Test"}])
    return mock_db
```

### 5. Async Testing
```python
@pytest.mark.asyncio
async def test_async_function():
    """Test async functions properly."""
    result = await async_function()
    assert result is not None

# For fixtures
@pytest.fixture
async def async_fixture():
    # Setup
    resource = await create_resource()
    yield resource
    # Cleanup
    await resource.cleanup()
```

### 6. Parametrized Tests
```python
@pytest.mark.parametrize("input_value,expected", [
    (0, "zero"),
    (1, "one"),
    (2, "two"),
])
def test_number_to_word(input_value, expected):
    """Test number to word conversion."""
    assert number_to_word(input_value) == expected
```

### 7. Exception Testing
```python
def test_invalid_input_raises_error():
    """Test that invalid input raises appropriate error."""
    with pytest.raises(ValueError, match="Invalid input"):
        process_invalid_input("bad data")

def test_file_not_found_error():
    """Test file not found error handling."""
    with pytest.raises(FileNotFoundError):
        read_nonexistent_file()
```

### 8. Performance Testing
```python
@pytest.mark.slow
def test_large_batch_processing():
    """Test processing large batches of documents."""
    large_batch = create_batch_documents(count=1000)

    start_time = time.time()
    results = process_batch(large_batch)
    duration = time.time() - start_time

    assert len(results) == 1000
    assert duration < 30  # Should complete within 30 seconds
```

### 9. Test Data Management
```python
# Use factories for consistent test data
def test_document_creation():
    doc = create_document_data(
        content="Test content",
        metadata={"author": "Test Author"}
    )
    assert doc["content"] == "Test content"
    assert doc["metadata"]["author"] == "Test Author"

# Edge cases
def test_edge_cases():
    edge_cases = create_edge_case_documents()
    for doc in edge_cases:
        # Test each edge case scenario
        result = process_document(doc)
        assert result is not None
```

### 10. CI/CD Integration
```python
@pytest.mark.skip_ci
def test_local_only_feature():
    """Test features that only work in local environment."""
    # This test is skipped in CI
    pass

@pytest.mark.docker
def test_docker_integration():
    """Test requiring Docker services."""
    # This test requires Docker to be available
    pass
```

## Troubleshooting

### Common Issues

1. **Import Errors**
   - Ensure `PYTHONPATH` includes the `app` directory
   - Check that all dependencies are installed
   - Verify module structure matches imports

2. **Fixture Errors**
   - Check fixture scope (`function`, `class`, `module`, `session`)
   - Ensure fixtures are defined in the correct conftest.py
   - Verify fixture dependencies are available

3. **Async Test Issues**
   - Use `@pytest.mark.asyncio` for async tests
   - Ensure event loop is properly configured
   - Check that async fixtures yield correctly

4. **Coverage Issues**
   - Run `coverage combine` if using parallel tests
   - Check source paths in coverage configuration
   - Exclude test files from coverage calculation

5. **Mock Issues**
   - Verify mock targets match actual import paths
   - Use `spec` parameter for better mock behavior
   - Check that mocks are applied at the correct level

### Debugging Tests
```bash
# Run specific test with debugging
pytest tests/unit/test_specific.py::TestClass::test_method -v -s

# Run with PDB on failure
pytest --pdb

# Run with detailed tracebacks
pytest --tb=long

# Show fixtures for specific test
pytest --fixtures tests/unit/test_specific.py::TestClass::test_method

# Show markers
pytest --markers
```

## Continuous Integration

### GitHub Actions Configuration
```yaml
- name: Run Tests
  run: |
    pytest tests/unit/ --cov=app --cov-report=xml
    pytest tests/integration/ --cov=app --cov-report=xml --cov-append

- name: Upload Coverage
  uses: codecov/codecov-action@v3
  with:
    file: ./coverage.xml
```

### Coverage Reporting
- HTML reports: `htmlcov/index.html`
- XML reports: `coverage.xml` (for CI tools)
- JSON reports: `coverage.json` (for custom tools)
- Terminal output: `--cov-report=term-missing`

## Maintenance

### Regular Tasks
1. **Update test data**: Keep factories current with schema changes
2. **Review coverage**: Ensure new code is tested
3. **Update mocks**: Reflect changes in external APIs
4. **Performance monitoring**: Track test execution times
5. **Dependency updates**: Update test dependencies regularly

### Coverage Maintenance
- Review coverage reports regularly
- Identify untested code paths
- Add tests for new features
- Remove obsolete tests
- Optimize slow-running tests

This testing suite provides comprehensive coverage of the InGest-LLM service with proper isolation, mocking, and realistic test scenarios. Follow these guidelines to maintain high-quality, reliable tests that support continuous integration and deployment.