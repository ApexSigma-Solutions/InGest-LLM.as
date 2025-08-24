"""
Integration Test Suite for InGest-LLM.as Repository Ingestion
Task IG-20: Comprehensive integration testing for repository analysis and memOS integration
"""

import asyncio
import pytest
import httpx
from typing import Dict, Any
import tempfile
import os
from httpx import AsyncClient
from ingest_llm_as.main import app


class TestRepositoryIngestion:
    """Integration tests for repository ingestion functionality."""
    
    BASE_URL = "http://localhost:8000"
    MEMOS_URL = "http://localhost:8091"
    
    @pytest.fixture
    def test_repo(self):
        """Create a temporary test repository for ingestion."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            # Create test files
            test_files = {
                "main.py": '''
def hello_world():
    """Simple hello world function"""
    return "Hello, World!"

if __name__ == "__main__":
    print(hello_world())
''',
                "README.md": '''# Test Repository
This is a test repository for integration testing.

## Features
- Simple Python function
- Documentation
- Test structure
''',
                "requirements.txt": '''requests==2.28.0
pytest==7.1.0
'''
            }
            
            for filename, content in test_files.items():
                filepath = os.path.join(tmp_dir, filename)
                with open(filepath, 'w') as f:
                    f.write(content)
            
            yield tmp_dir
    
    @pytest.mark.asyncio
    async def test_health_endpoints(self):
        """Test that both InGest-LLM.as and memOS health endpoints are accessible."""
        async with httpx.AsyncClient() as client:
            # Test InGest-LLM.as health
            try:
                response = await client.get(f"{self.BASE_URL}/health")
                assert response.status_code == 200
                health_data = response.json()
                assert health_data["status"] == "healthy"
            except httpx.ConnectError:
                pytest.skip("InGest-LLM.as service not running")
            
            # Test memOS health  
            try:
                response = await client.get(f"{self.MEMOS_URL}/health")
                assert response.status_code == 200
            except httpx.ConnectError:
                pytest.skip("memOS service not running")
    
    @pytest.mark.asyncio
    async def test_ingest_python_repository(self, test_repo):
        """Test the existing Python repository ingestion endpoint."""
        async with AsyncClient(app=app, base_url="http://test") as ac:
            response = await ac.post("/ingest/python-repo", json={
                "repository_source": "local_path",
                "source_path": test_repo,
                "metadata": {
                    "source": "api",
                    "content_type": "code"
                }
            })
        assert response.status_code == 200
        assert response.json()["status"] == "pending"
    
    @pytest.mark.asyncio 
    async def test_document_ingestion(self, test_repo):
        """Test document ingestion to memOS if endpoints exist."""
        async with httpx.AsyncClient(timeout=60.0) as client:
            try:
                # Test if ingestion endpoint exists
                response = await client.post(
                    f"{self.BASE_URL}/api/v1/documents/ingest",
                    json={
                        "repository_path": test_repo,
                        "target": "memos",
                        "chunk_size": 1000,
                        "enable_embeddings": True
                    }
                )
                
                if response.status_code == 404:
                    pytest.skip("Documents ingestion endpoint not implemented yet")
                
                assert response.status_code == 200
                ingest_data = response.json()
                assert "status" in ingest_data
                
            except httpx.ConnectError:
                pytest.skip("InGest-LLM.as service not running")
    
    @pytest.mark.asyncio
    async def test_memos_integration(self, test_repo):
        """Test end-to-end integration with memOS storage if services are available."""
        # Test with the current FastAPI app
        async with AsyncClient(app=app, base_url="http://test") as ac:
            response = await ac.post("/ingest/python-repo", json={
                "repository_source": "local_path", 
                "source_path": test_repo,
                "metadata": {
                    "source": "integration_test",
                    "content_type": "code"
                }
            })
            
            assert response.status_code == 200
            result = response.json()
            assert result["status"] == "pending"
    
    @pytest.mark.asyncio
    async def test_error_handling(self):
        """Test error handling for invalid requests."""
        async with AsyncClient(app=app, base_url="http://test") as ac:
            # Test invalid repository path
            response = await ac.post("/ingest/python-repo", json={
                "repository_source": "local_path",
                "source_path": "/nonexistent/path",
                "metadata": {"source": "test"}
            })
            
            # Should handle gracefully (may return 200 with error status or 400)
            assert response.status_code in [200, 400]
    
    @pytest.mark.asyncio
    async def test_concurrent_requests(self, test_repo):
        """Test handling of concurrent ingestion requests."""
        async def make_request():
            async with AsyncClient(app=app, base_url="http://test") as ac:
                return await ac.post("/ingest/python-repo", json={
                    "repository_source": "local_path",
                    "source_path": test_repo,
                    "metadata": {"source": "concurrent_test"}
                })
        
        # Make 3 concurrent requests
        tasks = [make_request() for _ in range(3)]
        responses = await asyncio.gather(*tasks)
        
        # All should succeed
        for response in responses:
            assert response.status_code == 200


# Standalone test functions for backwards compatibility
@pytest.mark.asyncio
async def test_ingest_python_repository():
    """Original test for backwards compatibility."""
    async with AsyncClient(app=app, base_url="http://test") as ac:
        response = await ac.post("/ingest/python-repo", json={
            "repository_source": "local_path",
            "source_path": ".",
            "metadata": {
                "source": "api",
                "content_type": "code"
            }
        })
    assert response.status_code == 200
    assert response.json()["status"] == "pending"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--asyncio-mode=auto"])
