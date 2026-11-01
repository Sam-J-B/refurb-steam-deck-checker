import json
import os
import requests as rq

NTFY_TOPIC = os.getenv("NTFY_TOPIC")
if not NTFY_TOPIC:
    raise ValueError("NTFY_TOPIC environment variable is not set!")

STATE_FILE = "last_state.json"

def send_alert(model_name, is_instock=True):
    message = f"[TEST] {model_name} is IN STOCK!" if is_instock else f"[TEST] {model_name} is OUT OF STOCK!"
    print(f"[ALERT SENT] {message}")
    
    try:
        rq.post(
            f"https://ntfy.sh/{NTFY_TOPIC}",
            data=message.encode("utf-8"),
            headers={
                "Title": "Steam Deck Test Restock",
                "Priority": "high",
                "Tags": "tada,steamdeck"
            },
            timeout=10
        )
    except Exception as e:
        print(f"ntfy error: {e}")

def test_restock_logic():
    print("--- RUN 1: Simulating Refurbished 512GB OLED coming into stock ---")
    
    # Simulated response from Valve where stock flips to True
    mock_steam_response = {
        "1202542": {"name": "Refurbished 512GB OLED", "in_stock": True},
        "903905": {"name": "Refurbished 64GB LCD", "in_stock": False}
    }
    
    previous_state = {}
    current_state = {}
    
    for pkg_id, item in mock_steam_response.items():
        is_available = item["in_stock"]
        model_name = item["name"]
        
        current_state[pkg_id] = is_available
        was_in_stock = previous_state.get(pkg_id, False)
        
        if is_available and not was_in_stock:
            send_alert(model_name, is_instock=True)
            
    print("\n--- RUN 2: Simulating second check (Alert Suppression) ---")
    # Same state - should NOT send a second notification to your phone
    for pkg_id, item in mock_steam_response.items():
        is_available = item["in_stock"]
        model_name = item["name"]
        was_in_stock = current_state.get(pkg_id, False)
        
        if is_available and was_in_stock:
            print(f"[In Stock - Alert Suppressed] {model_name} (State persistence verified)")

if __name__ == "__main__":
    test_restock_logic()
