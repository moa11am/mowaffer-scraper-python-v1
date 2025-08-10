#!/usr/bin/env python3
"""
Mowaffer Grocery Scraper - Main Orchestrator
The best grocery price scraper ever created!
"""
import logging
import sys
from typing import List, Dict, Any
from datetime import datetime

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(f'scraper_{datetime.now().strftime("%Y%m%d_%H%M%S")}.log')
    ]
)

logger = logging.getLogger(__name__)

# Import our modules
from config.settings import Settings
from core.database_manager import DatabaseManager
from core.browser_manager import BrowserManager
from scrapers.scraper_factory import ScraperFactory

class MowafferScraper:
    """Main scraper orchestrator"""
    
    def __init__(self):
        """Initialize the scraper"""
        self.database_manager = DatabaseManager()
        self.browser_manager = None
        self.total_urls = 0
        self.successful_scrapes = 0
        self.failed_scrapes = 0
        
    def print_banner(self):
        """Print application banner"""
        print("=" * 80)
        print("🛒 MOWAFFER GROCERY SCRAPER v1.0 🛒")
        print("The Best Grocery Price Scraper Ever Created!")
        print("=" * 80)
        print(f"🕐 Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        Settings.print_config()
        ScraperFactory.print_supported_domains()
        print("=" * 80)
    
    def load_urls_to_scrape(self) -> List[Dict[str, Any]]:
        """Load URLs from Supabase"""
        logger.info("📥 Loading URLs to scrape from database...")
        urls = self.database_manager.get_urls_to_scrape()
        
        if not urls:
            logger.error("❌ No URLs found in database!")
            return []
        
        self.total_urls = len(urls)
        logger.info(f"📋 Loaded {self.total_urls} URLs to scrape")
        
        # Group URLs by domain for better visualization
        domain_groups = {}
        for url_data in urls:
            domain = url_data['website']
            if domain not in domain_groups:
                domain_groups[domain] = []
            domain_groups[domain].append(url_data)
        
        print("\n📊 URLs by domain:")
        for domain, domain_urls in domain_groups.items():
            print(f"   • {domain}: {len(domain_urls)} URLs")
        print()
        
        return urls
    
    def scrape_url(self, url_data: Dict[str, Any]) -> bool:
        """Scrape a single URL using appropriate scraper"""
        url = url_data['url']
        website = url_data['website']
        
        logger.info(f"🎯 Processing: {website} - {url}")
        
        # Create appropriate scraper using factory pattern
        scraper = ScraperFactory.create_scraper(url, self.browser_manager, self.database_manager)
        
        if not scraper:
            logger.error(f"❌ No scraper available for {website} - {url}")
            self.failed_scrapes += 1
            return False
        
        # Execute scraping
        result = scraper.safe_scrape(url_data)
        
        if result['success']:
            logger.info(f"✅ Successfully scraped {website}")
            logger.info(f"   📦 Products found: {result.get('products_found', 0)}")
            logger.info(f"   📄 Pages scraped: {result.get('pages_scraped', 0)}")
            self.successful_scrapes += 1
            return True
        else:
            logger.error(f"❌ Failed to scrape {website}: {result.get('error_message', 'Unknown error')}")
            self.failed_scrapes += 1
            return False
    
    def print_progress(self, current: int, total: int):
        """Print progress information"""
        percentage = (current / total) * 100
        print(f"\n📊 Progress: {current}/{total} ({percentage:.1f}%)")
        print(f"   ✅ Successful: {self.successful_scrapes}")
        print(f"   ❌ Failed: {self.failed_scrapes}")
        print(f"   🔄 Remaining: {total - current}")
    
    def print_final_statistics(self):
        """Print final scraping statistics"""
        print("\n" + "=" * 80)
        print("📊 FINAL STATISTICS")
        print("=" * 80)
        print(f"🔢 Total URLs: {self.total_urls}")
        print(f"✅ Successful: {self.successful_scrapes}")
        print(f"❌ Failed: {self.failed_scrapes}")
        
        if self.total_urls > 0:
            success_rate = (self.successful_scrapes / self.total_urls) * 100
            print(f"📈 Success Rate: {success_rate:.1f}%")
        
        # Get database statistics
        db_stats = self.database_manager.get_scrape_statistics()
        if 'error' not in db_stats:
            print(f"📋 Database Statistics:")
            print(f"   • Total attempts: {db_stats['total_attempts']}")
            print(f"   • Success count: {db_stats['success_count']}")
            print(f"   • Fail count: {db_stats['fail_count']}")
            print(f"   • Pending count: {db_stats['pending_count']}")
            print(f"   • Success rate: {db_stats['success_rate']}%")
        
        print(f"🕐 Completed at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("=" * 80)
    
    def run(self):
        """Main execution method"""
        try:
            # Print banner
            self.print_banner()
            
            # Load URLs to scrape
            urls_to_scrape = self.load_urls_to_scrape()
            if not urls_to_scrape:
                return
            
            # Start browser
            logger.info("🚀 Starting browser...")
            with BrowserManager() as browser_manager:
                self.browser_manager = browser_manager
                
                # Process each URL
                for i, url_data in enumerate(urls_to_scrape, 1):
                    self.print_progress(i-1, len(urls_to_scrape))
                    
                    try:
                        self.scrape_url(url_data)
                    except KeyboardInterrupt:
                        logger.info("⏹️ Scraping interrupted by user")
                        break
                    except Exception as e:
                        logger.error(f"❌ Unexpected error processing {url_data['url']}: {e}")
                        self.failed_scrapes += 1
                
                # Final progress
                self.print_progress(len(urls_to_scrape), len(urls_to_scrape))
            
            # Print final statistics
            self.print_final_statistics()
            
        except Exception as e:
            logger.error(f"❌ Critical error in main execution: {e}")
            raise
        
        logger.info("🏁 Scraper execution completed!")

def main():
    """Entry point"""
    try:
        scraper = MowafferScraper()
        scraper.run()
    except KeyboardInterrupt:
        print("\n⏹️ Scraper stopped by user")
    except Exception as e:
        logger.error(f"❌ Fatal error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()