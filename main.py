import requests as rq

NTFY_TOPIC = "sam_steam_deck_refurb_alerts_99"
BUY_URL = "https://store.steampowered.com/sale/steamdeckrefurbished"
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

def send_alert(model_name):
    message = f"{model_name} is in stock"
    print(message)

    try:
        rq.post(
            f"https://ntfy.sh/{NTFY_TOPIC}",
            data=message.encode('utf-8'),
            headers={
                "Title": "Steam Deck Refurb Restock!",
                "Click": BUY_URL
            },
            timeout=10
        )
    except Exception as e:
        print(f"ntfy error: {e}")

def check_stock():
    stock_found = False
    for package_id, model_name in DECK_MODELS.items():
        url = f"https://api.steampowered.com/IPhysicalGoodsService/CheckInventoryAvailableByPackage/v1?packageid={package_id}&country_code=GB"

        try:
            response = rq.get(url, headers=headers, timeout=10)
            if response.status_code == 200:
                api_data = response.json()
                is_available = True 
                # api_data.get("response", {}).get("inventory_available", False)

                if is_available:
                    stock_found = True
                    send_alert(model_name)
                else:
                    print(f"[Out of stock] {model_name}")
        except Exception as e:
            print(f"Error checking {model_name}: {e}")

    if not stock_found:
        print("All refurbished models are out of stock")
        

if __name__ == "__main__":
    check_stock()