"""
Browser manager for handling Playwright browser instances and tab management
"""
from playwright.sync_api import sync_playwright, Browser, BrowserContext, Page
from typing import Dict, Optional
import logging
import time
import random
from config.settings import Settings
from urllib.parse import urlparse

logger = logging.getLogger(__name__)

class BrowserManager:
    """Manages browser instances and tab state for domain-specific scraping"""
    
    def __init__(self):
        """Initialize browser manager"""
        self.playwright = None
        self.browser: Optional[Browser] = None  
        self.context: Optional[BrowserContext] = None
        self.tabs: Dict[str, Page] = {}  # domain -> page mapping
        self.current_domain: Optional[str] = None
        logger.info("🌐 Browser manager initialized")
    
    def start_browser(self):
        """Start the browser with proxy configuration"""
        try:
            logger.info("🚀 Starting browser...")
            self.playwright = sync_playwright().start()
            
            # Browser arguments for stealth
            browser_args = [
                "--no-sandbox",
                "--disable-dev-shm-usage", 
                "--disable-blink-features=AutomationControlled",
                "--disable-features=VizDisplayCompositor"
            ]
            
            # Launch browser - using Chrome instead of default Chromium for better stability
            self.browser = self.playwright.chromium.launch(
                headless=Settings.BROWSER_HEADLESS,
                args=browser_args,
                channel="chrome"  # Use Chrome browser instead of default Chromium
            )
            
            # Create context with or without proxy
            proxy_config = Settings.get_proxy_config()
            if proxy_config:
                logger.info(f"🔒 Using proxy: {proxy_config['server']}")
                self.context = self.browser.new_context(proxy=proxy_config)
            else:
                logger.info("🌐 Using direct connection (no proxy)")
                self.context = self.browser.new_context()
            
            # Set user agent to look more human
            self.context.set_extra_http_headers({
                'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
            })
            
            logger.info("✅ Browser started successfully")
            
        except Exception as e:
            logger.error(f"❌ Error starting browser: {e}")
            raise
    
    def get_domain_from_url(self, url: str) -> str:
        """Extract domain from URL"""
        return urlparse(url).netloc.lower()
    
    def get_page_for_url(self, url: str) -> Page:
        """Get or create a page for the given URL's domain"""
        domain = self.get_domain_from_url(url)
        
        # Check if we already have a tab for this domain
        if domain in self.tabs:
            logger.info(f"🔄 Reusing existing tab for domain: {domain}")
            return self.tabs[domain]
        
        # Create new tab for this domain
        logger.info(f"🆕 Creating new tab for domain: {domain}")
        page = self.context.new_page()
        self.tabs[domain] = page
        
        # Set up page defaults
        page.set_default_timeout(Settings.BROWSER_TIMEOUT)
        
        return page
    
    def navigate_with_delay(self, page: Page, url: str):
        """Navigate to URL with random delay when staying on same domain"""
        current_domain = self.get_domain_from_url(url)
        
        # Add delay if staying on same domain (be gentle to same server)
        if self.current_domain and self.current_domain == current_domain:
            delay = random.uniform(Settings.MIN_URL_DELAY, Settings.MAX_URL_DELAY)
            logger.info(f"⏳ Same domain ({current_domain}), waiting {delay:.1f}s to be server-friendly...")
            time.sleep(delay)
        elif self.current_domain and self.current_domain != current_domain:
            logger.info(f"🔄 Switching from {self.current_domain} to {current_domain} (no delay - different servers)")
        
        # Navigate to the URL
        logger.info(f"🌐 Navigating to: {url}")
        page.goto(url, wait_until="load", timeout=Settings.BROWSER_TIMEOUT)
        
        # Update current domain
        self.current_domain = current_domain
    
    def random_click_delay(self):
        """Add random delay before clicks"""
        delay = random.uniform(Settings.MIN_CLICK_DELAY, Settings.MAX_CLICK_DELAY)
        logger.info(f"⏳ Random click delay: {delay:.1f}s")
        time.sleep(delay)
    
    def find_existing_domain_tab(self, domain: str) -> Optional[Page]:
        """Find existing tab for domain"""
        for tab_domain, page in self.tabs.items():
            if domain in tab_domain:
                logger.info(f"✅ Found existing tab for domain: {domain}")
                return page
        return None
    
    def close_tab(self, domain: str):
        """Close tab for specific domain"""
        if domain in self.tabs:
            try:
                self.tabs[domain].close()
                del self.tabs[domain]
                logger.info(f"🗑️ Closed tab for domain: {domain}")
            except Exception as e:
                logger.warning(f"⚠️ Error closing tab for {domain}: {e}")
    
    def get_active_domains(self) -> list:
        """Get list of currently active domains"""
        return list(self.tabs.keys())
    
    def cleanup(self):
        """Clean up browser resources"""
        try:
            logger.info("🧹 Cleaning up browser resources...")
            
            # Close all tabs
            for domain in list(self.tabs.keys()):
                self.close_tab(domain)
            
            # Close context and browser
            if self.context:
                self.context.close()
            if self.browser:
                self.browser.close()
            if self.playwright:
                self.playwright.stop()
                
            logger.info("✅ Browser cleanup completed")
            
        except Exception as e:
            logger.error(f"❌ Error during browser cleanup: {e}")
    
    def __enter__(self):
        """Context manager entry"""
        self.start_browser()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit"""  
        self.cleanup()