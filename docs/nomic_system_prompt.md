# Nomic Embedding Model System Configuration

## Model Information
- **Model**: `nomic-embed-code-i1`
- **Type**: Code Embedding Model (not chat/completion)
- **Purpose**: Generate semantic embeddings for code analysis
- **Endpoint**: `http://172.22.144.1:12345/v1/embeddings`

## System Prompt for LM Studio Configuration

Since `nomic-embed-code-i1` is an embedding model, it doesn't use traditional system prompts. However, here are the optimal settings for LM Studio:

### LM Studio Configuration

```json
{
  "model": "nomic-embed-code-i1",
  "max_tokens": 8192,
  "temperature": 0.0,
  "top_p": 1.0,
  "embedding_dimension": 768,
  "normalize_embeddings": true,
  "input_type": "search_document"
}
```

### Usage Instructions

#### 1. Basic Embedding Generation
```python
import httpx
import asyncio

async def generate_embedding(code_text):
    async with httpx.AsyncClient() as client:
        response = await client.post(
            "http://172.22.144.1:12345/v1/embeddings",
            json={
                "model": "nomic-embed-code-i1",
                "input": code_text,
                "encoding_format": "float"
            }
        )
        
        if response.status_code == 200:
            result = response.json()
            return result["data"][0]["embedding"]
        return None
```

#### 2. Code Analysis Prompt Format
When analyzing code for embedding generation, structure the input like this:

```
# Project Context
Project: {project_name}
Language: Python
Architecture: {architecture_type}

# Code Content
{actual_code_content}

# Metadata
File: {file_path}
Purpose: {component_purpose}
Dependencies: {key_dependencies}
```

#### 3. Semantic Analysis Guidelines
For optimal code embeddings:

- **Include context**: Add project name and architecture type
- **Preserve structure**: Keep original indentation and formatting
- **Add metadata**: Include file paths and component purposes
- **Limit size**: Keep inputs under 8,000 characters
- **Normalize inputs**: Use consistent formatting across similar code types

## ApexSigma-Specific Configuration

### Project Analysis Prompts

#### For FastAPI Services (InGest-LLM.as)
```
# ApexSigma Microservice - Data Ingestion
Project: InGest-LLM.as
Type: FastAPI Microservice
Purpose: Repository processing and embedding generation

{code_content}

Components: API endpoints, data models, ingestion services
Integration: memOS.as (storage), devenviro.as (orchestration)
```

#### For Memory Systems (memos.as)
```
# ApexSigma Memory System
Project: memos.as
Type: Memory Operating System
Purpose: Multi-tiered knowledge storage and retrieval

{code_content}

Components: Redis cache, PostgreSQL storage, Neo4j graphs
Integration: InGest-LLM.as (data flow), devenviro.as (queries)
```

#### For Orchestrators (devenviro.as)
```
# ApexSigma Agent Orchestrator
Project: devenviro.as
Type: Task Orchestration System
Purpose: Agent coordination and workflow management

{code_content}

Components: Task managers, agent coordinators, workflow engines
Integration: tools.as (utilities), memos.as (memory), InGest-LLM.as (data)
```

#### For Development Tools (tools.as)
```
# ApexSigma Development Toolkit
Project: tools.as
Type: Development Utilities
Purpose: CLI tools, build systems, automation scripts

{code_content}

Components: CLI commands, build scripts, automation tools
Integration: All projects (supporting infrastructure)
```

## Analysis Strategies

### 1. Component Classification
Use embeddings to classify code components:
- **API Modules**: FastAPI routes, endpoint handlers
- **Data Models**: Pydantic models, database schemas
- **Service Classes**: Business logic, processing services
- **Configuration**: Settings, environment management
- **Utilities**: Helper functions, common tools

### 2. Similarity Analysis
Calculate project similarities using cosine similarity:
- **High similarity (>0.8)**: Shared patterns, similar architecture
- **Medium similarity (0.5-0.8)**: Related functionality, complementary services
- **Low similarity (<0.5)**: Different purposes, distinct patterns

### 3. Architectural Pattern Detection
Identify patterns through embedding clusters:
- **Microservice patterns**: REST APIs, service boundaries
- **Data flow patterns**: ETL pipelines, processing chains
- **Integration patterns**: Database access, external APIs
- **Utility patterns**: Helper functions, shared libraries

## Expected Outputs

### Embedding Dimensions
- **Vector size**: 768 dimensions
- **Value range**: Typically [-1, 1] (normalized)
- **Similarity calculation**: Cosine similarity for comparison

### Analysis Results
1. **Project Descriptions**: AI-generated summaries based on code patterns
2. **Similarity Matrix**: Cross-project similarity scores
3. **Component Classification**: Automated categorization of code modules
4. **Integration Insights**: Detected relationships between services

## Testing Commands

Once LM Studio is running with `nomic-embed-code-i1`:

```bash
# Test basic functionality
python test_nomic_embeddings.py

# Generate project documentation
python scripts/generate_embedding_docs.py --project InGest-LLM.as

# Analyze all projects
python scripts/generate_embedding_docs.py --all

# Generate with custom output
python scripts/generate_embedding_docs.py --all --output ./embeddings_analysis
```

## Integration with Existing Systems

### 1. Update existing project analyzer
Replace Qwen chat completions with Nomic embeddings in:
- `src/ingest_llm_as/services/project_analyzer.py`

### 2. Modify documentation generator
Update to use embedding-based analysis:
- `src/ingest_llm_as/services/project_documentation_generator.py`

### 3. Adapt API endpoints
Modify REST endpoints to serve embedding analysis:
- Add `/embeddings/similarity` endpoint
- Add `/embeddings/projects/{name}` endpoint
- Add `/embeddings/ecosystem` endpoint

## Performance Considerations

- **Batch processing**: Generate embeddings for multiple files in parallel
- **Caching**: Store embeddings to avoid regeneration
- **Chunking**: Split large files into manageable segments
- **Filtering**: Skip binary files, very large files, generated code

This configuration provides a complete framework for using the Nomic embedding model with your ApexSigma ecosystem analysis system.