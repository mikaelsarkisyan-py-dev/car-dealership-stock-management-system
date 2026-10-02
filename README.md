# Car Dealership Stock Management

Desktop app (Python + Tkinter) for dealership staff: log in, browse stock, view specs,
add cars and record sales.

    pip install -r requirements.txt
    python main.py

## Files

| File | What it holds |
|------|---------------|
| `main.py` | Starts the app; the window plus the login and sign-up screens |
| `main_page.py` | Main screen: "All Stock" tab, "Stock by Brand" tab, add-car form |
| `widgets.py` | Colours/styling, table, brand drop-down, bar chart, pop-up windows |
| `stock.py` | Cars and sales, reading/writing `stock.xlsx`, search/filter rules, validation |
| `auth.py` | Accounts: sign-up/login rules, reading/writing `users.json` |
| `stock.xlsx` | Stock (each car has a Stock ID) and Sales sheets |
| `users.json` | Accounts (passwords stored as salted hashes, not plain text) |
| `docs/` | Requirements, data dictionaries, DFD |
| `tests/` | `pip install pytest`, then run `pytest` |

Put `car-16.ico` next to `main.py` for the window icon (optional).

Close `stock.xlsx` in Excel before using the app, otherwise saving is refused.
