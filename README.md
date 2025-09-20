# SaaS Review Scraper

This project scrapes reviews for a given SaaS company from **G2**, **Capterra**, or **Trustpilot** within a specific date range.
It supports proxy rotation to reduce blocking and saves extracted reviews into JSON files.

⚠️ **Disclaimer**: This script is for **educational/demo purposes only**. Please respect the Terms of Service of the websites you scrape.

---

https://github.com/user-attachments/assets/9a38c065-37c8-4a19-be65-b6a1f314f2f0

## 🚀 Features

* Scrape reviews from:

  * [G2](https://www.g2.com)
  * [Capterra](https://www.capterra.com)
  * [Trustpilot](https://www.trustpilot.com)
* Filter reviews by date range
* Save reviews to JSON file (`company_source_reviews.json`)
* Proxy support (rotational residential/backconnect proxies recommended)
* Random user-agents & request delays for stability

---

## 📦 Installation

Clone the repo and install required dependencies:

```bash
git clone https://github.com/<your-username>/<repo-name>.git
cd <repo-name>

# Create a virtual environment (recommended)
python3 -m venv venv
source venv/bin/activate   # On Windows use: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

---

## 📑 Requirements

The script uses:

```
requests
beautifulsoup4
urllib3
```

(Already listed in `requirements.txt`)

Install with:

```bash
pip install -r requirements.txt
```

---

## ⚙️ Usage

Run the scraper using:

```bash
python scraper.py --company <company-slug> --start YYYY-MM-DD --end YYYY-MM-DD --source <source>
```

### Example commands:

* Scrape **G2** reviews for Slack in 2024:

```bash
python scraper.py --company slack --start 2024-01-01 --end 2024-12-31 --source g2
```

* Scrape **Capterra** reviews for Slack:

```bash
python scraper.py --company Slack --start 2024-01-01 --end 2024-12-31 --source capterra
```

* Scrape **Trustpilot** reviews (use domain, e.g. `slack.com`):

```bash
python scraper.py --company slack.com --start 2024-01-01 --end 2024-12-31 --source trustpilot
```

---

## 🌐 Proxy Support

To reduce blocking, you can use proxies.

### Option 1: Single proxy

```bash
python scraper.py --company slack --start 2024-01-01 --end 2024-12-31 --source g2 --proxy http://ip:port
```

### Option 2: Multiple proxies (rotating)

Add your proxies (one per line) in `proxies.txt` (preferably **rotational residential/backconnect IPs**):

**proxies.txt** example:

```
http://username:password@residential-proxy1:8000
http://username:password@residential-proxy2:8000
socks5://username:password@residential-proxy3:1080
```

Run with:

```bash
python scraper.py --company slack --start 2024-01-01 --end 2024-12-31 --source g2 --proxy-file proxies.txt
```

---

## 📂 Output

Extracted reviews are saved to JSON:

```
<company>_<source>_reviews.json
```

Example:

```
slack_g2_reviews.json
slack_capterra_reviews.json
slack_trustpilot_reviews.json
```

---

## 💡 Troubleshooting

* If you see `403 Forbidden`, the site is blocking automated requests.

  * Try again with **residential/backconnect proxies**.
  * Increase delay time (in script, already randomized between 3–8 seconds).
* If you get `❌ Company not found`, check the correct **slug** or company domain.
* Only first 10 pages are scraped to prevent infinite loops.
