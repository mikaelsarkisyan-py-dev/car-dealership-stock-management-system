# Car Dealership Stock Management System

A desktop application for car dealership staff to manage vehicle stock. Employees log in, browse and filter the cars in stock, view full specifications, add new vehicles and record sales.

Built with Python and Tkinter, with stock stored in an Excel workbook so it can be opened and checked in Excel at any time.

## Features

**Accounts**
- Login page loads first so staff can sign in quickly, with a button for new employees to create an account
- Usernames are generated automatically: first letter of the first name + surname + a random 4-digit number (e.g. `MLanner5671`)
- Password rules enforced at sign-up: at least 8 characters, with capital and lowercase letters, a number and a special character
- Passwords are stored as salted hashes, never as plain text
- User icon (top left) shows the logged-in employee's details and username

**All Stock tab**
- Live search by make or model
- Filter by make, model, transmission, fuel type, gearbox, drivetrain, colour, used/new and price range
- Select a car to view its full specifications
- Mark a car as sold, which records the sale and removes it from stock

**Stock by Brand tab**
- Choose a brand from the drop-down to see every car of that brand and the total in stock
- Brands with no cars left in stock are greyed out
- Select a model to see its full spec table, the number in stock and a bar chart of its price ranges (e.g. £10k - £15k)

**Add new cars**
- A single form with validation that reports every problem at once, rather than one error at a time

## Getting started

You need Python 3 (developed and tested on Python 3.12). Tkinter comes with the standard Python installers.

1. Clone the repository:

   ```bash
   git clone https://github.com/mikaelsarkisyan-py-dev/car-dealership-stock-management-system.git
   cd car-dealership-stock-management-system
   ```

2. Install the one dependency:

   ```bash
   pip install -r requirements.txt
   ```

3. Run the app:

   ```bash
   python main.py
   ```

**First time running it:** the repository does not include any user accounts. Click **Create new account** on the login page, fill in the form, and your username will be generated and shown to you. It is saved in a `users.json` file that the app creates automatically (and Git ignores).

## Project structure

| File | What it does |
|------|--------------|
| `main.py` | Starts the app; the main window plus the login and sign-up screens |
| `main_page.py` | Main screen: the two stock tabs and the add-car form |
| `widgets.py` | Colours and styling, data table, brand drop-down, bar chart, pop-up windows |
| `stock.py` | Cars and sales, reading and writing `stock.xlsx`, search/filter rules, validation |
| `auth.py` | Sign-up and login rules, reading and writing `users.json` |
| `stock.xlsx` | Sample stock data (a **Stock** sheet and a **Sales** sheet) |
| `docs/` | Project documentation: requirements, data dictionaries, data flow diagram |
| `tests/` | Automated tests |

The code is split so each file has one job. Screens (`main.py`, `main_page.py`, `widgets.py`) only deal with what the user sees and clicks. The rules and file handling live in `stock.py` and `auth.py`, which contain no screen code, which makes them easy to test.

## Data

Stock is kept in `stock.xlsx`:
- **Stock** sheet: one row per car in stock, each with a unique Stock ID
- **Sales** sheet: one row per sold car, with the date, the employee who sold it and the sale price

Close `stock.xlsx` in Excel before using the app, otherwise saving will be refused (the app will tell you if this happens).

## Running the tests

```bash
pip install pytest
pytest
```

The tests cover the password and username rules, login, search and filtering, price-range grouping, add-car validation and reading/writing the stock file. They work on a temporary copy of the data, so they never change your real files.

## Documentation

The `docs/` folder holds the original design material for the project: the login and stock page requirements, the data dictionaries for the stock, sales and user tables, and the level 0 data flow diagram.

## Possible future improvements

- A change-password option and an admin screen for managing accounts
- Moving from Excel to a database for larger stock levels
- Sales reports (e.g. sales per employee)
