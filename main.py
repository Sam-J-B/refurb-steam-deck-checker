import json
import os
import requests as rq

NTFY_TOPIC = os.getenv("NTFY_TOPIC")
if not NTFY_TOPIC:
    raise ValueError("NTFY_TOPIC environment variable is not set!")

# 1. Swapped the URL to the main standard Steam Deck store page
BUY_URL = "https://store.steampowered.com/steamdeck"
STATE_FILE = "last_state.json"

# 2. Swapped to a standard, currently IN-STOCK Steam Deck package ID
DECK_MODELS = {
    "946114": "TEST: Standard 1TB OLED",
}

headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Accept-Language": "en-US,en;q=0.9",
}

def load_previous_state():
    if os.path.exists(STATE_FILE):
        try:
            with open(STATE_FILE, "r") as f:
                return json.load(f)
        except Exception as e:
            print(f"Error loading state file: {e}")
    return {}

def save_current_state(state):
    try:
        with open(STATE_FILE, "w") as f:
            json.dump(state, f, indent=4)
    except Exception as e:
        print(f"Error saving state file: {e}")

def send_alert(model_name, is_instock=True):
    if is_instock:
        message = f"{model_name} is in stock!"
        title = "Steam Deck Test Restock!"
        priority = "high"
        tags = "tada,steamdeck"
    else:
        message = f"{model_name} has just gone out of stock."
        title = "Steam Deck Sold Out"
        priority = "low"
        tags = "x,steamdeck"

    print(f"[ALERT SENT] {message}")

    try:
        rq.post(
            f"https://ntfy.sh/{NTFY_TOPIC}",
            data=message.encode("utf-8"),
            headers={
                "Title": title,
                "Click": BUY_URL,
                "Priority": priority,
                "Tags": tags
            },
            timeout=10
        )
    except Exception as e:
        print(f"ntfy error: {e}")

def check_stock_html():
    previous_state = load_previous_state()
    current_state = {}
    stock_found = False

    try:
        # Request page directly with cookies to bypass age gates/session blocks
        response = rq.get(BUY_URL, headers=headers, cookies={"birthtime": "0", "lastvisit": "0"}, timeout=15)
        
        if response.status_code != 200:
            print(f"Failed to fetch store page. HTTP Status: {response.status_code}")
            save_current_state(previous_state)
            return

        html = response.text

        for package_id, model_name in DECK_MODELS.items():
            is_available = False
            
            # Locate the package ID in the webpage HTML
            if f'packageid="{package_id}"' in html or f"packageid='{package_id}'" in html or f'data-ds-packageid="{package_id}"' in html:
                idx = html.find(package_id)
                snippet = html[max(0, idx - 200): min(len(html), idx + 500)]
                
                if "btn_add_to_cart" in snippet or "Add to Cart" in snippet:
                    is_available = True

            current_state[package_id] = is_available
            was_in_stock = previous_state.get(package_id, False)

            if is_available:
                stock_found = True
                if not was_in_stock:
                    send_alert(model_name, is_instock=True)
                else:
                    print(f"[In Stock - Alert Suppressed] {model_name}")
            else:
                if was_in_stock:
                    send_alert(model_name, is_instock=False)
                print(f"[Out of stock] {model_name}")

        if not stock_found:
            print("All refurbished models are out of stock")

        save_current_state(current_state)

    except Exception as e:
        print(f"Error parsing Steam page: {e}")
        save_current_state(previous_state)

if __name__ == "__main__":
    check_stock_html()
