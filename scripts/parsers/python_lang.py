"""Python adapter — stdlib ast, zero dependencies."""
import ast

from parsers import Symbol


def parse(text):
    try:
        tree = ast.parse(text)
    except SyntaxError:
        return []
    syms = []
    for node in tree.body:
        _visit(node, syms, parent="")
    return syms


def _sig(node):
    sig = f"{node.name}({ast.unparse(node.args)})"
    if node.returns is not None:
        sig += f" -> {ast.unparse(node.returns)}"
    return sig


def _visit(node, syms, parent):
    if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
        kind = "m" if parent else "f"
        syms.append(Symbol(kind, node.name, _sig(node), node.lineno, parent))
    elif isinstance(node, ast.ClassDef):
        base = ", ".join(ast.unparse(b) for b in node.bases)
        syms.append(Symbol("c", node.name, node.name, node.lineno, "", base))
        for child in node.body:
            _visit(child, syms, parent=node.name)
