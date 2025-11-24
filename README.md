# LinuxConfig SEO Toolkit

Modular SEO monitoring toolkit for LinuxConfig.org. Currently includes **Core Article Tracker** that identifies top performing articles and alerts you when they need updates.

## What It Does

**Core Article Tracker:**
- Finds your top 30 articles (by traffic + rankings)
- Tracks performance bi-weekly
- Alerts when articles need updating
- Combines data from: Google Analytics, Search Console, WordPress, Yoast SEO

**Alerts:**
- 🔴 Not updated in 12+ months (critical)
- 🟡 Not updated in 6+ months (warning)
- 🟡 Missing focus keywords
- 🟡 Rankings dropped
- 🟡 Traffic declined >20%

---

## Quick Start

### 1. Setup (One-Time)

```bash
# Extract the toolkit
tar -xzf linuxconfig-toolkit.tar.gz
cd linuxconfig-toolkit

# Copy your Google API credentials
mkdir -p shared/config/credentials
cp /home/tux/Downloads/linuxconfig-org-ed3c209ed133.json shared/config/credentials/
cp /home/tux/Downloads/token.json shared/config/credentials/

# Build the toolkit
docker-compose build

# Start the database
docker-compose up -d mariadb

# Wait 10 seconds for database to initialize
sleep 10
```

### 2. Run Your First Snapshot

```bash
docker-compose run --rm script-runner python scripts/core-article-tracker/main.py
```

**Output:**
- Console shows top 10 articles + alerts
- CSV report saved to `data/reports/core_articles_YYYY-MM-DD.csv`

### 3. View Results

```bash
# See the CSV report
ls -lh data/reports/

# Open in spreadsheet or:
cat data/reports/core_articles_*.csv | column -t -s, | less -S
```

---

## Bi-Weekly Usage

Run every 2 weeks to track trends:

```bash
docker-compose run --rm script-runner python scripts/core-article-tracker/main.py
```

**What happens:**
- Compares with previous run
- Shows which articles improved/declined
- Generates alerts for articles needing attention
- Saves new snapshot

---

## Understanding the CSV Report

Each row = one article, sorted by importance (rank 1-30)

**Key columns:**
- `Rank` - Position in top 30
- `Page Path` - Article URL path
- `Days Since Update` - Last modified
- `Pageviews (90d)` - Traffic
- `Avg Position` - Google search ranking
- `Focus Keyword` - From Yoast SEO
- `Alerts` - What needs attention

**Use it to:**
1. Find articles that haven't been updated in 6+ months
2. See which top articles are missing focus keywords
3. Identify articles with declining traffic/rankings
4. Prioritize your Monday maintenance tasks

---

## Database Queries

Connect to see historical data:

```bash
docker-compose exec mariadb mysql -u toolkit_user -ptoolkit_pass_2024! linuxconfig_toolkit
```

**Useful queries:**

```sql
-- All snapshots
SELECT snapshot_date, COUNT(*) as articles 
FROM core_articles_snapshots 
GROUP BY snapshot_date;

-- Articles needing updates
SELECT page_path, wp_days_since_update, yoast_focus_keyword
FROM core_articles_snapshots 
WHERE snapshot_date = CURDATE() 
  AND wp_days_since_update > 180
ORDER BY wp_days_since_update DESC;

-- Today's critical alerts
SELECT page_path, alert_message 
FROM core_articles_alerts 
WHERE snapshot_date = CURDATE() 
  AND alert_severity = 'critical';
```

---

## Maintenance

### Backup Database

```bash
docker-compose exec mariadb mysqldump -u toolkit_user -ptoolkit_pass_2024! linuxconfig_toolkit > backup.sql
```

### Stop Services

```bash
docker-compose down
```

### Restart

```bash
docker-compose up -d mariadb
```

---

## Troubleshooting

**Can't connect to WordPress staging:**
```bash
# Test connection
docker-compose run --rm script-runner python -c "
import MySQLdb
conn = MySQLdb.connect(host='192.168.100.3', port=3306, user='wpuser', passwd='wp2024secure!', db='wplinuxconfig')
print('✓ Connected')
conn.close()
"
```

**Google API errors:**
```bash
# Check credentials exist
ls -lh shared/config/credentials/

# Fix permissions
chmod 600 shared/config/credentials/*.json
```

**Database issues:**
```bash
# View logs
docker-compose logs mariadb

# Restart database
docker-compose restart mariadb
```

---

## Adding More Scripts

The toolkit is designed for easy expansion:

```bash
# Create new script directory
mkdir -p scripts/keyword-tracker

# Add your script
nano scripts/keyword-tracker/main.py

# Run it
docker-compose run --rm script-runner python scripts/keyword-tracker/main.py
```

All scripts share:
- Same database (MariaDB)
- Same libraries (in `shared/lib/`)
- Same credentials
- Same Docker environment

---

## Architecture

```
linuxconfig-toolkit/
├── scripts/
│   └── core-article-tracker/     # Current script
│       └── main.py
│   └── [future-scripts]/         # Add more here
│
├── shared/
│   ├── lib/                       # Shared code
│   │   ├── db.py                 # Database connections
│   │   ├── wp.py                 # WordPress helpers
│   │   └── google_apis.py        # GA/GSC helpers
│   └── config/
│       ├── credentials/           # Your API keys (not in git)
│       └── init.sql              # Database schema
│
└── data/
    ├── databases/                 # MariaDB data (persistent)
    └── reports/                   # CSV outputs
```

---

## Configuration

**WordPress Connection:** Edit `docker-compose.yml`
```yaml
environment:
  WP_DB_HOST: 192.168.100.3
  WP_DB_PASSWORD: wp2024secure!
```

**Alert Thresholds:** Edit `scripts/core-article-tracker/main.py`
```python
# Line ~230
if article['days_since_update'] >= 180:  # 6 months warning
if article['days_since_update'] >= 365:  # 12 months critical
```

---

## Questions?

- Toolkit design: Check `shared/lib/` for reusable code
- Database schema: See `shared/config/init.sql`
- Full details: See `DEPLOYMENT_SUMMARY.md`
