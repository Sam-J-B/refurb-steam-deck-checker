import sys
from playwright.sync_api import sync_playwright

BUY_URL = "https://store.steampowered.com/sale/steamdeckrefurbished"

# Using the literal text rendered on the screen rather than hidden package IDs
DECK_MODELS = {
    "64 GB LCD": "Refurbished 64GB LCD",
    "256 GB LCD": "Refurbished 256GB LCD",
    "512 GB LCD": "Refurbished 512GB LCD",
    "512 GB OLED": "Refurbished 512GB OLED",
    "1TB OLED": "Refurbished 1TB OLED",
}

def check_stock():
    print(f"Loading {BUY_URL} in Playwright...")
    
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        # Force UK localization so prices and stock reflect GB
        context = browser.new_context(locale="en-GB")
        context.add_cookies([
            {"name": "steamCountry", "value": "GB%7C", "domain": ".steampowered.com", "path": "/"}
        ])
        
        page = context.new_page()
        page.goto(BUY_URL, wait_until="networkidle", timeout=30000)
        
        # Give React 5 full seconds to fetch the Protobufs and render the UI hardware grid
        print("Waiting 5 seconds for React UI to hydrate...")
        page.wait_for_timeout(5000) 
        
        # Extract the literal visible text from the browser body
        visible_text = page.locator("body").inner_text()
        
        # Split into clean lines for easy reading
        lines = [line.strip() for line in visible_text.split('\n') if line.strip()]
        
        print("\n==================================================")
        print("VISIBLE SCREEN TEXT AROUND STEAM DECKS")
        print("==================================================")
        
        for key, name in DECK_MODELS.items():
            print(f"\nSearching screen for: '{key}'")
            found = False
            
            for i, line in enumerate(lines):
                if key in line:
                    found = True
                    print(f"  [MATCH FOUND] UI text snippet:")
                    
                    # Print the matching line and the next 5 lines below it on the page
                    # This will explicitly capture the price, stock status, and any buttons
                    snippet = lines[i : i+6]
                    for s in snippet:
                        print(f"    -> {s}")
                    break
            
            if not found:
                print("  [ERROR] Model name not found on screen. Page might not have rendered correctly.")

        browser.close()

if __name__ == "__main__":
    check_stock()
