```markdown
# Strategy Doc: POML-Based Agent Context Generation

ID: poml.strategy.as.md

Status: Adopted
Date: 2025-08-18

## 1. Overview

This document outlines the strategic shift from static, manually created JSON context files to a dynamic, automated prompt generation system using **POML (Prompt Orchestration Markup Language)**. This new direction for the `InGest-LLM.as` microservice will significantly enhance the efficiency, accuracy, and scalability of how we provide context to our AI agents.

## 2. The Core Concept

The fundamental idea is to treat agent context not as a static data file, but as a **dynamic artifact that is generated on-demand** from our single source of truth—the Master Knowledge Graph.

POML serves as the templating engine for this process. It allows us to define a library of reusable prompt components that can be programmatically assembled and populated with real-time data.

## 3. Key Benefits

This approach provides several major advantages over our current method:

-   **Automation & Accuracy**: Context bullets will be generated automatically by `InGest-LLM.as`. This eliminates the need for manual updates and ensures that agents **always receive the absolute latest information** from the Master Knowledge Graph.
-   **Modularity & Maintainability**: By breaking our prompts into reusable components (e.g., `mission_brief.poml`, `project_status.poml`), we make our prompt library much easier to manage. A change to one component is instantly reflected everywhere it's used.
-   **Efficiency & Effectiveness**: POML allows for conditional logic. We can create smarter prompts that, for example, **omit the "Critical Blocker" section if no blocker exists**. This saves valuable tokens and focuses the agent's attention on what is most important for the current task.

## 4. Implementation Plan

To bring this strategy to life, we will add a new high-priority task to the `InGest-LLM.as` project plan.

**New Task: "Prototype a POML-based Context Generator"**

1.  **Create a `prompts/` Directory**: This will house our library of reusable `.poml` components.
2.  **Develop Initial Components**: Create the first set of modular templates based on our current `ingest.as.json` format.
3.  **Build the Generator Script**: Create a Python script within `InGest-LLM.as` that:
    -   Fetches the latest Master Knowledge Graph.
    -   Extracts the relevant data (project statuses, blockers, etc.).
    -   Uses a POML rendering engine to populate the templates with this data.
    -   Outputs the final, token-efficient context bullet.

This new direction represents a significant step forward in building a more robust and intelligent "Society of Agents."

```