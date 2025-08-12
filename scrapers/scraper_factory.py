"""
Factory pattern for creating appropriate scrapers based on URL
"""
import logging
from typing import Optional
from core.base_scraper import BaseScraper
from core.browser_manager import BrowserManager
from core.database_manager import DatabaseManager

logger = logging.getLogger(__name__)

class ScraperFactory:
    """Factory for creating scrapers based on URL"""
    
    @staticmethod
    def create_scraper(url: str, browser_manager: BrowserManager, database_manager: DatabaseManager) -> Optional[BaseScraper]:
        """
        Create appropriate scraper for the given URL
        
        Args:
            url: URL to scrape
            browser_manager: Browser manager instance
            database_manager: Database manager instance
            
        Returns:
            Appropriate scraper instance or None if no scraper available
        """
        url_lower = url.lower()
        
        # Oscar Stores scraper
        if "oscarstores.com" in url_lower:
            from .oscar_scraper import OscarScraper
            logger.info(f"🏪 Creating Oscar Stores scraper for: {url}")
            return OscarScraper(browser_manager, database_manager)
        
        # Seoudi scraper  
        elif "seoudisupermarket.com" in url_lower:
            from .seoudi_scraper import SeoudiScraper
            logger.info(f"🏪 Creating Seoudi scraper for: {url}")
            return SeoudiScraper(browser_manager, database_manager)
        
        # Spinneys scraper (placeholder for future implementation)
        elif "spinneys" in url_lower:
            logger.warning(f"⚠️ Spinneys scraper not implemented yet for: {url}")
            return None
        
        # No scraper available
        else:
            logger.error(f"❌ No scraper available for URL: {url}")
            return None
    
    @staticmethod
    def get_supported_domains() -> dict:
        """Get list of all supported domains"""
        return {
            "oscarstores.com": "OscarScraper",
            "seoudisupermarket.com": "SeoudiScraper",
            "spinneys": "SpinneysScraper (Not implemented)"
        }
    
    @staticmethod
    def print_supported_domains():
        """Print all supported domains"""
        domains = ScraperFactory.get_supported_domains()
        print("🏪 Supported domains:")
        for domain, scraper in domains.items():
            print(f"   • {domain} → {scraper}")
