"""Shared look and building blocks: colours/styles, table, brand menu, bar chart, pop-up dialogs."""
from __future__ import annotations

import tkinter as tk
from dataclasses import dataclass
from pathlib import Path
from tkinter import ttk
from typing import Callable, Iterable, Sequence

from auth import User
from stock import Car

ICON_FILE = Path(__file__).resolve().parent / "car-16.ico"


# ============================================================================
# Theme
# ============================================================================

BG = "#64bad7"
ACCENT = "#dd787c"
ACCENT_HOVER = "#e99a9e"
ACCENT_PRESSED = "#c9666b"
SURFACE = "#ffffff"
SURFACE_ALT = "#e8f4f9"
CHIP = "#b9e0ee"
TEXT = "#1b1b1b"
MUTED = "#35505d"
DISABLED = "#c9d6dc"

FONT = ("Arial", 11)
FONT_BOLD = ("Arial", 11, "bold")
FONT_SMALL = ("Arial", 9)
FONT_TITLE = ("Arial", 16, "bold")


def apply_theme(root: tk.Misc) -> None:
    style = ttk.Style(root)
    style.theme_use("clam")

    style.configure(".", background=BG, foreground=TEXT, font=FONT)
    style.configure("TFrame", background=BG)
    style.configure("TLabel", background=BG)
    style.configure("Title.TLabel", font=FONT_TITLE)
    style.configure("Heading.TLabel", font=FONT_BOLD)
    style.configure("Muted.TLabel", foreground=MUTED, font=FONT_SMALL)

    style.configure("Accent.TButton", background=ACCENT, foreground=TEXT,
                    padding=(12, 6), borderwidth=0, focusthickness=0)
    style.map("Accent.TButton",
              background=[("disabled", DISABLED), ("pressed", ACCENT_PRESSED),
                          ("active", ACCENT_HOVER)])
    style.configure("Plain.TButton", background=CHIP, foreground=TEXT,
                    padding=(12, 6), borderwidth=0, focusthickness=0)
    style.map("Plain.TButton", background=[("disabled", DISABLED), ("active", SURFACE)])

    style.configure("TEntry", fieldbackground=SURFACE, padding=4)
    style.configure("TCombobox", fieldbackground=SURFACE, background=SURFACE, padding=4)
    style.map("TCombobox", fieldbackground=[("readonly", SURFACE)],
              foreground=[("readonly", TEXT)])
    style.configure("TMenubutton", background=SURFACE, foreground=TEXT, padding=(10, 6))
    style.map("TMenubutton", background=[("active", SURFACE_ALT)])

    style.configure("Treeview", background=SURFACE, fieldbackground=SURFACE,
                    foreground=TEXT, rowheight=26)
    style.configure("Treeview.Heading", font=FONT_BOLD, background=SURFACE_ALT,
                    foreground=TEXT, relief="flat")
    style.map("Treeview", background=[("selected", ACCENT)],
              foreground=[("selected", TEXT)])

    style.configure("TNotebook", background=BG, borderwidth=0)
    style.configure("TNotebook.Tab", padding=(18, 7), font=FONT_BOLD, background=CHIP)
    style.map("TNotebook.Tab", background=[("selected", SURFACE)])

    style.configure("TLabelframe", background=BG)
    style.configure("TLabelframe.Label", background=BG, font=FONT_BOLD)
    style.configure("TSeparator", background=MUTED)
    style.configure("Chip.Toolbutton", background=CHIP, foreground=TEXT, padding=(10, 5),
                    borderwidth=0, font=FONT)
    style.map("Chip.Toolbutton", background=[("selected", ACCENT), ("active", SURFACE)])

    root.option_add("*TCombobox*Listbox.font", FONT)
    root.option_add("*Menu.font", FONT)


def set_window_icon(window: tk.Misc) -> None:
    """Best effort: .ico files only work with Tk on Windows, so ignore failures."""
    if ICON_FILE.exists():
        try:
            window.iconbitmap(str(ICON_FILE))
        except tk.TclError:
            pass


# ============================================================================
# Widgets
# ============================================================================

def add_entry(parent: tk.Misc, row: int, label: str, show: str | None = None,
              width: int = 28) -> ttk.Entry:
    """Grid a 'label: [entry]' pair and return the entry."""
    ttk.Label(parent, text=label).grid(row=row, column=0, sticky="e", padx=(0, 10), pady=6)
    entry = ttk.Entry(parent, show=show or "", width=width)
    entry.grid(row=row, column=1, sticky="ew", pady=6)
    return entry


@dataclass(frozen=True)
class Column:
    key: str
    heading: str
    width: int = 100
    anchor: str = "w"


class DataTable(ttk.Frame):
    """A Treeview with scrollbars. Rows are (iid, values) so callers can look the
    underlying object up again when one is selected."""

    def __init__(self, master, columns: Sequence[Column], height: int = 10,
                 hscroll: bool = False,
                 on_select: Callable[[str | None], None] | None = None,
                 on_activate: Callable[[str], None] | None = None):
        super().__init__(master)
        self._on_select = on_select
        self._on_activate = on_activate

        self.tree = ttk.Treeview(self, columns=[c.key for c in columns], show="headings",
                                 height=height, selectmode="browse")
        for column in columns:
            self.tree.heading(column.key, text=column.heading)
            self.tree.column(column.key, width=column.width, anchor=column.anchor,
                             minwidth=40, stretch=not hscroll)

        vbar = ttk.Scrollbar(self, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=vbar.set)
        self.tree.grid(row=0, column=0, sticky="nsew")
        vbar.grid(row=0, column=1, sticky="ns")
        if hscroll:
            hbar = ttk.Scrollbar(self, orient="horizontal", command=self.tree.xview)
            self.tree.configure(xscrollcommand=hbar.set)
            hbar.grid(row=1, column=0, sticky="ew")
        self.columnconfigure(0, weight=1)
        self.rowconfigure(0, weight=1)

        self.tree.bind("<<TreeviewSelect>>", self._selected)
        self.tree.bind("<Double-1>", self._activated)

    def set_rows(self, rows: Iterable[tuple[str, Sequence]]) -> None:
        self.tree.delete(*self.tree.get_children())
        for iid, values in rows:
            self.tree.insert("", "end", iid=iid, values=tuple(values))

    @property
    def selected(self) -> str | None:
        chosen = self.tree.selection()
        return chosen[0] if chosen else None

    def _selected(self, _event) -> None:
        if self._on_select:
            self._on_select(self.selected)

    def _activated(self, event) -> None:
        iid = self.tree.identify_row(event.y)
        if iid and self._on_activate:
            self._on_activate(iid)


class BrandMenu(ttk.Menubutton):
    """Drop-down of brands. Brands with no stock are greyed out and can't be picked."""
    PLACEHOLDER = "Select car brand  ▾"

    def __init__(self, master, on_select: Callable[[str], None]):
        super().__init__(master, text=self.PLACEHOLDER, width=30, direction="below")
        self._on_select = on_select
        self._menu = tk.Menu(self, tearoff=False)
        self["menu"] = self._menu

    def set_brands(self, counts: dict[str, int]) -> None:
        self._menu.delete(0, "end")
        for brand, count in counts.items():
            if count:
                self._menu.add_command(label=f"{brand}  ({count} in stock)",
                                       command=lambda b=brand: self._choose(b))
            else:
                self._menu.add_command(label=f"{brand}  (none in stock)", state="disabled")

    def show(self, brand: str | None) -> None:
        self.configure(text=f"{brand}  ▾" if brand else self.PLACEHOLDER)

    def _choose(self, brand: str) -> None:
        self.show(brand)
        self._on_select(brand)


class BarChart(tk.Canvas):
    """Minimal vertical bar chart of (label, count) pairs. Redraws when resized."""

    def __init__(self, master, title: str = "", height: int = 200):
        super().__init__(master, height=height, bg=SURFACE, highlightthickness=1,
                         highlightbackground=MUTED)
        self._title = title
        self._data: list[tuple[str, int]] = []
        self.bind("<Configure>", lambda _e: self._draw())

    def set_data(self, data: list[tuple[str, int]]) -> None:
        self._data = data
        self._draw()

    def _draw(self) -> None:
        self.delete("all")
        width, height = self.winfo_width(), self.winfo_height()
        left, right, top, bottom = 45, 15, 34, 48
        self.create_text(width / 2, 14, text=self._title, font=FONT_BOLD, fill=TEXT)
        if not self._data:
            self.create_text(width / 2, height / 2, text="No data", fill=MUTED)
            return

        peak = max(count for _, count in self._data)
        step = max(1, -(-peak // 5))              # whole-number ticks, at most ~5 of them
        y_max = step * (peak // step + 1)            # always leave headroom for the count label
        plot_h = height - top - bottom
        base = height - bottom

        for tick in range(0, y_max + 1, step):
            y = base - plot_h * tick / y_max
            self.create_line(left, y, width - right, y, fill="#d9e3e8")
            self.create_text(left - 8, y, text=str(tick), anchor="e", fill=MUTED,
                             font=FONT_SMALL)

        slot = (width - left - right) / len(self._data)
        bar_w = min(slot * 0.6, 90)
        rotate = slot < 95
        for i, (label, count) in enumerate(self._data):
            x0 = left + slot * i + (slot - bar_w) / 2
            y0 = base - plot_h * count / y_max
            if count:
                self.create_rectangle(x0, y0, x0 + bar_w, base, fill=ACCENT, outline="")
                self.create_text(x0 + bar_w / 2, y0 - 8, text=str(count), font=FONT_BOLD,
                                 fill=TEXT)
            self.create_text(x0 + bar_w / 2 + (bar_w / 2 if rotate else 0), base + 8,
                             text=label, font=FONT_SMALL, fill=TEXT,
                             anchor="ne" if rotate else "n", angle=40 if rotate else 0)
        self.create_line(left, base, width - right, base, fill=MUTED)


# ============================================================================
# Dialogs
# ============================================================================

class Dialog(tk.Toplevel):
    """Modal pop-up centred over its parent."""

    def __init__(self, parent: tk.Misc, title: str):
        super().__init__(parent)
        self.title(title)
        self.configure(bg=BG)
        self.resizable(False, False)
        self.transient(parent.winfo_toplevel())
        set_window_icon(self)
        self.bind("<Escape>", lambda _e: self.destroy())
        self._parent = parent.winfo_toplevel()

    def present(self) -> None:
        self.update_idletasks()
        p = self._parent
        x = p.winfo_rootx() + (p.winfo_width() - self.winfo_reqwidth()) // 2
        y = p.winfo_rooty() + (p.winfo_height() - self.winfo_reqheight()) // 2
        self.geometry(f"+{max(x, 0)}+{max(y, 0)}")
        try:
            self.wait_visibility()
            self.grab_set()
        except tk.TclError:
            pass
        self.focus_set()


class UserDetailsDialog(Dialog):
    def __init__(self, parent: tk.Misc, user: User, on_logout: Callable[[], None]):
        super().__init__(parent, "User details")
        body = ttk.Frame(self, padding=24)
        body.pack()
        ttk.Label(body, text="User details", style="Title.TLabel").grid(
            row=0, column=0, columnspan=2, pady=(0, 14))
        rows = (("Name", user.full_name), ("Username / ID", user.username), ("Email", user.email))
        for i, (label, value) in enumerate(rows, start=1):
            ttk.Label(body, text=label + ":", style="Heading.TLabel").grid(
                row=i, column=0, sticky="e", padx=(0, 12), pady=4)
            ttk.Label(body, text=value).grid(row=i, column=1, sticky="w", pady=4)
        buttons = ttk.Frame(body)
        buttons.grid(row=4, column=0, columnspan=2, pady=(16, 0))
        ttk.Button(buttons, text="Close", style="Plain.TButton",
                   command=self.destroy).pack(side="left", padx=4)
        ttk.Button(buttons, text="Log out", style="Accent.TButton",
                   command=lambda: (self.destroy(), on_logout())).pack(side="left", padx=4)
        self.present()


class SpecsView(ttk.LabelFrame):
    """Label/value table for one car's specification."""

    def __init__(self, master, car: Car):
        super().__init__(master, text="Spec Overview", padding=12)
        self.columnconfigure(0, weight=1)
        for i, (label, value) in enumerate(car.spec_rows()):
            row = tk.Frame(self, bg=SURFACE if i % 2 == 0 else SURFACE_ALT)
            row.grid(row=i, column=0, sticky="ew")
            tk.Label(row, text=label, font=FONT, bg=row["bg"], fg=TEXT, anchor="w").pack(
                side="left", padx=8, pady=3)
            tk.Label(row, text=value, font=FONT_BOLD, bg=row["bg"], fg=TEXT, anchor="e").pack(
                side="right", padx=8, pady=3)


class SpecsDialog(Dialog):
    def __init__(self, parent: tk.Misc, car: Car):
        super().__init__(parent, "Specifications")
        body = ttk.Frame(self, padding=20)
        body.pack(fill="both", expand=True)
        ttk.Label(body, text=f"{car.name} ({car.year}) Specs & Dimensions",
                  style="Title.TLabel").pack(anchor="w", pady=(0, 14))
        SpecsView(body, car).pack(fill="x")
        ttk.Button(body, text="Close", style="Plain.TButton",
                   command=self.destroy).pack(pady=(14, 0))
        self.present()
