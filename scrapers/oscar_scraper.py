"""
Oscar Stores specific scraper implementation
"""
import logging
import re
from typing import Dict, Any, List, Union, Optional
from playwright.sync_api import Page, ElementHandle
from core.base_scraper import BaseScraper

logger = logging.getLogger(__name__)

class OscarScraper(BaseScraper):
    """Scraper for Oscar Stores website"""
    
    @property
    def supported_domains(self) -> list:
        return ["oscarstores.com"]
    
    def scrape_url(self, url_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Scrape Oscar Stores URL with pagination
        
        Oscar Stores Logic:
        1. Wait for page to load
        2. Extract total product count from <span class="c_gray3 f-12 f-w_500 mx-1">
        3. Scroll to bottom and get HTML
        4. Go to next page (add ?page=2 or increment existing page number)
        5. Repeat until no products found (no div.col-md-3.col-sm-4.col-6.p-1)
        """
        url = url_data["url"]
        page = self.get_page_for_url(url)
        
        total_products_expected = 0
        total_products_found = 0
        pages_scraped = 0
        current_url = url
        
        try:
            while True:
                logger.info(f"📄 Scraping page: {current_url}")
                
                # Navigate to current page
                self.navigate_to_url(page, current_url)
                
                # Wait for page to load
                page.wait_for_load_state("load")
                
                # Extract total product count (only on first page)
                if pages_scraped == 0:
                    total_products_expected = self._extract_total_products(page)
                    logger.info(f"📊 Expected total products: {total_products_expected}")
                
                # Check if there are products on this page
                products_on_page = page.query_selector_all('div.col-md-3.col-sm-4.col-6.p-1')
                
                if not products_on_page:
                    logger.info("✅ No more products found - pagination complete")
                    break
                
                # Count products on this page
                products_count = len(products_on_page)
                total_products_found += products_count
                pages_scraped += 1
                logger.info(f"📦 Found {products_count} products on page {pages_scraped}")

                # Extract page-level context
                category_header = self._safe_text(page, 'h3.f-20.c_black.f-w_bold.d-none.d-xl-block') or ""

                # Build rows for DB insert
                rows: List[Dict[str, Any]] = []
                for product_el in products_on_page:
                    row = self._extract_product_row(product_el, url_data, page_number=pages_scraped, current_url=current_url, category_header=category_header)
                    if row:
                        rows.append(row)

                # Persist this page batch to Supabase
                if rows:
                    inserted = self.database_manager.insert_oscar_price_history(rows)
                    logger.info(f"💾 Inserted {inserted}/{len(rows)} oscar_price_history rows for page {pages_scraped}")

                # Scroll to bottom to load any lazy content
                self.scroll_to_bottom(page)
                # Capture HTML for debugging only (not saved to disk here)
                html_content = page.content()
                logger.info(f"📄 Page {pages_scraped} HTML captured ({len(html_content)} chars)")
                
                # Prepare next page URL
                next_url = self._get_next_page_url(current_url)
                if not next_url:
                    logger.error("❌ Could not generate next page URL")
                    break
                
                current_url = next_url
                logger.info(f"➡️ Next page URL: {current_url}")
                
                # Safety check to prevent infinite loops
                if pages_scraped > 100:  # Reasonable limit
                    logger.warning("⚠️ Reached page limit (100), stopping pagination")
                    break
            
            # Validate results
            success = pages_scraped > 0
            if success and total_products_expected > 0:
                # Check if we got roughly the expected number of products
                if total_products_found < (total_products_expected * 0.8):  # Allow 20% variance
                    logger.warning(f"⚠️ Product count mismatch: expected {total_products_expected}, found {total_products_found}")
            
            logger.info(f"✅ Oscar scraping completed: {pages_scraped} pages, {total_products_found} products")
            
            return {
                'success': success,
                'products_found': total_products_found,
                'pages_scraped': pages_scraped,
                'expected_products': total_products_expected,
                'data': {
                    'total_products': total_products_found,
                    'pages_processed': pages_scraped,
                    'final_url': current_url
                }
            }
            
        except Exception as e:
            error_msg = f"Oscar scraping error: {str(e)}"
            logger.error(error_msg)
            return {
                'success': False,
                'error_message': error_msg,
                'products_found': total_products_found,
                'pages_scraped': pages_scraped
            }
    
    # -------------------- Parsing helpers & row builder --------------------
    def _safe_text(self, root: Union[Page, ElementHandle], selector: str) -> str:
        try:
            el = root.query_selector(selector)
            return (el.text_content() or "").strip() if el else ""
        except Exception:
            return ""

    def _safe_attr(self, root: Union[Page, ElementHandle], selector: str, attr: str) -> str:
        try:
            el = root.query_selector(selector)
            return el.get_attribute(attr) if el else ""
        except Exception:
            return ""

    def _extract_number(self, text: str) -> Optional[float]:
        try:
            if not text:
                return None
            # Keep digits and decimal separator
            match = re.search(r"(\d+[\.,]?\d*)", text.replace(",", ""))
            return float(match.group(1)) if match else None
        except Exception:
            return None

    def _extract_discount(self, text: str) -> str:
        if not text:
            return ""
        m = re.search(r"(\d+\s*%)", text)
        return m.group(1).replace(" ", "") if m else ""

    def _extract_product_row(
        self,
        product_el: ElementHandle,
        url_data: Dict[str, Any],
        page_number: int,
        current_url: str,
        category_header: str,
    ) -> Optional[Dict[str, Any]]:
        try:
            # Card body block
            card_body_sel = 'div.card-body.flex-column.d-flex.justify-content-between.p-0'

            # Product name
            product_name = self._safe_text(product_el, f"{card_body_sel} h5")

            # Price block
            price_block = 'div.price'
            final_price_text = self._safe_text(product_el, f"{price_block} span.c_red.f-15")
            price_before_text = self._safe_text(product_el, f"{price_block} span.f-12.c_gray5.text-decoration-line-through.mx-2")
            discount_text = self._safe_text(product_el, f"{price_block} span.c_green.f-12")

            final_price = self._extract_number(final_price_text)
            price_before = self._extract_number(price_before_text)
            discount_rate = self._extract_discount(discount_text)

            # URLs
            product_url = self._safe_attr(product_el, f"{card_body_sel} a", "href")
            image_url = self._safe_attr(product_el, "img.card-img-top", "src")

            # Category path snippet inside card
            category_path = (
                self._safe_text(product_el, f"{card_body_sel} p.c_gray3.f-12.f_oswald.f-w_300.border.px-1.rounded-1.mb-2.one-lines.ellipse")
                or self._safe_text(product_el, f"{card_body_sel} p.one-lines.ellipse")
                or ""
            )

            row: Dict[str, Any] = {
                # sku_gen is generated by DB (computed column), not provided here
                "product_name": product_name,
                "final_price": final_price,
                "price_before_discount": price_before,
                "discount_rate": discount_rate,  # stored as text with % per requirement
                "product_url": product_url,
                "product_category_path": category_path,
                "image_url": image_url,
                "site_name": url_data.get("website", ""),
                "path": url_data.get("category", ""),
                "category": category_header,
                "url": url_data.get("url", ""),
                "page_number": page_number,
                "url_with_page_number": current_url,
                "scraped_at": __import__("datetime").datetime.utcnow().isoformat(),
            }

            return row
        except Exception as e:
            logger.warning(f"⚠️ Failed to parse product card: {e}")
            return None

    def _extract_total_products(self, page: Page) -> int:
        """Extract total product count from the page"""
        try:
            # Wait for the product count element
            count_element = page.wait_for_selector('span.c_gray3.f-12.f-w_500.mx-1', timeout=10000)
            count_text = count_element.text_content().strip()
            
            # Extract number from text
            numbers = re.findall(r'\d+', count_text)
            if numbers:
                total_count = int(numbers[0])
                logger.info(f"📊 Extracted product count: {total_count}")
                return total_count
            else:
                logger.warning(f"⚠️ Could not parse product count from: {count_text}")
                return 0
                
        except Exception as e:
            logger.warning(f"⚠️ Could not extract total product count: {e}")
            return 0
    
    def _get_next_page_url(self, current_url: str) -> str:
        """Generate next page URL based on current URL"""
        try:
            if "page=" not in current_url:
                # First pagination - add ?page=2
                return f"{current_url}?page=2"
            else:
                # Extract current page number and increment
                page_match = re.search(r'page=(\d+)', current_url)
                if page_match:
                    current_page = int(page_match.group(1))
                    next_page = current_page + 1
                    next_url = re.sub(r'page=\d+', f'page={next_page}', current_url)
                    return next_url
                else:
                    logger.error("❌ Could not parse page number from URL")
                    return ""
                    
        except Exception as e:
            logger.error(f"❌ Error generating next page URL: {e}")
            return ""
