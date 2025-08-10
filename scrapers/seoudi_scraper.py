"""
Seoudi Supermarket specific scraper implementation
"""
import logging
from typing import Dict, Any, List
from playwright.sync_api import Page, Request, Response
from core.base_scraper import BaseScraper
from config.settings import Settings
import json

logger = logging.getLogger(__name__)

class SeoudiScraper(BaseScraper):
    """Scraper for Seoudi Supermarket website"""
    
    def __init__(self, *args, **kwargs):
        """Initialize with UID tracking"""
        super().__init__(*args, **kwargs)
        self.seen_category_uids = set()  # Track UIDs from previous URLs
        self.current_url_uid = None  # Track current URL's UID
        self.navigation_completed = False  # Track when navigation happens
    
    @property
    def supported_domains(self) -> list:
        return ["seoudisupermarket.com"]
    
    def scrape_url(self, url_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Scrape Seoudi URL with network interception
        
        Seoudi Logic:
        1. Intercept all network requests containing "Products"
        2. Navigate to target URL first
        3. Check for location setup indicator element
        4. If indicator found, perform location setup (steps 3-7) then re-navigate to target URL
        5. If no indicator, skip location setup
        6. Load all products and save intercepted Products requests
        """
        url = url_data["url"]
        page = self.get_page_for_url(url)
        
        # Reset current URL UID and navigation flag for new scraping session
        self.current_url_uid = None
        self.navigation_completed = False
        logger.info(f"🔄 Starting new URL scrape - reset current UID and navigation flag")
        
        # Set up network interception
        captured_requests = []
        self._setup_network_interception(page, captured_requests)
        
        try:
            # Navigate to the target URL first to check for location setup requirement
            logger.info(f"🌐 Navigating to target URL: {url}")
            self.navigate_to_url(page, url)
            
            # Mark navigation as completed AFTER navigation
            self.navigation_completed = True
            logger.info(f"✅ Navigation completed - now accepting network requests")
            
            # Wait for page to load
            page.wait_for_load_state("load")
            
            # Check if location setup is required by looking for specific element
            location_setup_required = self._check_location_setup_required(page)
            
            if location_setup_required:
                logger.info("📍 Location setup required - executing location setup steps")
                self._setup_seoudi_location(page)
                
                # Navigate back to the target URL after location setup
                logger.info("🔄 Re-navigating to target URL after location setup")
                self.navigate_to_url(page, url)
                page.wait_for_load_state("load")
            else:
                logger.info("✅ Location already set up - skipping location setup steps")
            
            # Load all products by clicking "Load More" button
            products_loaded = self._load_all_products(page)
            
            # Process captured network requests
            valid_requests = self._process_captured_requests(captured_requests)
            
            logger.info(f"✅ Seoudi scraping completed: {len(valid_requests)} valid requests captured")
            
            # Move current UID to seen UIDs for next URL
            if self.current_url_uid:
                self.seen_category_uids.add(self.current_url_uid)
                logger.info(f"📝 Moved current UID {self.current_url_uid} to seen UIDs for future URLs")
            
            return {
                'success': len(valid_requests) > 0,
                'products_found': products_loaded,
                'pages_scraped': 1,
                'data': {
                    'captured_requests': len(captured_requests),
                    'valid_requests': len(valid_requests),
                    'products_loaded': products_loaded,
                    'requests_data': valid_requests[:5]  # First 5 for logging
                }
            }
            
        except Exception as e:
            error_msg = f"Seoudi scraping error: {str(e)}"
            logger.error(error_msg)
            return {
                'success': False,
                'error_message': error_msg,
                'products_found': 0,
                'pages_scraped': 0
            }
    
    def _setup_network_interception(self, page: Page, captured_requests: List[Dict]):
        """Set up network request and response interception for Products URLs with comprehensive filtering"""
        
        def handle_response(response: Response):
            """Handle network responses to capture GraphQL product data with all filters"""
            # Filter 1: Check navigation completed (ignore pre-navigation requests)
            if not self.navigation_completed:
                logger.debug(f"🚫 Ignoring pre-navigation request from: {response.url}")
                return
            
            # Filter 2: URL must contain "Products"
            if "Products" not in response.url:
                return
            
            # Filter 3: Status must be 200
            if response.status != 200:
                logger.debug(f"🚫 Skipped non-200 response: {response.status} for {response.url}")
                return
            
            try:
                import json
                # Filter 4: Check initiator (restore previous functionality)
                request_initiator = "unknown"
                try:
                    # Get initiator from request timing
                    request_initiator = page.evaluate(f"""
                        () => {{
                            const entries = performance.getEntriesByType('navigation').concat(
                                performance.getEntriesByType('resource')
                            );
                            for (const entry of entries) {{
                                if (entry.name && entry.name.includes('graphql')) {{
                                    return entry.initiatorType || 'unknown';
                                }}
                            }}
                            return 'unknown';
                        }}
                    """)
                except:
                    request_initiator = "unknown"
                
                expected_initiator = Settings.SEOUDI_INITIATOR_EXPECTED
                if request_initiator != expected_initiator and request_initiator != f"{expected_initiator}:2":
                    logger.warning(f"⚠️ Products request from unexpected initiator!")
                    logger.warning(f"   Expected: {expected_initiator}")
                    logger.warning(f"   Found: {request_initiator}")
                    logger.warning(f"   URL: {response.url}")
                    # Continue processing despite initiator mismatch (for now)
                
                # Extract JSON response data
                response_data = response.json()
                
                # Filter 9: Check response content size (must have 100+ lines when saved)
                response_json_str = json.dumps(response_data, ensure_ascii=False, indent=2)
                response_line_count = len(response_json_str.split('\n'))
                if response_line_count < 100:
                    logger.info(f"🚫 Skipping response with only {response_line_count} lines (minimum 100)")
                    return
                
                # Filter 10: Extract and check category UID
                category_uid = self._extract_category_uid(response.url)
                if not category_uid:
                    logger.warning(f"⚠️ Could not extract category UID from: {response.url}")
                    return
                
                # Filter 11: Check if UID is from previous URLs (should be ignored)
                if category_uid in self.seen_category_uids:
                    logger.info(f"🚫 Skipping UID {category_uid} from previous URL: {response.url}")
                    return
                
                # Filter 12: Set current URL UID if not set yet
                if self.current_url_uid is None:
                    self.current_url_uid = category_uid
                    logger.info(f"🎯 Set current URL UID: {category_uid}")
                
                # Filter 13: Only process requests from current URL's UID
                if category_uid != self.current_url_uid:
                    logger.info(f"🚫 Skipping UID {category_uid} - current URL expects {self.current_url_uid}")
                    return
                
                # UID matches current URL - process and save
                logger.info(f"✅ Processing UID {category_uid} for current URL")
                
                # Create comprehensive request/response info
                request_info = {
                    'url': response.url,
                    'method': response.request.method,
                    'status': response.status,
                    'headers': dict(response.request.headers),
                    'response_headers': dict(response.headers),
                    'timestamp': page.evaluate('Date.now()'),
                    'response_data': response_data,
                    'category_uid': category_uid,
                    'initiator': request_initiator
                }
                
                # Debug: Log the response structure for analysis
                logger.info(f"🔍 Analyzing response structure from: {response.url}")
                if isinstance(response_data, dict):
                    logger.info(f"📊 Response keys: {list(response_data.keys())}")
                    if 'data' in response_data:
                        data = response_data['data']
                        if isinstance(data, dict):
                            logger.info(f"📊 Data keys: {list(data.keys())}")
                
                # Save all responses that pass filters
                logger.info(f"✅ Captured Products response: {response.url}")
                captured_requests.append(request_info)
                
                # Save raw response data immediately with new filename format
                saved = self._save_raw_response(response_data, response.url, page, category_uid)
                if saved:
                    logger.info(f"💾 Saved raw JSON response to file")
                else:
                    logger.info(f"⏭️ Skipped saving due to unknown category")
                        
            except Exception as e:
                logger.error(f"❌ Error processing Products response: {e}")
                logger.error(f"   URL: {response.url}")
        
        # Set up response interception (this captures the actual data!)
        page.on('response', handle_response)
        logger.info("🕸️ Network interception set up for Products responses with UID filtering")
    
    def _extract_category_uid(self, url: str) -> str:
        """Extract category UID from GraphQL URL variables"""
        try:
            import json
            from urllib.parse import urlparse, parse_qs
            
            parsed_url = urlparse(url)
            query_params = parse_qs(parsed_url.query)
            variables = query_params.get('variables', [''])[0]
            
            if variables:
                vars_dict = json.loads(variables)
                if 'filter' in vars_dict and isinstance(vars_dict['filter'], dict):
                    category_filter = vars_dict['filter'].get('category_uid', {})
                    if isinstance(category_filter, dict):
                        category_uid = category_filter.get('eq', '')
                        if category_uid:
                            logger.debug(f"🔍 Extracted UID: {category_uid}")
                            return category_uid
            
            logger.debug(f"🔍 No category UID found in URL: {url}")
            return ""
            
        except Exception as e:
            logger.error(f"❌ Error extracting category UID: {e}")
            return ""
    
    def _save_raw_response(self, response_data: Dict, source_url: str, page, category_uid: str) -> bool:
        """Save raw GraphQL response data to JSON file with new format: {HHMMSS}_{DDMMYY}_page{page_num}_{category_name}_{uid}_seoudi.json"""
        try:
            import json
            import os
            import re
            from datetime import datetime
            from urllib.parse import urlparse, parse_qs
            
            # Create responses directory if it doesn't exist
            responses_dir = "raw_responses"
            if not os.path.exists(responses_dir):
                os.makedirs(responses_dir)
            
            # Extract page number from URL for filename
            parsed_url = urlparse(source_url)
            query_params = parse_qs(parsed_url.query)
            variables = query_params.get('variables', [''])[0]
            page_num = 1
            try:
                if variables:
                    import json
                    vars_dict = json.loads(variables)
                    page_num = vars_dict.get('page', 1)
            except:
                page_num = 1
            
            # Get page title from h1 element
            category_name = "unknown"
            try:
                if page and not page.is_closed():
                    title_element = page.query_selector('h1.mt-3.lg\\:mt-6.text-4xl.font-semibold.text-primary-700.antialiased.tracking-wide[data-v-489a62ee]')
                    if title_element:
                        category_name = title_element.text_content() or "unknown"
                        # Clean title for filename (remove special characters)
                        category_name = re.sub(r'[^\w\s-]', '', category_name).strip()
                        category_name = re.sub(r'[-\s]+', '_', category_name)
                        category_name = category_name.lower()[:30]  # Limit length for filename
                        logger.info(f"📋 Extracted category name: {category_name}")
                    else:
                        logger.info("📋 Category name element not found, trying alternative selector...")
                        # Try a simpler selector
                        title_element = page.query_selector('h1[data-v-489a62ee]')
                        if title_element:
                            category_name = title_element.text_content() or "unknown"
                            category_name = re.sub(r'[^\w\s-]', '', category_name).strip()
                            category_name = re.sub(r'[-\s]+', '_', category_name)
                            category_name = category_name.lower()[:30]
                            logger.info(f"📋 Extracted category name (alt): {category_name}")
            except Exception as e:
                logger.warning(f"⚠️ Could not extract category name: {e}")
            
            # Filter: Skip saving if category is "unknown" (page not fully loaded)
            if category_name == "unknown":
                logger.info(f"🚫 Skipping save - category is 'unknown' (page not fully loaded)")
                return False
            
            # Generate new filename format: {HHMMSS}_{DDMMYY}_page{page_num}_{category_name}_{uid}_seoudi.json
            now = datetime.now()
            hhmmss = now.strftime("%H%M%S")  # Hour, minute, second
            ddmmyy = now.strftime("%d%m%y")  # Day, month, year (2-digit)
            
            filename = f"{responses_dir}/{hhmmss}_{ddmmyy}_page{page_num}_{category_name}_{category_uid}_seoudi.json"
            
            # Save response data
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(response_data, f, ensure_ascii=False, indent=2)
                
            logger.info(f"💾 Raw response saved to: {filename}")
            return True
                
        except Exception as e:
            logger.error(f"❌ Error saving raw response: {e}")
            return False
    
    def _is_valid_products_response(self, response_data: Dict) -> bool:
        """Check if response data contains valid product structure"""
        try:
            # Check for common GraphQL product response structures
            if isinstance(response_data, dict):
                # Look for data.connection structure (Seoudi specific)
                if 'data' in response_data:
                    data = response_data['data']
                    if isinstance(data, dict):
                        # Check for Seoudi's specific structure: data.connection.products.items (nodes aliased as items)
                        if 'connection' in data and isinstance(data['connection'], dict):
                            connection = data['connection']
                            # Handle both direct products and other connection structures
                            for key, value in connection.items():
                                if isinstance(value, dict):
                                    # Check for items (which could be nodes aliased as items)
                                    if 'items' in value and isinstance(value['items'], list):
                                        return True
                                    # Check for direct nodes
                                    if 'nodes' in value and isinstance(value['nodes'], list):
                                        return True
                        
                        # Check for other common structures
                        product_keys = ['products', 'items', 'results', 'productSearch', 'searchProducts']
                        for key in product_keys:
                            if key in data and isinstance(data[key], (list, dict)):
                                if isinstance(data[key], list) and len(data[key]) > 0:
                                    return True
                                if isinstance(data[key], dict) and ('items' in data[key] or 'nodes' in data[key]):
                                    return True
                
                # Direct products array
                if 'products' in response_data and isinstance(response_data['products'], list):
                    return True
                    
                # Items array
                if 'items' in response_data and isinstance(response_data['items'], list):
                    return True
            
            return False
        except Exception:
            return False
    
    def _count_products_in_response(self, response_data: Dict) -> int:
        """Count the number of products in a response"""
        try:
            if isinstance(response_data, dict):
                # Check Seoudi's specific structure: data.connection.*.items
                if 'data' in response_data and isinstance(response_data['data'], dict):
                    data = response_data['data']
                    
                    # Check for connection structure
                    if 'connection' in data and isinstance(data['connection'], dict):
                        connection = data['connection']
                        # Handle any connection structure
                        for key, value in connection.items():
                            if isinstance(value, dict):
                                # Check for items (which could be nodes aliased as items)
                                if 'items' in value and isinstance(value['items'], list):
                                    return len(value['items'])
                                # Check for direct nodes
                                if 'nodes' in value and isinstance(value['nodes'], list):
                                    return len(value['nodes'])
                    
                    # Check other common structures
                    product_keys = ['products', 'items', 'results', 'productSearch', 'searchProducts']
                    for key in product_keys:
                        if key in data:
                            if isinstance(data[key], list):
                                return len(data[key])
                            elif isinstance(data[key], dict):
                                if 'items' in data[key] and isinstance(data[key]['items'], list):
                                    return len(data[key]['items'])
                                if 'nodes' in data[key] and isinstance(data[key]['nodes'], list):
                                    return len(data[key]['nodes'])
                
                # Direct products/items arrays
                if 'products' in response_data and isinstance(response_data['products'], list):
                    return len(response_data['products'])
                if 'items' in response_data and isinstance(response_data['items'], list):
                    return len(response_data['items'])
            
            return 0
        except Exception:
            return 0
    
    def _check_location_setup_required(self, page: Page) -> bool:
        """Check if location setup is required by looking for specific element"""
        try:
            # Look for the specific element that indicates location setup is needed
            location_setup_element = page.query_selector('p[data-v-513ef701].my-4.font-light.text-grey-700.text-lg')
            
            if location_setup_element:
                element_text = location_setup_element.text_content().strip()
                if "We'll show you the products accordingly" in element_text:
                    logger.info("🔍 Found location setup indicator element")
                    return True
                    
            logger.info("🔍 Location setup indicator not found - location already configured")
            return False
            
        except Exception as e:
            logger.warning(f"⚠️ Error checking location setup requirement: {e}")
            return False  # Default to no location setup needed if we can't determine
    
    def _setup_seoudi_location(self, page: Page):
        """Set up location on Seoudi website (steps 3-7) - Vue.js Compatible Version"""
        try:
            logger.info("📍 Setting up Seoudi location with Vue.js compatible approach...")
            
            # Step 3: Close popup by clicking bottom left corner
            logger.info("Step 3: Closing popup")
            page.click('body', position={'x': 50, 'y': page.viewport_size['height'] - 50})
            self.browser_manager.random_click_delay()
            
            # Step 4: Select city using JavaScript approach
            logger.info("Step 4: Selecting city")
            city_success = page.evaluate("""
                () => {
                    try {
                        const citySelect = document.querySelector('select[name="city"]:not([disabled])');
                        if (citySelect && citySelect.options.length > 1) {
                            // Set to second option (first real city)
                            citySelect.selectedIndex = 1;
                            
                            // Trigger Vue.js events
                            const changeEvent = new Event('change', { bubbles: true });
                            const inputEvent = new Event('input', { bubbles: true });
                            citySelect.dispatchEvent(inputEvent);
                            citySelect.dispatchEvent(changeEvent);
                            
                            console.log('City selected:', citySelect.value);
                            return true;
                        }
                        return false;
                    } catch (e) {
                        console.error('City selection failed:', e);
                        return false;
                    }
                }
            """)
            
            if not city_success:
                raise Exception("Failed to select city")
            
            logger.info("✅ City selected successfully")
            page.wait_for_timeout(3000)  # Wait for Vue.js to process
            
            # Step 5: Wait for area dropdown to become enabled and select
            logger.info("Step 5: Selecting area")
            area_success = page.evaluate("""
                () => {
                    try {
                        // Wait for area select to become enabled
                        let attempts = 0;
                        const checkArea = () => {
                            const areaSelect = document.querySelector('select[name="area"]');
                            if (areaSelect && !areaSelect.disabled && areaSelect.options.length > 7) {
                                // Select 7th option (0-based index = 6)
                                areaSelect.selectedIndex = 7;
                                
                                // Trigger events
                                const changeEvent = new Event('change', { bubbles: true });
                                const inputEvent = new Event('input', { bubbles: true });
                                areaSelect.dispatchEvent(inputEvent);
                                areaSelect.dispatchEvent(changeEvent);
                                
                                console.log('Area selected:', areaSelect.value);
                                return true;
                            }
                            return false;
                        };
                        
                        // Try immediately first
                        if (checkArea()) return true;
                        
                        // If not ready, wait a bit and try again
                        return new Promise((resolve) => {
                            const interval = setInterval(() => {
                                attempts++;
                                if (checkArea() || attempts > 10) {
                                    clearInterval(interval);
                                    resolve(attempts <= 10);
                                }
                            }, 500);
                        });
                    } catch (e) {
                        console.error('Area selection failed:', e);
                        return false;
                    }
                }
            """)
            
            if not area_success:
                raise Exception("Failed to select area")
                
            logger.info("✅ Area selected successfully")
            page.wait_for_timeout(3000)  # Wait for Vue.js to process
            
            # Step 6: Wait for district dropdown to become enabled and select
            logger.info("Step 6: Selecting district")
            district_success = page.evaluate("""
                () => {
                    try {
                        // Wait for district select to become enabled
                        let attempts = 0;
                        const checkDistrict = () => {
                            const districtSelect = document.querySelector('select[name="district"]');
                            if (districtSelect && !districtSelect.disabled && districtSelect.options.length > 1) {
                                // Select first available district (index 1)
                                districtSelect.selectedIndex = 1;
                                
                                // Trigger events
                                const changeEvent = new Event('change', { bubbles: true });
                                const inputEvent = new Event('input', { bubbles: true });
                                districtSelect.dispatchEvent(inputEvent);
                                districtSelect.dispatchEvent(changeEvent);
                                
                                console.log('District selected:', districtSelect.value);
                                return true;
                            }
                            return false;
                        };
                        
                        // Try immediately first
                        if (checkDistrict()) return true;
                        
                        // If not ready, wait a bit and try again
                        return new Promise((resolve) => {
                            const interval = setInterval(() => {
                                attempts++;
                                if (checkDistrict() || attempts > 10) {
                                    clearInterval(interval);
                                    resolve(attempts <= 10);
                                }
                            }, 500);
                        });
                    } catch (e) {
                        console.error('District selection failed:', e);
                        return false;
                    }
                }
            """)
            
            if not district_success:
                raise Exception("Failed to select district")
                
            logger.info("✅ District selected successfully")
            page.wait_for_timeout(2000)
            
            # Step 7: Click the SVG confirmation icon
            logger.info("Step 7: Clicking confirmation icon")
            self.wait_and_click(page, 'svg.w-6.h-6.fill-current.text-primary-100.float-right.icon.sprite-icons')
            
            # Wait for location setup to complete
            page.wait_for_load_state("load")
            
            logger.info("✅ Seoudi location setup completed successfully!")
            
        except Exception as e:
            logger.error(f"❌ Error during Seoudi location setup: {e}")
            raise
    
    def _load_all_products(self, page: Page) -> int:
        """Load all products by clicking Load More button until it disappears"""
        products_loaded = 0
        load_more_clicks = 0
        
        try:
            logger.info("📦 Loading all products...")
            
            # Wait for initial page load and potential network requests
            logger.info("⏳ Waiting for initial page content to load...")
            page.wait_for_timeout(5000)  # Wait 5 seconds for initial load
            logger.info("✅ Initial wait completed - checking for products and Load More button")
            
            while True:
                # Scroll to bottom first
                self.scroll_to_bottom(page)
                
                # Check for "Out of Stock" indicator BEFORE clicking Load More
                logger.info("🔍 Checking for 'Out of stock' indicator before clicking...")
                out_of_stock = page.query_selector('div[data-v-33be66a4].OutOfStock')
                if out_of_stock:
                    out_of_stock_text = out_of_stock.text_content() or ""
                    logger.info(f"📋 Out of stock element found: '{out_of_stock_text.strip()}'")
                    if "Out of stock" in out_of_stock_text:
                        logger.info("✅ Out of stock indicator found - stopping Load More clicks (no extra click)")
                        break
                
                # Look for the Load More button
                load_more_button = page.query_selector(
                    'button[data-v-aa6a7d66][type="button"].mt-8.text-primary-700.border.border-primary-700.rounded-full.px-12.py-4.text-lg.font-bold.flex.items-center.justify-center.w-48.h-16.whitespace-nowrap'
                )
                
                if not load_more_button:
                    logger.info("✅ Load More button not found - all products loaded")
                    break
                
                # Check if button is visible and enabled
                if not load_more_button.is_visible():
                    logger.info("✅ Load More button not visible - all products loaded")
                    break
                
                # Click the Load More button
                logger.info(f"🔄 Clicking Load More button (click #{load_more_clicks + 1})")
                self.browser_manager.random_click_delay()
                load_more_button.click()
                load_more_clicks += 1
                
                # Wait for new content to load
                page.wait_for_load_state("load")
                
                # Brief wait for the page to update
                page.wait_for_timeout(1000)
                
                # Safety check to prevent infinite loops
                if load_more_clicks > 50:  # Reasonable limit
                    logger.warning("⚠️ Reached Load More click limit (50), stopping")
                    break
            
            # Count total products loaded (you can adjust this selector)
            products = page.query_selector_all('[data-product], .product-item, .product-card')
            products_loaded = len(products)
            
            logger.info(f"✅ Product loading completed: {load_more_clicks} clicks, {products_loaded} products")
            
        except Exception as e:
            logger.error(f"❌ Error loading products: {e}")
        
        return products_loaded
    
    def _process_captured_requests(self, captured_requests: List[Dict]) -> List[Dict]:
        """Process and filter captured network requests with response data"""
        valid_requests = []
        seen_urls = set()
        total_responses_saved = 0
        
        for request in captured_requests:
            url = request['url']
            
            # Remove duplicates
            if url in seen_urls:
                continue
            seen_urls.add(url)
            
            # Check if we have response data
            if 'response_data' in request:
                total_responses_saved += 1
                logger.info(f"📥 Processed Products response: {url}")
                logger.info(f"💾 Raw JSON response already saved to file")
            else:
                # Old format - just URL (for backward compatibility)
                logger.info(f"📥 Processed Products request (no response data): {url}")
            
            valid_requests.append(request)
        
        logger.info(f"📊 Processed {len(captured_requests)} requests, {len(valid_requests)} valid unique requests")
        logger.info(f"💾 Total raw JSON responses saved: {total_responses_saved}")
        return valid_requests
    
    def _save_product_data(self, response_data: Dict, source_url: str) -> int:
        """Extract and save individual product data from GraphQL response"""
        products_saved = 0
        
        try:
            # Extract products from various possible structures
            products_list = []
            
            if isinstance(response_data, dict):
                # Check Seoudi's specific structure: data.connection.*.items
                if 'data' in response_data and isinstance(response_data['data'], dict):
                    data = response_data['data']
                    
                    # Check for connection structure first
                    if 'connection' in data and isinstance(data['connection'], dict):
                        connection = data['connection']
                        # Handle any connection structure
                        for key, value in connection.items():
                            if isinstance(value, dict):
                                # Check for items (which could be nodes aliased as items)
                                if 'items' in value and isinstance(value['items'], list):
                                    products_list = value['items']
                                    break
                                # Check for direct nodes
                                elif 'nodes' in value and isinstance(value['nodes'], list):
                                    products_list = value['nodes']
                                    break
                    
                    # Check other common structures if not found
                    if not products_list:
                        product_keys = ['products', 'items', 'results', 'productSearch', 'searchProducts']
                        for key in product_keys:
                            if key in data:
                                if isinstance(data[key], list):
                                    products_list = data[key]
                                    break
                                elif isinstance(data[key], dict):
                                    if 'items' in data[key] and isinstance(data[key]['items'], list):
                                        products_list = data[key]['items']
                                        break
                                    elif 'nodes' in data[key] and isinstance(data[key]['nodes'], list):
                                        products_list = data[key]['nodes']
                                        break
                
                # Direct products/items arrays
                if not products_list:
                    if 'products' in response_data and isinstance(response_data['products'], list):
                        products_list = response_data['products']
                    elif 'items' in response_data and isinstance(response_data['items'], list):
                        products_list = response_data['items']
            
            # Process each product
            for product in products_list:
                if isinstance(product, dict):
                    # Extract key product information
                    product_info = self._extract_product_info(product)
                    product_info['source_url'] = source_url
                    from datetime import datetime
                    product_info['scraped_at'] = datetime.now().isoformat()
                    
                    # Save to file/database (you can customize this)
                    self._save_single_product(product_info)
                    products_saved += 1
            
            return products_saved
            
        except Exception as e:
            logger.error(f"❌ Error saving product data: {e}")
            return 0
    
    def _extract_product_info(self, product: Dict) -> Dict:
        """Extract standardized product information from raw product data"""
        try:
            # Common product fields to extract
            product_info = {
                'id': product.get('id', ''),
                'name': product.get('name', product.get('title', '')),
                'price': product.get('price', product.get('cost', '')),
                'original_price': product.get('originalPrice', product.get('original_price', '')),
                'discount': product.get('discount', ''),
                'brand': product.get('brand', ''),
                'category': product.get('category', ''),
                'description': product.get('description', ''),
                'image_url': product.get('image', product.get('imageUrl', '')),
                'availability': product.get('availability', product.get('inStock', True)),
                'sku': product.get('sku', ''),
                'raw_data': product  # Keep the full raw data for reference
            }
            
            return product_info
            
        except Exception as e:
            logger.error(f"❌ Error extracting product info: {e}")
            return {'raw_data': product}
    
    def _save_single_product(self, product_info: Dict):
        """Save a single product to file/database"""
        try:
            # For now, save to JSON file (you can modify to use database)
            import json
            import os
            from datetime import datetime
            
            # Create products directory if it doesn't exist
            products_dir = "scraped_products"
            if not os.path.exists(products_dir):
                os.makedirs(products_dir)
            
            # Generate filename with timestamp
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"{products_dir}/seoudi_products_{timestamp}.json"
            
            # Append to file (or create new)
            products_list = []
            if os.path.exists(filename):
                try:
                    with open(filename, 'r', encoding='utf-8') as f:
                        products_list = json.load(f)
                except:
                    products_list = []
            
            products_list.append(product_info)
            
            # Save back to file
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(products_list, f, ensure_ascii=False, indent=2)
                
        except Exception as e:
            logger.error(f"❌ Error saving single product: {e}")