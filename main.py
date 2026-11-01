import requests as rq
import time

# 2550670 = Refurbished Steam Deck
# 400 = Portal
APP_IDS = [2550670, 400]

headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Accept": "application/json"
}

def check_appdetails():
    for app_id in APP_IDS:
        api_url = f"https://store.steampowered.com/api/appdetails?appids={app_id}&cc=gb"
        print(f"Fetching {api_url}...\n")
        
        try:
            res = rq.get(api_url, headers=headers, timeout=15)
            if res.status_code != 200:
                print(f"HTTP ERROR {res.status_code} for App ID {app_id}\n")
                continue
                
            data = res.json()
            app_info = data.get(str(app_id), {})
            
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
                    
                    for k, v in sub.items():
                        if k not in ["packageid", "option_description", "option_text"]:
                            print(f"       - {k}: {v}")
            print("\n")
            
        except Exception as e:
            print(f"Error checking {app_id}: {e}\n")
            
        # Brief pause to avoid rate limiting
        time.sleep(1)

if __name__ == "__main__":
    check_appdetails()
