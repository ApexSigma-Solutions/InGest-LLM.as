#!/usr/bin/env python3
"""
POML-based Context Generator for ApexSigma

This script generates dynamic agent context bullets using POML templates
and real-time project data from the Master Knowledge Graph.
"""

import json
import argparse
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, Any

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

try:
    import poml

    POML_AVAILABLE = True
except ImportError:
    POML_AVAILABLE = False


class ContextBulletGenerator:
    """Generates agent context bullets using POML templates."""

    def __init__(self, prompts_dir: str = "prompts"):
        """
        Create a ContextBulletGenerator configured to load templates from a prompts directory.
        
        Parameters:
        	prompts_dir (str): Path to the prompts directory to load templates from (default "prompts").
        
        Description:
        	Saves `prompts_dir` as a Path, initializes the internal templates mapping, and attempts to load any templates
        	found in the configured prompts directory (may print warnings on I/O or parse errors).
        """
        self.prompts_dir = Path(prompts_dir)
        self.templates = {}
        self.load_templates()

    def load_templates(self) -> None:
        """
        Load POML templates from the prompts directory into self.templates.
        
        If the prompts directory does not exist this method prints a warning and returns.
        For each `*.poml` file found, the method stores an entry in `self.templates` keyed
        by the file stem: when a POML runtime is available the parsed template object is
        stored; otherwise the file's text content is stored. Any error loading an
        individual file is reported with a warning but does not raise.
        """
        if not self.prompts_dir.exists():
            print(f"Warning: Prompts directory {self.prompts_dir} not found")
            return

        for poml_file in self.prompts_dir.glob("*.poml"):
            try:
                if POML_AVAILABLE:
                    template = poml.load(str(poml_file))
                    self.templates[poml_file.stem] = template
                else:
                    # Fallback: read as text
                    content = poml_file.read_text(encoding="utf-8")
                    self.templates[poml_file.stem] = content
            except Exception as e:
                print(f"Warning: Could not load template {poml_file}: {e}")

    def generate_context_bullet(
        self,
        data_source: str = None,
        output_file: str = None,
        format_type: str = "markdown",
    ) -> str:
        """
        Generate the agent context bullet text using available templates or a fallback and optionally save it to a file.
        
        Loads context data from the provided data_source (or a default/built-in dataset), renders the content with POML templates when available or with the internal fallback generator, and either writes the result to output_file or prints it to stdout.
        
        Parameters:
            data_source (str): Path to a JSON ingest file to source context data; if omitted the generator uses the default internal data.
            output_file (str): Path to write the generated content; if omitted the content is printed to stdout.
            format_type (str): Preferred output format hint (e.g., "markdown", "json", "text"); rendering may vary depending on available templates.
        
        Returns:
            str: The generated context bullet content.
        """

        print("=" * 80)
        print("APEXSIGMA POML CONTEXT GENERATOR")
        print("=" * 80)
        print(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"Templates loaded: {len(self.templates)}")
        print()

        # Load data
        context_data = self._load_context_data(data_source)

        if POML_AVAILABLE:
            content = self._generate_with_poml(context_data)
        else:
            content = self._generate_fallback(context_data)

        # Save output
        if output_file:
            output_path = Path(output_file)
            output_path.write_text(content, encoding="utf-8")
            print(f"✓ Context bullet saved to: {output_path}")
        else:
            print("GENERATED CONTEXT BULLET")
            print("-" * 40)
            print(content)

        return content

    def _load_context_data(self, data_source: str = None) -> Dict[str, Any]:
        """
        Selects and returns the agent context data, preferring beta ingest data when present and falling back to a built-in default.
        
        Parameters:
            data_source (str, optional): An optional data source path. (Currently unused by this implementation; retained for API compatibility.)
        
        Returns:
            Dict[str, Any]: Context data containing keys such as `timestamp`, `session_id`, `version`, `mission_brief` (including `objective`, `agent_roster`, `embedding_service`), `project_status`, `critical_blocker`, `immediate_priorities`, `environment`, `active_tools`, and `network_status`.
        """

        # Try to load from beta.ingest.as.json first
        beta_file = Path(".ingest/beta.ingest.as.json")
        if beta_file.exists():
            try:
                with open(beta_file, "r", encoding="utf-8") as f:
                    beta_data = json.load(f)

                # Transform beta data to context format
                return self._transform_beta_data(beta_data)
            except Exception as e:
                print(f"Warning: Could not load beta data: {e}")

        # Fallback to default data structure
        return self._get_default_context_data()

    def _transform_beta_data(self, beta_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Convert a loaded beta.ingest.as.json structure into the context data shape used by the generator.
        
        Parameters:
            beta_data (Dict[str, Any]): Parsed JSON object from beta.ingest.as.json. Expected keys (optional) include:
                - "ingest_metadata": may contain "version"
                - "mission_brief": may contain "objective", "agent_roster" (which may include "embedding_service")
                - "project_status": list of status entries
                - "critical_blocker": single blocker description or object
                - "immediate_priorities": list of priority entries
        
        Returns:
            Dict[str, Any]: Context dictionary with keys:
                - "timestamp": ISO timestamp generated at conversion time
                - "session_id": autogenerated session identifier
                - "version": taken from ingest_metadata.version or "1.0"
                - "mission_brief": dict with "objective", "agent_roster", and "embedding_service"
                - "project_status": list (may be empty)
                - "critical_blocker": value from input or None
                - "immediate_priorities": list (may be empty)
                - "environment": environment label string
                - "active_tools": list of active tool names
                - "network_status": network status string
        """

        return {
            "timestamp": datetime.now().isoformat(),
            "session_id": f"auto_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            "version": beta_data.get("ingest_metadata", {}).get("version", "1.0"),
            "mission_brief": {
                "objective": beta_data.get("mission_brief", {}).get(
                    "objective", "Continue ApexSigma development"
                ),
                "agent_roster": beta_data.get("mission_brief", {}).get(
                    "agent_roster", {}
                ),
                "embedding_service": beta_data.get("mission_brief", {})
                .get("agent_roster", {})
                .get("embedding_service", "nomic-embed-text v1.5"),
            },
            "project_status": beta_data.get("project_status", []),
            "critical_blocker": beta_data.get("critical_blocker"),
            "immediate_priorities": beta_data.get("immediate_priorities", []),
            "environment": "Local Development",
            "active_tools": ["Docker", "Poetry", "Claude Code", "POML"],
            "network_status": "Pending Docker Network Fix",
        }

    def _get_default_context_data(self) -> Dict[str, Any]:
        """
        Provide a default context data structure used when no external ingest data is available.
        
        The returned dictionary mirrors the generator's expected context input format and includes:
        - `timestamp`: ISO-formatted generation time.
        - `session_id`: a default session identifier with a timestamp.
        - `version`: schema or payload version string.
        - `mission_brief`: mission details including `objective`, `agent_roster`, and `embedding_service`.
        - `project_status`: list of project status entries with `name`, `status`, and `details`.
        - `critical_blocker`: current critical blocker or `None`.
        - `immediate_priorities`: list of prioritized tasks each with `priority`, `task`, and `description`.
        - `environment`: deployment or runtime environment description.
        - `active_tools`: list of active tool names.
        - `network_status`: current network mode or status.
        
        Returns:
            dict: Default context data with the keys described above, suitable for template rendering or fallback generation.
        """

        return {
            "timestamp": datetime.now().isoformat(),
            "session_id": f"default_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            "version": "1.0",
            "mission_brief": {
                "objective": "Continue development of the ApexSigma 'Society of Agents' ecosystem",
                "agent_roster": {
                    "primary": ["Gemini CLI", "Claude Code"],
                    "support": "Local AI Models",
                    "embedding_service": "nomic-embed-text v1.5",
                },
            },
            "project_status": [
                {
                    "name": "InGest-LLM.as",
                    "status": "Active Development",
                    "details": "POML context generation system implemented",
                }
            ],
            "critical_blocker": None,
            "immediate_priorities": [
                {
                    "priority": "HIGH",
                    "task": "Implement POML Context Generation",
                    "description": "Create dynamic agent context bullets using POML templates",
                }
            ],
            "environment": "Local Development",
            "active_tools": ["Docker", "Poetry", "Claude Code", "POML"],
            "network_status": "Development Mode",
        }

    def _generate_with_poml(self, data: Dict[str, Any]) -> str:
        """
        Generate a context string from provided context data using a POML agent template when available.
        
        Parameters:
            data (Dict[str, Any]): Context data used to render the template (e.g., mission_brief, project_status, immediate_priorities, environment).
        
        Returns:
            str: Rendered context content. If the agent POML template is not present or rendering fails, returns a plain-text fallback context string.
        """

        try:
            if "agent_context_template" in self.templates:
                template = self.templates["agent_context_template"]
                return template.render(**data)
            else:
                return self._generate_fallback(data)
        except Exception as e:
            print(f"POML generation failed: {e}")
            return self._generate_fallback(data)

    def _generate_fallback(self, data: Dict[str, Any]) -> str:
        """
        Produce a markdown-formatted agent context bulletin from provided context data as a fallback when POML templates are unavailable.
        
        Parameters:
            data (Dict[str, Any]): Context values used to populate the bulletin. Expected keys include:
                - timestamp: ISO timestamp string for generation time.
                - session_id: Identifier for the current session.
                - version: Content/version identifier.
                - mission_brief: dict with 'objective' (str) and 'agent_roster' (dict of role -> list[str]).
                - project_status: list of dicts with 'name', 'status', and 'details'.
                - critical_blocker: optional dict with 'issue', 'impact', and 'status'.
                - immediate_priorities: list of dicts with 'priority', 'task', optional 'project', and 'description'.
                - environment: runtime environment description.
                - active_tools: list of active tool names.
                - network_status: network connectivity/status string.
        
        Returns:
            A markdown string containing a complete agent context bulletin populated from the provided data.
        """

        content = f"""# ApexSigma Agent Context Bullet

**Generated**: {data.get('timestamp', datetime.now().isoformat())}  
**Session ID**: {data.get('session_id', 'FALLBACK')}  
**Version**: {data.get('version', '1.0')}

---

## Mission Brief

**Objective**: {data.get('mission_brief', {}).get('objective', 'Continue ApexSigma development')}

**Agent Roster**:
"""

        agent_roster = data.get("mission_brief", {}).get("agent_roster", {})
        for role, agents in agent_roster.items():
            if isinstance(agents, list):
                agents_str = ", ".join(agents)
            else:
                agents_str = str(agents)
            content += f"- **{role.title()}**: {agents_str}\\n"

        content += "\\n---\\n\\n## Project Status\\n\\n"

        for project in data.get("project_status", []):
            content += f"### {project.get('name', 'Unknown Project')}\\n"
            content += f"**Status**: {project.get('status', 'Unknown')}  \\n"
            content += (
                f"**Details**: {project.get('details', 'No details available.')}\\n\\n"
            )

        # Critical blocker
        blocker = data.get("critical_blocker")
        if blocker:
            content += "---\\n\\n## ⚠️ Critical Blocker\\n\\n"
            content += f"**Issue**: {blocker.get('issue', 'Unknown issue')}  \\n"
            content += f"**Impact**: {blocker.get('impact', 'Unknown impact')}  \\n"
            content += f"**Status**: {blocker.get('status', 'Unknown status')}\\n\\n"

        # Priorities
        content += "---\\n\\n## Immediate Priorities\\n\\n"

        for task in data.get("immediate_priorities", []):
            content += f"### {task.get('priority', 'UNKNOWN')}: {task.get('task', 'Unknown Task')}\\n"
            if task.get("project"):
                content += f"**Project**: {task['project']}  \\n"
            content += f"**Description**: {task.get('description', 'No description available.')}\\n\\n"

        # Development context
        content += (
            """---

## Development Context

**Environment**: """
            + data.get("environment", "Local Development")
            + """  
**Tools Active**: """
            + ", ".join(data.get("active_tools", []))
            + """  
**Network Status**: """
            + data.get("network_status", "Unknown")
            + """

## Success Metrics

- [ ] Critical blockers resolved
- [ ] High-priority tasks advanced
- [ ] Integration tests passing
- [ ] Documentation updated

---

*This context bullet was automatically generated using POML templates and real-time project data.*"""
        )

        return content

    def list_templates(self) -> None:
        """
        List available POML templates.
        
        Prints each template name (with a .poml suffix) to stdout and, when a template exposes a `metadata` mapping, prints its `description` or "No description". If no templates are loaded, prints "No templates found". Finally prints the total template count.
        """

        print("AVAILABLE POML TEMPLATES")
        print("-" * 30)

        if not self.templates:
            print("No templates found")
            return

        for name, template in self.templates.items():
            print(f"✓ {name}.poml")
            if hasattr(template, "metadata"):
                desc = template.metadata.get("description", "No description")
                print(f"    {desc}")

        print(f"\\nTotal templates: {len(self.templates)}")

    def validate_templates(self) -> bool:
        """
        Validate each loaded POML template and report the results.
        
        Attempts to call `validate()` on each template when that method is available; counts templates that pass without raising an exception and prints a summary of results.
        
        Returns:
            bool: `True` if all loaded templates validated without error, `False` otherwise.
        """

        print("VALIDATING POML TEMPLATES")
        print("-" * 30)

        valid_count = 0
        total_count = len(self.templates)

        for name, template in self.templates.items():
            try:
                if POML_AVAILABLE and hasattr(template, "validate"):
                    template.validate()
                print(f"✓ {name}.poml - Valid")
                valid_count += 1
            except Exception as e:
                print(f"✗ {name}.poml - Error: {e}")

        print(f"\\nValidation complete: {valid_count}/{total_count} templates valid")
        return valid_count == total_count


def main():
    """
    Entrypoint for the CLI that generates agent context bullets.
    
    Parses command-line arguments, instantiates a ContextBulletGenerator, and performs one of:
    - list available templates when --list-templates is provided,
    - validate templates and exit with status 0 on success or 1 on failure when --validate is provided,
    - otherwise generate and optionally save a context bullet using the provided --data-source, --output, and --format options.
    
    Exits with status 1 on unexpected errors; prints progress and result messages to stdout.
    """

    parser = argparse.ArgumentParser(
        description="Generate dynamic agent context bullets using POML",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python generate_context_bullet.py                           # Generate using beta data
  python generate_context_bullet.py --output context.md       # Save to file
  python generate_context_bullet.py --list-templates          # List templates
  python generate_context_bullet.py --validate                # Validate templates
        """,
    )

    parser.add_argument(
        "--output", metavar="FILE", help="Output file path (default: print to console)"
    )

    parser.add_argument(
        "--data-source",
        metavar="FILE",
        help="Custom data source file (default: .ingest/beta.ingest.as.json)",
    )

    parser.add_argument(
        "--list-templates",
        action="store_true",
        help="List all available POML templates",
    )

    parser.add_argument(
        "--validate", action="store_true", help="Validate all POML templates"
    )

    parser.add_argument(
        "--format",
        choices=["markdown", "json", "text"],
        default="markdown",
        help="Output format (default: markdown)",
    )

    args = parser.parse_args()

    # Create generator
    generator = ContextBulletGenerator()

    if args.list_templates:
        generator.list_templates()
        return

    if args.validate:
        valid = generator.validate_templates()
        sys.exit(0 if valid else 1)

    # Generate context bullet
    try:
        generator.generate_context_bullet(
            data_source=args.data_source,
            output_file=args.output,
            format_type=args.format,
        )
        print("\\n✓ Context generation completed successfully!")

    except Exception as e:
        print(f"\\nError: Context generation failed: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    if not POML_AVAILABLE:
        print("Warning: POML library not available, using fallback generation")
        print("Install with: poetry add poml")
        print()

    main()