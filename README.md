# 🛒 Mowaffer Grocery Scraper v1.0
**The Best Grocery Price Scraper Ever Created!**

A sophisticated, modular Python scraper for grocery price comparison using Playwright and Supabase.

## 🎯 Features

- **🏭 Factory Pattern Architecture** - Automatically selects the right scraper for each website
- **🌐 Smart Browser Management** - One tab per domain with intelligent rotation  
- **🔄 Proxy Toggle** - Easy on/off switch for Rayobyte proxy
- **📊 Database Logging** - Complete tracking in Supabase
- **⚡ Domain Rotation** - Gives servers rest time between scrapes
- **🛡️ Error Handling** - Comprehensive retry mechanisms and logging

## 🏗️ Project Structure

```
mowaffer_scraper/
├── config/
│   ├── settings.py          # Configuration management
├── core/
│   ├── base_scraper.py      # Base scraper class
│   ├── browser_manager.py   # Browser/tab management  
│   ├── database_manager.py  # Supabase operations
├── scrapers/
│   ├── scraper_factory.py   # Factory pattern for scrapers
│   ├── oscar_scraper.py     # Oscar Stores scraper
│   ├── seoudi_scraper.py    # Seoudi Supermarket scraper
├── main.py                  # Main orchestrator
└── .env                     # Configuration file
```

## 🚀 Quick Start

### 1. Configure Your Environment

Edit the `.env` file with your credentials:

```bash
# Supabase Configuration
SUPABASE_KEY=your_actual_supabase_key_here

# Proxy Toggle - EASY TO CHANGE!
PROXY_ENABLED=true   # Set to 'false' to disable proxy
```

### 2. Run the Scraper

```bash
python3 main.py
```

## 🔧 Proxy Configuration

**Easy Proxy Toggle:**
- Set `PROXY_ENABLED=true` in `.env` to use Rayobyte proxy
- Set `PROXY_ENABLED=false` in `.env` to use direct connection

## 🏪 Supported Websites

- **Oscar Stores** (`oscarstores.com`)
  - ✅ Full pagination support
  - ✅ Product count validation
  - ✅ Dynamic page detection

- **Seoudi Supermarket** (`seoudisupermarket.com`)
  - ✅ Network request interception
  - ✅ Location setup automation
  - ✅ Load more button handling

- **Spinneys** (Coming Soon)

## 🔄 Smart Server-Friendly Processing

**Domain Rotation Logic:**
- Processes URLs in exact database order (by `serial` number)
- **Same Domain**: 10-20 second delay between requests (server-friendly)
- **Different Domain**: No delay when switching (efficient - different servers)
- **Tab Management**: One persistent tab per domain, reused for same-domain URLs

**Example Processing:**
```
Seoudi(1) → wait 15s → Seoudi(2) → immediate → Spinneys(3) → wait 12s → Spinneys(4)
```

This approach mimics natural human browsing and protects servers from bot detection.

## 📊 Database Schema

### `links_to_scrape` (Input)
- `serial`, `website`, `category`, `url`

### `links_to_scrape_log` (Output)
- All input fields plus:
- `scrape_status` (SUCCESS/FAIL/PENDING)
- `scraped_at`, `products_found`, `pages_scraped`
- `error_message` (if failed)

## 🎛️ Configuration Options

**Delays & Timing:**
- `MIN_CLICK_DELAY` / `MAX_CLICK_DELAY` - Random delays before clicks (2-6s)
- `MIN_URL_DELAY` / `MAX_URL_DELAY` - Delays between domains (10-20s)

**Browser:**
- `BROWSER_HEADLESS` - Run browser visibly (false) or hidden (true)
- `BROWSER_TIMEOUT` - Page load timeout in milliseconds

## 🔍 How It Works

1. **Load URLs** from Supabase `links_to_scrape` table
2. **Factory Pattern** selects appropriate scraper for each URL
3. **Smart Tab Management** - one tab per domain, rotating between sites
4. **Domain-Specific Logic**:
   - **Oscar**: Pagination with product count validation
   - **Seoudi**: Network interception with location setup
5. **Real-time Logging** to `links_to_scrape_log` table

## 📈 Monitoring

The scraper provides:
- **Real-time Progress** - Current URL, success/fail counts
- **Database Statistics** - Success rates, total attempts
- **Detailed Logging** - File logs with timestamps
- **Error Tracking** - Specific error messages in database

## 🛠️ Troubleshooting

**Common Issues:**

1. **Missing Supabase Key**: Update `SUPABASE_KEY` in `.env`
2. **Proxy Issues**: Set `PROXY_ENABLED=false` to test without proxy
3. **Browser Timeout**: Increase `BROWSER_TIMEOUT` in `.env`
4. **Initiator Warnings**: Check Seoudi's JavaScript file names haven't changed

## 🎯 Future Phases

- [ ] Data validation and cleaning
- [ ] Performance optimizations
- [ ] Concurrent processing
- [ ] Additional website scrapers
- [ ] Advanced analytics dashboard

## 📝 Usage Example

```bash
🛒 MOWAFFER GROCERY SCRAPER v1.0
The Best Grocery Price Scraper Ever Created!
===============================================
🕐 Started at: 2024-01-15 14:30:00
🔧 Configuration:
   Proxy Enabled: true
   Browser Headless: false
   Click Delays: 2.0-6.0s
   Domain Delays: 10.0-20.0s

📊 URLs by domain:
   • Seoudi: 2 URLs
   • Spinneys: 2 URLs

📊 Progress: 1/4 (25.0%)
   ✅ Successful: 1
   ❌ Failed: 0
   🔄 Remaining: 3
```

---
**Built with ❤️ using Python, Playwright, and Supabase**