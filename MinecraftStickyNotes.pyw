import ctypes
import json
import os
import sys
import uuid
import tkinter as tk
from tkinter import messagebox
from pathlib import Path

APP_NAME = "Minecraft Sticky Notes"
APP_DIR = Path(os.getenv("LOCALAPPDATA", str(Path.home()))) / "MinecraftStickyNotes"
DATA_FILE = APP_DIR / "notes.json"
GRASS = "#5b9d32"
GRASS_DARK = "#356b25"
DIRT = "#795437"
DIRT_DARK = "#4c3425"
PAPER = "#fff6cc"
INK = "#26351f"
RED = "#b94a43"
PALE = "#f0e3ad"

PAPER_THEMES = {
    "Wheat": ("#fff6cc", "#26351f"),
    "Diamond": ("#d9f5f3", "#173c42"),
    "Nether": ("#f7d7d2", "#55221e"),
    "End": ("#e9defa", "#33244b"),
}

# Registry Run entry is more reliable than a generated VBS Startup file.
RUN_KEY = r"Software\Microsoft\Windows\CurrentVersion\Run"
RUN_VALUE = "MinecraftStickyNotes"

def app_command():
    if getattr(sys, "frozen", False):
        return '"' + str(Path(sys.executable).resolve()) + '"'
    pythonw = Path(sys.executable).with_name("pythonw.exe")
    if not pythonw.exists():
        pythonw = Path(sys.executable)
    return '"' + str(pythonw.resolve()) + '" "' + str(Path(sys.argv[0]).resolve()) + '"'

def startup_enabled():
    if os.name != "nt":
        return False
    try:
        import winreg
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, RUN_KEY, 0, winreg.KEY_READ) as key:
            winreg.QueryValueEx(key, RUN_VALUE)
        return True
    except (OSError, ImportError):
        return False

def set_startup(enabled):
    if os.name != "nt":
        raise OSError("Windows startup is available only on Windows.")
    import winreg
    with winreg.CreateKey(winreg.HKEY_CURRENT_USER, RUN_KEY) as key:
        if enabled:
            winreg.SetValueEx(key, RUN_VALUE, 0, winreg.REG_SZ, app_command())
        else:
            try:
                winreg.DeleteValue(key, RUN_VALUE)
            except FileNotFoundError:
                pass

class StickyNote:
    def __init__(self, app, data):
        self.app, self.data = app, data
        self.save_job = None
        self.drag_offset = None
        self.win = tk.Toplevel(app.root)
        self.win.overrideredirect(True)
        self.win.configure(bg=DIRT_DARK)
        self.win.geometry(f'{data.get("width", 320)}x{data.get("height", 310)}+{data.get("x", 150)}+{data.get("y", 130)}')
        # Important: notes are NOT topmost by default, so they don't cover other apps.
        self.win.attributes("-topmost", bool(data.get("always_on_top", False)))
        self.build_ui()
        self.win.bind("<Configure>", self.on_configure)
        self.win.bind("<Escape>", lambda _e: self.hide())
        self.win.bind("<Control-s>", lambda _e: self.persist())
        self.win.bind("<Control-Return>", lambda _e: self.insert_checklist_item())
        if not data.get("visible", True):
            self.win.withdraw()

    def build_ui(self):
        self.header = tk.Frame(self.win, bg=GRASS, height=35, cursor="fleur")
        self.header.pack(fill="x")
        self.header.pack_propagate(False)
        self.logo = tk.Canvas(self.header, width=27, height=27, bg=GRASS, highlightthickness=0)
        self.logo.pack(side="left", padx=(6, 2), pady=4)
        self.logo.create_rectangle(2, 2, 25, 25, fill=DIRT, outline="#244d1c", width=2)
        self.logo.create_rectangle(2, 2, 25, 10, fill="#83c94b", outline="#83c94b")
        self.logo.create_rectangle(7, 5, 11, 8, fill="#a1e56a", outline="")
        self.title_var = tk.StringVar(value=self.data.get("title", "New Note"))
        self.title_entry = tk.Entry(self.header, textvariable=self.title_var, bg=GRASS, fg="white",
                                    insertbackground="white", relief="flat", font=("Consolas", 10, "bold"))
        self.title_entry.pack(side="left", fill="x", expand=True, padx=3)
        self.title_var.trace_add("write", self.schedule_save)
        tk.Button(self.header, text="⋯", command=self.show_menu, bg=GRASS, fg="white",
                  activebackground=GRASS_DARK, relief="flat", bd=0, cursor="hand2",
                  font=("Consolas", 14, "bold"), width=2).pack(side="right")
        tk.Button(self.header, text="＋", command=self.app.new_note, bg=GRASS, fg="white",
                  activebackground=GRASS_DARK, relief="flat", bd=0, cursor="hand2",
                  font=("Consolas", 13, "bold"), width=2).pack(side="right")
        tk.Button(self.header, text="×", command=self.close_note, bg=GRASS, fg="white",
                  activebackground=RED, relief="flat", bd=0, cursor="hand2",
                  font=("Consolas", 16), width=2).pack(side="right")
        for w in (self.header, self.logo):
            w.bind("<ButtonPress-1>", self.start_drag)
            w.bind("<B1-Motion>", self.drag)
            w.bind("<ButtonRelease-1>", self.end_drag)

        self.paper = tk.Frame(self.win, bg=DIRT, padx=2, pady=2)
        self.paper.pack(fill="both", expand=True)
        self.body_bg, self.body_fg = PAPER_THEMES.get(self.data.get("theme", "Wheat"), PAPER_THEMES["Wheat"])
        self.editor = tk.Text(self.paper, wrap="word", undo=True, bg=self.body_bg, fg=self.body_fg,
                              insertbackground=self.body_fg, selectbackground="#b9d99b", relief="flat",
                              bd=0, padx=12, pady=10, font=("Segoe UI", 11), spacing1=2, spacing3=3)
        self.editor.pack(fill="both", expand=True)
        self.editor.insert("1.0", self.data.get("body", ""))
        self.editor.edit_modified(False)
        self.editor.bind("<<Modified>>", self.on_modified)
        self.editor.bind("<Button-3>", self.show_menu)
        self.toolbar = tk.Frame(self.paper, bg=PALE, height=31)
        self.toolbar.pack(fill="x", side="bottom")
        self.toolbar.pack_propagate(False)
        for label, kind in [("B", "bold"), ("I", "italic"), ("U", "underline")]:
            tk.Button(self.toolbar, text=label, command=lambda k=kind: self.format_selection(k),
                      bg=PALE, fg=INK, relief="flat", activebackground="#dfd09a",
                      font=("Segoe UI", 10, kind), width=3).pack(side="left", padx=2, pady=2)
        self.pin_button = tk.Button(self.toolbar, text="📌 TOP: OFF", command=self.toggle_pin, bg=PALE, fg=INK,
                                    relief="flat", activebackground="#dfd09a", font=("Segoe UI", 8), padx=3)
        self.pin_button.pack(side="left", padx=2, pady=2)
        tk.Button(self.toolbar, text="✓ Checklist", command=self.insert_checklist_item, bg=PALE, fg=INK,
                  relief="flat", activebackground="#dfd09a", font=("Segoe UI", 9)).pack(side="left", padx=3, pady=2)
        self.update_pin_button()

    def show_menu(self, event=None):
        menu = tk.Menu(self.win, tearoff=0, bg=self.body_bg, fg=self.body_fg)
        menu.add_command(label="New sticky note", command=self.app.new_note)
        menu.add_command(label="Show all notes", command=self.app.show_all)
        menu.add_command(label="Duplicate this note", command=self.app.duplicate_note_for(self))
        menu.add_separator()
        theme_menu = tk.Menu(menu, tearoff=0)
        for theme in PAPER_THEMES:
            theme_menu.add_command(label=theme, command=lambda t=theme: self.set_theme(t))
        menu.add_cascade(label="Paper theme", menu=theme_menu)
        menu.add_command(label="Start with Windows: " + ("ON" if startup_enabled() else "OFF"),
                         command=self.app.toggle_startup)
        menu.add_command(label="Delete this note permanently…", command=lambda: self.app.delete_note(self))
        menu.add_separator()
        menu.add_command(label="Quit app", command=self.app.quit)
        try:
            if event and hasattr(event, "x_root"):
                menu.tk_popup(event.x_root, event.y_root)
            else:
                menu.tk_popup(self.win.winfo_pointerx(), self.win.winfo_pointery())
        finally:
            menu.grab_release()

    def set_theme(self, theme):
        self.data["theme"] = theme
        self.body_bg, self.body_fg = PAPER_THEMES[theme]
        self.editor.configure(bg=self.body_bg, fg=self.body_fg, insertbackground=self.body_fg)
        self.persist()

    def format_selection(self, kind):
        try:
            start, end = self.editor.index("sel.first"), self.editor.index("sel.last")
        except tk.TclError:
            return
        font = {"bold": ("Segoe UI", 11, "bold"), "italic": ("Segoe UI", 11, "italic"),
                "underline": ("Segoe UI", 11, "underline")}[kind]
        self.editor.tag_configure(kind, font=font)
        if kind in self.editor.tag_names(start):
            self.editor.tag_remove(kind, start, end)
        else:
            self.editor.tag_add(kind, start, end)
        self.schedule_save()

    def insert_checklist_item(self):
        self.editor.insert("insert", "☐ ")
        self.editor.focus_set()
        self.schedule_save()

    def start_drag(self, event):
        self.drag_offset = (event.x_root - self.win.winfo_x(), event.y_root - self.win.winfo_y())

    def drag(self, event):
        if self.drag_offset:
            x, y = event.x_root - self.drag_offset[0], event.y_root - self.drag_offset[1]
            self.win.geometry(f"+{x}+{y}")
            self.data["x"], self.data["y"] = x, y
            self.schedule_save()

    def end_drag(self, _event=None):
        self.drag_offset = None
        self.persist()

    def on_configure(self, _event=None):
        try:
            if self.win.winfo_exists():
                self.data["x"], self.data["y"] = self.win.winfo_x(), self.win.winfo_y()
                self.data["width"], self.data["height"] = self.win.winfo_width(), self.win.winfo_height()
                self.schedule_save()
        except tk.TclError:
            pass

    def on_modified(self, _event=None):
        if self.editor.edit_modified():
            self.editor.edit_modified(False)
            self.schedule_save()

    def schedule_save(self, *_):
        if self.save_job:
            try: self.win.after_cancel(self.save_job)
            except tk.TclError: pass
        self.save_job = self.win.after(350, self.persist)

    def persist(self):
        try:
            self.data["title"] = self.title_var.get().strip() or "New Note"
            self.data["body"] = self.editor.get("1.0", "end-1c")
            self.data["always_on_top"] = bool(self.win.attributes("-topmost"))
            self.app.save()
            self.save_job = None
        except tk.TclError:
            pass

    def toggle_pin(self):
        value = not bool(self.win.attributes("-topmost"))
        self.win.attributes("-topmost", value)
        self.data["always_on_top"] = value
        self.update_pin_button()
        self.persist()

    def update_pin_button(self):
        value = bool(self.win.attributes("-topmost"))
        self.pin_button.config(text="📌 TOP: ON" if value else "📌 TOP: OFF")

    def close_note(self):
        # Closing a note never deletes it; permanent deletion is a separate, confirmed action.
        if messagebox.askyesno("Close sticky note", "Hide this note? Your data will be saved and you can reopen it later.", parent=self.win):
            self.persist()
            self.data["visible"] = False
            self.win.withdraw()
            self.app.save()
            self.app.update_reopen_window()

    def show(self):
        self.data["visible"] = True
        self.win.deiconify()
        self.win.lift()
        self.win.attributes("-topmost", bool(self.data.get("always_on_top", False)))
        self.app.save()

    def destroy(self):
        self.persist()
        self.win.destroy()

class App:
    def __init__(self, root):
        self.root = root
        root.withdraw()
        root.title(APP_NAME)
        root.protocol("WM_DELETE_WINDOW", self.quit)
        APP_DIR.mkdir(parents=True, exist_ok=True)
        try:
            obj = json.loads(DATA_FILE.read_text(encoding="utf-8"))
            self.data = obj.get("notes", [])
        except (OSError, ValueError, TypeError):
            self.data = []
        if not self.data:
            self.data = [{
                "id": uuid.uuid4().hex, "title": "Welcome, Player!",
                "body": "⛏ Welcome to Minecraft Sticky Notes!\\n\\n• Drag this note anywhere on your desktop.\\n• Text and position save automatically.\\n• × asks before hiding the note; hidden notes can be restored.\\n• Use + to create another note.\\n• Ctrl+Enter inserts a checklist box.\\n• Right-click or click ⋯ for more options.",
                "x": 140, "y": 110, "width": 340, "height": 330, "visible": True, "always_on_top": False, "theme": "Wheat"
            }]
        self.notes = [StickyNote(self, d) for d in self.data]
        self.root.bind_all("<Control-Alt-m>", lambda _e: self.show_all())
        self.root.bind_all("<Control-Alt-M>", lambda _e: self.show_all())
        self.root.bind_all("<Control-Alt-n>", lambda _e: self.new_note())
        self.reopen_window = None
        self.update_reopen_window()
        self.save()

    def save(self):
        try:
            APP_DIR.mkdir(parents=True, exist_ok=True)
            DATA_FILE.write_text(json.dumps({"notes": self.data}, ensure_ascii=False, indent=2), encoding="utf-8")
        except OSError:
            pass

    def new_note(self):
        d = {"id": uuid.uuid4().hex, "title": "New Note", "body": "", "x": 170 + len(self.notes)*22,
             "y": 130 + len(self.notes)*22, "width": 320, "height": 300, "visible": True,
             "always_on_top": False, "theme": "Wheat"}
        self.data.append(d)
        self.notes.append(StickyNote(self, d))
        self.save()

    def duplicate_note_for(self, note):
        def duplicate():
            note.persist()
            d = dict(note.data)
            d.update({"id": uuid.uuid4().hex, "title": note.data.get("title", "Note") + " copy",
                      "x": note.data.get("x", 150)+28, "y": note.data.get("y", 120)+28, "visible": True})
            self.data.append(d)
            self.notes.append(StickyNote(self, d))
            self.save()
        return duplicate

    def delete_note(self, note):
        if not messagebox.askyesno("Delete permanently?", f'Delete "{note.title_var.get()}" and its saved text permanently? This cannot be undone.', icon="warning", parent=note.win):
            return
        note.persist()
        try: note.win.destroy()
        except tk.TclError: pass
        self.notes = [n for n in self.notes if n is not note]
        self.data = [d for d in self.data if d.get("id") != note.data.get("id")]
        if not self.notes:
            self.new_note()
        self.save()
        self.update_reopen_window()

    def show_all(self):
        for note in self.notes:
            note.show()
        if self.reopen_window:
            try: self.reopen_window.destroy()
            except tk.TclError: pass
            self.reopen_window = None

    def toggle_startup(self):
        try:
            set_startup(not startup_enabled())
            messagebox.showinfo("Windows startup", "Automatic startup is now " + ("ON." if startup_enabled() else "OFF.") +
                                "\\n\\nThe app will launch when this Windows account signs in.")
        except Exception as exc:
            messagebox.showerror("Windows startup", f"Could not change startup setting:\\n{exc}")

    def update_reopen_window(self):
        visible = any(n.data.get("visible", True) for n in self.notes)
        if visible:
            if self.reopen_window:
                try: self.reopen_window.destroy()
                except tk.TclError: pass
                self.reopen_window = None
            return
        if self.reopen_window:
            return
        self.reopen_window = tk.Toplevel(self.root)
        self.reopen_window.title("Minecraft Sticky Notes")
        self.reopen_window.attributes("-topmost", True)
        self.reopen_window.configure(bg=GRASS_DARK)
        self.reopen_window.geometry("310x130+40+40")
        self.reopen_window.resizable(False, False)
        self.reopen_window.protocol("WM_DELETE_WINDOW", self.quit)
        tk.Label(self.reopen_window, text="⛏ MINECRAFT NOTES", bg=GRASS_DARK, fg="white",
                 font=("Consolas", 12, "bold")).pack(pady=(12, 5))
        tk.Button(self.reopen_window, text="SHOW MY NOTES", command=self.show_all, bg=GRASS,
                  fg="white", font=("Consolas", 10, "bold"), relief="flat", padx=10, pady=6).pack()
        tk.Button(self.reopen_window, text="QUIT APP", command=self.quit, bg=DIRT,
                  fg="white", font=("Consolas", 8, "bold"), relief="flat").pack(pady=4)

    def quit(self):
        for note in self.notes:
            try: note.persist()
            except Exception: pass
        self.save()
        self.root.destroy()

def main():
    root = tk.Tk()
    App(root)
    root.mainloop()

if __name__ == "__main__":
    main()
