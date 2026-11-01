import os
import re
import requests as rq

BUY_URL = "https://store.steampowered.com/sale/steamdeckrefurbished"

DECK_MODELS = {
    "903905": "Refurbished 64GB LCD",
    "903906": "Refurbished 256GB LCD",
    "903907": "Refurbished 512GB LCD",
    "1202542": "Refurbished 512GB OLED",
    "1202547": "Refurbished 1TB OLED",
}

headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Accept-Language": "en-US,en;q=0.9",
}

def debug_dump():
    params = {"cc": "gb", "l": "english"}
    cookies = {"birthtime": "0", "lastvisit": "0", "steamCountry": "GB%7C"}
    
    response = rq.get(BUY_URL, headers=headers, params=params, cookies=cookies, timeout=15)
    print(f"[HTTP STATUS] {response.status_code}")
    html = response.text
    print(f"[TOTAL HTML LENGTH] {len(html)} chars\n")

    for pkg_id, name in DECK_MODELS.items():
        print(f"==================================================")
        print(f"DEBUG FOR {name} (ID: {pkg_id})")
        print(f"==================================================")
        
        matches = [m.start() for m in re.finditer(r'\b' + pkg_id + r'\b', html)]
        print(f"Total occurrences found in HTML: {len(matches)}")
        
        if not matches:
            print("  [WARNING] Package ID not found anywhere in raw HTML!")
            continue

        for i, idx in enumerate(matches[:3], start=1):
            snippet = html[max(0, idx - 150): min(len(html), idx + 350)]
            clean_snippet = " ".join(snippet.split())
            print(f"\n--- Match #{i} (Offset {idx}) ---")
            print(f"{clean_snippet}")
        print("\n")

if __name__ == "__main__":
    debug_dump()
