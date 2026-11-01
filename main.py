import json
import os
import sys
from playwright.sync_api import sync_playwright
import requests as rq

NTFY_TOPIC = os.getenv("NTFY_TOPIC")
if not NTFY_TOPIC:
    print("Error: NTFY_TOPIC environment variable is not set!")
    sys.exit(1)

BUY_URL = "https://store.steampowered.com/sale/steamdeckrefurbished"
STATE_FILE = "last_state.json"

DECK_MODELS = {
    "903905": "Refurbished 64GB LCD",
    "903906": "Refurbished 256GB LCD",
    "903907": "Refurbished 512GB LCD",
    "1202542": "Refurbished 512GB OLED",
    "1202547": "Refurbished 1TB OLED",
}

def load_previous_state():
    if os.path.exists(STATE_FILE):
        try:
            with open(STATE_FILE, "r") as f:
                return json.load(f)
        except Exception:
            pass
    return {}

def save_current_state(state):
    try:
        with open(STATE_FILE, "w") as f:
            json.dump(state, f, indent=4)
    except Exception as e:
        print(f"Error saving state: {e}")

def send_alert(model_name, is_instock=True):
    if is_instock:
        message = f"{model_name} is in stock!"
        priority = "high"
        tags = "tada,steamdeck"
    else:
        message = f"{model_name} went out of stock."
        priority = "low"
        tags = "x,steamdeck"

    print(f"[ALERT] {message}")
    try:
        rq.post(
            f"https://ntfy.sh/{NTFY_TOPIC}",
            data=message.encode("utf-8"),
            headers={
                "Title": "Steam Deck Refurb Restock!",
                "Click": BUY_URL,
                "Priority": priority,
                "Tags": tags
            },
            timeout=10
        )
    except Exception as e:
        print(f"ntfy error: {e}")

def check_stock():
    previous_state = load_previous_state()
    current_state = previous_state.copy()
    
    # Default everything to False
    stock_results = {pkg_id: False for pkg_id in DECK_MODELS.keys()}

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
            locale="en-GB"
        )
        context.add_cookies([
            {"name": "steamCountry", "value": "GB%7C", "domain": ".steampowered.com", "path": "/"}
        ])

        page = context.new_page()

        # Listen for Steam's backend stock check JSON
        def handle_response(response):
            if "ajaxgetpackageinfo" in response.url:
                try:
                    data = response.json()
                    for pkg_id in DECK_MODELS.keys():
                        if f"packageid={pkg_id}" in response.url:
                            b_purchasable = bool(data.get("bPurchasable", False))
                            b_in_stock = bool(data.get("bInStock", False))
                            stock_results[pkg_id] = b_purchasable or b_in_stock
                except Exception:
                    pass

        page.on("response", handle_response)
        print("Checking Steam Deck Refurbished page via Playwright...")
        page.goto(BUY_URL, wait_until="networkidle", timeout=30000)
        page.wait_for_timeout(2000)  # Ensure React finishes firing AJAX requests
        browser.close()

    stock_found = False
    for pkg_id, model_name in DECK_MODELS.items():
        is_available = stock_results[pkg_id]
        current_state[pkg_id] = is_available
        was_in_stock = previous_state.get(pkg_id, False)

        if is_available:
            stock_found = True
            if not was_in_stock:
                send_alert(model_name, is_instock=True)
            else:
                print(f"[{model_name}] Still in stock (Alert suppressed)")
        else:
            if was_in_stock:
                send_alert(model_name, is_instock=False)
            print(f"[{model_name}] Out of stock")

    if not stock_found:
        print("\nAll refurbished models are currently out of stock.")

    save_current_state(current_state)

if __name__ == "__main__":
    check_stock()
