"""
Nomic Code Analyzer Service

This service uses the nomic-embed-code-i1 model to generate embeddings
for code analysis and similarity matching across ApexSigma projects.
"""

import httpx
import numpy as np
from typing import Dict, List, Any, Optional
from dataclasses import dataclass
from pathlib import Path

from ..observability.logging import get_logger

logger = get_logger(__name__)


@dataclass
class CodeEmbedding:
    """Code embedding with metadata."""

    file_path: str
    content_hash: str
    embedding: List[float]
    content_type: str  # "function", "class", "module", "config"
    project_name: str
    metadata: Dict[str, Any]


@dataclass
class ProjectAnalysis:
    """Project analysis based on code embeddings."""

    project_name: str
    description: str
    architecture_type: str
    core_components: List[Dict[str, str]]
    api_patterns: List[str]
    dependencies: List[str]
    similarity_scores: Dict[str, float]  # Similarity to other projects


class NomicCodeAnalyzer:
    """
    Analyzes ApexSigma projects using Nomic code embeddings.

    Uses nomic-embed-code-i1 to generate semantic embeddings of code
    for similarity analysis and architectural pattern detection.
    """

    def __init__(self, base_url: str = "http://172.22.144.1:12345/v1"):
        """
        Create a NomicCodeAnalyzer configured to communicate with a Nomic embedding service.
        
        Parameters:
            base_url (str): Base URL of the embedding service API used to request embeddings (default: "http://172.22.144.1:12345/v1"). 
        
        Description:
            Initializes the instance-level resources used for analysis, including a logger, an asynchronous HTTP client, configured project paths, and an in-memory embeddings cache.
        """
        self.base_url = base_url
        self.logger = get_logger(__name__)
        self.client = httpx.AsyncClient(timeout=60.0)

        # Project paths
        self.base_path = Path("C:\\Users\\steyn\\ApexSigmaProjects.Dev")
        self.projects = {
            "InGest-LLM.as": self.base_path / "InGest-LLM.as",
            "memos.as": self.base_path / "memos.as",
            "devenviro.as": self.base_path / "devenviro.as",
            "tools.as": self.base_path / "tools.as",
        }

        # Embedding cache
        self.embeddings_cache: Dict[str, CodeEmbedding] = {}

    async def analyze_all_projects(self) -> Dict[str, ProjectAnalysis]:
        """
        Run embedding-based analysis for all configured ApexSigma projects.
        
        Iterates the analyzer's configured project paths, generates embeddings for each existing project, and produces a ProjectAnalysis for each project that yielded embeddings.
        
        Returns:
            Dict[str, ProjectAnalysis]: Mapping from project name to its analysis; projects with no embeddings are not included.
        """
        self.logger.info("Starting embedding-based project analysis")

        analyses = {}
        project_embeddings = {}

        # Generate embeddings for each project
        for project_name, project_path in self.projects.items():
            if project_path.exists():
                self.logger.info(f"Generating embeddings for {project_name}")
                embeddings = await self._generate_project_embeddings(
                    project_name, project_path
                )
                project_embeddings[project_name] = embeddings

        # Analyze each project based on embeddings
        for project_name, embeddings in project_embeddings.items():
            if embeddings:
                analysis = await self._analyze_project_from_embeddings(
                    project_name, embeddings, project_embeddings
                )
                analyses[project_name] = analysis

        return analyses

    async def _generate_project_embeddings(
        self, project_name: str, project_path: Path
    ) -> List[CodeEmbedding]:
        """
        Generate embeddings for representative code and key configuration files within a project.
        
        Scans the project's Python files (up to 20 files) and selected config files, reads their text (UTF-8, errors ignored), and produces a CodeEmbedding for each file that is processed. Files larger than 100 KB or with fewer than 50 non-whitespace characters are skipped; pyproject.toml, README.md, and docker-compose.yml are included when present and smaller than 50 KB. Each embedding includes a relative file path, a content hash, a content type, the originating project name, and metadata such as file size, line count, and simple presence flags (classes, functions, imports, is_main).
        
        Parameters:
            project_name (str): Name of the project to attribute to generated embeddings.
            project_path (Path): Filesystem path to the root of the project to scan.
        
        Returns:
            List[CodeEmbedding]: A list of generated CodeEmbedding objects for the files that were successfully processed.
        """

        embeddings = []

        # Find Python files
        python_files = list(project_path.glob("**/*.py"))

        for py_file in python_files[:20]:  # Limit to 20 files for performance
            if py_file.stat().st_size > 100000:  # Skip very large files
                continue

            try:
                content = py_file.read_text(encoding="utf-8", errors="ignore")

                # Skip empty or very small files
                if len(content.strip()) < 50:
                    continue

                # Generate embedding for the file
                embedding = await self._generate_embedding(content)

                if embedding:
                    code_embedding = CodeEmbedding(
                        file_path=str(py_file.relative_to(project_path)),
                        content_hash=str(hash(content)),
                        embedding=embedding,
                        content_type=self._classify_content_type(content),
                        project_name=project_name,
                        metadata={
                            "file_size": len(content),
                            "line_count": len(content.splitlines()),
                            "has_classes": "class " in content,
                            "has_functions": "def " in content,
                            "has_imports": "import " in content or "from " in content,
                            "is_main": py_file.name
                            in ["main.py", "app.py", "__init__.py"],
                        },
                    )
                    embeddings.append(code_embedding)

            except Exception as e:
                self.logger.warning(f"Could not process {py_file}: {e}")

        # Also analyze key configuration files
        for config_file in ["pyproject.toml", "README.md", "docker-compose.yml"]:
            config_path = project_path / config_file
            if config_path.exists() and config_path.stat().st_size < 50000:
                try:
                    content = config_path.read_text(encoding="utf-8", errors="ignore")
                    embedding = await self._generate_embedding(content)

                    if embedding:
                        code_embedding = CodeEmbedding(
                            file_path=config_file,
                            content_hash=str(hash(content)),
                            embedding=embedding,
                            content_type="config",
                            project_name=project_name,
                            metadata={
                                "file_type": config_path.suffix,
                                "file_size": len(content),
                            },
                        )
                        embeddings.append(code_embedding)

                except Exception as e:
                    self.logger.warning(f"Could not process {config_path}: {e}")

        self.logger.info(f"Generated {len(embeddings)} embeddings for {project_name}")
        return embeddings

    async def _generate_embedding(self, content: str) -> Optional[List[float]]:
        """
        Request an embedding for the given code/text content using the Nomic `nomic-embed-code-i1` model.
        
        Parameters:
            content (str): The text or code to embed. Content longer than 8000 characters will be truncated.
        
        Returns:
            Optional[List[float]]: The embedding vector as a list of floats if successful, `None` on failure or error.
        """

        try:
            # Truncate content if too long (Nomic models have token limits)
            if len(content) > 8000:
                content = content[:8000] + "..."

            response = await self.client.post(
                f"{self.base_url}/embeddings",
                json={
                    "model": "nomic-embed-code-i1",
                    "input": content,
                    "encoding_format": "float",
                },
                headers={"Content-Type": "application/json"},
            )

            if response.status_code == 200:
                result = response.json()
                if "data" in result and len(result["data"]) > 0:
                    return result["data"][0]["embedding"]
            else:
                self.logger.error(
                    f"Embedding API error: {response.status_code} - {response.text}"
                )

        except Exception as e:
            self.logger.error(f"Error generating embedding: {e}")

        return None

    def _classify_content_type(self, content: str) -> str:
        """
        Classifies a block of code into a concise content-type label based on simple heuristics.
        
        Parameters:
            content (str): The source text of a code file or fragment to classify.
        
        Returns:
            content_type (str): One of:
                - "class_module": contains both class and function definitions
                - "main_module": contains functions and an application entry point (`if __name__`)
                - "api_module": contains web/API indicators (e.g., `@app.route`, `@router.`, or `fastapi`)
                - "class_definition": contains class definitions but no functions
                - "function_module": contains function definitions but no classes
                - "utility_module": contains imports and is short (fewer than 50 lines)
                - "general_module": none of the above heuristics matched
        """

        content_lower = content.lower()

        if "class " in content and "def " in content:
            return "class_module"
        elif "def " in content and "if __name__" in content:
            return "main_module"
        elif (
            "@app.route" in content
            or "@router." in content
            or "fastapi" in content_lower
        ):
            return "api_module"
        elif "class " in content:
            return "class_definition"
        elif "def " in content:
            return "function_module"
        elif "import " in content and len(content.splitlines()) < 50:
            return "utility_module"
        else:
            return "general_module"

    async def _analyze_project_from_embeddings(
        self,
        project_name: str,
        embeddings: List[CodeEmbedding],
        all_project_embeddings: Dict[str, List[CodeEmbedding]],
    ) -> ProjectAnalysis:
        """
        Produce a ProjectAnalysis summarizing a project's structure, detected patterns, inferred architecture, core components, dependencies, and similarity scores against other projects.
        
        Parameters:
            project_name (str): Name of the project being analyzed.
            embeddings (List[CodeEmbedding]): Embedding records for files in the project; used to infer content types, metadata flags, and build core components.
            all_project_embeddings (Dict[str, List[CodeEmbedding]]): Embeddings for other projects used to compute pairwise similarity scores.
        
        Returns:
            ProjectAnalysis: Analysis containing the project's name, a short description, inferred architecture_type (e.g., "microservice", "monolith", "library", "tool"), a list of up to five core_components (each with name, type, and short description), detected api_patterns, inferred dependencies, and similarity_scores mapping other project names to cosine similarity values.
        """

        # Calculate similarity scores with other projects
        similarity_scores = {}
        for other_project, other_embeddings in all_project_embeddings.items():
            if other_project != project_name and other_embeddings:
                similarity = self._calculate_project_similarity(
                    embeddings, other_embeddings
                )
                similarity_scores[other_project] = similarity

        # Analyze content types and patterns
        content_types = [emb.content_type for emb in embeddings]
        api_patterns = []

        # Detect API patterns
        if any("api" in ct for ct in content_types):
            api_patterns.append("REST API")
        if any(emb.metadata.get("has_classes") for emb in embeddings):
            api_patterns.append("Object-Oriented Design")
        if any("main" in ct for ct in content_types):
            api_patterns.append("Application Entry Point")

        # Determine architecture type based on patterns
        if "api_module" in content_types:
            architecture_type = "microservice"
        elif len(embeddings) > 15:
            architecture_type = "monolith"
        elif any("utility" in ct for ct in content_types):
            architecture_type = "library"
        else:
            architecture_type = "tool"

        # Extract core components
        core_components = []
        for emb in embeddings:
            if emb.content_type in ["api_module", "class_module", "main_module"]:
                core_components.append(
                    {
                        "name": emb.file_path.replace(".py", "").replace("/", "."),
                        "type": emb.content_type,
                        "description": f"{emb.content_type.replace('_', ' ').title()} with {emb.metadata.get('line_count', 0)} lines",
                    }
                )

        # Generate description based on analysis
        description = self._generate_project_description(
            project_name, embeddings, content_types
        )

        # Extract dependencies (simplified)
        dependencies = []
        for emb in embeddings:
            if emb.content_type == "config" and "pyproject.toml" in emb.file_path:
                dependencies.extend(["Poetry", "Python 3.x"])
            elif emb.metadata.get("has_imports"):
                dependencies.append("External Python packages")

        return ProjectAnalysis(
            project_name=project_name,
            description=description,
            architecture_type=architecture_type,
            core_components=core_components[:5],  # Limit to top 5
            api_patterns=api_patterns,
            dependencies=dependencies,
            similarity_scores=similarity_scores,
        )

    def _calculate_project_similarity(
        self, embeddings1: List[CodeEmbedding], embeddings2: List[CodeEmbedding]
    ) -> float:
        """
        Compute a cosine similarity score between two projects by averaging their code embeddings.
        
        Returns:
            similarity (float): Cosine similarity in the range -1.0 to 1.0; returns 0.0 if either embedding list is empty or if either averaged embedding has zero magnitude.
        """

        if not embeddings1 or not embeddings2:
            return 0.0

        # Calculate average embedding for each project
        avg_emb1 = np.mean([emb.embedding for emb in embeddings1], axis=0)
        avg_emb2 = np.mean([emb.embedding for emb in embeddings2], axis=0)

        # Calculate cosine similarity
        dot_product = np.dot(avg_emb1, avg_emb2)
        norm1 = np.linalg.norm(avg_emb1)
        norm2 = np.linalg.norm(avg_emb2)

        if norm1 == 0 or norm2 == 0:
            return 0.0

        similarity = dot_product / (norm1 * norm2)
        return float(similarity)

    def _generate_project_description(
        self,
        project_name: str,
        embeddings: List[CodeEmbedding],
        content_types: List[str],
    ) -> str:
        """
        Create a short, human-readable description of a project derived from its code embeddings and classified content types.
        
        Parameters:
            project_name (str): The project's name used for context in description (not required to be unique).
            embeddings (List[CodeEmbedding]): Embedding records for the project's files; used to infer file counts and metadata flags (e.g., presence of classes).
            content_types (List[str]): Classified content type labels for the project's files (e.g., "api_module", "class_module", "main_module").
        
        Returns:
            str: A concise description summarizing the project's size and prominent characteristics (for example: API presence, object-oriented design, entry point, or lightweight tool).
        """

        # Count different types of content
        type_counts = {}
        for ct in content_types:
            type_counts[ct] = type_counts.get(ct, 0) + 1

        total_files = len(embeddings)
        has_api = "api_module" in content_types
        has_classes = any(emb.metadata.get("has_classes") for emb in embeddings)
        has_main = "main_module" in content_types

        if has_api and has_classes:
            return f"FastAPI-based microservice with {total_files} modules, featuring object-oriented design and REST API endpoints"
        elif has_main and total_files > 10:
            return f"Comprehensive Python application with {total_files} modules, including main entry point and modular architecture"
        elif has_classes and total_files > 5:
            return f"Object-oriented Python system with {total_files} modules, featuring class-based design patterns"
        elif total_files < 5:
            return f"Lightweight Python tool with {total_files} modules, focused on specific functionality"
        else:
            return f"Python-based system with {total_files} modules, providing structured functionality"

    async def generate_embedding_analysis_report(
        self, analyses: Dict[str, ProjectAnalysis]
    ) -> str:
        """
        Compose a Markdown report summarizing embedding-based analyses across projects.
        
        The report includes per-project summaries (type, description, core components count, API patterns), a pairwise project similarity matrix, and integration insights that identify the most similar project for each entry.
        
        Parameters:
            analyses (Dict[str, ProjectAnalysis]): Mapping from project name to its analysis result; each ProjectAnalysis supplies fields used to build summaries and similarity values.
        
        Returns:
            report (str): Markdown-formatted analysis report.
        """

        report = "# ApexSigma Ecosystem - Code Embedding Analysis\n\n"
        report += "**Analysis Method**: Nomic Code Embeddings (nomic-embed-code-i1)\n"
        report += f"**Projects Analyzed**: {len(analyses)}\n\n"

        # Project summaries
        report += "## Project Summaries\n\n"
        for project_name, analysis in analyses.items():
            report += f"### {project_name}\n"
            report += f"- **Type**: {analysis.architecture_type.title()}\n"
            report += f"- **Description**: {analysis.description}\n"
            report += f"- **Core Components**: {len(analysis.core_components)}\n"
            report += f"- **API Patterns**: {', '.join(analysis.api_patterns) if analysis.api_patterns else 'None detected'}\n\n"

        # Similarity matrix
        report += "## Project Similarity Matrix\n\n"
        report += "| Project | "
        for proj in analyses.keys():
            report += f"{proj} | "
        report += "\n|---------|"
        for _ in analyses.keys():
            report += "------|"
        report += "\n"

        for proj1, analysis in analyses.items():
            report += f"| **{proj1}** | "
            for proj2 in analyses.keys():
                if proj1 == proj2:
                    report += "- | "
                else:
                    similarity = analysis.similarity_scores.get(proj2, 0.0)
                    report += f"{similarity:.2f} | "
            report += "\n"

        # Integration insights
        report += "\n## Integration Insights\n\n"

        # Find most similar projects
        for proj1, analysis in analyses.items():
            if analysis.similarity_scores:
                most_similar = max(
                    analysis.similarity_scores.items(), key=lambda x: x[1]
                )
                report += f"- **{proj1}** is most similar to **{most_similar[0]}** (similarity: {most_similar[1]:.2f})\n"

        return report

    async def close(self):
        """
        Close the analyzer's internal HTTP client and release its resources.
        """
        await self.client.aclose()


# Global analyzer instance
_nomic_analyzer: Optional[NomicCodeAnalyzer] = None


def get_nomic_code_analyzer() -> NomicCodeAnalyzer:
    """
    Return the global NomicCodeAnalyzer singleton used by the module.
    
    Returns:
        NomicCodeAnalyzer: The shared analyzer instance; creates and caches a new instance if none exists.
    """
    global _nomic_analyzer
    if _nomic_analyzer is None:
        _nomic_analyzer = NomicCodeAnalyzer()
    return _nomic_analyzer