# Implements: WC-036 — WC036-03
# constitutional_basis: C-082 (Build Validation), ADR-039 §5.3
from __future__ import annotations

import ast
import textwrap
from pathlib import Path


class Track2SpliceError(ValueError):
    pass


class Track2PolymorphicEngine:
    """
    Surgically extracts and splices AST function/method nodes.

    Supports:
    - Class methods: find_target_node(name, class_name="ClassName")
    - Top-level functions: find_target_node(name, class_name=None)

    ADR-039 §5.3 requirements:
    - extract_node_for_llm() strips decorators via try/finally (no permanent AST mutation)
    - splice_node_safely() enforces signature lock, extracts decorator lines verbatim
      from source, applies ast.unparse() only to the def+body block, compile() gate before write
    - No astor dependency — ast.unparse() (stdlib 3.9+) only
    """

    def __init__(self, file_path: Path) -> None:
        self.file_path = file_path
        self._reload()

    # ── Public API ────────────────────────────────────────────────────────────

    def find_target_node(
        self,
        target_name: str,
        class_name: str | None = None,
    ) -> ast.FunctionDef | ast.AsyncFunctionDef:
        if class_name:
            for node in ast.walk(self.tree):
                if isinstance(node, ast.ClassDef) and node.name == class_name:
                    for child in node.body:
                        if (
                            isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef))
                            and child.name == target_name
                        ):
                            return child
            raise Track2SpliceError(
                f"Method '{class_name}.{target_name}' not found in '{self.file_path}'"
            )
        for node in ast.iter_child_nodes(self.tree):
            if (
                isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
                and node.name == target_name
            ):
                return node
        raise Track2SpliceError(
            f"Top-level function '{target_name}' not found in '{self.file_path}'"
        )

    def extract_node_for_llm(
        self,
        target_name: str,
        class_name: str | None = None,
    ) -> str:
        """
        Returns the function/method as a string with decorators stripped so the
        LLM does not hallucinate decorator mutations.
        Uses try/finally to restore decorator_list — prevents permanent AST mutation.
        """
        node = self.find_target_node(target_name, class_name)
        saved = node.decorator_list
        try:
            node.decorator_list = []
            result = ast.unparse(node)
        finally:
            node.decorator_list = saved
        return result

    def splice_node_safely(
        self,
        target_name: str,
        new_logic: str,
        class_name: str | None = None,
        locked_signature: str | None = None,
    ) -> None:
        """
        Replaces the target function/method with new_logic in-place.

        new_logic: complete 'def name(...):\\n    body' block (no decorators).

        Invariants enforced (ADR-039 §5.3):
        - locked_signature: asserts original and new function signatures are identical
        - compile() gate: rejects syntactically invalid new_logic before any file write
        - Decorator lines: extracted verbatim from source_lines (no reformatting)
        - ast.unparse() applies only to def+body — avoids double-indent on decorators
        """
        node = self.find_target_node(target_name, class_name)

        if locked_signature:
            actual = _signature_string(node)
            if actual != locked_signature.strip():
                raise Track2SpliceError(
                    f"Original signature does not match lock: "
                    f"expected '{locked_signature.strip()}', found '{actual}'"
                )

        # Parse and validate the replacement node
        try:
            new_tree = ast.parse(textwrap.dedent(new_logic))
        except SyntaxError as exc:
            raise Track2SpliceError(f"new_logic parse error: {exc}") from exc

        new_nodes = [
            n for n in new_tree.body
            if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))
        ]
        if not new_nodes:
            raise Track2SpliceError("No function definition found in new_logic")
        new_node = new_nodes[0]

        if locked_signature:
            new_sig = _signature_string(new_node)
            if new_sig != locked_signature.strip():
                raise Track2SpliceError(
                    f"LLM mutated signature: expected '{locked_signature.strip()}', "
                    f"got '{new_sig}'"
                )

        # Determine indentation of original function (from its def line)
        def_line_0 = node.lineno - 1  # 0-based
        original_def_line = self.source_lines[def_line_0]
        indent = len(original_def_line) - len(original_def_line.lstrip())
        indent_str = " " * indent

        # Collect decorator lines verbatim (already carry correct indentation + newlines)
        decorator_lines = self._decorator_source_lines(node)

        # Build replacement: decorators verbatim + def+body with indent_str prepended
        replacement: list[str] = list(decorator_lines)
        unparsed = ast.unparse(new_node)  # unindented def+body
        for raw in unparsed.splitlines():
            if raw.strip():
                replacement.append(indent_str + raw + "\n")
            else:
                replacement.append("\n")

        # Slice range: first decorator (or def line) through end of body
        start_0 = (
            node.decorator_list[0].lineno - 1
            if node.decorator_list
            else def_line_0
        )
        end_0 = node.end_lineno  # 1-based inclusive → 0-based exclusive for slicing

        new_source = "".join(
            self.source_lines[:start_0] + replacement + self.source_lines[end_0:]
        )

        try:
            compile(new_source, str(self.file_path), "exec")
        except SyntaxError as exc:
            raise Track2SpliceError(
                f"Splice compile gate failed for '{self.file_path}': {exc}"
            ) from exc

        self.file_path.write_text(new_source, encoding="utf-8")
        self._reload()

    # ── Private helpers ───────────────────────────────────────────────────────

    def _reload(self) -> None:
        self.source = self.file_path.read_text(encoding="utf-8")
        self.source_lines = self.source.splitlines(keepends=True)
        self.tree = ast.parse(self.source, filename=str(self.file_path))

    def _decorator_source_lines(
        self, node: ast.FunctionDef | ast.AsyncFunctionDef
    ) -> list[str]:
        if not node.decorator_list:
            return []
        first_dec_0 = node.decorator_list[0].lineno - 1
        def_line_0 = node.lineno - 1
        return self.source_lines[first_dec_0:def_line_0]


def _signature_string(node: ast.FunctionDef | ast.AsyncFunctionDef) -> str:
    """Returns 'def name(args) -> ret:' string without body or decorators."""
    args_str = ast.unparse(node.args)
    ret_str = f" -> {ast.unparse(node.returns)}" if node.returns else ""
    prefix = "async def" if isinstance(node, ast.AsyncFunctionDef) else "def"
    return f"{prefix} {node.name}({args_str}){ret_str}:"
