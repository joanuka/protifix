# protifit

A restaurant website for a Nigerian kitchen in Abuja, with online ordering and a **plant-based menu** that lets customers swap meat for an affordable alternative protein: same portion, a photo of what they get, and a lower price.

Built with Python ([FastAPI](https://fastapi.tiangolo.com/)) and plain HTML/CSS/JavaScript. No database server and no build step.

## Features

- **Restaurant menu** with photos and prices, generated from one file (`menu.json`)
- **Online ordering**: tap **Order** on a dish, review the basket, send the order for pickup or delivery
- **Plant-based "Swap and save"**: pick a dish, see every plant-based version with a picture, a plain description, protein, allergens and a cheaper price
- **Kitchen consultant**: tell it the dish, budget and skill level and it recommends the best alternative protein for the kitchen, with cost, protein, texture match and CO₂ saved (works offline; an AI model is optional)
- **Customer accounts**: sign up, log in, saved address and allergy filters, order history
- **Staff dashboard** (`/admin`): see incoming orders, change their status, read customer feedback
- **Feedback page**

## Quick start (Windows)

You need [Python 3.10 or newer](https://www.python.org/downloads/) (tick "Add Python to PATH" when installing).

```powershell
# 1. open a terminal in the project folder (the one containing app.py)
cd path\to\jojo

# 2. install the packages (once)
py -m pip install -r requirements.txt

# 3. start the server
py -m uvicorn app:app --reload --port 8000
```

Now open **http://127.0.0.1:8000** in your browser. Press `Ctrl+C` in the terminal to stop the server.

macOS / Linux: use `python3` instead of `py`.

To open the site on your phone, start it with `--host 0.0.0.0` and visit `http://<your-computer-ip>:8000` while on the same Wi-Fi.

> `uvicorn` is the program that runs the website. If port 8000 is busy, pick another number (for example `--port 8001`).

## Pages

| Address | What it is |
|---|---|
| `/` | Restaurant home page and menu |
| `/order` | Basket and checkout |
| `/plant-based` | Swap and save, and the kitchen consultant |
| `/account` | Log in, sign up, saved details, order history |
| `/feedback` | Customer feedback |
| `/admin` | Staff login and orders dashboard |

## Optional settings

Set these in the terminal before starting the server (PowerShell shown). None are required.

```powershell
$env:ACCOUNT_SECRET="any-long-random-text"     # keeps customers logged in after a restart
$env:ADMIN_USER="owner"                         # staff login for /admin
$env:ADMIN_PASSWORD="a-long-password"           # /admin stays off until this is set
$env:ADMIN_SECRET="another-long-random-text"    # keeps staff logged in after a restart
$env:GEMINI_API_KEY="..."                       # optional AI answers (Google Gemini)
$env:ANTHROPIC_API_KEY="..."                    # optional AI answers (Claude)
```

Without an AI key the consultant uses its built-in data engine, so everything still works. **Never put keys or passwords in the code or commit them to GitHub.**

## How the plant-based prices work

Each alternative is sold at the **same portion** as the meat version (100 g cooked), and the customer gets the saving on the ingredient:

```
price = dish price - (meat cost - plant cost)      at least 10% and at most 45% cheaper, rounded to ₦50
```

Example: beef suya at ₦3,500 becomes ₦2,950 with awara (tofu) and ₦2,700 with soya chunks. Tune the rules at the top of the "pictures and prices" section in `app.py` (`SWAP_PASS_THROUGH`, `SWAP_MIN_OFF`, `SWAP_MAX_OFF`). The meat costs are estimates: replace them with your real costs.

## Project layout

```
app.py                 the server: menu, orders, swap prices, consultant
menu.json              dishes and prices (edit this to change the menu)
ingredients.csv        135 plant-protein options with cost, protein, allergens, CO2
accounts.py            customer accounts          account.html, account-nav.js
admin.py, admin.html   staff dashboard
feedback.py            feedback page and API      feedback.html
order.html, cart.js    ordering
index.html             plant-based page
restaurant.html        home page
make_alt_images.py     drawn pictures used when there is no photo
get_food_photos.py     downloads real food photos into images/alt/
images/                photos (hero.jpg, jollof.jpg, ... and images/alt/)
```

See `DATA SOURCES.md` for where the ingredient numbers come from.

## Photos

Dish photos live in `images/`. For the alternative foods, run `py get_food_photos.py` to download free photos from Wikimedia Commons into `images/alt/`, or add your own (for example `images/alt/tofu.jpg`); a real photo always replaces the drawing. Many Wikimedia photos need credit: keep `images/alt/CREDITS.txt`, or use your own photos.

## Customer data

Orders, accounts and feedback are stored in local files (`orders.jsonl`, `accounts.db`, `feedback.db`, `order_status.json`). They contain customers' names and phone numbers, so they are listed in `.gitignore` and must not be committed.

## Licence

Add a licence of your choice (for example MIT) before sharing the code publicly.
