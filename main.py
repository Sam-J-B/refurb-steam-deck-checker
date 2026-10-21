import json
import os
import requests as rq

NTFY_TOPIC = "sam_steam_deck_refurb_alerts_99"
BUY_URL = "https://store.steampowered.com/sale/steamdeckrefurbished"
STATE_FILE = "last_state.json"

DECK_MODELS = {
    "903905": "Refurbished 64GB LCD",
    "903906": "Refurbished 256GB LCD",
    "903907": "Refurbished 512GB LCD",
    "1202542": "Refurbished 512GB OLED",
    "1202547": "Refurbished 1TB OLED",
}

headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
}

def load_previous_state():
    """Loads previously tracked stock states from last_state.json."""
    if os.path.exists(STATE_FILE):
        try:
            with open(STATE_FILE, "r") as f:
                return json.load(f)
        except Exception as e:
            print(f"Error loading state file: {e}")
    return {}

def save_current_state(state):
    """Saves updated stock states to last_state.json."""
    try:
        with open(STATE_FILE, "w") as f:
            json.dump(state, f, indent=4)
    except Exception as e:
        print(f"Error saving state file: {e}")

def send_alert(model_name, is_instock=True):
    """Sends a push notification to ntfy.sh for both restocks and sell-outs."""
    if is_instock:
        message = f"{model_name} is in stock!"
        title = "Steam Deck Refurb Restock!"
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

def check_stock():
    previous_state = load_previous_state()
    current_state = {}
    stock_found = False

    for package_id, model_name in DECK_MODELS.items():
        url = f"https://api.steampowered.com/IPhysicalGoodsService/CheckInventoryAvailableByPackage/v1?packageid={package_id}&country_code=GB"

        try:
            response = rq.get(url, headers=headers, timeout=10)
            if response.status_code == 200:
                api_data = response.json()
                is_available = api_data.get("response", {}).get("inventory_available", False)
                current_state[package_id] = is_available

                # Check state transition using previous run state
                was_in_stock = previous_state.get(package_id, False)

                if is_available:
                    stock_found = True
                    if not was_in_stock:
                        # Transition 1: Out of stock -> In stock
                        send_alert(model_name, is_instock=True)
                    else:
                        print(f"[In Stock - Alert Suppressed] {model_name}")
                else:
                    if was_in_stock:
                        # Transition 2: In stock -> Out of stock
                        send_alert(model_name, is_instock=False)
                    print(f"[Out of stock] {model_name}")
            else:
                print(f"API Error {response.status_code} for {model_name}")
                current_state[package_id] = previous_state.get(package_id, False)
        except Exception as e:
            print(f"Error checking {model_name}: {e}")
            current_state[package_id] = previous_state.get(package_id, False)

    if not stock_found:
        print("All refurbished models are out of stock")

    save_current_state(current_state)

if __name__ == "__main__":
    check_stock()
