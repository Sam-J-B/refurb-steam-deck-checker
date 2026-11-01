import json
import urllib.parse
import requests as rq

# Portal 2 (7877) and Refurb 64GB LCD (903905)
PACKAGE_IDS = [7877, 903905]

def check_store_browse_api():
    url = "https://api.steampowered.com/IStoreBrowseService/GetItems/v1"
    
    # We construct the exact JSON payload the React frontend requests
    input_dict = {
        "context": {
            "language": "english",
            "country_code": "GB",
            "steam_realm": 1
        },
        "data_request": {
            "include_assets": False,
            "include_release": False,
            "include_platforms": False,
            "include_all_purchase_options": True,
            "include_screenshots": False,
            "include_trailers": False,
            "include_ratings": False,
            "include_tag_count": 0,
            "include_reviews": False,
            "include_basic_info": True,
            "include_supported_languages": False,
            "include_full_description": False,
            "include_included_items": False
        },
        "ids": [{"packageid": pid} for pid in PACKAGE_IDS]
    }
    
    params = {
        "input_json": json.dumps(input_dict)
    }
    
    print(f"Requesting: {url}\n")
    
    try:
        res = rq.get(url, params=params, timeout=15)
        
        if res.status_code != 200:
            print(f"HTTP Error: {res.status_code}")
            print(res.text[:200])
            return
            
        data = res.json()
        store_items = data.get("response", {}).get("store_items", [])
        
        if not store_items:
            print("[EMPTY] No store items returned.")
            print(f"Raw response: {data}")
            return
            
        for item in store_items:
            name = item.get("name", "Unknown")
            pid = item.get("id")
            print(f"{'='*50}\nID: {pid} | {name}\n{'='*50}")
            
            purchase_options = item.get("purchase_options", [])
            if not purchase_options:
                print("  [NO PURCHASE OPTIONS] (Often means out of stock/delisted)")
                continue
                
            for i, opt in enumerate(purchase_options):
                print(f"\n  -- Purchase Option #{i+1} --")
                # Expose every single raw boolean/integer attached to the purchase option
                for k, v in opt.items():
                    print(f"     {k}: {v}")
            print("\n")
            
    except Exception as e:
        print(f"Exception: {e}")

if __name__ == "__main__":
    check_store_browse_api()
