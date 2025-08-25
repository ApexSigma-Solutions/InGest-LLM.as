# API Reference

Welcome to the InGest-LLM.as API reference documentation. This section provides comprehensive documentation for all modules, classes, and functions in the data ingestion service.

## Overview

InGest-LLM.as is a FastAPI-based microservice designed for data ingestion within the ApexSigma ecosystem. The API is organized into key areas:

- **[Ingestion API](ingestion.md)** - Core data ingestion endpoints and repository processing
- **[Analysis API](analysis.md)** - Code analysis and project documentation generation  
- **[Services](services.md)** - Backend services including vectorizer and LLM clients
- **[Observability](observability.md)** - Telemetry, logging, and monitoring components

## Architecture

InGest-LLM.as serves as the data ingestion layer in the ApexSigma Society of Agents architecture:

- **FastAPI Application**: Modern async web framework with comprehensive validation
- **Integration Layer**: Seamless communication with memOS.as memory system
- **Observability**: Full OpenTelemetry instrumentation with Langfuse LLM monitoring
- **Processing Pipeline**: Advanced code parsing and content analysis

## Getting Started

For implementation details and usage examples, see the [How-To Guides](../how-to/index.md) and [Tutorials](../tutorials/index.md) sections.