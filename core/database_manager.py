"""
Database manager for Supabase operations
"""
from supabase import create_client, Client
from typing import List, Dict, Any, Optional
import logging
from datetime import datetime
from config.settings import Settings

logger = logging.getLogger(__name__)

class DatabaseManager:
    """Handles all database operations with Supabase"""
    
    def __init__(self):
        """Initialize Supabase client"""
        self.client: Client = create_client(Settings.SUPABASE_URL, Settings.SUPABASE_KEY)
        logger.info("✅ Database manager initialized")
    
    def get_urls_to_scrape(self) -> List[Dict[str, Any]]:
        """Fetch all URLs from links_to_scrape table"""
        try:
            response = self.client.table(Settings.URLS_TABLE).select("*").order("id").execute()
            urls = response.data
            logger.info(f"📥 Retrieved {len(urls)} URLs to scrape")
            return urls
        except Exception as e:
            logger.error(f"❌ Error fetching URLs: {e}")
            return []
    
    def log_scrape_start(self, url_data: Dict[str, Any]) -> Optional[int]:
        """Log the start of a scraping session"""
        try:
            log_entry = {
                "serial": url_data.get("serial", url_data["id"]),  # Use id if serial not available
                "website": url_data["website"],
                "category": url_data["category"],
                "url": url_data["url"],
                "scrape_status": "PENDING",
                "scraped_at": datetime.now().isoformat()
            }
            
            response = self.client.table(Settings.LOG_TABLE).insert(log_entry).execute()
            log_id = response.data[0]["id"]
            logger.info(f"📝 Started scraping log for {url_data['website']} (ID: {log_id})")
            return log_id
            
        except Exception as e:
            logger.error(f"❌ Error logging scrape start: {e}")
            return None
    
    def log_scrape_success(self, log_id: int, products_found: int = 0, pages_scraped: int = 0):
        """Log successful scraping"""
        try:
            update_data = {
                "scrape_status": "SUCCESS",
                "products_found": products_found,
                "pages_scraped": pages_scraped,
                "scraped_at": datetime.now().isoformat()
            }
            
            self.client.table(Settings.LOG_TABLE).update(update_data).eq("id", log_id).execute()
            logger.info(f"✅ Logged successful scrape (ID: {log_id}) - {products_found} products, {pages_scraped} pages")
            
        except Exception as e:
            logger.error(f"❌ Error logging success: {e}")
    
    def log_scrape_failure(self, log_id: int, error_message: str):
        """Log failed scraping"""
        try:
            update_data = {
                "scrape_status": "FAIL",
                "error_message": error_message[:1000],  # Limit error message length
                "scraped_at": datetime.now().isoformat()
            }
            
            self.client.table(Settings.LOG_TABLE).update(update_data).eq("id", log_id).execute()
            logger.error(f"❌ Logged failed scrape (ID: {log_id}): {error_message}")
            
        except Exception as e:
            logger.error(f"❌ Error logging failure: {e}")
    
    def get_scrape_statistics(self) -> Dict[str, Any]:
        """Get scraping statistics"""
        try:
            # Get total counts by status
            response = self.client.table(Settings.LOG_TABLE)\
                .select("scrape_status", count="exact")\
                .execute()
            
            stats = {
                "total_attempts": len(response.data),
                "success_count": len([r for r in response.data if r["scrape_status"] == "SUCCESS"]),
                "fail_count": len([r for r in response.data if r["scrape_status"] == "FAIL"]),
                "pending_count": len([r for r in response.data if r["scrape_status"] == "PENDING"])
            }
            
            if stats["total_attempts"] > 0:
                stats["success_rate"] = round((stats["success_count"] / stats["total_attempts"]) * 100, 2)
            else:
                stats["success_rate"] = 0
            
            return stats
            
        except Exception as e:
            logger.error(f"❌ Error getting statistics: {e}")
            return {"error": str(e)}

    # Oscar-specific persistence helpers
    def insert_oscar_price_history(self, rows: List[Dict[str, Any]]) -> int:
        """Insert a batch of Oscar product rows into oscar_price_history.

        Returns the number of inserted records, or 0 on error.
        """
        try:
            if not rows:
                return 0
            response = self.client.table("oscar_price_history").insert(rows).execute()
            return len(response.data) if response and getattr(response, "data", None) else 0
        except Exception as e:
            logger.error(f"❌ Error inserting oscar_price_history rows: {e}")
            return 0
