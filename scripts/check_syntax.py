import os
import ast

def check_syntax_in_dir(directory):
    error_count = 0
    for root, dirs, files in os.walk(directory):
        # Exclude directories
        for skip in ['venv', '.venv', 'jarvis_env', 'backups', 'node_modules', '__pycache__', '.git', '.pytest_cache']:
            if skip in dirs:
                dirs.remove(skip)
        
        for file in files:
            if file.endswith('.py'):
                file_path = os.path.join(root, file)
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        source = f.read()
                    ast.parse(source, filename=file_path)
                except SyntaxError as e:
                    print(f"Syntax Error in {file_path}: {e}")
                    error_count += 1
                except Exception as e:
                    print(f"Other Error in {file_path}: {e}")
                    error_count += 1
                    
    if error_count == 0:
        print("All Python files compiled successfully without syntax errors!")
    else:
        print(f"Found {error_count} files with errors.")

if __name__ == "__main__":
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    check_syntax_in_dir(base_dir)
