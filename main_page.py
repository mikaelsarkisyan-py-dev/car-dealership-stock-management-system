"""The main system screen: header, 'All Stock' tab, 'Stock by Brand' tab and the add-car form."""
from __future__ import annotations

import tkinter as tk
from tkinter import messagebox, simpledialog, ttk
from typing import Callable

from auth import User
from stock import (SPEC_LABELS, Car, CarFilter, StockDataError, ValidationError, brand_counts,
                   build_car_fields, cars_for, distinct_values, filter_cars, model_counts,
                   price_distribution)
from widgets import (BarChart, BrandMenu, Column, DataTable, Dialog, SpecsDialog,
                     UserDetailsDialog)


# ============================================================================
# Main page
# ============================================================================

class MainPage(ttk.Frame):
    def __init__(self, master, app, user: User):
        super().__init__(master)
        self.app, self.user = app, user
        self._cars: list[Car] = []

        header = ttk.Frame(self, padding=(10, 8))
        header.pack(fill="x")
        ttk.Button(header, text="👤", width=3, style="Accent.TButton",
                   command=self.show_user_details).pack(side="left")
        ttk.Label(header, text="Main System", style="Title.TLabel").pack(side="left", padx=14)
        ttk.Button(header, text="Log out", style="Plain.TButton",
                   command=app.log_out).pack(side="right")
        ttk.Button(header, text="Add new +", style="Accent.TButton",
                   command=self.open_add_car).pack(side="right", padx=8)
        ttk.Separator(self).pack(fill="x")

        notebook = ttk.Notebook(self)
        notebook.pack(fill="both", expand=True, padx=8, pady=8)
        self.inventory = InventoryTab(notebook, on_view=self.view_specs, on_sell=self.sell_car)
        self.car_stock = CarStockTab(notebook)
        notebook.add(self.inventory, text="All Stock")
        notebook.add(self.car_stock, text="Stock by Brand")

        self.refresh()

    # ------------------------------------------------------------------ data
    def refresh(self) -> None:
        """Reload from disk and update every tab."""
        try:
            self._cars = self.app.stock.all()
            known = self.app.stock.known_brands()
        except StockDataError as exc:
            messagebox.showerror("Stock data", str(exc), parent=self)
            return
        self.inventory.set_cars(self._cars)
        self.car_stock.set_cars(self._cars, known)

    # --------------------------------------------------------------- actions
    def show_user_details(self) -> None:
        UserDetailsDialog(self, self.user, on_logout=self.app.log_out)

    def view_specs(self, car: Car) -> None:
        SpecsDialog(self, car)

    def open_add_car(self) -> None:
        makes = sorted({car.make for car in self._cars}, key=str.casefold)
        AddCarDialog(self, makes, on_submit=self._add_car)

    def _add_car(self, fields: dict) -> None:
        self.app.stock.add(fields)  # may raise StockDataError; the dialog reports it
        self.refresh()

    def sell_car(self, car: Car) -> None:
        price = simpledialog.askinteger(
            "Mark as sold", f"Sale price for {car.name} (£):",
            initialvalue=car.price, minvalue=1, parent=self)
        if price is None:
            return
        try:
            self.app.stock.sell(car.stock_id, self.user.username, price)
        except StockDataError as exc:
            messagebox.showerror("Could not record sale", str(exc), parent=self)
        self.refresh()


# ============================================================================
# 'All Stock' tab
# ============================================================================

ANY = "Any"

COMBO_FILTERS = (
    ("make", "Make"), ("model", "Model"), ("transmission", "Transmission"),
    ("fuel_type", "Fuel type"), ("gearbox", "Gearbox"), ("drivetrain", "Drivetrain"),
    ("colour", "Colour"),
)
COLUMNS = (
    Column("stock_id", "Stock ID", 70, "center"),
    Column("make", "Make", 170),
    Column("model", "Model", 250),
    Column("condition", "Used/New", 100, "center"),
    Column("price", "Price (£)", 130, "e"),
)


def _parse_price(text: str) -> int | None:
    cleaned = text.replace("£", "").replace(",", "").strip()
    return int(cleaned) if cleaned.isdigit() else None


class InventoryTab(ttk.Frame):
    def __init__(self, master, on_view: Callable[[Car], None], on_sell: Callable[[Car], None]):
        super().__init__(master, padding=8)
        self._on_view, self._on_sell = on_view, on_sell
        self._cars: list[Car] = []
        self._visible: dict[str, Car] = {}
        self._suspend = False  # True while we change variables ourselves

        self._search = tk.StringVar()
        self._condition = tk.StringVar(value="All")
        self._min_price, self._max_price = tk.StringVar(), tk.StringVar()
        self._combo_vars = {attr: tk.StringVar(value=ANY) for attr, _ in COMBO_FILTERS}
        self._combos: dict[str, ttk.Combobox] = {}

        self._build_filter_panel()
        self._build_main_area()

        watched = [self._search, self._condition, self._min_price, self._max_price,
                   *self._combo_vars.values()]
        for var in watched:
            var.trace_add("write", self._on_change)

    # ---------------------------------------------------------------- layout
    def _build_filter_panel(self) -> None:
        panel = ttk.Frame(self)
        panel.pack(side="left", fill="y", padx=(0, 12))
        ttk.Label(panel, text="Filter Menu", style="Heading.TLabel").pack(pady=(0, 6))

        for attr, label in COMBO_FILTERS:
            ttk.Label(panel, text=label, style="Muted.TLabel").pack(anchor="w", pady=(6, 0))
            combo = ttk.Combobox(panel, textvariable=self._combo_vars[attr], state="readonly",
                                 values=[ANY], width=22)
            combo.pack(fill="x")
            self._combos[attr] = combo

        ttk.Label(panel, text="Price range (£): min to max", style="Muted.TLabel").pack(anchor="w", pady=(10, 0))
        prices = ttk.Frame(panel)
        prices.pack(fill="x")
        ttk.Entry(prices, textvariable=self._min_price, width=9).pack(side="left", expand=True)
        ttk.Label(prices, text=" to ").pack(side="left")
        ttk.Entry(prices, textvariable=self._max_price, width=9).pack(side="left", expand=True)

        ttk.Button(panel, text="Reset filters", style="Plain.TButton",
                   command=self.reset_filters).pack(fill="x", pady=(16, 0))

    def _build_main_area(self) -> None:
        main = ttk.Frame(self)
        main.pack(side="left", fill="both", expand=True)

        bar = ttk.Frame(main)
        bar.pack(fill="x", pady=(0, 8))
        ttk.Label(bar, text="Search:").pack(side="left")
        ttk.Entry(bar, textvariable=self._search, width=26).pack(side="left", padx=(6, 16))
        for label in ("All", "Used", "New"):
            ttk.Radiobutton(bar, text=label, value=label, variable=self._condition,
                            style="Chip.Toolbutton").pack(side="left", padx=2)
        self._count = ttk.Label(bar, style="Muted.TLabel")
        self._count.pack(side="right")

        self._table = DataTable(main, COLUMNS, height=14, on_select=self._selection_changed,
                                on_activate=lambda iid: self._on_view(self._visible[iid]))
        self._table.pack(fill="both", expand=True)

        actions = ttk.Frame(main)
        actions.pack(fill="x", pady=(8, 0))
        self._view_btn = ttk.Button(actions, text="View Specs", style="Accent.TButton",
                                    command=lambda: self._act(self._on_view))
        self._sell_btn = ttk.Button(actions, text="Mark as Sold", style="Plain.TButton",
                                    command=lambda: self._act(self._on_sell))
        self._view_btn.pack(side="left", fill="x", expand=True)
        self._sell_btn.pack(side="left", padx=(8, 0))
        self._selection_changed(None)

    # ------------------------------------------------------------ public API
    def set_cars(self, cars: list[Car]) -> None:
        self._cars = cars
        self._suspend = True
        for attr, _ in COMBO_FILTERS:
            if attr == "model":
                continue
            values = [ANY, *distinct_values(cars, attr)]
            self._combos[attr]["values"] = values
            if self._combo_vars[attr].get() not in values:
                self._combo_vars[attr].set(ANY)
        self._suspend = False
        self._sync_models()
        self._apply()

    def reset_filters(self) -> None:
        self._suspend = True
        for var in self._combo_vars.values():
            var.set(ANY)
        self._search.set("")
        self._min_price.set("")
        self._max_price.set("")
        self._condition.set("All")
        self._suspend = False
        self._sync_models()
        self._apply()

    # --------------------------------------------------------------- internals
    def _value(self, attr: str) -> str | None:
        value = self._combo_vars[attr].get()
        return None if value == ANY else value

    def _criteria(self) -> CarFilter:
        condition = self._condition.get()
        return CarFilter(
            text=self._search.get(),
            condition=None if condition == "All" else condition,
            min_price=_parse_price(self._min_price.get()),
            max_price=_parse_price(self._max_price.get()),
            **{attr: self._value(attr) for attr, _ in COMBO_FILTERS},
        )

    def _on_change(self, *_args) -> None:
        if self._suspend:
            return
        self._sync_models()
        self._apply()

    def _sync_models(self) -> None:
        """Only offer models belonging to the chosen make."""
        pool = filter_cars(self._cars, CarFilter(make=self._value("make")))
        values = [ANY, *distinct_values(pool, "model")]
        self._combos["model"]["values"] = values
        if self._combo_vars["model"].get() not in values:
            self._suspend = True
            self._combo_vars["model"].set(ANY)
            self._suspend = False

    def _apply(self) -> None:
        shown = filter_cars(self._cars, self._criteria())
        self._visible = {str(car.stock_id): car for car in shown}
        self._table.set_rows(
            (str(car.stock_id),
             (car.stock_id, car.make, car.model, car.condition, f"£{car.price:,}"))
            for car in shown
        )
        self._count.configure(text=f"Showing {len(shown)} of {len(self._cars)} cars")
        self._selection_changed(None)

    def _selection_changed(self, iid: str | None) -> None:
        state = "normal" if iid in self._visible else "disabled"
        self._view_btn.configure(state=state)
        self._sell_btn.configure(state=state)

    def _act(self, callback: Callable[[Car], None]) -> None:
        iid = self._table.selected
        if iid in self._visible:
            callback(self._visible[iid])


# ============================================================================
# 'Stock by Brand' tab
# ============================================================================

MODEL_CHIPS_PER_ROW = 6

BRAND_COLUMNS = (
    Column("stock_id", "Stock ID", 70, "center"),
    Column("model", "Model", 230),
    Column("condition", "Used/New", 90, "center"),
    Column("year", "Year", 70, "center"),
    Column("colour", "Colour", 100),
    Column("price", "Price (£)", 110, "e"),
)
_SPEC_WIDTHS = {"Dimensions (L x W x H mm)": 190, "Fuel (L) / battery (kWh)": 170,
                "Transmission": 110, "Drivetrain": 110, "Fuel type": 190}
SPEC_COLUMNS = (
    Column("stock_id", "Stock ID", 70, "center"),
    Column("condition", "Used/New", 90, "center"),
    *(Column(f"spec{i}", label, _SPEC_WIDTHS.get(label, 100))
      for i, label in enumerate(SPEC_LABELS)),
)


class CarStockTab(ttk.Frame):
    def __init__(self, master):
        super().__init__(master, padding=8)
        self._cars: list[Car] = []
        self._brand: str | None = None
        self._model: str | None = None
        self._model_var = tk.StringVar()
        self._brand_cars: dict[str, Car] = {}

        # --- brand picker + total
        top = ttk.Frame(self)
        top.pack(fill="x")
        self._brand_menu = BrandMenu(top, self._select_brand)
        self._brand_menu.pack(side="left")
        self._brand_total = ttk.Label(top, style="Heading.TLabel")
        self._brand_total.pack(side="left", padx=16)

        self._hint = ttk.Label(self, text="Select a car brand to see what's in stock.",
                               style="Muted.TLabel")
        self._hint.pack(pady=40)

        # --- everything below only shows once a brand is chosen
        self._brand_area = ttk.Frame(self)
        ttk.Label(self._brand_area, text="Models (tap one to see its specs)",
                  style="Muted.TLabel").pack(anchor="w", pady=(10, 2))
        self._chips = ttk.Frame(self._brand_area)
        self._chips.pack(fill="x")
        self._brand_table = DataTable(self._brand_area, BRAND_COLUMNS, height=6,
                                      on_select=self._row_selected)
        self._brand_table.pack(fill="x", pady=(8, 0))

        # --- model details (specs + chart)
        self._detail = ttk.Frame(self._brand_area)
        self._model_total = ttk.Label(self._detail, style="Heading.TLabel")
        self._model_total.pack(anchor="w", pady=(12, 4))
        self._spec_table = DataTable(self._detail, SPEC_COLUMNS, height=3, hscroll=True)
        self._spec_table.pack(fill="x")
        self._chart = BarChart(self._detail, title="Price ranges of this model in stock")
        self._chart.pack(fill="both", expand=True, pady=(10, 0))

    # ------------------------------------------------------------ public API
    def set_cars(self, cars: list[Car], known_brands: set[str]) -> None:
        self._cars = cars
        counts = brand_counts(cars, known_brands)
        self._brand_menu.set_brands(counts)
        if self._brand is not None and counts.get(self._brand, 0) == 0:
            self._brand = self._model = None  # last car of this brand was just sold
        self._render()

    # --------------------------------------------------------------- handlers
    def _select_brand(self, brand: str) -> None:
        self._brand, self._model = brand, None
        self._render()

    def _select_model(self) -> None:
        self._model = self._model_var.get() or None
        self._render_detail()

    def _row_selected(self, iid: str | None) -> None:
        car = self._brand_cars.get(iid) if iid else None
        if car and car.model != self._model:
            self._model_var.set(car.model)
            self._select_model()

    # --------------------------------------------------------------- rendering
    def _render(self) -> None:
        self._brand_menu.show(self._brand)
        if self._brand is None:
            self._brand_area.pack_forget()
            self._brand_total.configure(text="")
            self._hint.pack(pady=40)
            return

        self._hint.pack_forget()
        self._brand_area.pack(fill="both", expand=True)

        brand_cars = cars_for(self._cars, self._brand)
        self._brand_cars = {str(c.stock_id): c for c in brand_cars}
        self._brand_total.configure(text=f"Total {self._brand} in stock: {len(brand_cars)}")

        models = model_counts(self._cars, self._brand)
        if self._model not in models:
            self._model = None
        self._model_var.set(self._model or "")
        for chip in self._chips.winfo_children():
            chip.destroy()
        for i, (model, count) in enumerate(models.items()):
            ttk.Radiobutton(self._chips, text=f"{model} ({count})", value=model,
                            variable=self._model_var, style="Chip.Toolbutton",
                            command=self._select_model).grid(
                row=i // MODEL_CHIPS_PER_ROW, column=i % MODEL_CHIPS_PER_ROW,
                padx=(0, 6), pady=3, sticky="w")

        self._brand_table.set_rows(
            (str(c.stock_id), (c.stock_id, c.model, c.condition, c.year, c.colour,
                               f"£{c.price:,}"))
            for c in brand_cars
        )
        self._render_detail()

    def _render_detail(self) -> None:
        if self._brand is None or self._model is None:
            self._detail.pack_forget()
            return
        model_cars = cars_for(self._cars, self._brand, self._model)
        self._detail.pack(fill="both", expand=True)
        self._model_total.configure(
            text=f"{self._brand} {self._model}: {len(model_cars)} in stock")
        self._spec_table.set_rows(
            (str(c.stock_id), (c.stock_id, c.condition, *c.spec_values()))
            for c in model_cars
        )
        self._chart.set_data(price_distribution(model_cars))


# ============================================================================
# 'Add new' form
# ============================================================================

# (attribute, label, widget kind, options)
FIELDS = (
    ("make", "Make", "suggest", None),
    ("model", "Model", "text", None),
    ("condition", "Used / New", "choice", ("Used", "New")),
    ("price", "Price (£)", "text", None),
    ("power", "Power (bhp)", "text", None),
    ("top_speed", "Top speed (mph)", "text", None),
    ("acceleration", "0-60 mph (seconds)", "text", None),
    ("fuel_type", "Fuel type", "text", None),
    ("transmission", "Transmission", "choice", ("Manual", "Automatic")),
    ("gearbox", "Gearbox", "text", None),
    ("drivetrain", "Drivetrain", "text", None),
    ("capacity", "Fuel (L) / battery (kWh) capacity", "text", None),
    ("weight", "Weight (kg)", "text", None),
    ("dimensions", "Dimensions L x W x H (mm)", "text", None),
    ("colour", "Colour", "text", None),
    ("year", "Year", "text", None),
    ("road_tax", "Annual road tax (£)", "text", None),
)


class AddCarDialog(Dialog):
    def __init__(self, parent: tk.Misc, makes: list[str],
                 on_submit: Callable[[dict], None]):
        super().__init__(parent, "Add New Data")
        self._on_submit = on_submit
        self._vars: dict[str, tk.StringVar] = {}

        body = ttk.Frame(self, padding=20)
        body.pack()
        ttk.Label(body, text="Add New Data", style="Title.TLabel").grid(
            row=0, column=0, columnspan=2, pady=(0, 10))

        for index, (attr, label, kind, options) in enumerate(FIELDS):
            row, column = 1 + (index // 2) * 2, index % 2
            var = self._vars[attr] = tk.StringVar()
            ttk.Label(body, text=label).grid(row=row, column=column, sticky="w",
                                             padx=10, pady=(8, 0))
            if kind == "choice":
                widget = ttk.Combobox(body, textvariable=var, values=options,
                                      state="readonly", width=26)
            elif kind == "suggest":
                widget = ttk.Combobox(body, textvariable=var, values=makes, width=26)
            else:
                widget = ttk.Entry(body, textvariable=var, width=28)
            widget.grid(row=row + 1, column=column, padx=10, sticky="ew")
            if index == 0:
                widget.focus_set()

        last_row = 2 + ((len(FIELDS) - 1) // 2) * 2 + 1
        ttk.Label(body, style="Muted.TLabel",
                  text="Type N/A for optional values you don't know "
                       "(top speed, 0-60, capacity, weight, dimensions).").grid(
            row=last_row, column=0, columnspan=2, pady=(12, 0))
        buttons = ttk.Frame(body)
        buttons.grid(row=last_row + 1, column=0, columnspan=2, pady=(10, 0))
        ttk.Button(buttons, text="Cancel", style="Plain.TButton",
                   command=self.destroy).pack(side="left", padx=4)
        ttk.Button(buttons, text="Add Data", style="Accent.TButton",
                   command=self.submit).pack(side="left", padx=4)
        self.bind("<Return>", lambda _e: self.submit())
        self.present()

    def submit(self) -> None:
        form = {attr: var.get() for attr, var in self._vars.items()}
        try:
            fields = build_car_fields(form)
        except ValidationError as exc:
            messagebox.showerror("Invalid input", "\n".join(exc.errors.values()), parent=self)
            return
        try:
            self._on_submit(fields)
        except StockDataError as exc:
            messagebox.showerror("Could not save", str(exc), parent=self)
            return
        self.destroy()
