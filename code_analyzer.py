import ast

class SecurityVisitor(ast.NodeVisitor):
    def __init__(self):
        self.privacy_libs = []
        self.unsafe_calls = []
        self.hardcoded_secrets = []

    def visit_Import(self, node):
        for alias in node.names: self._check_lib(alias.name)
        self.generic_visit(node)

    def visit_ImportFrom(self, node):
        if node.module: self._check_lib(node.module)
        self.generic_visit(node)

    def _check_lib(self, lib_name):
        lib = lib_name.lower()
        whitelist = ['opacus', 'tensorflow_privacy', 'diffprivlib', 'presidio', 'faker', 'cryptography', 'hashlib', 'shap', 'lime']
        if any(p in lib for p in whitelist):
            if lib_name not in self.privacy_libs: self.privacy_libs.append(lib_name)

    def visit_Call(self, node):
        if isinstance(node.func, ast.Attribute) and isinstance(node.func.value, ast.Name):
            if node.func.value.id == 'pickle' and node.func.attr in ['load', 'loads']:
                self.unsafe_calls.append("pickle.load (Deserialization Vulnerability)")
        self.generic_visit(node)

    def visit_Assign(self, node):
        for target in node.targets:
            if isinstance(target, ast.Name):
                var_name = target.id.lower()
                if any(k in var_name for k in ['password', 'secret', 'api_key', 'token']):
                    if isinstance(node.value, ast.Constant) and isinstance(node.value.value, str):
                        if len(node.value.value) > 5:
                            self.hardcoded_secrets.append(f"Hardcoded Secret detected: {target.id}")
        self.generic_visit(node)

def check_code_privacy_security(file_content):
    report = {"has_risk": False, "privacy_libs": [], "unsafe_calls": [], "hardcoded_secrets": []}
    try:
        if not file_content: return report
        tree = ast.parse(file_content)
        visitor = SecurityVisitor()
        visitor.visit(tree)
        report["privacy_libs"] = visitor.privacy_libs
        report["unsafe_calls"] = visitor.unsafe_calls
        report["hardcoded_secrets"] = visitor.hardcoded_secrets
        if report["unsafe_calls"] or report["hardcoded_secrets"]: report["has_risk"] = True
    except: pass
    return report