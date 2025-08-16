# InGest-LLM.as

A microservice for ingesting data into the ApexSigma ecosystem.

## Development

```bash
poetry install
poetry run uvicorn src.ingest_llm_as.main:app --reload
```

## Docker

```bash
docker build -t ingest-llm-as .
docker run -p 8000:8000 ingest-llm-as
```