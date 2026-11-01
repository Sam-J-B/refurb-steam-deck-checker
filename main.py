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
    "Steam Deck 64 GB LCD - Valve Certified Refurbished": "Refurbished 64GB LCD",
    "Steam Deck 256 GB LCD - Valve Certified Refurbished": "Refurbished 256GB LCD",
    "Steam Deck 512 GB LCD - Valve Certified Refurbished": "Refurbished 512GB LCD",
    "Steam Deck 512 GB OLED - Valve Certified Refurbished": "Refurbished 512GB OLED",
    "Steam Deck 1TB OLED - Valve Certified Refurbished": "Refurbished 1TB OLED",
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
        message = f"{model_name} is IN STOCK!"
        priority = "high"
        tags = "tada,steamdeck"
    else:
        message = f"{model_name} went out of stock."
        priority = "low"
        tags = "x,steamdeck"

    print(f"[ALERT SENT] {message}")
    try:
        rq.post(
            f"https://ntfy.sh/{NTFY_TOPIC}",
            data=message.encode("utf-8"),
            headers={
                "Title": "Steam Deck Restock Alert!",
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
    
    print(f"Loading {BUY_URL} via Playwright...")

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(locale="en-GB")
        context.add_cookies([
            {"name": "steamCountry", "value": "GB%7C", "domain": ".steampowered.com", "path": "/"}
        ])
        
        page = context.new_page()
        page.goto(BUY_URL, wait_until="networkidle", timeout=30000)
        page.wait_for_timeout(5000) 
        
        visible_text = page.locator("body").inner_text()
        lines = [line.strip() for line in visible_text.split('\n') if line.strip()]
        browser.close()

    stock_found = False

    for exact_title, friendly_name in DECK_MODELS.items():
        is_available = False
        
        for i, line in enumerate(lines):
            if exact_title in line:
                block_snippet = " ".join(lines[i : i + 4]).lower()
                
                if "out of stock" in block_snippet:
                    is_available = False
                else:
                    is_available = True
                break

        current_state[friendly_name] = is_available
        was_in_stock = previous_state.get(friendly_name, False)

        if is_available:
            stock_found = True
            if not was_in_stock:
                send_alert(friendly_name, is_instock=True)
            else:
                print(f"[{friendly_name}] Still in stock (Alert suppressed)")
        else:
            if was_in_stock:
                send_alert(friendly_name, is_instock=False)
            print(f"[{friendly_name}] Evaluated Out of Stock")

    if not stock_found:
        print("\nAll refurbished models are currently out of stock.")

    save_current_state(current_state)

if __name__ == "__main__":
    check_stock()
