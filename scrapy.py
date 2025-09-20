import requests
from bs4 import BeautifulSoup
import json
import argparse
from datetime import datetime
import random
import time
import urllib3

# Disable SSL warnings
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

def get_proxy_session(proxy_list=None):
    """Create a requests session with proxy configuration"""
    session = requests.Session()
    
    if proxy_list:
        proxy = random.choice(proxy_list)
        proxies = {
            'http': proxy,
            'https': proxy
        }
        session.proxies.update(proxies)
        print(f"🔄 Using proxy: {proxy}")
    
    # Enhanced headers to look more like a real browser
    headers = {
        'User-Agent': random.choice([
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/121.0'
        ]),
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.5',
        'Accept-Encoding': 'gzip, deflate, br',
        'DNT': '1',
        'Connection': 'keep-alive',
        'Upgrade-Insecure-Requests': '1',
        'Sec-Fetch-Dest': 'document',
        'Sec-Fetch-Mode': 'navigate',
        'Sec-Fetch-Site': 'none',
        'Sec-Fetch-User': '?1'
    }
    session.headers.update(headers)
    
    # Disable SSL verification for proxies that might have issues
    session.verify = False
    
    return session

def test_proxy(proxy):
    """Test if a proxy is working"""
    try:
        response = requests.get(
            'http://httpbin.org/ip', 
            proxies={'http': proxy, 'https': proxy}, 
            timeout=15,
            verify=False
        )
        if response.status_code == 200:
            print(f"✅ Proxy {proxy} is working")
            return True
    except Exception as e:
        print(f"❌ Proxy {proxy} failed: {str(e)}")
        return False

def find_company_slug(company_name, source):
    """Help find the correct company slug by testing different variations"""
    variations = [
        company_name.lower(),
        company_name.lower().replace(' ', '-'),
        company_name.lower().replace(' ', '_'),
        f"{company_name.lower()}-technologies",
        f"{company_name.lower()}-inc"
    ]
    
    print(f"🔍 Suggested slugs for {company_name} on {source}:")
    for variation in variations:
        print(f"   - {variation}")
    
    return variations[0]  # Return the first variation as default

def scrape_g2(company, start_date, end_date, session):
    reviews = []
    page = 1
    
    # Test the URL first
    test_url = f"https://www.g2.com/products/{company}"
    try:
        test_response = session.get(test_url, timeout=30)
        print(f"🔍 Testing G2 URL: {test_url} - Status: {test_response.status_code}")
        
        if test_response.status_code == 404:
            print(f"❌ Company '{company}' not found on G2. Try checking the correct slug.")
            suggested = find_company_slug(company, "G2")
            print(f"💡 Try: python script.py --company {suggested} ...")
            return reviews
        elif test_response.status_code == 403:
            print("❌ G2 is blocking requests. The site may have anti-bot protection.")
            return reviews
    except Exception as e:
        print(f"❌ Error testing G2 URL: {e}")
        return reviews
    
    while True:
        url = f"https://www.g2.com/products/{company}/reviews?page={page}"
        try:
            # Add random delay between requests
            time.sleep(random.uniform(3, 8))
            
            res = session.get(url, timeout=30)
            print(f"Page {page}: {res.status_code}")
            
            if res.status_code != 200:
                if res.status_code == 403:
                    print("❌ Access forbidden. G2 detected scraping attempt.")
                break

            soup = BeautifulSoup(res.text, "html.parser")
            
            # Try multiple selectors as G2 might use different ones
            selectors = [
                ".review-card",
                "[data-testid='review-card']",
                ".paper--white",
                ".review"
            ]
            
            review_cards = []
            for selector in selectors:
                review_cards = soup.select(selector)
                if review_cards:
                    print(f"✅ Found {len(review_cards)} reviews using selector: {selector}")
                    break
            
            if not review_cards:
                print(f"❌ No review cards found on page {page}")
                if page == 1:
                    print("🔍 Available elements on page:")
                    # Debug: print some elements to understand page structure
                    for elem in soup.find_all(['div', 'article'], limit=5):
                        classes = elem.get('class', [])
                        if classes:
                            print(f"   - Element with classes: {' '.join(classes)}")
                break

            for card in review_cards:
                try:
                    # Try multiple date selectors
                    date_text = None
                    for date_selector in ["time", "[datetime]", ".review-date"]:
                        date_elem = card.select_one(date_selector)
                        if date_elem:
                            date_text = date_elem
                            break
                    
                    if not date_text:
                        continue
                    
                    # Try different date formats
                    date_attr = date_text.get("datetime") or date_text.get_text(strip=True)
                    try:
                        review_date = datetime.strptime(date_attr, "%Y-%m-%d")
                    except:
                        try:
                            review_date = datetime.strptime(date_attr, "%Y-%m-%dT%H:%M:%S")
                        except:
                            continue
                    
                    if not (start_date <= review_date <= end_date):
                        continue

                    # Try multiple selectors for each field
                    title_selectors = [".review-title", "[data-testid='review-title']", "h3", "h4"]
                    body_selectors = [".review-body", "[data-testid='review-body']", ".review-content", "p"]
                    name_selectors = [".reviewer-name", "[data-testid='reviewer-name']", ".author-name"]
                    rating_selectors = [".star-rating", "[data-rating]", ".stars"]

                    title = ""
                    for selector in title_selectors:
                        elem = card.select_one(selector)
                        if elem:
                            title = elem.get_text(strip=True)
                            break

                    description = ""
                    for selector in body_selectors:
                        elem = card.select_one(selector)
                        if elem:
                            description = elem.get_text(strip=True)
                            break

                    reviewer_name = ""
                    for selector in name_selectors:
                        elem = card.select_one(selector)
                        if elem:
                            reviewer_name = elem.get_text(strip=True)
                            break

                    rating = None
                    for selector in rating_selectors:
                        elem = card.select_one(selector)
                        if elem:
                            rating = elem.get("data-rating") or elem.get("aria-label")
                            break

                    reviews.append({
                        "title": title,
                        "description": description,
                        "date": review_date.strftime("%Y-%m-%d"),
                        "reviewer_name": reviewer_name,
                        "rating": rating,
                        "source": "G2"
                    })
                except Exception as e:
                    print(f"⚠️ Skipping a review due to error: {e}")
            
            page += 1
            if page > 10:  # Limit pages to avoid infinite loops
                print("🛑 Reached page limit (10 pages)")
                break
                
        except requests.exceptions.RequestException as e:
            print(f"❌ Request failed for page {page}: {e}")
            break
    
    return reviews

def find_capterra_product_url(company, session):
    """Search Capterra for the company and extract the product URL"""
    search_url = f"https://www.capterra.com/search/?query={company}"
    
    try:
        print(f"🔍 Searching Capterra for '{company}': {search_url}")
        time.sleep(random.uniform(2, 4))
        
        res = session.get(search_url, timeout=30)
        print(f"Search results status: {res.status_code}")
        
        if res.status_code != 200:
            print(f"❌ Failed to search Capterra: HTTP {res.status_code}")
            return None
            
        soup = BeautifulSoup(res.text, "html.parser")
        
        # Look for product cards in search results
        product_cards = soup.select('[data-testid="search-product-card"]')
        
        if not product_cards:
            print("❌ No product cards found in search results")
            return None
        
        print(f"✅ Found {len(product_cards)} product(s) in search results")
        
        # Look for the best matching product
        for card in product_cards:
            try:
                # Extract product name and URL
                product_name_elem = card.select_one('[data-testid="product-name"]')
                if not product_name_elem:
                    continue
                    
                product_name = product_name_elem.get_text(strip=True).lower()
                product_url = product_name_elem.get('href')
                
                if not product_url:
                    continue
                
                print(f"📦 Found product: '{product_name}' - {product_url}")
                
                # Check if this matches our search (simple matching)
                if company.lower() in product_name or product_name in company.lower():
                    print(f"✅ Best match found: {product_name}")
                    return product_url
                    
            except Exception as e:
                print(f"⚠️ Error processing product card: {e}")
                continue
        
        # If no exact match, return the first result
        first_card = product_cards[0]
        first_product_elem = first_card.select_one('[data-testid="product-name"]')
        if first_product_elem:
            first_url = first_product_elem.get('href')
            first_name = first_product_elem.get_text(strip=True)
            print(f"⚠️ No exact match found, using first result: {first_name}")
            return first_url
            
        return None
        
    except Exception as e:
        print(f"❌ Error searching Capterra: {e}")
        return None

def scrape_capterra(company, start_date, end_date, session):
    reviews = []
    
    # First, search for the company to get the correct product URL
    product_url = find_capterra_product_url(company, session)
    
    if not product_url:
        print(f"❌ Could not find product URL for '{company}' on Capterra")
        return reviews
    
    # Extract the product ID and slug from the URL
    # URL format: https://www.capterra.com/p/135003/Slack/
    try:
        import re
        url_match = re.search(r'/p/(\d+)/([^/]+)/', product_url)
        if url_match:
            product_id = url_match.group(1)
            product_slug = url_match.group(2)
            print(f"✅ Extracted product info - ID: {product_id}, Slug: {product_slug}")
        else:
            print(f"❌ Could not extract product info from URL: {product_url}")
            return reviews
    except Exception as e:
        print(f"❌ Error parsing product URL: {e}")
        return reviews
    
    # Test the product page first
    try:
        test_response = session.get(product_url, timeout=30)
        print(f"🔍 Testing product page: {product_url} - Status: {test_response.status_code}")
        
        if test_response.status_code != 200:
            print(f"❌ Product page not accessible: HTTP {test_response.status_code}")
            return reviews
    except Exception as e:
        print(f"❌ Error testing product page: {e}")
        return reviews
    
    # Now scrape reviews from the reviews page
    page = 1
    while True:
        # Build reviews URL using the extracted product info
        reviews_url = f"https://www.capterra.com/p/{product_id}/{product_slug}/reviews/?page={page}"
        
        try:
            time.sleep(random.uniform(3, 8))
            res = session.get(reviews_url, timeout=30)
            print(f"Page {page}: {res.status_code} - {reviews_url}")
            
            if res.status_code != 200:
                if res.status_code == 404 and page == 1:
                    print("❌ Reviews page not found. Product might not have reviews.")
                break

            soup = BeautifulSoup(res.text, "html.parser")
            
            # Look for review cards with multiple selectors
            review_selectors = [
                '[data-testid="review-card"]',
                '.review-card',
                '[data-testid="review"]',
                '.review',
                '.user-review',
                '[data-review-id]'
            ]
            
            review_cards = []
            for selector in review_selectors:
                review_cards = soup.select(selector)
                if review_cards:
                    print(f"✅ Found {len(review_cards)} reviews using selector: {selector}")
                    break
            
            if not review_cards:
                print(f"❌ No review cards found on page {page}")
                if page == 1:
                    print("🔍 Available elements on page:")
                    # Debug: print some elements to understand page structure
                    for elem in soup.find_all(['div', 'article'], limit=10):
                        classes = elem.get('class', [])
                        test_id = elem.get('data-testid', '')
                        if classes or test_id:
                            print(f"   - Element: classes={classes}, testid={test_id}")
                break

            for card in review_cards:
                try:
                    # Extract date
                    date_elem = None
                    for date_selector in ["time[datetime]", ".review-date", "[data-testid='review-date']", ".date"]:
                        date_elem = card.select_one(date_selector)
                        if date_elem:
                            break
                    
                    if not date_elem:
                        continue
                    
                    # Try to parse the date
                    date_text = date_elem.get("datetime") or date_elem.get_text(strip=True)
                    try:
                        if 'T' in date_text:
                            review_date = datetime.strptime(date_text.split('T')[0], "%Y-%m-%d")
                        else:
                            # Try different date formats
                            for fmt in ["%Y-%m-%d", "%m/%d/%Y", "%B %d, %Y"]:
                                try:
                                    review_date = datetime.strptime(date_text, fmt)
                                    break
                                except:
                                    continue
                            else:
                                continue
                    except:
                        continue
                    
                    # Check if date is within range
                    if not (start_date <= review_date <= end_date):
                        continue

                    # Extract title
                    title = ""
                    title_selectors = [
                        ".review-title", 
                        "[data-testid='review-title']", 
                        "h3", "h4", 
                        ".title",
                        ".review-header"
                    ]
                    for selector in title_selectors:
                        title_elem = card.select_one(selector)
                        if title_elem:
                            title = title_elem.get_text(strip=True)
                            break

                    # Extract review text/description
                    description = ""
                    text_selectors = [
                        ".review-body", 
                        "[data-testid='review-body']", 
                        ".review-content", 
                        ".review-text",
                        "p"
                    ]
                    for selector in text_selectors:
                        text_elem = card.select_one(selector)
                        if text_elem:
                            description = text_elem.get_text(strip=True)
                            break

                    # Extract reviewer name
                    reviewer_name = ""
                    name_selectors = [
                        ".reviewer-name", 
                        "[data-testid='reviewer-name']", 
                        ".author-name",
                        ".user-name",
                        ".reviewer"
                    ]
                    for selector in name_selectors:
                        name_elem = card.select_one(selector)
                        if name_elem:
                            reviewer_name = name_elem.get_text(strip=True)
                            break

                    # Extract rating
                    rating = None
                    rating_selectors = [
                        ".star-rating[data-rating]",
                        "[data-rating]",
                        ".stars",
                        ".rating"
                    ]
                    for selector in rating_selectors:
                        rating_elem = card.select_one(selector)
                        if rating_elem:
                            rating = rating_elem.get("data-rating")
                            if not rating:
                                # Try to extract from aria-label or text
                                aria_label = rating_elem.get("aria-label", "")
                                if "star" in aria_label.lower():
                                    import re
                                    rating_match = re.search(r'(\d+(?:\.\d+)?)', aria_label)
                                    if rating_match:
                                        rating = rating_match.group(1)
                            break

                    # Only add review if we have essential data
                    if description and reviewer_name:
                        review_data = {
                            "title": title,
                            "description": description,
                            "date": review_date.strftime("%Y-%m-%d"),
                            "reviewer_name": reviewer_name,
                            "rating": rating,
                            "source": "Capterra"
                        }
                        
                        reviews.append(review_data)
                        print(f"✅ Extracted review from {reviewer_name} - Rating: {rating}")

                except Exception as e:
                    print(f"⚠️ Skipping a review due to error: {e}")
            
            page += 1
            if page > 10:
                print("🛑 Reached page limit (10 pages)")
                break
                
        except requests.exceptions.RequestException as e:
            print(f"❌ Request failed for page {page}: {e}")
            break
    
    return reviews

def scrape_trustpilot(company, start_date, end_date, session):
    reviews = []
    
    # Test URL first
    test_url = f"https://www.trustpilot.com/review/{company}"
    try:
        test_response = session.get(test_url, timeout=30)
        print(f"🔍 Testing Trustpilot URL: {test_url} - Status: {test_response.status_code}")
        
        if test_response.status_code == 404:
            print(f"❌ Company '{company}' not found on Trustpilot.")
            # For Trustpilot, company might be a domain like slack.com
            if not company.endswith('.com'):
                suggested = f"{company}.com"
                print(f"💡 Try: python script.py --company {suggested} --source trustpilot ...")
            return reviews
    except Exception as e:
        print(f"❌ Error testing Trustpilot URL: {e}")
        return reviews
    
    page = 1
    while True:
        url = f"https://www.trustpilot.com/review/{company}?page={page}"
        try:
            time.sleep(random.uniform(3, 8))
            res = session.get(url, timeout=30)
            print(f"Page {page}: {res.status_code}")
            
            if res.status_code != 200:
                break

            soup = BeautifulSoup(res.text, "html.parser")
            
            # Updated selectors based on the new HTML structure
            review_cards = soup.select('article[data-service-review-card-paper="true"]')
            
            if not review_cards:
                # Try alternative selectors
                review_cards = soup.select('.styles_reviewCard__Qwhpy, .CDS_Card_card__485220')
                
            if not review_cards:
                print(f"❌ No review cards found on page {page}")
                if page == 1:
                    print("🔍 Available elements on page:")
                    # Debug: print some elements to understand page structure
                    for elem in soup.find_all(['article', 'div'], class_=lambda x: x and 'review' in str(x).lower(), limit=5):
                        classes = elem.get('class', [])
                        if classes:
                            print(f"   - Element with classes: {' '.join(classes)}")
                break

            print(f"✅ Found {len(review_cards)} reviews on page {page}")

            for card in review_cards:
                try:
                    # Extract date - look for time element with datetime attribute
                    date_elem = card.select_one("time[data-service-review-date-time-ago='true']")
                    if not date_elem:
                        date_elem = card.select_one("time[datetime]")
                    
                    if not date_elem:
                        continue
                    
                    # Get datetime attribute and parse it
                    date_attr = date_elem.get("datetime")
                    if not date_attr:
                        continue
                    
                    try:
                        # Parse ISO format datetime (e.g., "2025-01-21T16:46:14.000Z")
                        if 'T' in date_attr:
                            review_date = datetime.strptime(date_attr.split('T')[0], "%Y-%m-%d")
                        else:
                            review_date = datetime.strptime(date_attr, "%Y-%m-%d")
                    except ValueError:
                        continue
                    
                    # Check if date is within range
                    if not (start_date <= review_date <= end_date):
                        continue

                    # Extract reviewer name
                    reviewer_name = ""
                    name_elem = card.select_one("[data-consumer-name-typography='true']")
                    if name_elem:
                        reviewer_name = name_elem.get_text(strip=True)

                    # Extract rating from star image alt text
                    rating = None
                    star_img = card.select_one(".CDS_StarRating_starRating__614d2e")
                    if star_img:
                        alt_text = star_img.get("alt", "")
                        # Extract number from "Rated X out of 5 stars"
                        import re
                        rating_match = re.search(r'Rated (\d+) out of 5 stars', alt_text)
                        if rating_match:
                            rating = rating_match.group(1)

                    # Extract review title (now available in the new structure)
                    title = ""
                    title_elem = card.select_one("[data-service-review-title-typography='true']")
                    if title_elem:
                        title = title_elem.get_text(strip=True)

                    # Extract review text
                    review_text = ""
                    text_elem = card.select_one("[data-service-review-text-typography='true']")
                    if text_elem:
                        review_text = text_elem.get_text(strip=True)

                    # Extract additional info like country and review count
                    country = ""
                    country_elem = card.select_one("[data-consumer-country-typography='true']")
                    if country_elem:
                        country = country_elem.get_text(strip=True)

                    review_count = ""
                    count_elem = card.select_one("[data-consumer-reviews-count-typography='true']")
                    if count_elem:
                        review_count = count_elem.get_text(strip=True)

                    # Extract experience date from badge if available
                    experience_date = ""
                    badge_date_elem = card.select_one('[data-testid="review-badge-date"] .CDS_Badge_badgeText__9995a1')
                    if badge_date_elem:
                        experience_date = badge_date_elem.get_text(strip=True)

                    # Check if review is unprompted
                    is_unprompted = bool(card.select_one('[data-testid="review-badge-unprompted"]'))

                    # Only add review if we have essential data
                    if review_text and reviewer_name:
                        review_data = {
                            "title": title,
                            "description": review_text,
                            "date": review_date.strftime("%Y-%m-%d"),
                            "reviewer_name": reviewer_name,
                            "rating": rating,
                            "source": "Trustpilot",
                            "country": country,
                            "reviewer_total_reviews": review_count,
                            "experience_date": experience_date,
                            "is_unprompted": is_unprompted
                        }
                        
                        reviews.append(review_data)
                        print(f"✅ Extracted review from {reviewer_name} ({country}) - Rating: {rating}/5")
                        print(f"   Title: {title[:50]}...")
                        print(f"   Experience Date: {experience_date}")

                except Exception as e:
                    print(f"⚠️ Skipping a review due to error: {e}")
            
            page += 1
            if page > 10:
                print("🛑 Reached page limit (10 pages)")
                break
                
        except requests.exceptions.RequestException as e:
            print(f"❌ Request failed for page {page}: {e}")
            break
    
    return reviews

def load_proxies_from_file(filename):
    """Load proxies from a text file (one proxy per line)"""
    try:
        with open(filename, 'r') as f:
            proxies = [line.strip() for line in f.readlines() if line.strip()]
        return proxies
    except FileNotFoundError:
        print(f"❌ Proxy file {filename} not found")
        return []

def main(company, start, end, source, proxy_file=None, proxy_list=None):
    try:
        start_date = datetime.strptime(start, "%Y-%m-%d")
        end_date = datetime.strptime(end, "%Y-%m-%d")
    except ValueError:
        raise ValueError("❌ Invalid date format. Use YYYY-MM-DD")

    if start_date > end_date:
        raise ValueError("❌ Start date cannot be later than end date")

    # Load proxies
    proxies = []
    if proxy_file:
        proxies = load_proxies_from_file(proxy_file)
    elif proxy_list:
        proxies = proxy_list

    # Test proxies if provided
    if proxies:
        print(f"🔍 Testing {len(proxies)} proxies...")
        working_proxies = [proxy for proxy in proxies if test_proxy(proxy)]
        print(f"✅ Found {len(working_proxies)} working proxies")
        proxies = working_proxies

    # Create session with proxy
    session = get_proxy_session(proxies if proxies else None)

    # Scrape based on source
    if source == "g2":
        reviews = scrape_g2(company, start_date, end_date, session)
    elif source == "capterra":
        reviews = scrape_capterra(company, start_date, end_date, session)
    elif source == "trustpilot":
        reviews = scrape_trustpilot(company, start_date, end_date, session)
    else:
        raise ValueError("❌ Unsupported source. Choose g2, capterra, or trustpilot")

    if not reviews:
        print("⚠️ No reviews found for given parameters.")
        print("\n💡 Troubleshooting tips:")
        print("1. Check if the company slug is correct")
        print("2. Try different date ranges")
        print("3. The website might be blocking scraping attempts")
        print("4. CSS selectors might have changed")
    else:
        filename = f"{company}_{source}_reviews.json"
        with open(filename, "w", encoding="utf-8") as f:
            json.dump(reviews, f, indent=2, ensure_ascii=False)
        print(f"✅ Saved {len(reviews)} reviews to {filename}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Scrape SaaS reviews from G2, Capterra, or Trustpilot")
    parser.add_argument("--company", required=True, help="Company slug used in the review site URL")
    parser.add_argument("--start", required=True, help="Start date YYYY-MM-DD")
    parser.add_argument("--end", required=True, help="End date YYYY-MM-DD")
    parser.add_argument("--source", required=True, choices=["g2", "capterra", "trustpilot"], help="Review source")
    parser.add_argument("--proxy-file", help="Path to file containing proxy list (one per line)")
    parser.add_argument("--proxy", help="Single proxy to use (format: http://ip:port or socks5://ip:port)")

    args = parser.parse_args()
    
    proxy_list = None
    if args.proxy:
        proxy_list = [args.proxy]
    
    main(args.company, args.start, args.end, args.source, args.proxy_file, proxy_list)