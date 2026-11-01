import json
import os
import sys
import re
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
    
    print("==================================================")
    print("STARTING MULTI-VECTOR STOCK CHECK")
    print("==================================================\n")

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
            locale="en-GB"
        )
        context.add_cookies([{"name": "steamCountry", "value": "GB%7C", "domain": ".steampowered.com", "path": "/"}])
        page = context.new_page()

        # METHOD 1: Passive Network Interception
        print("--- METHOD 1: Listening for Steam AJAX Calls ---")
        def handle_response(response):
            url = response.url
            if "steampowered.com" in url and ("packageinfo" in url.lower() or "getitem" in url.lower()):
                try:
                    print(f"[INTERCEPT] URL: {url} | Status: {response.status}")
                    text = response.text()
                    print(f"  -> Payload Snippet: {text[:200]}\n")
                except Exception:
                    pass

        page.on("response", handle_response)
        
        print(f"Loading {BUY_URL} ...")
        res = page.goto(BUY_URL, wait_until="networkidle", timeout=30000)
        print(f"Page Load HTTP Status: {res.status if res else 'Unknown'}\n")
        page.wait_for_timeout(3000) # Let React render

        # METHOD 2: Live DOM Parsing
        print("--- METHOD 2: Parsing Rendered DOM ---")
        html = page.content()
        dom_results = {}
        for pkg_id in DECK_MODELS.keys():
            # Look for Valve's standard purchase button wrappers or package ID mentions
            matches = re.finditer(f'[^>]*{pkg_id}[^>]*>(.*?)</div>', html, re.IGNORECASE)
            snippets = [m.group(0)[:100].replace('\n', ' ') for m in matches]
            
            if snippets:
                print(f"[{pkg_id}] Found DOM element snippet(s): {snippets[:2]}")
                dom_results[pkg_id] = "out of stock" not in str(snippets).lower()
            else:
                print(f"[{pkg_id}] No explicit DOM elements found linking to this package ID.")
                dom_results[pkg_id] = False
        print("\n")

        # METHOD 3: Active Internal API Fetch
        print("--- METHOD 3: Authenticated Context API Fetch ---")
        fetch_results = {}
        for pkg_id, name in DECK_MODELS.items():
            api_url = f"https://store.steampowered.com/saleaction/ajaxgetpackageinfo?packageid={pkg_id}&cc=GB"
            try:
                # This request comes FROM the browser, bypassing the CDN 404s
                api_res = context.request.get(api_url)
                body = api_res.text()
                
                print(f"[{pkg_id}] Fetch Status: {api_res.status} | Payload: {body[:150]}")
                
                if api_res.status == 200 and "{" in body:
                    data = json.loads(body)
                    b_purchasable = bool(data.get("bPurchasable", False))
                    b_in_stock = bool(data.get("bInStock", False))
                    fetch_results[pkg_id] = b_purchasable or b_in_stock
                else:
                    fetch_results[pkg_id] = False
            except Exception as e:
                print(f"[{pkg_id}] Fetch Error: {e}")
                fetch_results[pkg_id] = False
        
        browser.close()

    print("\n==================================================")
    print("FINAL EVALUATION")
    print("==================================================")
    
    stock_found = False
    for pkg_id, model_name in DECK_MODELS.items():
        # Using the direct fetch as the primary source of truth, fallback to DOM if API failed
        is_available = fetch_results.get(pkg_id, False) or dom_results.get(pkg_id, False)
        
        current_state[pkg_id] = is_available
        was_in_stock = previous_state.get(pkg_id, False)

        if is_
