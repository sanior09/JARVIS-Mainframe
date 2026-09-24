import os


def check_fixes():
    with open('jarvis.py', 'r', encoding='utf-8') as f:
        content = f.read()
        
    with open('script.js', 'r', encoding='utf-8') as f:
        script_content = f.read()

    checks = {
        'BUG-001 (del response guard)': 'except NameError:' in content or 'del response' not in content,
        'BUG-004 (SQLite check_same_thread=False)': 'check_same_thread=False' in content and 'jarvis_checkpoints.sqlite' in content,
        'Language Policy (Katakana fix)': 'STRICT LANGUAGE POLICY' in content,
        'Real name removed (ณชพล)': 'ณชพล' not in content,
        'script.js (MAX_SPEECH_QUEUE guard)': 'MAX_SPEECH_QUEUE' in script_content
    }

    for name, status in checks.items():
        print(f"[{'OK' if status else 'MISSING'}] {name}")

if __name__ == '__main__':
    check_fixes()
