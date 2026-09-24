import tkinter as tk
import sys
import threading
import time

def check_stdin():
    # If standard input is closed or sends 'UNLOCK', we exit.
    while True:
        try:
            line = sys.stdin.readline()
            if not line:
                break
            if 'UNLOCK' in line:
                sys.exit(0)
        except:
            break
        time.sleep(0.5)
    sys.exit(0)

# Thread to listen for unlock command from parent process
t = threading.Thread(target=check_stdin, daemon=True)
t.start()

root = tk.Tk()
root.attributes('-fullscreen', True)
root.attributes('-topmost', True)
root.configure(background='black')
root.config(cursor="none") # Hide mouse cursor

def disable_event():
    pass
# Prevent Alt+F4
root.protocol("WM_DELETE_WINDOW", disable_event)

frame = tk.Frame(root, bg="black")
frame.place(relx=0.5, rely=0.5, anchor="center")

lbl_title = tk.Label(frame, text="J.A.R.V.I.S.", fg="red", bg="black", font=("Arial", 64, "bold"))
lbl_title.pack(pady=10)

lbl_subtitle = tk.Label(frame, text="UNAUTHORIZED ACCESS DETECTED", fg="red", bg="black", font=("Arial", 32, "bold"))
lbl_subtitle.pack(pady=10)

lbl_status = tk.Label(frame, text="SYSTEM LOCKED", fg="white", bg="black", font=("Arial", 20))
lbl_status.pack(pady=40)

def check_pin(event):
    if entry.get().strip() == "1123":
        root.destroy()
        sys.exit(0)
    else:
        entry.delete(0, tk.END)
        lbl_status.config(text="ACCESS DENIED", fg="red")
        
        # Reset text back to SYSTEM LOCKED after 2s
        def reset_text():
            lbl_status.config(text="SYSTEM LOCKED", fg="white")
        root.after(2000, reset_text)

# Invisible entry for PIN
entry = tk.Entry(frame, bg="black", fg="#222222", font=("Arial", 16), borderwidth=0, highlightthickness=0, insertbackground="black")
entry.pack()
entry.focus_set()
entry.bind("<Return>", check_pin)

# Re-focus if user clicks away
def keep_focus(event):
    entry.focus_set()
root.bind("<Button-1>", keep_focus)

# Blink animation
def blink():
    current_color = lbl_subtitle.cget("fg")
    next_color = "black" if current_color == "red" else "red"
    lbl_subtitle.config(fg=next_color)
    root.after(800, blink)

blink()
root.mainloop()
