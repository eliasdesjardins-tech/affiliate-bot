"""
🤖 Amazon Affiliate Deal Bot für Telegram
==========================================
Postet automatisch Top-Deals von Amazon.de in deinen Telegram-Kanal.
Kategorien: Tech & Gadgets, Haushalt & Alltag, Bestseller

Setup:
1. Bot Token von @BotFather holen
2. Telegram Kanal erstellen + Bot als Admin hinzufügen
3. Amazon PartnerNet ID eintragen
4. .env Datei ausfüllen
5. python bot.py starten
"""

import os
import time
import random
import logging
import json
import hashlib
from datetime import datetime, timedelta
from urllib.parse import quote_plus
import requests
from bs4 import BeautifulSoup

# ============================================
# KONFIGURATION - Nur .env Datei ausfüllen!
# ============================================

from dotenv import load_dotenv
load_dotenv()

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "DEIN_BOT_TOKEN_HIER")
TELEGRAM_CHANNEL_ID = os.getenv("TELEGRAM_CHANNEL_ID", "@dein_kanal_name")
AMAZON_AFFILIATE_TAG = os.getenv("AMAZON_AFFILIATE_TAG", "dein-tag-21")

# Posting-Einstellungen
POSTS_PER_DAY = int(os.getenv("POSTS_PER_DAY", "5"))
POST_INTERVAL_HOURS = 24 / POSTS_PER_DAY  # Gleichmäßig über den Tag verteilt
MIN_DISCOUNT_PERCENT = int(os.getenv("MIN_DISCOUNT_PERCENT", "20"))
MIN_RATING = float(os.getenv("MIN_RATING", "4.0"))

# Logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('bot.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# ============================================
# AMAZON DEAL SCRAPER
# ============================================

# Kategorien die gescraped werden
CATEGORIES = {
    "tech": {
        "name": "🔌 Tech & Gadgets",
        "urls": [
            "https://www.amazon.de/gp/bestsellers/ce-de/ref=zg_bs_nav_ce-de_0",
            "https://www.amazon.de/gp/bestsellers/computers/ref=zg_bs_nav_computers_0",
            "https://www.amazon.de/gp/movers-and-shakers/ce-de/",
        ],
        "keywords": [
            "Kopfhörer", "Ladekabel", "USB", "Bluetooth", "Lautsprecher",
            "Powerbank", "Tablet", "Maus", "Tastatur", "Kamera",
            "Smartwatch", "Handy", "Laptop", "Monitor", "SSD",
            "Festplatte", "Adapter", "Hub", "Webcam", "Mikrofon"
        ],
        "emojis": ["🎧", "📱", "💻", "🖥️", "⌨️", "🔋", "📷", "⌚", "🖱️", "🎮"]
    },
    "haushalt": {
        "name": "🏠 Haushalt & Alltag",
        "urls": [
            "https://www.amazon.de/gp/bestsellers/kitchen/ref=zg_bs_nav_kitchen_0",
            "https://www.amazon.de/gp/bestsellers/drugstore/ref=zg_bs_nav_drugstore_0",
            "https://www.amazon.de/gp/movers-and-shakers/kitchen/",
        ],
        "keywords": [
            "Küchenmaschine", "Staubsauger", "Wasserkocher", "Mixer",
            "Pfanne", "Topf", "Messer", "Luftreiniger", "Lampe",
            "Handtuch", "Bettwäsche", "Aufbewahrung", "Reiniger"
        ],
        "emojis": ["🍳", "🧹", "☕", "🔪", "💡", "🧼", "🛏️", "🏡", "🧴", "🪴"]
    },
    "bestseller": {
        "name": "🔥 Bestseller",
        "urls": [
            "https://www.amazon.de/gp/bestsellers/ref=zg_bs_unv_t_0_t_1",
            "https://www.amazon.de/gp/movers-and-shakers/ref=zg_bsms_tab",
            "https://www.amazon.de/deals/ref=gbps_ftr_s-3_4bc8_dlt_ACTIVE",
        ],
        "keywords": [],
        "emojis": ["🔥", "⭐", "💥", "🏆", "✨", "🎯", "💎", "🚀", "👑", "🎁"]
    }
}

# User-Agent Rotation
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2 Safari/605.1.15",
]

# Bereits gepostete Produkte tracken
POSTED_FILE = "posted_products.json"


def load_posted_products():
    """Lädt Liste bereits geposteter Produkte."""
    try:
        with open(POSTED_FILE, "r") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return []


def save_posted_product(product_id):
    """Speichert Produkt als gepostet."""
    posted = load_posted_products()
    posted.append({
        "id": product_id,
        "posted_at": datetime.now().isoformat()
    })
    # Nur letzte 500 behalten
    posted = posted[-500:]
    with open(POSTED_FILE, "w") as f:
        json.dump(posted, f)


def is_already_posted(product_id):
    """Prüft ob Produkt schon gepostet wurde."""
    posted = load_posted_products()
    posted_ids = [p["id"] for p in posted]
    return product_id in posted_ids


def get_headers():
    """Gibt zufällige Headers zurück."""
    return {
        "User-Agent": random.choice(USER_AGENTS),
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "de-DE,de;q=0.9,en;q=0.5",
        "Accept-Encoding": "gzip, deflate, br",
        "Connection": "keep-alive",
    }


def search_amazon_deals(keyword, category_name):
    """Sucht nach Deals auf Amazon.de für ein bestimmtes Keyword."""
    try:
        search_url = f"https://www.amazon.de/s?k={quote_plus(keyword)}&deals-widget=%257B%2522version%2522%253A1%252C%2522viewIndex%2522%253A0%252C%2522presetId%2522%253A%2522deals-collection-all-702500801%2522%257D"
        
        response = requests.get(search_url, headers=get_headers(), timeout=15)
        
        if response.status_code != 200:
            logger.warning(f"Amazon returned {response.status_code} for keyword: {keyword}")
            return []

        soup = BeautifulSoup(response.text, "html.parser")
        products = []

        # Produkt-Container finden
        items = soup.select('div[data-component-type="s-search-result"]')
        
        for item in items[:5]:  # Max 5 pro Keyword
            try:
                product = parse_product(item, category_name)
                if product and not is_already_posted(product["id"]):
                    products.append(product)
            except Exception as e:
                logger.debug(f"Error parsing product: {e}")
                continue

        return products

    except Exception as e:
        logger.error(f"Error searching Amazon for '{keyword}': {e}")
        return []


def scrape_bestseller_page(url, category_name):
    """Scraped eine Amazon Bestseller/Deals Seite."""
    try:
        response = requests.get(url, headers=get_headers(), timeout=15)
        
        if response.status_code != 200:
            logger.warning(f"Amazon returned {response.status_code} for URL: {url}")
            return []

        soup = BeautifulSoup(response.text, "html.parser")
        products = []

        # Verschiedene Selektoren für verschiedene Seitentypen
        selectors = [
            'div[data-component-type="s-search-result"]',
            'div.zg-item-immersion',
            'div.a-cardui',
            'li.zg-item-immersion',
        ]

        items = []
        for selector in selectors:
            items = soup.select(selector)
            if items:
                break

        for item in items[:10]:
            try:
                product = parse_product(item, category_name)
                if product and not is_already_posted(product["id"]):
                    products.append(product)
            except Exception as e:
                logger.debug(f"Error parsing product: {e}")
                continue

        return products

    except Exception as e:
        logger.error(f"Error scraping {url}: {e}")
        return []


def parse_product(item, category_name):
    """Parst ein einzelnes Produkt aus HTML."""
    product = {}

    # Titel
    title_el = item.select_one("h2 a span") or item.select_one(".p13n-sc-truncate") or item.select_one("a.a-link-normal span")
    if not title_el:
        return None
    product["title"] = title_el.get_text(strip=True)[:100]

    # Link / ASIN
    link_el = item.select_one("h2 a") or item.select_one("a.a-link-normal[href*='/dp/']")
    if link_el and link_el.get("href"):
        href = link_el["href"]
        # ASIN extrahieren
        if "/dp/" in href:
            asin = href.split("/dp/")[1].split("/")[0].split("?")[0]
            product["asin"] = asin
            product["id"] = asin
            product["url"] = f"https://www.amazon.de/dp/{asin}?tag={AMAZON_AFFILIATE_TAG}"
        else:
            product["id"] = hashlib.md5(product["title"].encode()).hexdigest()[:10]
            product["url"] = f"https://www.amazon.de{href}" if href.startswith("/") else href
            if "?" in product["url"]:
                product["url"] += f"&tag={AMAZON_AFFILIATE_TAG}"
            else:
                product["url"] += f"?tag={AMAZON_AFFILIATE_TAG}"
    else:
        return None

    # Preis
    price_el = item.select_one("span.a-price span.a-offscreen") or item.select_one("span.p13n-sc-price")
    if price_el:
        product["price"] = price_el.get_text(strip=True)
    else:
        product["price"] = "Preis auf Amazon checken"

    # Alter Preis (für Rabatt)
    old_price_el = item.select_one("span.a-price.a-text-price span.a-offscreen")
    if old_price_el:
        product["old_price"] = old_price_el.get_text(strip=True)
    
    # Rating
    rating_el = item.select_one("span.a-icon-alt")
    if rating_el:
        rating_text = rating_el.get_text(strip=True)
        try:
            rating = float(rating_text.split(" ")[0].replace(",", "."))
            product["rating"] = rating
            if rating < MIN_RATING:
                return None
        except ValueError:
            product["rating"] = None
    
    # Review Count
    review_el = item.select_one("span.a-size-base.s-underline-text") or item.select_one("a.a-link-normal span.a-size-base")
    if review_el:
        product["reviews"] = review_el.get_text(strip=True)

    product["category"] = category_name
    return product


def find_deals():
    """Findet die besten Deals aus allen Kategorien."""
    all_products = []
    
    for cat_key, cat_data in CATEGORIES.items():
        logger.info(f"Suche Deals in {cat_data['name']}...")
        
        # Methode 1: Keyword-Suche
        if cat_data["keywords"]:
            keywords = random.sample(cat_data["keywords"], min(3, len(cat_data["keywords"])))
            for keyword in keywords:
                products = search_amazon_deals(keyword, cat_data["name"])
                all_products.extend(products)
                time.sleep(random.uniform(2, 5))  # Anti-Bot Delay
        
        # Methode 2: Bestseller-Seiten scrapen
        for url in cat_data["urls"]:
            products = scrape_bestseller_page(url, cat_data["name"])
            all_products.extend(products)
            time.sleep(random.uniform(2, 5))
    
    # Duplikate entfernen
    seen_ids = set()
    unique_products = []
    for product in all_products:
        if product["id"] not in seen_ids:
            seen_ids.add(product["id"])
            unique_products.append(product)
    
    # Mischen für Abwechslung
    random.shuffle(unique_products)
    
    logger.info(f"Insgesamt {len(unique_products)} einzigartige Deals gefunden")
    return unique_products


# ============================================
# TELEGRAM POSTING
# ============================================

def format_deal_message(product):
    """Formatiert ein Produkt als Telegram-Nachricht."""
    
    # Emoji basierend auf Kategorie
    cat_emojis = {"🔌 Tech & Gadgets": "🔌", "🏠 Haushalt & Alltag": "🏠", "🔥 Bestseller": "🔥"}
    cat_emoji = cat_emojis.get(product["category"], "🛒")
    
    # Random Extra-Emoji
    extra_emojis = ["💰", "⚡", "🎯", "✅", "👀", "🏷️"]
    extra = random.choice(extra_emojis)
    
    # Nachricht bauen
    message = f"{cat_emoji} **{product['title']}**\n\n"
    
    # Preis-Info
    if "old_price" in product:
        message += f"~~{product['old_price']}~~ → **{product['price']}** 🔥\n"
    else:
        message += f"💰 **{product['price']}**\n"
    
    # Rating
    if product.get("rating"):
        stars = "⭐" * int(product["rating"])
        message += f"{stars} {product['rating']}/5"
        if product.get("reviews"):
            message += f" ({product['reviews']} Bewertungen)"
        message += "\n"
    
    message += f"\n{extra} **Zum Deal:** {product['url']}\n"
    message += f"\n_{product['category']}_"
    
    return message


def send_telegram_message(text):
    """Sendet eine Nachricht an den Telegram-Kanal."""
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    
    payload = {
        "chat_id": TELEGRAM_CHANNEL_ID,
        "text": text,
        "parse_mode": "Markdown",
        "disable_web_page_preview": False,
    }
    
    try:
        response = requests.post(url, json=payload, timeout=10)
        result = response.json()
        
        if result.get("ok"):
            logger.info("✅ Nachricht erfolgreich gepostet!")
            return True
        else:
            logger.error(f"❌ Telegram Error: {result.get('description', 'Unknown error')}")
            return False
    except Exception as e:
        logger.error(f"❌ Error sending Telegram message: {e}")
        return False


def send_daily_summary():
    """Sendet eine tägliche Zusammenfassung."""
    posted = load_posted_products()
    today = datetime.now().date().isoformat()
    today_count = sum(1 for p in posted if p["posted_at"].startswith(today))
    
    message = (
        f"📊 **Tages-Update**\n\n"
        f"Heute gepostet: {today_count} Deals\n"
        f"Gesamt gepostet: {len(posted)} Deals\n\n"
        f"💡 _Neue Deals kommen morgen automatisch!_"
    )
    send_telegram_message(message)


# ============================================
# TELEGRAM BOT COMMANDS
# ============================================

def handle_bot_commands():
    """Prüft auf neue Bot-Befehle (optional, für Admin-Kontrolle)."""
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/getUpdates"
    
    try:
        response = requests.get(url, params={"timeout": 5, "limit": 10}, timeout=10)
        result = response.json()
        
        if not result.get("ok"):
            return
        
        for update in result.get("result", []):
            message = update.get("message", {})
            text = message.get("text", "")
            chat_id = message.get("chat", {}).get("id")
            
            if text == "/status":
                posted = load_posted_products()
                status_msg = f"🤖 Bot läuft!\n📦 {len(posted)} Deals gepostet\n⏰ Nächster Post in ~{POST_INTERVAL_HOURS:.1f}h"
                requests.post(
                    f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage",
                    json={"chat_id": chat_id, "text": status_msg}
                )
            
            elif text == "/post":
                deals = find_deals()
                if deals:
                    deal = deals[0]
                    msg = format_deal_message(deal)
                    if send_telegram_message(msg):
                        save_posted_product(deal["id"])
                        requests.post(
                            f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage",
                            json={"chat_id": chat_id, "text": "✅ Deal manuell gepostet!"}
                        )
            
            # Update ID bestätigen
            requests.get(url, params={"offset": update["update_id"] + 1})
    
    except Exception as e:
        logger.debug(f"Command check error: {e}")


# ============================================
# HAUPTPROGRAMM
# ============================================

def run_bot():
    """Hauptschleife - läuft 24/7 und postet automatisch."""
    
    logger.info("=" * 50)
    logger.info("🤖 Amazon Affiliate Bot gestartet!")
    logger.info(f"📢 Kanal: {TELEGRAM_CHANNEL_ID}")
    logger.info(f"🏷️ Affiliate Tag: {AMAZON_AFFILIATE_TAG}")
    logger.info(f"📮 Posts pro Tag: {POSTS_PER_DAY}")
    logger.info(f"⏰ Interval: alle {POST_INTERVAL_HOURS:.1f} Stunden")
    logger.info("=" * 50)
    
    # Startmeldung senden
    send_telegram_message(
        "🤖 **Affiliate Deal Bot ist online!**\n\n"
        f"Ich poste ab jetzt {POSTS_PER_DAY}x täglich die besten Amazon Deals.\n\n"
        "Befehle:\n"
        "/status - Bot-Status\n"
        "/post - Deal sofort posten"
    )
    
    post_count_today = 0
    last_post_time = None
    last_summary_date = None
    
    while True:
        try:
            now = datetime.now()
            
            # Bot-Befehle checken (alle 30 Sekunden)
            handle_bot_commands()
            
            # Tages-Reset
            if last_post_time and now.date() > last_post_time.date():
                post_count_today = 0
                logger.info("📅 Neuer Tag - Counter zurückgesetzt")
            
            # Posten wenn Zeit dafür
            should_post = False
            if last_post_time is None:
                should_post = True
            elif (now - last_post_time).total_seconds() >= POST_INTERVAL_HOURS * 3600:
                should_post = True
            
            if should_post and post_count_today < POSTS_PER_DAY:
                # Nur zwischen 8:00 und 22:00 posten
                if 8 <= now.hour <= 22:
                    logger.info(f"🔍 Suche nach Deals... (Post {post_count_today + 1}/{POSTS_PER_DAY})")
                    
                    deals = find_deals()
                    
                    if deals:
                        deal = random.choice(deals[:5])  # Aus Top 5 zufällig wählen
                        message = format_deal_message(deal)
                        
                        if send_telegram_message(message):
                            save_posted_product(deal["id"])
                            post_count_today += 1
                            last_post_time = now
                            logger.info(f"✅ Deal gepostet: {deal['title'][:50]}...")
                        else:
                            logger.warning("⚠️ Konnte Deal nicht posten, versuche später erneut")
                    else:
                        logger.warning("⚠️ Keine neuen Deals gefunden")
                        last_post_time = now  # Trotzdem Timer setzen
                else:
                    logger.info(f"🌙 Außerhalb der Posting-Zeit ({now.hour}:00)")
            
            # Tages-Zusammenfassung um 22:00
            if now.hour == 22 and last_summary_date != now.date():
                send_daily_summary()
                last_summary_date = now.date()
            
            # 30 Sekunden warten
            time.sleep(30)
            
        except KeyboardInterrupt:
            logger.info("🛑 Bot gestoppt!")
            send_telegram_message("🛑 Bot wurde gestoppt. Bis bald!")
            break
        except Exception as e:
            logger.error(f"❌ Unerwarteter Fehler: {e}")
            time.sleep(60)  # 1 Minute warten bei Fehler


if __name__ == "__main__":
    # Prüfe ob Konfiguration gesetzt ist
    if TELEGRAM_BOT_TOKEN == "DEIN_BOT_TOKEN_HIER":
        print("\n⚠️  SETUP NÖTIG!")
        print("=" * 40)
        print("1. Kopiere .env.example zu .env")
        print("2. Fülle die Werte aus")
        print("3. Starte den Bot erneut")
        print("=" * 40)
    else:
        run_bot()
