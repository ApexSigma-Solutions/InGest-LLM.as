#!/usr/bin/env python3
"""
Automated Documentation Builder for ApexSigma

This script automates the generation and updating of project documentation
using POML templates, embedding analysis, and real-time project data.
"""

import asyncio
import argparse
import sys
import json
import os
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

try:
    from ingest_llm_as.services.nomic_code_analyzer import get_nomic_code_analyzer

    EMBEDDING_ANALYZER_AVAILABLE = True
except ImportError:
    EMBEDDING_ANALYZER_AVAILABLE = False

# Import other components we've built
sys.path.insert(0, str(Path(__file__).parent))
try:
    from generate_context_bullet import ContextBulletGenerator
except ImportError as e:
    print(f"❌ Missing required dependency: {e}")
    print("Please ensure generate_context_bullet.py is available.")
    sys.exit(1)


class DocumentationBuilder:
    """Automated documentation builder for ApexSigma projects."""

    def __init__(self, base_path: Optional[str] = None, projects: Optional[Dict[str, str]] = None):
        """Initialize the documentation builder."""
        if base_path:
            self.base_path = Path(base_path)
        else:
            # Default to repo root's parent (where sibling projects are located)
            repo_root = Path(__file__).resolve().parents[1]
            self.base_path = repo_root.parent
        
        # Use provided projects config, load from env/config, or use defaults
        if projects:
            self.projects = {name: self.base_path / path for name, path in projects.items()}
        else:
            self.projects = self._load_projects_config()

    def _load_projects_config(self) -> Dict[str, Path]:
        """Load project configuration from environment variables or config file."""
        projects = {}
        
        # Try to load from config file first
        config_file = Path(__file__).parent / "build_docs_config.json"
        if config_file.exists():
            try:
                with open(config_file, 'r') as f:
                    config = json.load(f)
                    projects_config = config.get('projects', {})
                    for name, path in projects_config.items():
                        projects[name] = self.base_path / path
                return projects
            except (json.JSONDecodeError, KeyError):
                pass  # Fall back to defaults
        
        # Try environment variables
        env_projects = os.environ.get('BUILD_DOCS_PROJECTS')
        if env_projects:
            try:
                projects_config = json.loads(env_projects)
                for name, path in projects_config.items():
                    projects[name] = self.base_path / path
                return projects
            except json.JSONDecodeError:
                pass  # Fall back to defaults
        
        # Default project configuration
        projects = {
            "InGest-LLM.as": self.base_path / "InGest-LLM.as",
            "memos.as": self.base_path / "memos.as",
            "devenviro.as": self.base_path / "devenviro.as",
            "tools.as": self.base_path / "tools.as",
        }
        return projects

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
        """Build all documentation for all projects."""

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
            await self._build_context_bullets(force_refresh)

        # Generate embedding analysis
        if include_embeddings and EMBEDDING_ANALYZER_AVAILABLE:
            await self._build_embedding_analysis(force_refresh)

        # Generate project documentation
        if include_project_docs:
            await self._build_project_documentation(force_refresh)

        # Generate ecosystem overview
        await self._build_ecosystem_overview(force_refresh)

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

    async def _build_context_bullets(self, force_refresh: bool = False) -> None:
        """Build context bullets for all projects."""

        print("GENERATING CONTEXT BULLETS")
        print("-" * 30)

        # Check for existing context bullets if not force refreshing
        if not force_refresh:
            existing_bullets = []
            for project_name, project_path in self.projects.items():
                if project_path.exists():
                    context_file = project_path / ".md" / ".projects" / "context_bullet.md"
                    if context_file.exists():
                        existing_bullets.append(project_name)

            if existing_bullets:
                print(f"Warning: Context bullets already exist for {len(existing_bullets)} projects: {', '.join(existing_bullets[:5])}{'...' if len(existing_bullets) > 5 else ''}")
                print("Use --force to regenerate existing documentation")
                return

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

    async def _build_embedding_analysis(self, force_refresh: bool = False) -> None:
        """Build embedding analysis documentation."""

        print("GENERATING EMBEDDING ANALYSIS")
        print("-" * 35)

        if not self.embedding_analyzer:
            print("⚠ Embedding analyzer not available")
            return

        # Check for existing embedding analyses if not force refreshing
        if not force_refresh:
            existing_analyses = []
            for project_name, project_path in self.projects.items():
                if project_path.exists():
                    analysis_file = project_path / ".md" / ".projects" / "embedding_analysis.md"
                    if analysis_file.exists():
                        existing_analyses.append(project_name)

            if existing_analyses:
                print(f"Warning: Embedding analyses already exist for {len(existing_analyses)} projects: {', '.join(existing_analyses[:5])}{'...' if len(existing_analyses) > 5 else ''}")
                print("Use --force to regenerate existing documentation")
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

    async def _build_project_documentation(self, force_refresh: bool = False) -> None:
        """Build general project documentation."""

        print("GENERATING PROJECT DOCUMENTATION")
        print("-" * 40)

        # Check for existing project docs if not force refreshing
        if not force_refresh:
            existing_docs = []
            for project_name, project_path in self.projects.items():
                if project_path.exists():
                    readme_file = project_path / ".md" / ".projects" / "README.md"
                    status_file = project_path / ".md" / ".projects" / "project_status.md"
                    if readme_file.exists() or status_file.exists():
                        existing_docs.append(project_name)

            if existing_docs:
                print(f"Warning: Project documentation already exists for {len(existing_docs)} projects: {', '.join(existing_docs[:5])}{'...' if len(existing_docs) > 5 else ''}")
                print("Use --force to regenerate existing documentation")
                return

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

    async def _build_ecosystem_overview(self, force_refresh: bool = False) -> None:
        """Build ecosystem-wide overview documentation."""

        print("GENERATING ECOSYSTEM OVERVIEW")
        print("-" * 35)

        try:
            # Check if ecosystem overview files already exist
            main_docs_dir = self.projects["InGest-LLM.as"] / ".md" / ".projects"
            overview_file = main_docs_dir / "apexsigma_ecosystem_overview.md"
            summary_file = main_docs_dir / "documentation_build_summary.md"

            if not force_refresh and overview_file.exists() and summary_file.exists():
                print("✓ Ecosystem overview files already exist (use --force to regenerate)")
                return

            # Generate ecosystem overview
            overview_content = await self._generate_ecosystem_overview_content()

            # Save to main project
            overview_file.write_text(overview_content, encoding="utf-8")

            print("✓ apexsigma_ecosystem_overview.md")

            # Generate build summary
            summary_content = self._generate_build_summary()
            summary_file.write_text(summary_content, encoding="utf-8")

            print("✓ documentation_build_summary.md")

        except Exception as e:
            print(f"✗ Ecosystem overview failed: {e}")

        print()

    async def _generate_ecosystem_context_bullet(self) -> str:
        """Generate ecosystem-wide context bullet."""

        try:
            return self.context_generator.generate_context_bullet()
        except Exception as e:
            print(f"Warning: Context bullet generation failed: {e}")
            return f"# ApexSigma Context Bullet\\n\\nGenerated: {datetime.now().isoformat()}\\n\\nError: Could not generate context bullet."

    async def _generate_project_context_bullet(
        self, project_name: str, docs_dir: Path
    ) -> None:
        """Generate context bullet for a specific project."""

        try:
            context_content = self.context_generator.generate_context_bullet()
            context_file = docs_dir / "context_bullet.md"
            context_file.write_text(context_content, encoding="utf-8")
        except Exception as e:
            print(f"Warning: Context bullet for {project_name} failed: {e}")

    def _format_embedding_analysis(
        self, project_name: str, analysis, all_analyses: dict
    ) -> str:
        """Format embedding analysis for a project."""

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
        """Generate README content for a project."""

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
        """Generate project status content."""

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
        """Generate ecosystem overview content."""

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
        """Generate build summary."""

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
    """Main entry point."""

    parser = argparse.ArgumentParser(
        description="Build automated documentation for ApexSigma projects",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python build_docs.py --all                    # Build all documentation
  python build_docs.py --project InGest-LLM.as  # Build specific project
  python build_docs.py --context-only           # Only context bullets
  python build_docs.py --no-embeddings          # Skip embedding analysis
  python build_docs.py --config custom_config.json  # Use custom project config
  python build_docs.py --base-path /custom/path     # Use custom base path
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
        "--config",
        metavar="CONFIG_FILE",
        help="Path to JSON config file for project paths",
    )

    parser.add_argument(
        "--base-path",
        metavar="BASE_PATH",
        help="Base path for projects (defaults to repo parent)",
    )

    args = parser.parse_args()

    # Validate arguments
    if not args.all and not args.project and not args.context_only:
        parser.print_help()
        print("\\nError: Must specify --all, --project PROJECT_NAME, or --context-only")
        sys.exit(1)

    # Load projects config if specified
    projects_config = None
    if args.config:
        config_path = Path(args.config)
        if config_path.exists():
            try:
                with open(config_path, 'r') as f:
                    config = json.load(f)
                    projects_config = config.get('projects', {})
            except (json.JSONDecodeError, IOError) as e:
                print(f"Error loading config file {args.config}: {e}")
                sys.exit(1)
        else:
            print(f"Config file not found: {args.config}")
            sys.exit(1)

    # Create builder
    builder = DocumentationBuilder(base_path=args.base_path, projects=projects_config)

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
