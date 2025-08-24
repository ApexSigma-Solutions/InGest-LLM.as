# Core Integration Testing Suite

This document describes the core integration testing suite for validating the workflow between **InGest-LLM.as** and **memOS.as** services.

## 🎯 Purpose

This test suite fulfills the **P1-CC-02** task requirement: *"Establish Core Integration Testing Suite between InGest-LLM.as and memOS.as"*.

It validates:
- Service-to-service communication
- End-to-end data ingestion workflow
- Memory tier selection and storage
- Error handling and recovery
- Concurrent processing capabilities

## 📁 Files

| File | Location | Purpose |
|------|----------|---------|
| `test_memos_integration_core.py` | `tests/` | Main integration test suite |
| `run_core_integration_tests.py` | `scripts/` | Test runner with service validation |
| `pytest.ini` | `tests/` | Pytest configuration |

## 🚀 Quick Start

### Prerequisites
- InGest-LLM.as running on port 8000
- memOS.as running on port 8091
- Python dependencies: `pytest`, `httpx`, `pytest-asyncio`

### Install Dependencies
```bash
poetry install
# or
pip install pytest httpx pytest-asyncio
```

### Run Integration Tests
```bash
# Using the test runner (recommended)
python scripts/run_core_integration_tests.py

# Or directly with pytest
pytest tests/test_memos_integration_core.py -v -s
```

## 🧪 Test Categories

### Core Integration Tests (`TestCoreIntegration`)
- **`test_text_ingestion_to_memos()`**: Complete text content workflow
- **`test_code_ingestion_procedural_memory()`**: Code content → procedural memory
- **`test_memory_search_integration()`**: Search functionality validation  
- **`test_concurrent_ingestion()`**: Concurrent processing validation

### Error Handling Tests (`TestErrorHandling`)
- **`test_invalid_content_handling()`**: Invalid content rejection

## 🔧 Configuration

Update service URLs if needed:
```python
INGEST_SERVICE_URL = "http://localhost:8000"
MEMOS_SERVICE_URL = "http://localhost:8091"
```

## 🔍 Validation Patterns

### Integration Flow
1. **Content Ingestion** → InGest-LLM.as processes content
2. **Memory Storage** → Content forwarded to memOS.as  
3. **Storage Confirmation** → Memory IDs returned
4. **Retrieval Validation** → Content accessible in memOS.as
5. **Search Validation** → Content findable via search

### Memory Tier Validation
- **Text/Documentation** → Semantic/Episodic memory
- **Code** → Procedural memory
- **Task Data** → Episodic memory

## 🚨 Troubleshooting

### Service Not Ready
```bash
❌ InGest-LLM.as : unreachable - http://localhost:8000
```
**Solution**: Start the services:
```bash
# InGest-LLM.as
poetry run uvicorn src.ingest_llm_as.main:app --reload

# memOS.as  
cd ../memos.as && uvicorn app.main:app --port 8091 --reload
```

### Test Failures
For detailed debugging:
```bash
pytest tests/test_memos_integration_core.py -v -s --tb=long
```

## 📊 Success Criteria

✅ **All tests pass** - Integration is working correctly  
✅ **Services communicate** - HTTP requests succeed  
✅ **Data flows properly** - Content ingested and stored  
✅ **Memory tiers correct** - Content in appropriate tiers  
✅ **Search works** - Ingested content discoverable  
✅ **Concurrent handling** - Multiple requests processed

## 🔄 CI/CD Integration

This test suite can be integrated into CI/CD pipelines:

```yaml
# Example GitHub Actions step
- name: Run Core Integration Tests
  run: |
    docker-compose up -d
    sleep 30
    python scripts/run_core_integration_tests.py
```

## 📚 Related Documentation

- [InGest-LLM.as API Documentation](../README.md)
- [memOS.as Integration Guide](../../memos.as/README.md)
- [ApexSigma Architecture](../../CLAUDE.md)