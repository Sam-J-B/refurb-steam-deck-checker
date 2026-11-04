import json
import os
import sys
import traceback
from curl_cffi import requests as rq

NTFY_TOPIC = os.getenv("NTFY_TOPIC")
if not NTFY_TOPIC:
    print("Error: NTFY_TOPIC environment variable is not set!")
    sys.exit(1)

BUY_URL = "https://store.steampowered.com/sale/steamdeckrefurbished"
STATE_FILE = "last_state.json"

# Valve Package IDs for UK Refurbished Steam Decks
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

def send_error_alert(error_message):
    print(f"[ERROR ALERT SENT] {error_message}")
    try:
        rq.post(
            f"https://ntfy.sh/{NTFY_TOPIC}",
            data=error_message.encode("utf-8"),
            headers={
                "Title": "Steam Checker FAILED",
                "Priority": "high",
                "Tags": "warning,skull"
            },
            timeout=10
        )
    except Exception as e:
        print(f"ntfy error: {e}")

def query_steam_api(pkg_id, friendly_name):
    api_url = f"https://store.steampowered.com/saleaction/ajaxgetpackageinfo?packageid={pkg_id}&cc=GB"
    
    try:
        # TLS fingerprint spoofing via curl_cffi
        res = rq.get(
            api_url, 
            impersonate="chrome", 
            cookies={"steamCountry": "GB%7C"},
            headers={"X-Requested-With": "XMLHttpRequest", "Referer": BUY_URL},
            timeout=15
        )
        
        print(f"[{friendly_name}] HTTP Status: {res.status_code}")
        
        if res.status_code == 200 and res.text.strip().startswith("{"):
            data = res.json()
            b_purchasable = bool(data.get("bPurchasable", False))
            b_in_stock = bool(data.get("bInStock", False))
            
            print(f"  -> Raw Keys: bPurchasable={b_purchasable} | bInStock={b_in_stock}")
            return b_purchasable or b_in_stock
        else:
            print(f"  -> Non-JSON / WAF Blocked Payload: {res.text[:80]}")
            return None
            
    except Exception as e:
        print(f"  -> Exception: {e}")
        return None

def check_stock():
    previous_state = load_previous_state()
    current_state = previous_state.copy()
    stock_found = False
    failed_calls = 0

    print("==================================================")
    print("DIRECT API STOCK CHECK (ajaxgetpackageinfo)")
    print("==================================================")

    for pkg_id, friendly_name in DECK_MODELS.items():
        is_available = query_steam_api(pkg_id, friendly_name)
        
        if is_available is None:
            failed_calls += 1
            is_available = False

        current_state[pkg_id] = is_available
        was_in_stock = previous_state.get(pkg_id, False)

        if is_available:
            stock_found = True
            if not was_in_stock:
                send_alert(friendly_name, is_instock=True)
            else:
                print(f"  -> Evaluation: Still in stock (Alert suppressed)\n")
        else:
            if was_in_stock:
                send_alert(friendly_name, is_instock=False)
            print(f"  -> Evaluation: Out of Stock\n")

    # Trigger alert if all package API calls return blocked empty responses
    if failed_calls == len(DECK_MODELS):
        send_error_alert("API returned empty payloads across all packages. Akamai challenge blocking request.")
        return

    if not stock_found:
        print("Final Status: All refurbished models are currently out of stock.")

    save_current_state(current_state)

if __name__ == "__main__":
    check_stock()
