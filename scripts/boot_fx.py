"""
scripts/boot_fx.py
==================
High-tech visual & audio terminal effects for J.A.R.V.I.S. Mainframe Boot.
Provides:
  - Typewriter text effect
  - Real-time animated loading bar [■■■■□□□□□□]
  - Status checklists with sleek icons
"""
import sys
import time

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

CYAN = "\033[36m"
BLUE = "\033[94m"
WHITE = "\033[97m"
GREEN = "\033[92m"
YELLOW = "\033[93m"
RESET = "\033[0m"

def typewriter(text: str, delay: float = 0.02, color: str = WHITE, newline: bool = True):
    sys.stdout.write(color)
    for ch in text:
        sys.stdout.write(ch)
        sys.stdout.flush()
        time.sleep(delay)
    sys.stdout.write(RESET)
    if newline:
        sys.stdout.write("\n")
    sys.stdout.flush()

def loading_bar(label: str = "Synthesizing Neural Matrix", duration: float = 0.7, width: int = 24):
    steps = width
    step_delay = duration / steps
    for i in range(steps + 1):
        filled = "■" * i
        empty = "□" * (width - i)
        percent = int((i / steps) * 100)
        sys.stdout.write(f"\r  {CYAN}{label} {BLUE}[{CYAN}{filled}{WHITE}{empty}{BLUE}] {GREEN}{percent:>3}%{RESET}")
        sys.stdout.flush()
        time.sleep(step_delay)
    sys.stdout.write(f"  {GREEN}✔ COMPLETE{RESET}\n")
    sys.stdout.flush()

def status_item(label: str, status: str = "Active", delay: float = 0.05):
    dots_count = max(2, 46 - len(label))
    dots = "." * dots_count
    sys.stdout.write(f"  {GREEN}✔{RESET} {WHITE}{label}{RESET} {CYAN}{dots}{RESET} {GREEN}[ {status} ]{RESET}\n")
    sys.stdout.flush()
    time.sleep(delay)

if __name__ == "__main__":
    if len(sys.argv) < 2:
        sys.exit(0)
    
    cmd = sys.argv[1]
    if cmd == "--type":
        msg = sys.argv[2] if len(sys.argv) > 2 else ""
        color = sys.argv[3] if len(sys.argv) > 3 else "white"
        color_code = {"cyan": CYAN, "blue": BLUE, "white": WHITE, "green": GREEN, "yellow": YELLOW}.get(color.lower(), WHITE)
        delay = float(sys.argv[4]) if len(sys.argv) > 4 else 0.02
        typewriter(msg, delay=delay, color=color_code)
    elif cmd == "--bar":
        label = sys.argv[2] if len(sys.argv) > 2 else "Loading Subsystems"
        duration = float(sys.argv[3]) if len(sys.argv) > 3 else 0.7
        loading_bar(label, duration=duration)
    elif cmd == "--status":
        label = sys.argv[2] if len(sys.argv) > 2 else "System"
        status = sys.argv[3] if len(sys.argv) > 3 else "Active"
        status_item(label, status)
