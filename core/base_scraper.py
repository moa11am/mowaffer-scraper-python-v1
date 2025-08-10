"""
Base scraper class that all website-specific scrapers inherit from
"""
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
import logging
from playwright.sync_api import Page
from core.database_manager import DatabaseManager
from core.browser_manager import BrowserManager

logger = logging.getLogger(__name__)

class BaseScraper(ABC):
    """Abstract base class for all scrapers"""
    
    def __init__(self, browser_manager: BrowserManager, database_manager: DatabaseManager):
        """Initialize base scraper"""
        self.browser_manager = browser_manager
        self.database_manager = database_manager
        self.current_log_id: Optional[int] = None
        
    @property
    @abstractmethod
    def supported_domains(self) -> list:
        """Return list of domains this scraper supports"""
        pass
    
    @abstractmethod
    def scrape_url(self, url_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Scrape a specific URL and return results
        
        Args:
            url_data: Dictionary containing url, website, category, serial
            
        Returns:
            Dictionary with scraping results:
            {
                'success': bool,
                'products_found': int,
                'pages_scraped': int,
                'error_message': str (if failed),
                'data': Any (scraped data)
            }
        """
        pass
    
    def can_scrape_url(self, url: str) -> bool:
        """Check if this scraper can handle the given URL"""
        return any(domain in url.lower() for domain in self.supported_domains)
    
    def start_scraping_session(self, url_data: Dict[str, Any]):
        """Start a scraping session and log it"""
        logger.info(f"🎯 Starting scrape: {url_data['website']} - {url_data['url']}")
        self.current_log_id = self.database_manager.log_scrape_start(url_data)
    
    def end_scraping_session(self, success: bool, **kwargs):
        """End scraping session and update logs"""
        if not self.current_log_id:
            logger.warning("⚠️ No active log ID for scraping session")
            return
            
        if success:
            products_found = kwargs.get('products_found', 0)
            pages_scraped = kwargs.get('pages_scraped', 0)
            self.database_manager.log_scrape_success(
                self.current_log_id, 
                products_found, 
                pages_scraped
            )
            logger.info(f"✅ Scraping completed successfully")
        else:
            error_message = kwargs.get('error_message', 'Unknown error')
            self.database_manager.log_scrape_failure(self.current_log_id, error_message)
            logger.error(f"❌ Scraping failed: {error_message}")
        
        self.current_log_id = None
    
    def get_page_for_url(self, url: str) -> Page:
        """Get browser page for URL"""
        return self.browser_manager.get_page_for_url(url)
    
    def navigate_to_url(self, page: Page, url: str):
        """Navigate to URL with proper delays"""
        self.browser_manager.navigate_with_delay(page, url)
    
    def wait_and_click(self, page: Page, selector: str, timeout: int = 10000):
        """Wait for element and click with random delay"""
        logger.info(f"🖱️ Waiting for element: {selector}")
        page.wait_for_selector(selector, timeout=timeout)
        
        # Random delay before clicking
        self.browser_manager.random_click_delay()
        
        # Click the element
        page.click(selector)
        logger.info(f"✅ Clicked: {selector}")
    
    def wait_for_element(self, page: Page, selector: str, timeout: int = 10000):
        """Wait for element to appear"""
        logger.info(f"⏳ Waiting for element: {selector}")
        return page.wait_for_selector(selector, timeout=timeout)
    
    def scroll_to_bottom(self, page: Page):
        """Scroll to bottom of page"""
        logger.info("📜 Scrolling to bottom of page")
        page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
        
    def safe_scrape(self, url_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Safely execute scraping with error handling and logging
        """
        self.start_scraping_session(url_data)
        
        try:
            result = self.scrape_url(url_data)
            
            if result.get('success', False):
                self.end_scraping_session(
                    success=True,
                    products_found=result.get('products_found', 0),
                    pages_scraped=result.get('pages_scraped', 0)
                )
            else:
                self.end_scraping_session(
                    success=False,
                    error_message=result.get('error_message', 'Scraping failed')
                )
            
            return result
            
        except Exception as e:
            error_msg = f"Exception during scraping: {str(e)}"
            logger.exception(error_msg)
            
            self.end_scraping_session(success=False, error_message=error_msg)
            
            return {
                'success': False,
                'error_message': error_msg,
                'products_found': 0,
                'pages_scraped': 0
            }