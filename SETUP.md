# 🤖 Amazon Affiliate Deal Bot - Setup Guide

## Was der Bot macht:
- Findet automatisch Top-Deals auf Amazon.de
- Postet 5x täglich in deinen Telegram-Kanal
- Fügt deinen Affiliate-Link ein → du verdienst bei jedem Kauf
- Kategorien: Tech, Haushalt, Bestseller
- Läuft 24/7 ohne dass du was machen musst

---

## Setup in 4 Schritten (ca. 30 Minuten)

### Schritt 1: Telegram Bot erstellen (5 Min)
1. Öffne Telegram → suche **@BotFather**
2. Schreib `/newbot`
3. Wähle einen Namen (z.B. "Top Deals Deutschland")
4. Wähle einen Username (z.B. `TopDealsDE_bot`)
5. **Kopiere den Bot Token** → sieht so aus: `7123456789:AAH...`

### Schritt 2: Telegram Kanal erstellen (5 Min)
1. Telegram → Neuer Kanal erstellen
2. Name: z.B. "🔥 Top Deals Deutschland"
3. **Öffentlich** machen → Username wählen (z.B. `@TopDealsDeutschland`)
4. Bot als **Admin** zum Kanal hinzufügen (wichtig!)

### Schritt 3: Amazon PartnerNet (10 Min)
1. Geh zu: **partnernet.amazon.de**
2. Account erstellen (mit deinem Amazon-Konto)
3. Website/App angeben → deinen Telegram-Kanal Link
4. Deine **Tracking-ID** kopieren (z.B. `meinkanal-21`)

### Schritt 4: Bot starten (10 Min)

**Option A: Lokal (zum Testen)**
```bash
cd affiliate-bot
cp .env.example .env
# .env Datei mit deinen Daten ausfüllen
pip install -r requirements.txt
python bot.py
```

**Option B: Kostenlos auf Railway.app (24/7)**
1. Geh zu **railway.app** → GitHub Login
2. "New Project" → "Deploy from GitHub"
3. Repo hochladen oder manuell deployen
4. Environment Variables setzen:
   - `TELEGRAM_BOT_TOKEN` = dein Token
   - `TELEGRAM_CHANNEL_ID` = @dein_kanal
   - `AMAZON_AFFILIATE_TAG` = dein-tag-21
5. Deploy → Bot läuft 24/7!

---

## Bot-Befehle
- `/status` - Zeigt ob Bot läuft und wie viele Deals gepostet
- `/post` - Postet sofort einen Deal manuell

## Einnahmen-Erwartung
- **Monat 1:** 0-20€ (Kanal wächst)
- **Monat 2-3:** 20-100€ (mehr Follower)  
- **Monat 6+:** 100-500€ (wenn Kanal wächst)

## Tipps zum Kanal wachsen lassen
1. Teile den Kanal in deutschen Deal-Gruppen
2. Poste den Link auf Reddit (r/de_deals, r/Sparfuechse)
3. Erstelle eine Instagram-Seite die auf den Kanal verlinkt
4. Je mehr Follower, desto mehr kaufen über deine Links
