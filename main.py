import requests as rq

# 2550670 = Refurbished Steam Deck (Master App ID)
# 400 = Portal (Test App ID)
API_URL = "https://store.steampowered.com/api/appdetails?appids=2550670,400&cc=gb"

headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
    "Accept": "application/json"
}

def check_appdetails():
    print(f"Fetching {API_URL}...\n")
    try:
        res = rq.get(API_URL, headers=headers, timeout=15)
        if res.status_code != 200:
            print(f"HTTP ERROR: {res.status_code}")
            return
            
        data = res.json()
        
        for app_id, app_info in data.items():
            print(f"{'='*50}")
            print(f"APP ID: {app_id}")
            print(f"{'='*50}")
            
            if not app_info.get("success"):
                print("  [STATUS] success: False\n")
                continue
                
            app_data = app_info.get("data", {})
            print(f"  Name: {app_data.get('name')}")
            
            groups = app_data.get("package_groups", [])
            if not groups:
                print("  [INVENTORY] No package groups found (Item unavailable).\n")
                continue
                
            for group in groups:
                print(f"  -> Group: {group.get('name', 'N/A')}")
                subs = group.get("subs", [])
                
                if not subs:
                    print("     [EMPTY] No active packages (Sub IDs) available in this group.")
                
                for sub in subs:
                    pkg_id = sub.get("packageid")
                    print(f"\n     * ACTIVE SUB ID: {pkg_id}")
                    
                    # Print all keys attached to this active package to see if a stock flag exists
                    for k, v in sub.items():
                        if k not in ["packageid", "option_description", "option_text"]:
                            print(f"       - {k}: {v}")
            print("\n")
            
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    check_appdetails()
