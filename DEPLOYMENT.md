# LinuxConfig Toolkit - Deployment Checklist

## ✅ What's Been Created

### Core Structure
- [x] Docker Compose configuration with MariaDB
- [x] Python script runner environment
- [x] Modular directory structure for future scripts
- [x] Database schema with 3 tables (snapshots, alerts, runs)
- [x] Shared libraries (db, WordPress, Google APIs)

### Core Article Tracker Script
- [x] Fetches GA data (pageviews, sessions, duration)
- [x] Fetches GSC data (clicks, impressions, CTR, position)
- [x] Pulls WordPress post metadata (last modified)
- [x] Pulls Yoast SEO data (focus keywords, scores)
- [x] Calculates composite scores
- [x] Stores bi-weekly snapshots
- [x] Compares with previous run
- [x] Generates 10+ alert types
- [x] Outputs CSV reports

### Documentation
- [x] Comprehensive README
- [x] Quick start guide
- [x] .gitignore for credentials

## 📋 Before First Run

### 1. Copy credentials to server
```bash
scp -r linuxconfig-toolkit/ user@your-server:/path/to/
```

### 2. Add your credentials
```bash
cd linuxconfig-toolkit
cp /home/tux/Downloads/linuxconfig-org-ed3c209ed133.json shared/config/credentials/
cp /home/tux/Downloads/token.json shared/config/credentials/
```

### 3. Verify WordPress DB access
```bash
mysql -h 192.168.100.3 -P 3306 -u wpuser -pwp2024secure! wplinuxconfig -e "SELECT COUNT(*) FROM wp_posts WHERE post_type='post' AND post_status='publish';"
```

Should show ~30,000+ published posts.

### 4. Build and start
```bash
docker-compose build
docker-compose up -d mariadb
```

## 🚀 First Execution

```bash
docker-compose run --rm script-runner python scripts/core-article-tracker/main.py
```

**Expected duration:** 2-3 minutes

**What you'll get:**
- Console output with top 10 articles
- CSV report in `data/reports/core_articles_YYYY-MM-DD.csv`
- 30 articles saved to database
- Alerts for stale content, missing keywords, etc.

## 📊 Review Results

### Console
Shows top 10 articles with:
- Rank, Title, Score, Views, Clicks, Position, Age, Focus Keyword

### CSV Report
Open in Excel/LibreOffice with columns:
- All metrics from GA/GSC
- WordPress metadata
- Yoast SEO data
- Generated alerts

### Database
```bash
docker-compose exec mariadb mysql -u toolkit_user -ptoolkit_pass_2024! linuxconfig_toolkit

# View snapshot
SELECT rank_position, page_path, composite_score, ga_pageviews 
FROM core_articles_snapshots 
WHERE snapshot_date = CURDATE() 
ORDER BY rank_position LIMIT 10;

# View alerts
SELECT alert_severity, page_path, alert_message 
FROM core_articles_alerts 
WHERE snapshot_date = CURDATE() 
ORDER BY FIELD(alert_severity, 'critical', 'warning', 'info');
```

## 🔄 Bi-Weekly Workflow

**Every 2 weeks:**

1. **Run tracker**
   ```bash
   docker-compose run --rm script-runner python scripts/core-article-tracker/main.py
   ```

2. **Review alerts**
   - 🔴 Critical: Address immediately (traffic drops, dropped from top 30)
   - 🟡 Warning: Schedule updates (stale content 6+ months)
   - 🔵 Info: Monitor trends

3. **Take action**
   - Update stale articles (6+ months old)
   - Set missing focus keywords in Yoast
   - Investigate ranking/traffic declines
   - Celebrate improvements!

4. **Track progress**
   - Next run will show before/after comparison
   - CSV includes historical context

## 🎯 Success Metrics

After 3-4 bi-weekly runs (6-8 weeks), you should see:
- [ ] Reduced "stale content" alerts
- [ ] Fewer articles without focus keywords
- [ ] Trend data showing improvements
- [ ] Clear picture of top 30 stability

## 🔮 Future Additions

Ready to add more scripts:

```bash
# Example: Keyword tracker
mkdir -p scripts/keyword-tracker
nano scripts/keyword-tracker/main.py

# Run it
docker-compose run --rm script-runner python scripts/keyword-tracker/main.py
```

All scripts share:
- Database connection
- WordPress access  
- Google APIs
- Common utilities

## 📞 Support

**Issues?**
1. Check logs: `docker-compose logs script-runner`
2. Verify credentials in `shared/config/credentials/`
3. Test WP DB: `mysql -h 192.168.100.3 ...`
4. Rebuild: `docker-compose build --no-cache`

**Need modifications?**
- Adjust scoring weights in `shared/lib/google_apis.py`
- Add/remove alerts in `scripts/core-article-tracker/main.py`
- Customize thresholds (6 months → 3 months, etc.)

## 🎉 You're Ready!

The LinuxConfig SEO Toolkit is set up and ready to use. Run it bi-weekly to maintain your core articles and watch your rankings improve!
