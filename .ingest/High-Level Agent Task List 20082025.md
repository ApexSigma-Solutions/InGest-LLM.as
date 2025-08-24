# ApexSigma Ecosystem - Agent Task Assignments

This plan assigns the immediate development priorities to the appropriate AI agents based on their specialized roles.

## 🤖 Claude Code (The Architect)

Your primary focus is on high-level architecture and complex refactoring.

  - **Refactor AgentRegistry and AgentPersona**
      - **Project**: DevEnviro.as
      - **Description**: Relocate the AgentPersona class to the central `schemas.py` file, update all imports, and refactor the `AgentRegistry` to be the single source of truth for live agent objects. This will fix a core architectural flaw.

## ⚙️ Gemini CLI (The Implementer)

Your role is to handle hands-on implementation, infrastructure configuration, and integration tasks.

  - **Integrate Gemini CLI Listener**
    
      - **Project**: DevEnviro.as
      - **Description**: Integrate the `gemini_cli_listener.py` script into the Docker Compose setup to run as a persistent service. The goal is to verify the full, bi-directional communication loop between RabbitMQ and the Gemini CLI.

  - **Integrate and Test 'Sigma Coder' Agent**
    
      - **Project**: DevEnviro.as
      - **Description**: Integrate the newly selected GGUF models (Qwen3-6B and Qwen2-1.5B) and apply the optimized configurations. The main task is to develop the application-side logic to parse the model's `<tool_call>` output, execute the corresponding functions, and return the results.

  - **Implement GitHub Actions and Branch Protection**
    
      - **Project**: Ecosystem-Wide
      - **Description**: Implement the `pull_request_check.yml` workflow in all repositories and configure branch protection rules on the `main` and `alpha` branches to require all checks (lint, test, build) to pass before merging.

  - **Implement Specific Graph API Endpoints**
    
      - **Project**: memOS.as
      - **Description**: Begin development on the API endpoints for the Neo4j knowledge graph, focusing on the three specified high-value queries: `/graph/related`, `/graph/shortest-path`, and `/graph/subgraph`.

## 助手 GitHub Co-Pilot (The Assistant)

Your role is to assist the Implementer (Gemini CLI) with code generation and boilerplate.

  - **Assist with 'Sigma Coder' Integration**: Help generate the Python logic for parsing the agent's tool calls and formatting the responses.
  - **Assist with Graph API Endpoints**: Help generate the boilerplate code for the new FastAPI endpoints in `memOS.as`, including request/response models and basic function structure.
