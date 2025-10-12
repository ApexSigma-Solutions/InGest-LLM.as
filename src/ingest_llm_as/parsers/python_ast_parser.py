"""
Python AST Parser for extracting structured code elements.

This module provides sophisticated parsing of Python source code using the
Abstract Syntax Tree (AST) to extract meaningful, context-aware code elements
for semantic indexing and retrieval.
"""

import ast
import hashlib
from enum import Enum
from pathlib import Path
from typing import List, Dict, Any, Optional, Set
from dataclasses import dataclass, field
from datetime import datetime

from ..observability.logging import get_logger

logger = get_logger(__name__)


class CodeElementType(str, Enum):
    """Types of code elements that can be extracted."""

    FUNCTION = "function"
    ASYNC_FUNCTION = "async_function"
    CLASS = "class"
    METHOD = "method"
    ASYNC_METHOD = "async_method"
    PROPERTY = "property"
    STATICMETHOD = "staticmethod"
    CLASSMETHOD = "classmethod"
    MODULE = "module"


@dataclass
class CodeElement:
    """Represents a single code element extracted from Python source."""

    # Core identification
    element_type: CodeElementType
    name: str
    qualified_name: str  # Full dotted path like "MyClass.my_method"

    # Source information
    source_code: str
    docstring: Optional[str] = None
    signature: Optional[str] = None

    # Location information
    file_path: Optional[str] = None
    line_start: int = 0
    line_end: int = 0

    # Code analysis
    complexity_score: int = 0
    dependencies: List[str] = field(default_factory=list)
    decorators: List[str] = field(default_factory=list)

    # Relationships
    parent_class: Optional[str] = None
    child_elements: List[str] = field(default_factory=list)
    relationships: Dict[str, List[str]] = field(default_factory=dict)

    # Metadata
    tags: Set[str] = field(default_factory=set)
    custom_metadata: Dict[str, Any] = field(default_factory=dict)
    content_hash: str = ""

    def __post_init__(self):
        """
        Set a content hash for the element if one was not provided.
        
        If `content_hash` is empty, compute a 16-character MD5 hash derived from the element's
        `qualified_name` and `source_code` and assign it to `self.content_hash`.
        """
        if not self.content_hash:
            content_for_hash = f"{self.qualified_name}:{self.source_code}"
            self.content_hash = hashlib.md5(content_for_hash.encode()).hexdigest()[:16]

    def to_searchable_content(self) -> str:
        """
        Assembles a searchable text representation of the code element.
        
        The returned string includes the element type and qualified name, optional signature, optional docstring, decorators, parent class context, tags, and the full source code, with sections separated by blank lines.
        
        Returns:
            A single string containing the assembled searchable content for the element.
        """
        parts = []

        # Add element type and name
        parts.append(f"{self.element_type.value}: {self.qualified_name}")

        # Add signature if available
        if self.signature:
            parts.append(f"Signature: {self.signature}")

        # Add docstring if available
        if self.docstring:
            parts.append(f"Documentation: {self.docstring}")

        # Add decorators
        if self.decorators:
            parts.append(f"Decorators: {', '.join(self.decorators)}")

        # Add parent class context
        if self.parent_class:
            parts.append(f"Class: {self.parent_class}")

        # Add tags
        if self.tags:
            parts.append(f"Tags: {', '.join(sorted(self.tags))}")

        # Add the actual source code
        parts.append(f"Source Code:\n{self.source_code}")

        return "\n\n".join(parts)


@dataclass
class ParsingResult:
    """Result of parsing a Python file."""

    success: bool
    file_path: Optional[str] = None
    elements: List[CodeElement] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    processing_time_ms: int = 0
    total_lines: int = 0

    @property
    def element_count(self) -> int:
        """
        Report the total number of extracted code elements.
        
        Returns:
            count (int): The total number of extracted code elements.
        """
        return len(self.elements)

    @property
    def function_count(self) -> int:
        """
        Number of extracted function and async function elements.
        
        Returns:
            int: Count of elements whose `element_type` is `CodeElementType.FUNCTION` or `CodeElementType.ASYNC_FUNCTION`.
        """
        return len(
            [
                e
                for e in self.elements
                if e.element_type
                in [CodeElementType.FUNCTION, CodeElementType.ASYNC_FUNCTION]
            ]
        )

    @property
    def class_count(self) -> int:
        """
        Get the number of class elements extracted.
        
        Returns:
            int: Count of elements whose `element_type` is `CodeElementType.CLASS`.
        """
        return len(
            [e for e in self.elements if e.element_type == CodeElementType.CLASS]
        )


class ASTVisitor(ast.NodeVisitor):
    """AST visitor for extracting code elements."""

    def __init__(self, source_lines: List[str], file_path: Optional[str] = None):
        """
        Initialize the visitor state with source lines and optional file path.
        
        Sets up containers for extracted CodeElement instances, class context tracking, and module-level import/dependency collection used during AST traversal.
        
        Parameters:
            source_lines (List[str]): The source code split into lines for node source extraction and location mapping.
            file_path (Optional[str]): Optional path of the source file used for qualified name resolution and module element creation.
        """
        self.source_lines = source_lines
        self.file_path = file_path
        self.elements: List[CodeElement] = []
        self.current_class: Optional[str] = None
        self.class_stack: List[str] = []
        self.imports: Set[str] = set()
        self.dependencies: Set[str] = set()

    def visit_Import(self, node: ast.Import):
        """
        Record modules referenced by an import statement into the visitor's import and dependency sets.
        
        Each module name from the import statement is added to self.imports and self.dependencies. Continues traversal for the node's children.
        
        Parameters:
            node (ast.Import): The AST Import node being visited.
        """
        for alias in node.names:
            self.imports.add(alias.name)
            self.dependencies.add(alias.name)
        self.generic_visit(node)

    def visit_ImportFrom(self, node: ast.ImportFrom):
        """
        Record names imported by a `from ... import ...` statement into the visitor's tracking sets.
        
        Parameters:
            node (ast.ImportFrom): The AST node representing a `from <module> import <names>` statement.
        
        Details:
            For each alias in the node, adds an entry of the form `<module>.<name>` to the visitor's `imports` and `dependencies` sets. Continues traversal by calling `generic_visit`.
        """
        if node.module:
            for alias in node.names:
                import_name = f"{node.module}.{alias.name}"
                self.imports.add(import_name)
                self.dependencies.add(import_name)
        self.generic_visit(node)

    def visit_ClassDef(self, node: ast.ClassDef):
        """
        Extracts a class definition into a CodeElement and processes its nested members.
        
        Creates a CodeElement for the given AST ClassDef, recording the class name, qualified name,
        base classes (stored in `custom_metadata["base_classes"]` and added to `dependencies`),
        decorators, and tags (`"class"` and `"inheritance"` when bases are present). The created
        element is appended to `self.elements`. The parser context (`class_stack` and `current_class`)
        is updated while child nodes are visited and restored after processing.
        
        Parameters:
            node (ast.ClassDef): The AST node representing the class definition to visit.
        """
        # Build qualified name
        parent_path = ".".join(self.class_stack) if self.class_stack else ""
        qualified_name = f"{parent_path}.{node.name}" if parent_path else node.name

        # Extract class information
        element = self._create_code_element(
            node=node,
            element_type=CodeElementType.CLASS,
            name=node.name,
            qualified_name=qualified_name,
            parent_class=self.current_class,
        )

        # Add class-specific metadata
        if node.bases:
            base_classes = [ast.unparse(base) for base in node.bases]
            element.custom_metadata["base_classes"] = base_classes
            element.dependencies.extend(base_classes)

        if node.decorator_list:
            element.decorators = [ast.unparse(dec) for dec in node.decorator_list]

        # Add class tag
        element.tags.add("class")
        if node.bases:
            element.tags.add("inheritance")

        self.elements.append(element)

        # Update context for nested processing
        self.class_stack.append(node.name)
        old_current_class = self.current_class
        self.current_class = qualified_name

        # Visit children to find methods
        self.generic_visit(node)

        # Restore context
        self.class_stack.pop()
        self.current_class = old_current_class

    def visit_FunctionDef(self, node: ast.FunctionDef):
        """Visit function definitions."""
        self._process_function(node, CodeElementType.FUNCTION)

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef):
        """
        Handle an async function definition node and record it as an ASYNC_FUNCTION code element.
        
        Parameters:
            node (ast.AsyncFunctionDef): AST node representing the async function to process.
        """
        self._process_function(node, CodeElementType.ASYNC_FUNCTION)

    def _process_function(self, node: ast.FunctionDef, element_type: CodeElementType):
        """
        Create a CodeElement for the given function/async function AST node and append it to self.elements.
        
        Processes the node to determine its qualified name and element type (adjusting for methods when inside a class), extracts the signature and decorators, assigns tags (e.g., function, method, async, decorated, generator), computes cyclomatic complexity, gathers function dependencies, and sets the element's metadata. If signature extraction fails, a warning is logged. Nested function bodies are not visited.
        
        Parameters:
        	node (ast.FunctionDef): The AST node representing the function or async function to process.
        	element_type (CodeElementType): The initial element type; may be adjusted to a method-specific type when the function is a method of the current class.
        """
        # Build qualified name
        if self.current_class:
            qualified_name = f"{self.current_class}.{node.name}"
            # Determine method type
            if self.current_class and self._is_method():
                if element_type == CodeElementType.FUNCTION:
                    element_type = self._determine_method_type(node)
                else:
                    element_type = CodeElementType.ASYNC_METHOD
        else:
            qualified_name = node.name

        # Create code element
        element = self._create_code_element(
            node=node,
            element_type=element_type,
            name=node.name,
            qualified_name=qualified_name,
            parent_class=self.current_class,
        )

        # Add function signature
        try:
            element.signature = self._extract_signature(node)
        except Exception as e:
            logger.warning(f"Failed to extract signature for {qualified_name}: {e}")

        # Add decorators
        if node.decorator_list:
            element.decorators = [ast.unparse(dec) for dec in node.decorator_list]

        # Add function-specific tags
        element.tags.add("function")
        if element_type == CodeElementType.ASYNC_FUNCTION:
            element.tags.add("async")
        if self.current_class:
            element.tags.add("method")
        if node.decorator_list:
            element.tags.add("decorated")
        if self._has_yield(node):
            element.tags.add("generator")

        # Calculate complexity
        element.complexity_score = self._calculate_complexity(node)

        # Extract function dependencies
        element.dependencies.extend(self._extract_function_dependencies(node))

        self.elements.append(element)

        # Don't visit children of functions to avoid nested functions for now
        # self.generic_visit(node)

    def _create_code_element(
        self,
        node: ast.AST,
        element_type: CodeElementType,
        name: str,
        qualified_name: str,
        parent_class: Optional[str] = None,
    ) -> CodeElement:
        """
        Create a CodeElement representing the given AST node.
        
        Parameters:
            node (ast.AST): AST node to convert into a CodeElement; its location is used for line range.
            element_type (CodeElementType): Type of the code element (e.g., FUNCTION, CLASS).
            name (str): Short name of the element (unqualified).
            qualified_name (str): Fully qualified name including parent context.
            parent_class (Optional[str]): Name of the enclosing class if the element is a class member.
        
        Returns:
            CodeElement: An element containing the node's source code and docstring, file path, start/end line numbers, parent class, and collected dependencies.
        """

        # Extract source code
        source_code = self._extract_source_code(node)

        # Extract docstring
        docstring = ast.get_docstring(node)

        return CodeElement(
            element_type=element_type,
            name=name,
            qualified_name=qualified_name,
            source_code=source_code,
            docstring=docstring,
            file_path=self.file_path,
            line_start=node.lineno,
            line_end=getattr(node, "end_lineno", node.lineno),
            parent_class=parent_class,
            dependencies=list(self.dependencies),
        )

    def _extract_source_code(self, node: ast.AST) -> str:
        """
        Extract the source code corresponding to an AST node, with fallbacks for older Python versions.
        
        Returns:
            source (str): The source code snippet for the node, or a placeholder message if extraction is not possible.
        """
        try:
            # Try using ast.unparse for Python 3.9+
            return ast.unparse(node)
        except AttributeError:
            # Fallback for older Python versions
            if hasattr(node, "lineno") and hasattr(node, "end_lineno"):
                start = node.lineno - 1
                end = getattr(node, "end_lineno", node.lineno)
                return "\n".join(self.source_lines[start:end])
            else:
                return f"# Unable to extract source for {type(node).__name__}"

    def _extract_signature(self, node: ast.FunctionDef) -> str:
        """
        Builds a human-readable function signature from an AST FunctionDef node.
        
        Parameters:
        	node (ast.FunctionDef): AST node for the function whose signature will be produced.
        
        Returns:
        	signature (str): The function signature including parameter names, annotations, default values, varargs (`*args`), kwargs (`**kwargs`), and return annotation (e.g. "func(a: int = 1, *args, **kwargs) -> str").
        """
        args = []

        # Regular arguments
        for arg in node.args.args:
            arg_str = arg.arg
            if arg.annotation:
                arg_str += f": {ast.unparse(arg.annotation)}"
            args.append(arg_str)

        # Default arguments
        defaults = node.args.defaults
        if defaults:
            default_offset = len(args) - len(defaults)
            for i, default in enumerate(defaults):
                args[default_offset + i] += f" = {ast.unparse(default)}"

        # *args
        if node.args.vararg:
            vararg = f"*{node.args.vararg.arg}"
            if node.args.vararg.annotation:
                vararg += f": {ast.unparse(node.args.vararg.annotation)}"
            args.append(vararg)

        # **kwargs
        if node.args.kwarg:
            kwarg = f"**{node.args.kwarg.arg}"
            if node.args.kwarg.annotation:
                kwarg += f": {ast.unparse(node.args.kwarg.annotation)}"
            args.append(kwarg)

        signature = f"{node.name}({', '.join(args)})"

        # Return annotation
        if node.returns:
            signature += f" -> {ast.unparse(node.returns)}"

        return signature

    def _is_method(self) -> bool:
        """Check if function is a method."""
        return self.current_class is not None

    def _determine_method_type(self, node: ast.FunctionDef) -> CodeElementType:
        """
        Classifies a function AST node as a specific method kind based on its decorators.
        
        Parameters:
            node (ast.FunctionDef): The function AST node to inspect for method decorators.
        
        Returns:
            CodeElementType: `CodeElementType.PROPERTY` if decorated with `@property`, `CodeElementType.STATICMETHOD` if decorated with `@staticmethod`, `CodeElementType.CLASSMETHOD` if decorated with `@classmethod`, otherwise `CodeElementType.METHOD`.
        """
        for decorator in node.decorator_list:
            if isinstance(decorator, ast.Name):
                if decorator.id == "property":
                    return CodeElementType.PROPERTY
                elif decorator.id == "staticmethod":
                    return CodeElementType.STATICMETHOD
                elif decorator.id == "classmethod":
                    return CodeElementType.CLASSMETHOD
        return CodeElementType.METHOD

    def _has_yield(self, node: ast.FunctionDef) -> bool:
        """
        Determine whether a function AST node contains any `yield` or `yield from` expressions.
        
        Parameters:
            node (ast.FunctionDef): The function AST node to inspect.
        
        Returns:
            true if the node contains a `yield` or `yield from` expression, false otherwise.
        """
        for child in ast.walk(node):
            if isinstance(child, (ast.Yield, ast.YieldFrom)):
                return True
        return False

    def _calculate_complexity(self, node: ast.FunctionDef) -> int:
        """
        Estimate the cyclomatic complexity of the given function AST node.
        
        Parameters:
            node (ast.FunctionDef): The AST node representing the function or async function to analyze.
        
        Returns:
            int: Cyclomatic complexity as an integer; computed as a base of 1 plus one for each occurrence of `if`, `while`, `for`, `async for`, `except` handler, and boolean operators `and`/`or`.
        """
        complexity = 1  # Base complexity

        for child in ast.walk(node):
            if isinstance(child, (ast.If, ast.While, ast.For, ast.AsyncFor)):
                complexity += 1
            elif isinstance(child, ast.ExceptHandler):
                complexity += 1
            elif isinstance(child, (ast.And, ast.Or)):
                complexity += 1

        return complexity

    def _extract_function_dependencies(self, node: ast.FunctionDef) -> List[str]:
        """
        Extract names of external identifiers referenced inside the function.
        
        Returns:
            List[str]: Up to 10 unique identifier names referenced in the function body, excluding names that start with "_" and the conventional method receivers `self` and `cls`.
        """
        deps = set()

        for child in ast.walk(node):
            if isinstance(child, ast.Name):
                deps.add(child.id)
            elif isinstance(child, ast.Attribute):
                # For obj.method calls, add the base object
                if isinstance(child.value, ast.Name):
                    deps.add(child.value.id)

        # Filter out built-ins and local variables
        filtered_deps = []
        for dep in deps:
            if not dep.startswith("_") and dep not in {"self", "cls"}:
                filtered_deps.append(dep)

        return filtered_deps[:10]  # Limit to top 10 dependencies


class PythonASTParser:
    """
    Advanced Python AST parser for extracting structured code elements.

    Provides sophisticated parsing of Python source code to extract functions,
    classes, methods, and other code elements with rich metadata for semantic
    indexing and retrieval.
    """

    def __init__(self):
        """Initialize the Python AST parser."""
        self.logger = get_logger(__name__)

    def parse_file(self, file_path: str) -> ParsingResult:
        """
        Parse a Python file and extract code elements.
        
        Parameters:
            file_path (str): Path to the Python file to parse.
        
        Returns:
            result (ParsingResult): Parsing outcome containing:
                - success (bool): Whether parsing succeeded.
                - file_path (str): The parsed file path.
                - elements (list[CodeElement]): Extracted code elements (may be empty).
                - errors (list[str]): Error messages if parsing failed.
                - warnings (list[str]): Non-fatal parsing warnings.
                - processing_time_ms (int): Time spent parsing in milliseconds.
        """
        start_time = datetime.now()

        try:
            # Read the file
            path = Path(file_path)
            if not path.exists():
                return ParsingResult(
                    success=False,
                    file_path=file_path,
                    errors=[f"File not found: {file_path}"],
                )

            source_code = path.read_text(encoding="utf-8")
            result = self.parse_source(source_code, file_path)

            # Update timing
            processing_time = (datetime.now() - start_time).total_seconds() * 1000
            result.processing_time_ms = int(processing_time)

            return result

        except Exception as e:
            self.logger.error(f"Failed to parse file {file_path}: {e}")
            return ParsingResult(
                success=False, file_path=file_path, errors=[f"Parsing error: {str(e)}"]
            )

    def parse_source(
        self, source_code: str, file_path: Optional[str] = None
    ) -> ParsingResult:
        """
        Parse Python source code and extract structured code elements.
        
        Parameters:
            source_code (str): Python source to parse.
            file_path (Optional[str]): Optional file path used for context (affects module element name and log messages).
        
        Returns:
            ParsingResult: Result of parsing. `success` is `True` when parsing completed without exception; `elements` contains extracted CodeElement instances (a module element may be prepended when module-level code is present); `errors` and `warnings` record parsing issues; `total_lines` is set to the number of source lines.
        """
        result = ParsingResult(success=False, file_path=file_path)

        try:
            # Parse the AST
            tree = ast.parse(source_code)
            source_lines = source_code.split("\n")
            result.total_lines = len(source_lines)

            # Create visitor and extract elements
            visitor = ASTVisitor(source_lines, file_path)
            visitor.visit(tree)

            result.elements = visitor.elements
            result.success = True

            # Add module-level element if there are module-level statements
            if self._has_module_level_code(tree):
                module_element = self._create_module_element(source_code, file_path)
                result.elements.insert(0, module_element)

            self.logger.info(
                f"Successfully parsed {file_path or 'source'}: "
                f"{result.element_count} elements extracted"
            )

        except SyntaxError as e:
            error_msg = f"Syntax error: {e.msg} at line {e.lineno}"
            result.errors.append(error_msg)
            self.logger.warning(f"Syntax error in {file_path or 'source'}: {error_msg}")

        except Exception as e:
            error_msg = f"Parsing error: {str(e)}"
            result.errors.append(error_msg)
            self.logger.error(f"Failed to parse {file_path or 'source'}: {error_msg}")

        return result

    def _has_module_level_code(self, tree: ast.AST) -> bool:
        """
        Determine whether an AST tree contains at least three significant top-level statements (ignoring module docstrings).
        
        Parameters:
            tree (ast.AST): The AST node to inspect, typically the module-level AST.
        
        Returns:
            `true` if the tree contains three or more significant top-level nodes (assignments, expressions excluding docstrings, if/for/while), `false` otherwise.
        """
        significant_nodes = 0

        for node in ast.walk(tree):
            if isinstance(node, (ast.Assign, ast.Expr, ast.If, ast.For, ast.While)):
                # Skip docstrings
                if isinstance(node, ast.Expr) and isinstance(node.value, ast.Constant):
                    if isinstance(node.value.value, str):
                        continue
                significant_nodes += 1
                if significant_nodes >= 3:  # Threshold for significant code
                    return True

        return False

    def _create_module_element(
        self, source_code: str, file_path: Optional[str]
    ) -> CodeElement:
        """
        Create a CodeElement representing the module defined by the given source.
        
        The returned element contains the module docstring (if present), the original source, the file path (if provided), a name derived from the file path stem or `"module"` when no path is given, and a line range that spans the source.
        
        Parameters:
            source_code (str): Complete source code of the module.
            file_path (Optional[str]): Path to the source file; used to derive the module name when provided.
        
        Returns:
            CodeElement: A module-level CodeElement populated with name, qualified_name, source_code, docstring, file_path, line_start, line_end, and tags indicating module/top-level.
        """
        tree = ast.parse(source_code)
        docstring = ast.get_docstring(tree)

        # Extract module name from file path
        module_name = "module"
        if file_path:
            module_name = Path(file_path).stem

        return CodeElement(
            element_type=CodeElementType.MODULE,
            name=module_name,
            qualified_name=module_name,
            source_code=source_code,
            docstring=docstring,
            file_path=file_path,
            line_start=1,
            line_end=len(source_code.split("\n")),
            tags={"module", "top-level"},
        )

    def parse_directory(
        self, directory_path: str, recursive: bool = True, file_pattern: str = "*.py"
    ) -> List[ParsingResult]:
        """
        Parse Python files in a directory and return a ParsingResult for each file processed.
        
        Parameters:
            directory_path (str): Path to the directory to search for Python files.
            recursive (bool): If true, include files in subdirectories.
            file_pattern (str): Glob pattern for matching files (currently unused; default `"*.py"`).
        
        Returns:
            List[ParsingResult]: A list of parsing results, one per file examined.
        """
        results = []
        path = Path(directory_path)

        if not path.exists():
            self.logger.error(f"Directory not found: {directory_path}")
            return results

        # Find Python files
        pattern = "**/*.py" if recursive else "*.py"
        python_files = list(path.glob(pattern))

        self.logger.info(f"Found {len(python_files)} Python files in {directory_path}")

        for file_path in python_files:
            try:
                result = self.parse_file(str(file_path))
                results.append(result)
            except Exception as e:
                self.logger.error(f"Failed to parse {file_path}: {e}")
                results.append(
                    ParsingResult(
                        success=False,
                        file_path=str(file_path),
                        errors=[f"Parsing failed: {str(e)}"],
                    )
                )

        successful_parses = len([r for r in results if r.success])
        self.logger.info(
            f"Parsed {successful_parses}/{len(results)} files successfully"
        )

        return results


def extract_code_elements(
    source_code: str, file_path: Optional[str] = None
) -> List[CodeElement]:
    """
    Convenience function that extracts CodeElement objects from Python source.
    
    Parameters:
        source_code (str): Python source code to parse.
        file_path (Optional[str]): Optional file path used for context (for example to derive module name and locations).
    
    Returns:
        List[CodeElement]: A list of extracted CodeElement instances; an empty list if parsing failed.
    """
    parser = PythonASTParser()
    result = parser.parse_source(source_code, file_path)
    return result.elements if result.success else []