import os
import sys
import threading
import time
import tkinter as tk

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
LOCK_FILE = os.path.join(BASE_DIR, "system_cache", "lockdown.lock")
PIN = os.getenv("LOCKDOWN_PIN", "140952").strip()


def start_lockdown():
    # Record lock state for mobile app / backend sync
    os.makedirs(os.path.dirname(LOCK_FILE), exist_ok=True)
    try:
        with open(LOCK_FILE, "w", encoding="utf-8") as f:
            f.write(f"LOCKED:{os.getpid()}")
    except Exception:
        pass

    root = tk.Tk()
    root.attributes('-fullscreen', True)
    root.attributes('-topmost', True)
    root.configure(background='black')
    root.config(cursor="none")  # Hide mouse cursor

    def disable_event():
        pass

    # Prevent Alt+F4
    root.protocol("WM_DELETE_WINDOW", disable_event)

    # Listen for unlock command from parent process (stdin or lock file)
    def check_unlock():
        while True:
            try:
                # Check lock file signal
                if os.path.exists(LOCK_FILE):
                    try:
                        with open(LOCK_FILE, "r", encoding="utf-8") as f:
                            content = f.read().strip()
                        if content == "UNLOCK":
                            try:
                                root.after(0, root.destroy)
                            except Exception:
                                pass
                            time.sleep(0.1)
                            sys.exit(0)
                    except Exception:
                        pass

                # Check stdin if available
                if sys.stdin and not sys.stdin.closed:
                    line = sys.stdin.readline()
                    if not line:
                        break
                    if 'UNLOCK' in line.upper():
                        try:
                            root.after(0, root.destroy)
                        except Exception:
                            pass
                        time.sleep(0.1)
                        sys.exit(0)
            except Exception:
                break
            time.sleep(0.4)
        sys.exit(0)

    t = threading.Thread(target=check_unlock, daemon=True)
    t.start()

    frame = tk.Frame(root, bg="black")
    frame.place(relx=0.5, rely=0.5, anchor="center")

    lbl_title = tk.Label(frame, text="J.A.R.V.I.S.", fg="red", bg="black", font=("Arial", 64, "bold"))
    lbl_title.pack(pady=10)

    lbl_subtitle = tk.Label(frame, text="UNAUTHORIZED ACCESS DETECTED", fg="red", bg="black", font=("Arial", 32, "bold"))
    lbl_subtitle.pack(pady=10)

    lbl_status = tk.Label(frame, text="SYSTEM LOCKED", fg="white", bg="black", font=("Arial", 20))
    lbl_status.pack(pady=40)

    def check_pin(event):
        typed_pin = entry.get().strip()
        if typed_pin == "140952":
            try:
                if os.path.exists(LOCK_FILE):
                    os.remove(LOCK_FILE)
            except Exception:
                pass
            root.destroy()
            sys.exit(0)
        else:
            entry.delete(0, tk.END)
            lbl_status.config(text="ACCESS DENIED", fg="red")

            # Reset text back to SYSTEM LOCKED after 2s
            def reset_text():
                try:
                    lbl_status.config(text="SYSTEM LOCKED", fg="white")
                except Exception:
                    pass

            root.after(2000, reset_text)

    # Invisible entry for PIN
    entry = tk.Entry(
        frame,
        bg="black",
        fg="#222222",
        font=("Arial", 16),
        borderwidth=0,
        highlightthickness=0,
        insertbackground="black"
    )
    entry.pack()
    entry.focus_set()
    entry.bind("<Return>", check_pin)

    # Re-focus if user clicks away
    def keep_focus(event):
        entry.focus_set()

    root.bind("<Button-1>", keep_focus)

    # Blink animation
    def blink():
        try:
            current_color = lbl_subtitle.cget("fg")
            next_color = "black" if current_color == "red" else "red"
            lbl_subtitle.config(fg=next_color)
            root.after(800, blink)
        except Exception:
            pass

    blink()

    try:
        root.mainloop()
    finally:
        try:
            if os.path.exists(LOCK_FILE):
                os.remove(LOCK_FILE)
        except Exception:
            pass


if __name__ == "__main__":
    start_lockdown()
