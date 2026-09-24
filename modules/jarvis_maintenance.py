"""
JARVIS Autonomous Codebase Maintainer
Overnight worker to scan for complexity and unused variables.
"""
import os
import ast
import datetime
from pathlib import Path

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
REPORT_DIR = os.path.join(BASE_DIR, "reports")

def scan_and_refactor_codebase() -> str:
    """
    Scans Python files in BASE_DIR for complexity and issues.
    Generates a markdown report instead of directly modifying code for safety.
    """
    os.makedirs(REPORT_DIR, exist_ok=True)
    report_file = os.path.join(REPORT_DIR, f"upgrade_report_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.md")
    
    report_lines = [
        f"# JARVIS Autonomous Maintenance Report",
        f"**Date:** {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        f"**Target:** {BASE_DIR}",
        "",
        "## Complexity Analysis",
    ]
    
    py_files = list(Path(BASE_DIR).glob("*.py"))
    
    total_lines = 0
    complex_functions = []
    
    for py_file in py_files:
        try:
            with open(py_file, "r", encoding="utf-8") as f:
                source = f.read()
                total_lines += len(source.splitlines())
                
                tree = ast.parse(source)
                
                for node in ast.walk(tree):
                    if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                        
                        num_stmts = sum(1 for _ in ast.walk(node))
                        if num_stmts > 100:
                            complex_functions.append((py_file.name, node.name, num_stmts))
        except Exception as e:
            pass

    report_lines.append(f"- **Total Lines of Code Scanned:** {total_lines}")
    report_lines.append(f"- **Total Python Files:** {len(py_files)}")
    report_lines.append("")
    report_lines.append("### High Complexity Functions (Refactor Recommended)")
    
    for fn in sorted(complex_functions, key=lambda x: x[2], reverse=True)[:10]:
        report_lines.append(f"- `{fn[1]}` in `{fn[0]}` (Complexity Score: {fn[2]})")
        
    report_lines.append("\n## Dead Code / Unused Imports Analysis")
    report_lines.append("> (Static analysis phase currently uses AST statement counting. Full dead-code tracking requires vulture/flake8 integration.)")
    
    with open(report_file, "w", encoding="utf-8") as f:
        f.write("\n".join(report_lines))
        
    return f"ระบบได้สแกนและวิเคราะห์โค้ดเสร็จสิ้น สร้างรายงานไว้ที่ {report_file} เรียบร้อยครับเจ้านาย"

if __name__ == "__main__":
    print(scan_and_refactor_codebase())
