"""Unit tests for Linear processor."""

import pytest
from src.ingest_llm_as.core.linear_processor import process_linear_issue


@pytest.mark.asyncio
async def test_process_linear_issue_success():
    """Test processing a valid Linear webhook payload."""
    payload = {
        "action": "create",
        "data": {
            "id": "TEST-001",
            "title": "Test Issue",
            "description": "Test description"
        }
    }
    
    result = await process_linear_issue(payload)
    
    assert result["id"] == "TEST-001"
    assert result["action"] == "create"
    assert result["status"] == "processed"


@pytest.mark.asyncio
async def test_process_linear_issue_missing_action():
    """Test processing payload without action."""
    payload = {
        "data": {
            "id": "TEST-001"
        }
    }
    
    with pytest.raises(ValueError, match="Invalid Linear webhook payload"):
        await process_linear_issue(payload)


@pytest.mark.asyncio
async def test_process_linear_issue_missing_id():
    """Test processing payload without issue ID."""
    payload = {
        "action": "create",
        "data": {}
    }
    
    with pytest.raises(ValueError, match="Invalid Linear webhook payload"):
        await process_linear_issue(payload)


@pytest.mark.asyncio
async def test_process_linear_issue_missing_data():
    """Test processing payload without data section."""
    payload = {
        "action": "create"
    }
    
    with pytest.raises(ValueError, match="Invalid Linear webhook payload"):
        await process_linear_issue(payload)
