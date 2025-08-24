# ApexSigma Ecosystem - Prioritized Task List

Here are the immediate development priorities, starting with the most critical tasks required to unblock the ecosystem.

## 🚨 Critical Priorities

- [ ] **Refactor AgentRegistry and AgentPersona**
  
    - **Project**: DevEnviro.as
    - **Description**: Relocate the AgentPersona class to the central `schemas.py` file, update all imports, and refactor the AgentRegistry to be the single source of truth for live agent objects. This will fix a core architectural flaw.

- [ ] **Integrate Gemini CLI Listener**
  
    - **Project**: DevEnviro.as
    - **Description**: Integrate the `gemini_cli_listener.py` script into the Docker Compose setup to run as a persistent service. The goal is to verify the full, bi-directional communication loop between RabbitMQ and the Gemini CLI.

- [ ] **Integrate and Test 'Sigma Coder' Agent**
  
    - **Project**: DevEnviro.as
    - **Description**: Integrate the newly selected GGUF models (Qwen3-6B and Qwen2-1.5B) and apply the optimized configurations. The main task is to develop the application-side logic to parse the model's `<tool_call>` output, execute the corresponding functions, and return the results.

## 🚀 High Priorities

- [ ] **Implement GitHub Actions and Branch Protection**
  
    - **Project**: Ecosystem-Wide
    - **Description**: Implement the `pull_request_check.yml` workflow in all repositories and configure branch protection rules on the `main` and `alpha` branches to require all checks (lint, test, build) to pass before merging.

- [ ] **Implement Specific Graph API Endpoints**
  
    - **Project**: memOS.as
    - **Description**: Begin development on the API endpoints for the Neo4j knowledge graph, focusing on the three specified high-value queries: `/graph/related`, `/graph/shortest-path`, and `/graph/subgraph`.
