import json
import os
import sys
import traceback
from playwright.sync_api import sync_playwright
import requests as rq

NTFY_TOPIC = os.getenv("NTFY_TOPIC")
if not NTFY_TOPIC:
    print("Error: NTFY_TOPIC environment variable is not set!")
    sys.exit(1)

BUY_URL = "https://store.steampowered.com/sale/steamdeckrefurbished?cc=gb"
STATE_FILE = "last_state.json"

DECK_MODELS = {
    "64 GB LCD": "Refurbished 64GB LCD",
    "256 GB LCD": "Refurbished 256GB LCD",
    "512 GB LCD": "Refurbished 512GB LCD",
    "512 GB OLED": "Refurbished 512GB OLED",
    "1TB OLED": "Refurbished 1TB OLED",
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

def check_stock():
    previous_state = load_previous_state()
    current_state = previous_state.copy()
    
    print(f"Loading {BUY_URL} via Playwright...")

    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            context = browser.new_context(locale="en-GB")
            context.add_cookies([
                {"name": "steamCountry", "value": "GB%7C", "domain": ".steampowered.com", "path": "/"}
            ])
            
            page = context.new_page()
            response = page.goto(BUY_URL, wait_until="networkidle", timeout=30000)
            
            if response and response.status not in [200, 304]:
                send_error_alert(f"Valve returned bad HTTP status: {response.status}")
                return

            page.wait_for_timeout(6000) 
            
            visible_text = page.locator("body").inner_text()
            lines = [line.strip() for line in visible_text.split('\n') if line.strip()]
            browser.close()

        if not lines or len(lines) < 10:
            send_error_alert("Page loaded but no text found. WAF block or React failure.")
            return

        stock_found = False
        models_found_in_dom = 0

        print("\n==================================================")
        print("DOM MATCHING & PARSING LOGS")
        print("==================================================")

        for key_phrase, friendly_name in DECK_MODELS.items():
            is_available = False
            matched_line = None
            snippet_checked = None
            
            for i, line in enumerate(lines):
                line_lower = line.lower()
                # Must contain BOTH the capacity identifier AND 'refurbished'
                if key_phrase.lower() in line_lower and "refurbished" in line_lower:
                    models_found_in_dom += 1
                    matched_line = line
                    
                    snippet_lines = lines[i : i + 5]
                    snippet_checked = " | ".join(snippet_lines)
                    block_snippet = " ".join(snippet_lines).lower()
                    
                    # 1. Explicitly check for Out of Stock first
                    if "out of stock" in block_snippet:
                        is_available = False
                    # 2. Require positive confirmation for availability
                    elif any(kw in block_snippet for kw in ["add to cart", "add to basket", "buy", "in stock", "available"]):
                        is_available = True
                    # 3. Handle unhydrated/glitched DOM states safely
                    else:
                        print(f"  -> HYDRATION WARNING: Neither 'out of stock' nor stock buttons found for {friendly_name}.")
                        print(f"     Raw block captured: '{snippet_checked}'")
                        is_available = False
                    break

            if matched_line:
                print(f"[{friendly_name}] MATCH FOUND:")
                print(f"  -> Title Line: '{matched_line}'")
                print(f"  -> Block Checked: '{snippet_checked}'")
            else:
                print(f"[{friendly_name}] NO MATCH FOUND IN DOM")

            current_state[friendly_name] = is_available
            was_in_stock = previous_state.get(friendly_name, False)

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

        if models_found_in_dom == 0:
            print("\n[DIAGNOSTIC LOG DUMP] Top 40 lines captured on page:")
            for line in lines[:40]:
                print(f"  -> {line}")
            send_error_alert("Could not find Steam Deck model keywords on page.")
            return

        if not stock_found:
            print("Final Status: All refurbished models are currently out of stock.")

        save_current_state(current_state)

    except Exception as e:
        error_details = str(e).split('\n')[0]
        send_error_alert(f"Script crashed: {error_details}")
        traceback.print_exc()

if __name__ == "__main__":
    check_stock()
