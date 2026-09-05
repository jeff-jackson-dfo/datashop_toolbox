import ast, os, sys

def get_docstring_summary(node):
    doc = ast.get_docstring(node, clean=True)
    if not doc:
        return "", ""
    lines = doc.strip().split("\n")
    summary = lines[0].strip()
    return summary, doc

def format_args(node):
    a = node.args
    parts = []
    defaults = [None]*(len(a.args)-len(a.defaults)) + list(a.defaults)
    for arg, default in zip(a.args, defaults):
        if arg.arg == "self":
            continue
        s = arg.arg
        if arg.annotation is not None:
            try:
                s += f": {ast.unparse(arg.annotation)}"
            except Exception:
                pass
        if default is not None:
            try:
                s += f" = {ast.unparse(default)}"
            except Exception:
                pass
        parts.append(s)
    if a.vararg:
        parts.append(f"*{a.vararg.arg}")
    for kwarg, default in zip(a.kwonlyargs, a.kw_defaults):
        s = kwarg.arg
        if default is not None:
            try:
                s += f"={ast.unparse(default)}"
            except Exception:
                pass
        parts.append(s)
    if a.kwarg:
        parts.append(f"**{a.kwarg.arg}")
    ret = ""
    if node.returns is not None:
        try:
            ret = f" -> {ast.unparse(node.returns)}"
        except Exception:
            pass
    return f"({', '.join(parts)}){ret}"


def get_all(tree):
    for node in tree.body:
        if isinstance(node, ast.Assign):
            for t in node.targets:
                if isinstance(t, ast.Name) and t.id == "__all__":
                    try:
                        return ast.literal_eval(node.value)
                    except Exception:
                        return []
    return []

def process_file(path):
    with open(path, encoding="utf-8") as f:
        src = f.read()
    tree = ast.parse(src)
    mod_doc = ast.get_docstring(tree, clean=True) or ""
    mod_summary = mod_doc.strip().split("\n")[0] if mod_doc else ""
    all_exports = get_all(tree)
    classes = []
    functions = []
    for node in tree.body:
        if isinstance(node, ast.ClassDef):
            bases = []
            for b in node.bases:
                try:
                    bases.append(ast.unparse(b))
                except Exception:
                    pass
            csum, cdoc = get_docstring_summary(node)
            methods = []
            for item in node.body:
                if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    if item.name.startswith("__") and item.name != "__init__":
                        continue
                    msum, mdoc = get_docstring_summary(item)
                    decorators = []
                    for d in item.decorator_list:
                        try:
                            decorators.append(ast.unparse(d))
                        except Exception:
                            pass
                    methods.append({
                        "name": item.name,
                        "args": format_args(item),
                        "summary": msum,
                        "decorators": decorators,
                    })
            classes.append({
                "name": node.name,
                "bases": bases,
                "summary": csum,
                "doc": cdoc,
                "methods": methods,
            })
        elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            if node.name == "main":
                continue
            fsum, fdoc = get_docstring_summary(node)
            functions.append({
                "name": node.name,
                "args": format_args(node),
                "summary": fsum,
            })
    return {
        "module_summary": mod_summary,
        "classes": classes,
        "functions": functions,
        "all_exports": all_exports,
    }

if __name__ == "__main__":
    import json
    path = sys.argv[1]
    print(json.dumps(process_file(path), indent=2))
