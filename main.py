"""Car Dealership Stock Management - run with:  python main.py

Windows/pages: the window itself and the login / sign-up screens live in this file.
  main_page.py  main screen (stock tabs, add car)      widgets.py  look + shared widgets
  stock.py      cars, sales, stock.xlsx, filters       auth.py     accounts, users.json
"""
from __future__ import annotations

import tkinter as tk
from pathlib import Path
from tkinter import messagebox, ttk

from auth import PASSWORD_MIN_LENGTH, AuthError, AuthService, User, UserRepository
from main_page import MainPage
from stock import StockDataError, StockRepository
from widgets import BG, add_entry, apply_theme, set_window_icon

BASE_DIR = Path(__file__).resolve().parent
STOCK_FILE = BASE_DIR / "stock.xlsx"
USERS_FILE = BASE_DIR / "users.json"

APP_TITLE = "Car Dealership Stock Management"
AUTH_SIZE = (420, 460)
MAIN_SIZE = (1180, 780)


# ============================================================================
# Login page
# ============================================================================

class LoginPage(ttk.Frame):
    def __init__(self, master, app, username: str = ""):
        super().__init__(master)
        self.app = app

        card = ttk.Frame(self, padding=24)
        card.place(relx=0.5, rely=0.5, anchor="center")
        ttk.Label(card, text="Login", style="Title.TLabel").grid(
            row=0, column=0, columnspan=2, pady=(0, 12))

        self.username = add_entry(card, 1, "Username*")
        self.password = add_entry(card, 2, "Password*", show="*")
        self.username.insert(0, username)

        ttk.Button(card, text="Login", style="Accent.TButton", command=self.submit).grid(
            row=3, column=0, columnspan=2, sticky="ew", pady=(14, 0))

        ttk.Separator(card).grid(row=4, column=0, columnspan=2, sticky="ew", pady=18)
        ttk.Label(card, text="New employee?", style="Muted.TLabel").grid(
            row=5, column=0, columnspan=2)
        ttk.Button(card, text="Create new account", style="Plain.TButton",
                   command=app.show_signup).grid(
            row=6, column=0, columnspan=2, sticky="ew", pady=(4, 0))

        for entry in (self.username, self.password):
            entry.bind("<Return>", lambda _e: self.submit())
        (self.password if username else self.username).focus_set()

    def submit(self) -> None:
        try:
            user = self.app.auth.login(self.username.get(), self.password.get())
        except AuthError as exc:
            messagebox.showerror("Invalid login", str(exc), parent=self)
            self.password.delete(0, "end")
            self.password.focus_set()
            return
        self.app.show_main(user)


# ============================================================================
# Sign-up page
# ============================================================================

class SignupPage(ttk.Frame):
    def __init__(self, master, app):
        super().__init__(master)
        self.app = app

        card = ttk.Frame(self, padding=24)
        card.place(relx=0.5, rely=0.5, anchor="center")
        ttk.Label(card, text="Sign-up", style="Title.TLabel").grid(
            row=0, column=0, columnspan=2, pady=(0, 12))

        self.first_name = add_entry(card, 1, "First name*")
        self.surname = add_entry(card, 2, "Surname*")
        self.email = add_entry(card, 3, "Email*")
        self.password = add_entry(card, 4, "Password*", show="*")
        self.confirm = add_entry(card, 5, "Confirm password*", show="*")

        ttk.Label(
            card, style="Muted.TLabel", wraplength=330, justify="left",
            text=(f"Password: at least {PASSWORD_MIN_LENGTH} characters with capital and "
                  "lowercase letters, a number and a special character. "
                  "Your username is generated for you."),
        ).grid(row=6, column=0, columnspan=2, pady=(4, 0))

        ttk.Button(card, text="Sign-up", style="Accent.TButton", command=self.submit).grid(
            row=7, column=0, columnspan=2, sticky="ew", pady=(14, 0))
        ttk.Button(card, text="Back to login", style="Plain.TButton",
                   command=app.show_login).grid(
            row=8, column=0, columnspan=2, sticky="ew", pady=(8, 0))

        for entry in (self.first_name, self.surname, self.email, self.password, self.confirm):
            entry.bind("<Return>", lambda _e: self.submit())
        self.first_name.focus_set()

    def submit(self) -> None:
        try:
            user = self.app.auth.register(
                self.first_name.get(), self.surname.get(), self.email.get(),
                self.password.get(), self.confirm.get(),
            )
        except AuthError as exc:
            messagebox.showerror("Invalid sign-up", str(exc), parent=self)
            return
        messagebox.showinfo(
            "Account created",
            f"Welcome, {user.first_name}!\n\nYour username is:\n{user.username}\n\n"
            "You can find it again any time via the user icon (top left).",
            parent=self,
        )
        self.app.show_main(user)


# ============================================================================
# Application window
# ============================================================================

AUTH_SIZE = (420, 460)
MAIN_SIZE = (1180, 780)


class App(tk.Tk):
    def __init__(self, auth: AuthService, stock: StockRepository):
        super().__init__()
        self.auth = auth
        self.stock = stock
        self.user: User | None = None
        self._page: ttk.Frame | None = None

        self.title(APP_TITLE)
        self.configure(bg=BG)
        apply_theme(self)
        set_window_icon(self)
        self.protocol("WM_DELETE_WINDOW", self.confirm_exit)

        self.show_login()

    # -------------------------------------------------------------- navigation
    def show_login(self) -> None:
        self._show(LoginPage(self, self), AUTH_SIZE)

    def show_signup(self) -> None:
        self._show(SignupPage(self, self), AUTH_SIZE)

    def show_main(self, user: User) -> None:
        self.user = user
        self._show(MainPage(self, self, user), MAIN_SIZE, resizable=True)

    def log_out(self) -> None:
        self.user = None
        self.show_login()

    def confirm_exit(self) -> None:
        if messagebox.askyesno("Exit", "Do you want to exit?", parent=self):
            self.destroy()

    # ---------------------------------------------------------------- internals
    def _show(self, page: ttk.Frame, size: tuple[int, int], resizable: bool = False) -> None:
        if self._page is not None:
            self._page.destroy()
        self._page = page
        page.pack(fill="both", expand=True)

        width, height = size
        x = (self.winfo_screenwidth() - width) // 2
        y = max((self.winfo_screenheight() - height) // 2 - 20, 0)
        self.geometry(f"{width}x{height}+{x}+{y}")
        self.resizable(resizable, resizable)
        self.minsize(*(960, 640) if resizable else size)


# ============================================================================
# Entry point
# ============================================================================

def main() -> None:
    try:
        stock = StockRepository(STOCK_FILE)
    except StockDataError as exc:
        root = tk.Tk()
        root.withdraw()
        messagebox.showerror("Cannot start", str(exc))
        return
    App(AuthService(UserRepository(USERS_FILE)), stock).mainloop()


if __name__ == "__main__":
    main()
