"""
Purpose: วิเคราะห์โครงสร้างโค้ด Python ที่มีการทำงานหนักหรือใช้ทรัพยากรสูง เพื่อค้นหาคอขวด (Bottlenecks) แนะนำการปรับสถาปัตยกรรม (Refactoring) และสร้าง Patch เพื่อเพิ่มประสิทธิภาพการประมวลผลแบบ Real-time
Created: 2026-09-15 22:02:25.542587
"""

"""Neural Code Optimization Engine: Analyzes Python code for bottlenecks and suggests optimizations."""

import ast
import inspect
import re
from typing import Any, Dict, List, Optional, Tuple


TOOL_SCHEMA: Dict[str, Any] = {
    "type": "function",
    "function": {
        "name": "neural_code_optimizer",
        "description": "Analyzes Python code for performance bottlenecks, suggests refactoring, and generates optimization patches.",
        "parameters": {
            "type": "object",
            "properties": {
                "code": {
                    "type": "string",
                    "description": "The Python source code to analyze for performance bottlenecks."
                },
                "optimization_level": {
                    "type": "integer",
                    "description": "Aggressiveness of optimization (1=conservative, 2=moderate, 3=aggressive).",
                    "default": 2,
                    "minimum": 1,
                    "maximum": 3
                },
                "target_runtime": {
                    "type": "string",
                    "description": "Target runtime environment for optimizations (e.g., 'cpython', 'pypy', 'numba').",
                    "default": "cpython"
                }
            },
            "required": ["code"]
        }
    }
}


def _analyze_ast_for_bottlenecks(tree: ast.AST) -> List[Dict[str, Any]]:
    """
    Analyzes the AST of Python code to identify common performance bottlenecks.
    
    Args:
        tree: The parsed AST of the source code.
        
    Returns:
        List of bottleneck findings with location and description.
    """
    bottlenecks: List[Dict[str, Any]] = []
    
    class BottleneckFinder(ast.NodeVisitor):
        def __init__(self) -> None:
            self.in_nested_loop = 0
            self.loop_depth = 0
            
        def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
            self.generic_visit(node)
            
        def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:
            self.generic_visit(node)
            
        def visit_For(self, node: ast.For) -> None:
            self.loop_depth += 1
            if self.loop_depth > 3:
                bottlenecks.append({
                    "type": "deeply_nested_loop",
                    "line": node.lineno,
                    "description": f"Loop nested {self.loop_depth} levels deep. Consider flattening or using vectorized operations.",
                    "severity": "high"
                })
            self.generic_visit(node)
            self.loop_depth -= 1
            
        def visit_While(self, node: ast.While) -> None:
            self.loop_depth += 1
            if self.loop_depth > 3:
                bottlenecks.append({
                    "type": "deeply_nested_loop",
                    "line": node.lineno,
                    "description": f"While loop nested {self.loop_depth} levels deep. Consider refactoring for better performance.",
                    "severity": "high"
                })
            self.generic_visit(node)
            self.loop_depth -= 1
            
        def visit_Call(self, node: ast.Call) -> None:
            if isinstance(node.func, ast.Name):
                if node.func.id in ('open', 'requests.get', 'requests.post', 'urllib.request.urlopen'):
                    if self.loop_depth > 0:
                        bottlenecks.append({
                            "type": "io_in_loop",
                            "line": node.lineno,
                            "description": "I/O operation inside a loop. Consider batching or async I/O.",
                            "severity": "high"
                        })
                if node.func.id == 'append' and self.loop_depth > 0:
                    pass
            self.generic_visit(node)
            
        def visit_BinOp(self, node: ast.BinOp) -> None:
            if isinstance(node.op, ast.Pow) and self.loop_depth > 0:
                bottlenecks.append({
                    "type": "expensive_math_in_loop",
                    "line": node.lineno,
                    "description": "Exponentiation inside a loop. Consider precomputing or using math functions.",
                    "severity": "medium"
                })
            self.generic_visit(node)
            
        def visit_Subscript(self, node: ast.Subscript) -> None:
            self.generic_visit(node)
            
        def visit_ListComp(self, node: ast.ListComp) -> None:
            self.generic_visit(node)
            
        def visit_DictComp(self, node: ast.DictComp) -> None:
            self.generic_visit(node)
            
        def visit_GeneratorExp(self, node: ast.GeneratorExp) -> None:
            self.generic_visit(node)
            
        def visit_If(self, node: ast.If) -> None:
            if self.loop_depth > 0 and len(node.orelse) == 0:
                # Check if it's a simple if without else inside loop
                pass
            self.generic_visit(node)
            
    BottleneckFinder().visit(tree)
    return bottlenecks


def _suggest_refactoring(bottlenecks: List[Dict[str, Any]], optimization_level: int) -> List[Dict[str, Any]]:
    """
    Generates refactoring suggestions based on identified bottlenecks.
    
    Args:
        bottlenecks: List of identified bottlenecks.
        optimization_level: The aggressiveness level (1-3).
        
    Returns:
        List of refactoring suggestions.
    """
    suggestions: List[Dict[str, Any]] = []
    seen_types = set()
    
    for b in bottlenecks:
        btype = b["type"]
        if btype in seen_types:
            continue
        seen_types.add(btype)
        
        if btype == "deeply_nested_loop":
            if optimization_level >= 2:
                suggestions.append({
                    "type": "flatten_loops",
                    "description": "Flatten nested loops using list comprehensions or itertools.product where possible.",
                    "example": "for x in range(n):\n    for y in range(m):\n        f(x, y)"
                    " => [f(x, y) for x in range(n) for y in range(m)]"
                })
            else:
                suggestions.append({
                    "type": "extract_loop_body",
                    "description": "Extract inner loop body into a separate function for clarity and potential caching.",
                    "example": "def inner_loop(x, data):\n    ..."
                })
                
        elif btype == "io_in_loop":
            if optimization_level >= 2:
                suggestions.append({
                    "type": "batch_io",
                    "description": "Batch I/O operations or use async I/O (asyncio/aiohttp) to reduce overhead.",
                    "example": "Use aiohttp.ClientSession with asyncio.gather() for concurrent requests."
                })
            else:
                suggestions.append({
                    "type": "cache_io_results",
                    "description": "Cache I/O results if data is repeated, or move I/O outside the loop.",
                    "example": "Load all data upfront, then process in memory."
                })
                
        elif btype == "expensive_math_in_loop":
            suggestions.append({
                "type": "vectorize_math",
                "description": "Use numpy or numba for vectorized math operations instead of Python loops.",
                "example": "import numpy as np; result = np.power(arr, exponent)"
            })
            
    return suggestions


def _generate_patch(source_code: str, bottlenecks: List[Dict[str, Any]], 
                    suggestions: List[Dict[str, Any]], optimization_level: int) -> str:
    """
    Generates a patch string with optimization comments and suggested changes.
    
    Args:
        source_code: The original Python source code.
        bottlenecks: List of identified bottlenecks.
        suggestions: List of refactoring suggestions.
        optimization_level: The aggressiveness level (1-3).
        
    Returns:
        A string containing the patch with annotated suggestions.
    """
    lines = source_code.split('\n')
    patch_lines: List[str] = []
    lines_to_patch = {b["line"]: b for b in bottlenecks}
    
    for i, line in enumerate(lines, start=1):
        if i in lines_to_patch:
            b = lines_to_patch[i]
            patch_lines.append(f"# [OPTIMIZATION: {b['type']}] {b['description']}")
            patch_lines.append(line)
        else:
            patch_lines.append(line)
    
    if suggestions:
        patch_lines.append("")
        patch_lines.append("# === SUGGESTED REFACTORING ===")
        for s in suggestions:
            patch_lines.append(f"# - {s['description']}")
            if 'example' in s:
                patch_lines.append(f"#   Example: {s['example']}")
    
    return '\n'.join(patch_lines)


def neural_code_optimizer(code: str, optimization_level: int = 2, target_runtime: str = "cpython") -> Dict[str, Any]:
    """
    Main function to analyze Python code for performance bottlenecks and generate optimization patches.
    
    Args:
        code: The Python source code to analyze.
        optimization_level: Aggressiveness of optimization (1=conservative, 2=moderate, 3=aggressive).
        target_runtime: Target runtime environment (e.g., 'cpython', 'pypy', 'numba').
        
    Returns:
        Dictionary containing:
        - 'bottlenecks': List of identified bottlenecks
        - 'suggestions': List of refactoring suggestions
        - 'patch': Generated optimization patch
        - 'summary': Human-readable summary of findings
    """
    try:
        tree = ast.parse(code)
    except SyntaxError as e:
        return {
            "error": f"Failed to parse code: {e}",
            "bottlenecks": [],
            "suggestions": [],
            "patch": code,
            "summary": "Code could not be parsed due to syntax errors."
        }
    
    bottlenecks = _analyze_ast_for_bottlenecks(tree)
    suggestions = _suggest_refactoring(bottlenecks, optimization_level)
    patch = _generate_patch(code, bottlenecks, suggestions, optimization_level)
    
    severity_counts = {"high": 0, "medium": 0, "low": 0}
    for b in bottlenecks:
        sev = b.get("severity", "low")
        if sev in severity_counts:
            severity_counts[sev] += 1
    
    summary = (
        f"Analyzed code for {target_runtime} at optimization level {optimization_level}. "
        f"Found {len(bottlenecks)} bottleneck(s): "
        f"{severity_counts['high']} high, {severity_counts['medium']} medium, {severity_counts['low']} low severity. "
        f"Generated {len(suggestions)} refactoring suggestion(s)."
    )
    
    return {
        "bottlenecks": bottlenecks,
        "suggestions": suggestions,
        "patch": patch,
        "summary": summary
    }


if __name__ == "__main__":
    sample_code = """
import time

def process_data(data):
    results = []
    for i in range(len(data)):
        for j in range(len(data)):
            for k in range(len(data)):
                results.append(data[i] * data[j] * data[k])
    return results

def fetch_and_process(urls):
    results = []
    for url in urls:
        time.sleep(0.1)
        results.append(url)
    return results
"""
    
    result = neural_code_optimizer(sample_code, optimization_level=2)
    print(result["summary"])
    print("\nBottlenecks:")
    for b in result["bottlenecks"]:
        print(f"  Line {b['line']}: [{b['severity']}] {b['description']}")
    print("\nSuggestions:")
    for s in result["suggestions"]:
        print(f"  - {s['description']}")
    print("\nPatch:")
    print(result["patch"])