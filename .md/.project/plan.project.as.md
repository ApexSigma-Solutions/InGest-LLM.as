```markdown
# Development Plan: InGest-LLM.as

This document provides a granular breakdown of the development tasks for the InGest-LLM.as microservice, which is responsible for all data acquisition, parsing, and preparation for storage.

## Milestone 1: Foundational Ingestion Pipeline

This milestone focuses on bootstrapping the service and implementing the first data source parser.

### Task: Bootstrap InGest-LLM.as Service

-   **Objective:** To create the initial project structure.
-   **Sub-Tasks:**
    -   • **Scaffold:** Run `gemini -c scaffold service "InGest-LLM"` to generate the boilerplate FastAPI app, Dockerfile, and initial documentation.
    -   • **Repository:** Create the `InGest-LLM.as` repository on GitHub and push the initial scaffold.

### Task: Set Up Docker Configuration

-   **Objective:** To containerize the service and integrate it into the main ecosystem.
-   **Sub-Tasks:**
    -   • **Dockerfile:** Review and finalize the generated Dockerfile.
    -   • **Docker Compose:** Add the `ingest-llm.as` service to the primary `docker-compose.yml` file, ensuring it shares the same network as `memos.as` for direct API communication.

### Task: Integrate Local Embedding Model

-   **Objective:** To create a self-contained embedding capability.
-   **Sub-Tasks:**
    -   • **Model Selection:** Research and select a suitable `sentence-transformer` model from Hugging Face, optimized for code and text.
    -   • **Service:** Create `app/services/embedding_client.py` to handle loading the model on startup and providing a simple `generate_embedding(text)` function.

### Task: Develop Python Codebase Parser

-   **Objective:** To extract meaningful information from Python source files.
-   **Sub-Tasks:**
    -   • **AST Parser:** Create `app/parsers/python_ast_parser.py`.
    -   • **Logic:** Implement a function that uses Python's built-in `ast` module to traverse a source file and extract function names, arguments, return types, and complete docstrings.
    -   • **Output:** The parser must return a structured list of JSON objects, each representing a single function or class.

### Task: Create the Core Ingestion Pipeline

-   **Objective:** To orchestrate the parsing, embedding, and storage process.
-   **Sub-Tasks:**
    -   • **Endpoint:** Create a `POST /ingest/python-repo` endpoint that accepts a path to a local git repository.
    -   **Orchestration Logic:**
        1.  Iterate through all `.py` files in the provided repository path.
        2.  For each file, call the `python_ast_parser`.
        3.  For each extracted function/class, call the `embedding_client` to generate a vector from its docstring.
        4.  Make a `POST` request to the `memos.as/memory/store` endpoint, sending the structured JSON and the generated embedding.

## Milestone 2: Command Suite & Expanded Sources

This milestone focuses on making ingestion user-driven and expanding the types of data the service can handle.

### Task: Develop Web Scraper Parser

-   **Objective:** To ingest knowledge from web pages.
-   **Sub-Tasks:**
    -   • **Dependencies:** Add `beautifulsoup4` and `httpx` to `requirements.txt`.
    -   • **Parser:** Create `app/parsers/web_parser.py`.
    -   • **Logic:** Implement a function `parse_url(url)` that fetches the page content, uses BeautifulSoup to extract the main article text (stripping out navigation, ads, etc.), and returns it as cleaned text.
    -   • **Endpoint:** Create a `POST /ingest/url` endpoint that accepts a URL and orchestrates the web scraping pipeline.

### Task: Develop Git Repository Parser

-   **Objective:** To analyze and index entire git repositories, not just Python files.
-   **Sub-Tasks:**
    -   • **Dependency:** Add the `GitPython` library to `requirements.txt`.
    -   • **Parser:** Create `app/parsers/git_parser.py`.
    -   • **Logic:** Implement a function that can clone a remote repository, iterate through every file, and route each file to the appropriate parser based on its extension (e.g., `.py` to the AST parser, `.md` to a text parser).

```