"""
Configuration settings for the Mowaffer grocery scraper
"""
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

class Settings:
    """Application settings"""
    
    # Supabase Configuration
    SUPABASE_URL = os.getenv("SUPABASE_URL", "https://nbyoqwhpprgwfvnmaglr.supabase.co")
    SUPABASE_KEY = os.getenv("SUPABASE_KEY", "")
    
    # Rayobyte Proxy Configuration  
    PROXY_HOST = os.getenv("PROXY_HOST", "la.residential.rayobyte.com")
    PROXY_PORT = int(os.getenv("PROXY_PORT", "8000"))
    PROXY_USER = os.getenv("PROXY_USER", "moallammail_gmail_com")
    PROXY_PASS = os.getenv("PROXY_PASS", "123456rayobyte-country-EG")
    
    # Proxy Toggle (TRUE/FALSE)
    PROXY_ENABLED = os.getenv("PROXY_ENABLED", "false").lower() == "true"  # Temporarily disabled for testing
    
    # Browser Configuration
    BROWSER_HEADLESS = os.getenv("BROWSER_HEADLESS", "false").lower() == "true"
    BROWSER_TIMEOUT = int(os.getenv("BROWSER_TIMEOUT", "30000"))  # 30 seconds
    
    # Scraping Configuration
    MIN_CLICK_DELAY = float(os.getenv("MIN_CLICK_DELAY", "2.0"))  # 2 seconds
    MAX_CLICK_DELAY = float(os.getenv("MAX_CLICK_DELAY", "6.0"))  # 6 seconds
    MIN_URL_DELAY = float(os.getenv("MIN_URL_DELAY", "10.0"))     # 10 seconds between domains
    MAX_URL_DELAY = float(os.getenv("MAX_URL_DELAY", "20.0"))     # 20 seconds between domains
    
    # Database Tables
    URLS_TABLE = "links_to_scrape"
    LOG_TABLE = "links_to_scrape_log"
    
    # Seoudi Specific Settings
    SEOUDI_INITIATOR_EXPECTED = "660ec14.modern.js"
    
    @classmethod
    def get_proxy_config(cls):
        """Get proxy configuration for Playwright"""
        if not cls.PROXY_ENABLED:
            return None
            
        return {
            "server": f"http://{cls.PROXY_HOST}:{cls.PROXY_PORT}",
            "username": cls.PROXY_USER,
            "password": cls.PROXY_PASS
        }
    
    @classmethod  
    def print_config(cls):
        """Print current configuration (without sensitive data)"""
        print("🔧 Configuration:")
        print(f"   Proxy Enabled: {cls.PROXY_ENABLED}")
        print(f"   Browser Headless: {cls.BROWSER_HEADLESS}")
        print(f"   Click Delays: {cls.MIN_CLICK_DELAY}-{cls.MAX_CLICK_DELAY}s")
        print(f"   Domain Delays: {cls.MIN_URL_DELAY}-{cls.MAX_URL_DELAY}s")
        print(f"   Supabase URL: {cls.SUPABASE_URL}")