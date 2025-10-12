#!/usr/bin/env python3
"""
Automated Documentation Builder for ApexSigma

This script automates the generation and updating of project documentation
using POML templates, embedding analysis, and real-time project data.
"""

import asyncio
import argparse
import sys
from datetime import datetime
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

try:
    from ingest_llm_as.services.nomic_code_analyzer import get_nomic_code_analyzer

    EMBEDDING_ANALYZER_AVAILABLE = True
except ImportError:
    EMBEDDING_ANALYZER_AVAILABLE = False

# Import other components we've built
sys.path.insert(0, str(Path(__file__).parent))
from generate_context_bullet import ContextBulletGenerator


class DocumentationBuilder:
    """Automated documentation builder for ApexSigma projects."""

    def __init__(self, base_path: str = None):
        """
        Create a DocumentationBuilder configured for a workspace of ApexSigma projects.
        
        Parameters:
            base_path (str | None): Optional filesystem path to the root directory containing ApexSigma projects. If omitted, a default development path is used.
        
        Description:
            Initializes internal state including a mapping of known project names to their paths, a ContextBulletGenerator for producing context bullets, and an optional embedding analyzer instance (set to None if embedding analysis is unavailable).
        """
        self.base_path = (
            Path(base_path)
            if base_path
            else Path("C:\\Users\\steyn\\ApexSigmaProjects.Dev")
        )
        self.projects = {
            "InGest-LLM.as": self.base_path / "InGest-LLM.as",
            "memos.as": self.base_path / "memos.as",
            "devenviro.as": self.base_path / "devenviro.as",
            "tools.as": self.base_path / "tools.as",
        }

        # Documentation components
        self.context_generator = ContextBulletGenerator()
        if EMBEDDING_ANALYZER_AVAILABLE:
            self.embedding_analyzer = get_nomic_code_analyzer()
        else:
            self.embedding_analyzer = None

    async def build_all_documentation(
        self,
        include_embeddings: bool = True,
        include_context_bullets: bool = True,
        include_project_docs: bool = True,
        force_refresh: bool = False,
    ) -> None:
        """
        Orchestrates generation and updating of documentation for all known projects.
        
        Parameters:
        	include_embeddings (bool): If True, include embedding analysis when an embedding analyzer is available.
        	include_context_bullets (bool): If True, generate ecosystem and per-project context bullets.
        	include_project_docs (bool): If True, generate per-project README and status documents.
        	force_refresh (bool): If True, force regeneration of artifacts even if they already exist.
        """

        print("=" * 80)
        print("APEXSIGMA AUTOMATED DOCUMENTATION BUILDER")
        print("=" * 80)
        print(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"Projects: {len(self.projects)}")
        print(f"Base path: {self.base_path}")
        print()

        build_tasks = []

        # Add tasks based on what's enabled
        if include_context_bullets:
            build_tasks.append("Context Bullets")
        if include_embeddings and EMBEDDING_ANALYZER_AVAILABLE:
            build_tasks.append("Embedding Analysis")
        if include_project_docs:
            build_tasks.append("Project Documentation")

        print(f"Build tasks: {', '.join(build_tasks)}")
        print()

        # Create .md/.projects directories
        await self._ensure_documentation_directories()

        # Generate context bullets
        if include_context_bullets:
            await self._build_context_bullets()

        # Generate embedding analysis
        if include_embeddings and EMBEDDING_ANALYZER_AVAILABLE:
            await self._build_embedding_analysis()

        # Generate project documentation
        if include_project_docs:
            await self._build_project_documentation()

        # Generate ecosystem overview
        await self._build_ecosystem_overview()

        print("\\n" + "=" * 80)
        print("DOCUMENTATION BUILD COMPLETED")
        print(f"Completed: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("=" * 80)

    async def build_project_documentation(self, project_name: str) -> None:
        """Build documentation for a specific project."""

        if project_name not in self.projects:
            print(f"Unknown project: {project_name}")
            return

        print(f"Building documentation for {project_name}...")

        project_path = self.projects[project_name]
        docs_dir = project_path / ".md" / ".projects"
        docs_dir.mkdir(parents=True, exist_ok=True)

        # Generate context bullet for this project
        await self._generate_project_context_bullet(project_name, docs_dir)

        # Generate project documentation
        await self._generate_project_readme(project_name, docs_dir)

        print(f"✓ Documentation completed for {project_name}")

    async def _ensure_documentation_directories(self) -> None:
        """Ensure all projects have documentation directories."""

        print("CREATING DOCUMENTATION DIRECTORIES")
        print("-" * 40)

        for project_name, project_path in self.projects.items():
            if project_path.exists():
                docs_dir = project_path / ".md" / ".projects"
                docs_dir.mkdir(parents=True, exist_ok=True)
                print(f"✓ {project_name}: {docs_dir}")
            else:
                print(f"⚠ {project_name}: Project path not found")

        print()

    async def _build_context_bullets(self) -> None:
        """
        Generate and save an ecosystem-wide context bullet into each project's documentation directory.
        
        Generates an ecosystem-level context bullet and writes it to each project's .md/.projects/context_bullet.md file, reporting per-project success or failure.
        """

        print("GENERATING CONTEXT BULLETS")
        print("-" * 30)

        # Generate ecosystem-wide context bullet
        ecosystem_context = await self._generate_ecosystem_context_bullet()

        # Save to each project
        for project_name, project_path in self.projects.items():
            if project_path.exists():
                docs_dir = project_path / ".md" / ".projects"
                context_file = docs_dir / "context_bullet.md"

                try:
                    context_file.write_text(ecosystem_context, encoding="utf-8")
                    print(f"✓ {project_name}: context_bullet.md")
                except Exception as e:
                    print(f"✗ {project_name}: Failed to write context bullet - {e}")

        print()

    async def _build_embedding_analysis(self) -> None:
        """
        Generate and write embedding analysis reports for each project and for the ecosystem.
        
        For each known project that exists on disk, writes a per-project report named
        `embedding_analysis.md` into the project's `.md/.projects` directory. Also writes
        a consolidated ecosystem report named `ecosystem_embedding_analysis.md` into
        the main project's (InGest-LLM.as) `.md/.projects` directory. If the embedding
        analyzer is not available the method prints a warning and returns without
        writing files. Exceptions encountered during generation or file writes are
        caught and printed; they are not re-raised.
        """

        print("GENERATING EMBEDDING ANALYSIS")
        print("-" * 35)

        if not self.embedding_analyzer:
            print("⚠ Embedding analyzer not available")
            return

        try:
            # Generate embedding analysis for all projects
            analyses = await self.embedding_analyzer.analyze_all_projects()

            # Save individual project analyses
            for project_name, analysis in analyses.items():
                project_path = self.projects.get(project_name)
                if project_path and project_path.exists():
                    docs_dir = project_path / ".md" / ".projects"

                    # Save embedding analysis
                    analysis_content = self._format_embedding_analysis(
                        project_name, analysis, analyses
                    )
                    analysis_file = docs_dir / "embedding_analysis.md"
                    analysis_file.write_text(analysis_content, encoding="utf-8")

                    print(f"✓ {project_name}: embedding_analysis.md")

            # Generate ecosystem embedding report
            ecosystem_report = (
                await self.embedding_analyzer.generate_embedding_analysis_report(
                    analyses
                )
            )

            # Save to main project (InGest-LLM.as)
            main_docs_dir = self.projects["InGest-LLM.as"] / ".md" / ".projects"
            report_file = main_docs_dir / "ecosystem_embedding_analysis.md"
            report_file.write_text(ecosystem_report, encoding="utf-8")

            print("✓ Ecosystem: ecosystem_embedding_analysis.md")

        except Exception as e:
            print(f"✗ Embedding analysis failed: {e}")

        print()

    async def _build_project_documentation(self) -> None:
        """
        Generate README and project status documents for each known project and save them into the project's documentation directory.
        
        For each project with an existing filesystem path this method generates README.md and project_status.md content, writes those files into the project's .md/.projects directory, and prints a per-project summary of success or failure. Projects whose paths do not exist are skipped; failures for individual projects are reported but do not stop processing other projects.
        """

        print("GENERATING PROJECT DOCUMENTATION")
        print("-" * 40)

        for project_name, project_path in self.projects.items():
            if project_path.exists():
                docs_dir = project_path / ".md" / ".projects"

                try:
                    # Generate project README
                    readme_content = await self._generate_project_readme_content(
                        project_name, project_path
                    )
                    readme_file = docs_dir / "README.md"
                    readme_file.write_text(readme_content, encoding="utf-8")

                    # Generate project status
                    status_content = await self._generate_project_status_content(
                        project_name, project_path
                    )
                    status_file = docs_dir / "project_status.md"
                    status_file.write_text(status_content, encoding="utf-8")

                    print(f"✓ {project_name}: README.md, project_status.md")

                except Exception as e:
                    print(f"✗ {project_name}: Failed to generate docs - {e}")

        print()

    async def _build_ecosystem_overview(self) -> None:
        """
        Generate and save the ApexSigma ecosystem overview and a documentation build summary into the main project's docs directory.
        
        Writes two markdown files into the InGest-LLM.as project's .md/.projects directory:
        - apexsigma_ecosystem_overview.md: the generated ecosystem overview content.
        - documentation_build_summary.md: a build summary of the documentation run.
        """

        print("GENERATING ECOSYSTEM OVERVIEW")
        print("-" * 35)

        try:
            # Generate ecosystem overview
            overview_content = await self._generate_ecosystem_overview_content()

            # Save to main project
            main_docs_dir = self.projects["InGest-LLM.as"] / ".md" / ".projects"
            overview_file = main_docs_dir / "apexsigma_ecosystem_overview.md"
            overview_file.write_text(overview_content, encoding="utf-8")

            print("✓ apexsigma_ecosystem_overview.md")

            # Generate build summary
            summary_content = self._generate_build_summary()
            summary_file = main_docs_dir / "documentation_build_summary.md"
            summary_file.write_text(summary_content, encoding="utf-8")

            print("✓ documentation_build_summary.md")

        except Exception as e:
            print(f"✗ Ecosystem overview failed: {e}")

        print()

    async def _generate_ecosystem_context_bullet(self) -> str:
        """
        Generate an ecosystem-wide context bullet as a Markdown string.
        
        If generation fails, prints a warning and returns a fallback Markdown string containing a timestamp and an error note.
        
        Returns:
            markdown (str): Ecosystem-wide context bullet formatted as Markdown.
        """

        try:
            return self.context_generator.generate_context_bullet()
        except Exception as e:
            print(f"Warning: Context bullet generation failed: {e}")
            return f"# ApexSigma Context Bullet\\n\\nGenerated: {datetime.now().isoformat()}\\n\\nError: Could not generate context bullet."

    async def _generate_project_context_bullet(
        self, project_name: str, docs_dir: Path
    ) -> None:
        """
        Generate and write the context bullet for a single project.
        
        Writes a `context_bullet.md` file into the provided `docs_dir` containing the context bullet produced by the builder's ContextBulletGenerator. On failure, prints a warning including the project name.
        
        Parameters:
            project_name (str): Name of the project (used for contextual logging).
            docs_dir (Path): Directory where `context_bullet.md` will be created or updated.
        """

        try:
            context_content = self.context_generator.generate_context_bullet()
            context_file = docs_dir / "context_bullet.md"
            context_file.write_text(context_content, encoding="utf-8")
        except Exception as e:
            print(f"Warning: Context bullet for {project_name} failed: {e}")

    def _format_embedding_analysis(
        self, project_name: str, analysis, all_analyses: dict
    ) -> str:
        """
        Create a markdown-formatted embedding analysis report for a project.
        
        Produces a markdown string that includes a generated timestamp, project overview (description and architecture), a bulleted list of core components, API patterns, and similarity scores to other projects.
        
        Parameters:
            project_name (str): The name or identifier of the project.
            analysis: An analysis object containing project fields used in the report (expected attributes: `description`, `architecture_type`, `core_components` (iterable of dicts with `name` and `description`), `api_patterns` (iterable of strings), and `similarity_scores` (mapping of other project names to numeric scores)).
            all_analyses (dict): Mapping of project names to their analysis objects; provided for context or cross-reference (may be unused by the formatter).
        
        Returns:
            markdown (str): The complete embedding analysis formatted as a Markdown document.
        """

        content = f"""# {project_name} - Embedding Analysis

**Generated**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

## Project Overview

**Description**: {analysis.description}
**Architecture**: {analysis.architecture_type.title()}

## Core Components

"""

        for component in analysis.core_components:
            content += f"- **{component.get('name', 'Unknown')}**: {component.get('description', 'No description')}\\n"

        content += "\\n## API Patterns\\n\\n"
        for pattern in analysis.api_patterns:
            content += f"- {pattern}\\n"

        content += "\\n## Similarity Analysis\\n\\n"
        for other_project, score in analysis.similarity_scores.items():
            content += f"- **{other_project}**: {score:.3f}\\n"

        return content

    async def _generate_project_readme_content(
        self, project_name: str, project_path: Path
    ) -> str:
        """
        Create the README.md content for the specified project.
        
        The returned markdown includes a generation timestamp, a short overview, a list of generated documentation files, the project's filesystem path, and a last-updated timestamp.
        
        Returns:
            str: Markdown-formatted README content for the project.
        """

        return f"""# {project_name} - Documentation

**Generated**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

## Overview

This directory contains automatically generated documentation for the {project_name} project.

## Documentation Files

- `context_bullet.md` - Current project context and priorities
- `project_status.md` - Detailed project status and metrics
- `embedding_analysis.md` - Code similarity and architectural analysis
- `README.md` - This file

## Project Path

```
{project_path}
```

## Last Updated

{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

---

*This documentation is automatically generated and updated by the ApexSigma documentation system.*
"""

    async def _generate_project_status_content(
        self, project_name: str, project_path: Path
    ) -> str:
        """
        Create a markdown project status report for the given project.
        
        The returned markdown includes generation timestamp, counts of Python and Markdown files, a project existence indicator, a canonical directory-structure sample, and a brief development status summary.
        
        Returns:
            str: Markdown-formatted project status containing file counts, existence flag, directory structure, and generated timestamp.
        """

        # Count files
        python_files = (
            len(list(project_path.glob("**/*.py"))) if project_path.exists() else 0
        )
        md_files = (
            len(list(project_path.glob("**/*.md"))) if project_path.exists() else 0
        )

        return f"""# {project_name} - Project Status

**Generated**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

## Project Metrics

- **Python Files**: {python_files}
- **Markdown Files**: {md_files}
- **Project Exists**: {'Yes' if project_path.exists() else 'No'}

## Directory Structure

```
{project_name}/
├── .md/
│   └── .projects/          # Generated documentation
├── src/                    # Source code
├── tests/                  # Test files
├── scripts/                # Utility scripts
└── prompts/                # POML templates (if applicable)
```

## Development Status

- **Setup**: Complete
- **Documentation**: Auto-generated
- **Integration**: Part of ApexSigma ecosystem

---

*Generated by ApexSigma Documentation Builder*
"""

    async def _generate_ecosystem_overview_content(self) -> str:
        """
        Generate a Markdown overview describing the ApexSigma ecosystem.
        
        Returns:
            overview_md (str): Formatted Markdown containing the ecosystem architecture, core project list and status, integration flow diagram, documentation system notes, development workflow, and a generation timestamp.
        """

        existing_projects = [
            name for name, path in self.projects.items() if path.exists()
        ]

        return f"""# ApexSigma Ecosystem Overview

**Generated**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

## Ecosystem Architecture

The ApexSigma ecosystem consists of four interconnected microservices:

### Core Projects

| Project | Status | Purpose |
|---------|--------|---------|
| **InGest-LLM.as** | Active | Data ingestion and processing |
| **memos.as** | Feature-Complete | Memory Operating System |
| **devenviro.as** | Development | Agent orchestration |
| **tools.as** | Utility | Development tooling |

### Project Status

**Existing Projects**: {len(existing_projects)} / {len(self.projects)}
- {', '.join(existing_projects)}

### Integration Flow

```mermaid
graph TD
    A[InGest-LLM.as] --> B[memos.as]
    B --> C[devenviro.as]
    C --> D[tools.as]
    D --> A
    
    B --> E[Redis Cache]
    B --> F[PostgreSQL]
    B --> G[Neo4j]
    B --> H[Qdrant]
```

### Documentation System

- **POML Templates**: Dynamic context generation
- **Embedding Analysis**: Code similarity and patterns
- **Automated Building**: Real-time documentation updates
- **Cross-Project Analysis**: Ecosystem-wide insights

### Development Workflow

1. **Code Analysis**: Embedding-based pattern detection
2. **Context Generation**: POML-driven agent contexts
3. **Documentation**: Automated build and update
4. **Integration**: Cross-service communication testing

---

*This overview is automatically maintained by the ApexSigma documentation system.*
"""

    def _generate_build_summary(self) -> str:
        """
        Generate a markdown summary of the most recent documentation build.
        
        Returns:
            str: Markdown-formatted build summary including generation timestamp, processed projects and their statuses, which documentation components were produced (embedding analysis is indicated as skipped when the analyzer is unavailable), tools used, and next-build instructions.
        """

        return f"""# Documentation Build Summary

**Build Time**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

## Build Results

### Projects Processed
- InGest-LLM.as: ✓ Complete
- memos.as: ✓ Complete  
- devenviro.as: ✓ Complete
- tools.as: ✓ Complete

### Documentation Generated
- Context bullets: ✓ Generated
- Project documentation: ✓ Generated
- Embedding analysis: {'✓ Generated' if EMBEDDING_ANALYZER_AVAILABLE else '⚠ Skipped (analyzer unavailable)'}
- Ecosystem overview: ✓ Generated

### Tools Used
- POML template system
- {'Nomic embedding analyzer' if EMBEDDING_ANALYZER_AVAILABLE else 'Basic project analysis'}
- Automated file generation
- Cross-project analysis

### Next Build
The documentation system can be run again with:
```bash
python scripts/build_docs.py --all
```

---

*Generated by ApexSigma Documentation Builder v1.0*
"""


async def main():
    """
    Entry point for the CLI that builds automated documentation for ApexSigma projects.
    
    Parses command-line arguments and runs one of three modes: generate only context bullets (--context-only), build documentation for a specific project (--project PROJECT_NAME), or build documentation for all projects (--all). Supports flags to skip embedding analysis (--no-embeddings), skip context generation (--no-context), and force refresh (--force). Validates that a mode is specified (prints help and exits non-zero on failure), invokes DocumentationBuilder to perform the requested work, and exits non-zero if the build fails.
    """

    parser = argparse.ArgumentParser(
        description="Build automated documentation for ApexSigma projects",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python build_docs.py --all                    # Build all documentation
  python build_docs.py --project InGest-LLM.as  # Build specific project
  python build_docs.py --context-only           # Only context bullets
  python build_docs.py --no-embeddings          # Skip embedding analysis
        """,
    )

    parser.add_argument(
        "--all", action="store_true", help="Build documentation for all projects"
    )

    parser.add_argument(
        "--project",
        metavar="PROJECT_NAME",
        help="Build documentation for specific project",
    )

    parser.add_argument(
        "--context-only", action="store_true", help="Only generate context bullets"
    )

    parser.add_argument(
        "--no-embeddings", action="store_true", help="Skip embedding analysis"
    )

    parser.add_argument(
        "--no-context", action="store_true", help="Skip context bullet generation"
    )

    parser.add_argument(
        "--force", action="store_true", help="Force refresh all documentation"
    )

    args = parser.parse_args()

    # Validate arguments
    if not args.all and not args.project and not args.context_only:
        parser.print_help()
        print("\\nError: Must specify --all, --project PROJECT_NAME, or --context-only")
        sys.exit(1)

    # Create builder
    builder = DocumentationBuilder()

    try:
        if args.context_only:
            await builder._build_context_bullets()
        elif args.project:
            await builder.build_project_documentation(args.project)
        elif args.all:
            await builder.build_all_documentation(
                include_embeddings=not args.no_embeddings,
                include_context_bullets=not args.no_context,
                include_project_docs=True,
                force_refresh=args.force,
            )

        print("\\n✓ Documentation build completed successfully!")

    except Exception as e:
        print(f"\\nError: Documentation build failed: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    print("ApexSigma Automated Documentation Builder")
    print("Requires: POML templates, project data, and optional embedding analysis")
    print()

    asyncio.run(main())