"""
Rayobyte Playwright Script with Chrome Browser
Based on Rayobyte customer service script
"""

from playwright.sync_api import sync_playwright
import time

# ============================================
# EASILY EDITABLE TARGET URL
# ============================================
TARGET_URL = "https://seoudisupermarket.com/"  # Egyptian e-commerce site

# Proxy configuration
PROXY_HOST = "la.residential.rayobyte.com"
PROXY_PORT = 8000
PROXY_USER = "moallammail"
PROXY_PASS = "123456rayobyte"

def test_with_chrome():
    """Test the proxy using Chrome browser"""
    
    playwright = None
    browser = None
    context = None
    page = None
    
    try:
        print("🎭 Testing Rayobyte Proxy with Chrome Browser")
        print("=" * 50)
        
        playwright = sync_playwright().start()
        
        # Proxy configuration
        proxy_config = {
            "server": f"http://{PROXY_HOST}:{PROXY_PORT}",
            "username": PROXY_USER,
            "password": PROXY_PASS
        }
        
        print("🚀 Launching Chrome browser...")
        
        # Launch Chrome browser with proxy
        browser = playwright.chromium.launch(
            headless=False,  # Use visible browser
            channel="chrome",  # Explicitly use Chrome
            args=[
                "--no-sandbox",
                "--disable-dev-shm-usage",
                "--disable-blink-features=AutomationControlled"
            ]
        )
        
        # Create context with proxy
        context = browser.new_context(proxy=proxy_config)
        page = context.new_page()
        
        print("✅ Browser setup complete with residential proxy")
        
        # Test 1: Check IP address
        print("\n🔍 Testing proxy IP address...")
        print("-" * 40)
        
        try:
            print("📍 Checking IP with HTTPBin...")
            page.goto("https://httpbin.org/ip", wait_until="networkidle", timeout=30000)
            ip_content = page.content()
            print(f"   ✅ IP check successful")
            print(f"   Response preview: {ip_content[:200]}...")
        except Exception as e:
            print(f"   ❌ Error testing IP: {e}")
            
        # Test 2: Navigate to target URL
        print(f"\n🌐 Navigating to target: {TARGET_URL}")
        print("-" * 40)
        
        try:
            page.goto(TARGET_URL, wait_until="networkidle", timeout=30000)
            title = page.title()
            print(f"   ✅ Successfully loaded: {title}")
            
            # Take a screenshot for verification
            page.screenshot(path="rayobyte_test_chrome.png")
            print("   📸 Screenshot saved as: rayobyte_test_chrome.png")
            
            # Wait a bit to see the page
            print("   ⏳ Waiting 3 seconds...")
            time.sleep(3)
            
        except Exception as e:
            print(f"   ❌ Error loading target URL: {e}")
        
        print("\n✅ Test completed successfully!")
        
    except Exception as e:
        print(f"\n❌ Error during browser setup: {e}")
        
    finally:
        # Clean up
        if page:
            page.close()
        if context:
            context.close()
        if browser:
            browser.close()
        if playwright:
            playwright.stop()
        print("🧹 Browser closed and cleaned up")

if __name__ == "__main__":
    test_with_chrome()