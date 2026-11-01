import json
import os
import requests as rq

NTFY_TOPIC = os.getenv("NTFY_TOPIC")
if not NTFY_TOPIC:
    raise ValueError("NTFY_TOPIC environment variable is not set!")

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
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Accept": "application/json",
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

def send_error_alert(error_message):
    print(f"[ERROR ALERT SENT] {error_message}")
    try:
        rq.post(
            f"https://ntfy.sh/{NTFY_TOPIC}",
            data=error_message.encode("utf-8"),
            headers={
                "Title": "Script Error: Steam Deck Checker",
                "Priority": "high",
                "Tags": "warning"
            },
            timeout=10
        )
    except Exception as e:
        print(f"ntfy error: {e}")

def check_stock():
    previous_state = load_previous_state()
    current_state = previous_state.copy()
    stock_found = False
    all_checks_successful = True

    for package_id, model_name in DECK_MODELS.items():
        api_url = f"https://store.steampowered.com/api/packagedetails?packageids={package_id}&cc=gb&l=english"
        
        try:
            response = rq.get(api_url, headers=headers, timeout=10)
            if response.status_code != 200:
                print(f"[HTTP ERROR {response.status_code}] {model_name}")
                all_checks_successful = False
                continue

            api_data = response.json()
            pkg_info = api_data.get(package_id, {})
            is_available = False

            if pkg_info.get("success") and "data" in pkg_info:
                data = pkg_info["data"]
                name_in_api = data.get("name", "Unknown Package")
                can_purchase = data.get("can_purchase", False)
                
                # Expose raw payload details directly in the runner log
                print(f"[STEAM VERIFIED] ID: {package_id} | Name: '{name_in_api}' | can_purchase: {can_purchase}")
                
                is_available = bool(can_purchase)
            else:
                print(f"[API RESPONSE FAILED] ID: {package_id} | success: {pkg_info.get('success')} | Raw: {pkg_info}")
                all_checks_successful = False

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
                print(f"[Out of stock] {model_name}\n")

        except Exception as e:
            print(f"[EXCEPTION] Failed checking {model_name}: {e}\n")
            all_checks_successful = False

    if not all_checks_successful:
        error_msg = "Steam API returned non-200 status or unparseable payloads."
        if not previous_state.get("in_error_state", False):
            send_error_alert(error_msg)
        current_state["in_error_state"] = True
    else:
        current_state["in_error_state"] = False
        if not stock_found:
            print("All refurbished models are out of stock")

    save_current_state(current_state)

if __name__ == "__main__":
    check_stock()
