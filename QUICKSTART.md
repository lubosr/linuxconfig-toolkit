# Quick Start Guide

## First Time Setup (5 minutes)

### 1. Copy credentials
```bash
cd linuxconfig-toolkit

# Copy your Google credentials
cp /home/tux/Downloads/linuxconfig-org-ed3c209ed133.json shared/config/credentials/
cp /home/tux/Downloads/token.json shared/config/credentials/

# Verify files are there
ls -la shared/config/credentials/
```

### 2. Build and start database
```bash
# Build the Docker images
docker-compose build

# Start MariaDB (will create schema automatically)
docker-compose up -d mariadb

# Check it's running
docker-compose ps
```

### 3. Run your first tracker
```bash
# Execute the core article tracker
docker-compose run --rm script-runner python scripts/core-article-tracker/main.py
```

## What happens on first run?

1. ✅ Connects to Google Analytics (last 90 days)
2. ✅ Connects to Search Console (last 90 days)
3. ✅ Connects to WordPress staging DB
4. ✅ Pulls Yoast SEO data
5. ✅ Calculates composite scores
6. ✅ Saves snapshot to toolkit database
7. ✅ Generates CSV report
8. ⚠️ No trend alerts (needs 2nd run for comparison)

## Expected output:

```
================================================================================
LinuxConfig Core Article Tracker - Enhanced Version
================================================================================
Snapshot Date: 2025-11-24
Date Range: Last 90 days

✓ Run ID: 1

📊 Fetching Google Analytics data...
✓ Retrieved 95 pages from Analytics

🔍 Fetching Search Console data...
✓ Retrieved 87 pages from Search Console

🧮 Calculating composite scores...
✓ Scored 112 total pages

📝 Fetching WordPress metadata...
✓ Retrieved metadata for 30 posts

💾 Saving snapshot to database...
✓ Saved 30 articles to snapshot

🚨 Generating alerts...
✓ Generated 15 alerts

💾 Saving alerts to database...
✓ Saved 15 alerts

================================================================================
📊 TOP 30 CORE ARTICLES REPORT
================================================================================
[Table showing top 10 articles]

💾 CSV Report saved: /app/reports/core_articles_2025-11-24.csv

================================================================================
✅ COMPLETE
================================================================================
```

## View the report:

```bash
# On your host machine
ls -lh data/reports/

# Open with Excel or:
cat data/reports/core_articles_2025-11-24.csv | column -t -s, | less -S
```

## Run again in 2 weeks:

Second run will include trend analysis:
- 📈 Rankings up/down
- 📊 Traffic changes
- 🆕 New top 30 entrants
- 📉 Articles dropped from top 30

## Need help?

```bash
# Check logs
docker-compose logs script-runner

# Connect to database
docker-compose exec mariadb mysql -u toolkit_user -ptoolkit_pass_2024! linuxconfig_toolkit

# Restart from scratch
docker-compose down -v
docker-compose up -d mariadb
```

## Common first-run issues:

**"Can't connect to WordPress DB"**
→ Check staging server is running and port 3306 is accessible

**"Google API authentication failed"**
→ Verify credential files are in `shared/config/credentials/`

**"Module not found"**
→ Rebuild: `docker-compose build --no-cache`
