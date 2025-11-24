#!/usr/bin/env python3
"""
LinuxConfig.org - Attention Finder
Identifies articles outside top 30 that need attention
Prioritizes by potential impact and provides actionable recommendations
"""
import os
import sys
from datetime import datetime, date
from tabulate import tabulate

# Add parent directory to path for shared imports
sys.path.insert(0, '/app')

from shared.lib.db import DatabaseConnection, execute_query, execute_insert
from shared.lib.wp import get_post_metadata, extract_post_name_from_path
from shared.lib.google_apis import (
    get_analytics_data,
    get_search_console_data,
    calculate_composite_score
)


class AttentionFinder:
    """Finds and prioritizes articles needing attention"""

    def __init__(self):
        self.snapshot_date = date.today()
        self.run_id = None
        self.top_30_paths = set()
        self.attention_articles = []

    def start_run(self):
        """Record script run start"""
        print("=" * 80)
        print("LinuxConfig.org - Attention Finder")
        print("=" * 80)
        print(f"Analysis Date: {self.snapshot_date}")
        print(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print()

        with DatabaseConnection.get_toolkit_connection() as conn:
            self.run_id = execute_insert(
                conn,
                """INSERT INTO toolkit_runs
                   (script_name, status, run_date)
                   VALUES (%s, %s, NOW())""",
                ('attention-finder', 'started')
            )

    def get_current_top_30(self):
        """Get current top 30 articles to exclude them"""
        print("📊 Getting current top 30 articles...")

        with DatabaseConnection.get_toolkit_connection() as conn:
            top_30 = execute_query(
                conn,
                """SELECT page_path FROM core_articles_snapshots
                   WHERE snapshot_date = (
                       SELECT MAX(snapshot_date) FROM core_articles_snapshots
                   )
                   ORDER BY rank_position LIMIT 30"""
            )

        self.top_30_paths = {row['page_path'] for row in top_30}
        print(f"✓ Excluding {len(self.top_30_paths)} top articles from analysis")

    def fetch_all_articles(self):
        """Fetch ALL articles from Google APIs"""
        print("\n📊 Fetching ALL articles from Google Analytics...")
        ga_data = get_analytics_data(days=90, limit=500)  # Get more articles
        print(f"✓ Retrieved {len(ga_data)} pages from Analytics")

        print("\n🔍 Fetching ALL articles from Search Console...")
        sc_data = get_search_console_data(days=90, limit=500)
        print(f"✓ Retrieved {len(sc_data)} pages from Search Console")

        return ga_data, sc_data

    def get_historical_data(self, page_paths):
        """Get historical data for traffic decline detection"""
        print("\n📈 Fetching historical data...")

        if not page_paths:
            return {}

        with DatabaseConnection.get_toolkit_connection() as conn:
            # Get data from 90 days ago (previous snapshot)
            placeholders = ','.join(['%s'] * len(page_paths))
            query = f"""
                SELECT
                    page_path,
                    ga_pageviews,
                    gsc_position,
                    rank_position
                FROM core_articles_snapshots
                WHERE snapshot_date = (
                    SELECT snapshot_date
                    FROM core_articles_snapshots
                    WHERE snapshot_date < CURDATE()
                    ORDER BY snapshot_date DESC
                    LIMIT 1
                )
                AND page_path IN ({placeholders})
            """

            results = execute_query(conn, query, tuple(page_paths))

        historical = {}
        for row in results:
            historical[row['page_path']] = {
                'old_pageviews': row['ga_pageviews'],
                'old_position': row['gsc_position'],
                'was_top_30': row['rank_position'] <= 30 if row['rank_position'] else False
            }

        print(f"✓ Retrieved historical data for {len(historical)} articles")
        return historical

    def calculate_priority_score(self, article, wp_data, historical_data):
        """
        Calculate priority score (0-130 points)
        Higher score = more urgent attention needed
        """
        score = 0
        issues = []
        actions = []

        # 1. SEO FUNDAMENTALS (0-30 pts)
        if not wp_data.get('focus_keyword'):
            score -= 20
            issues.append("Missing focus keyword")
            actions.append("Add focus keyword in Yoast SEO")
        else:
            score += 10

        days_old = wp_data.get('days_since_update', 0)
        if days_old > 365:
            score -= 15
            issues.append(f"Not updated in {days_old} days")
            actions.append("Content refresh urgently needed - article over 1 year old")
        elif days_old > 180:
            score -= 10
            issues.append(f"Not updated in {days_old} days")
            actions.append("Schedule content update - approaching 6 months")
        elif days_old < 180:
            score += 5

        # 2. RANKING OPPORTUNITY (0-40 pts)
        position = article.get('position', 999)
        if 4 <= position <= 10:
            score += 40
            issues.append(f"Position {position:.1f} - near page 1 top")
            actions.append("Quick push to top 3 positions - optimize title and add internal links")
        elif 11 <= position <= 20:
            score += 25
            issues.append(f"Position {position:.1f} - page 2")
            actions.append("Target page 1 - improve content depth and backlinks")
        elif 21 <= position <= 30:
            score += 10
            issues.append(f"Position {position:.1f}")
            actions.append("Long-term optimization - expand content and target related keywords")

        # 3. TRAFFIC POTENTIAL (0-30 pts)
        impressions = article.get('impressions', 0)
        ctr = article.get('ctr', 0) * 100  # Convert to percentage

        if impressions > 10000 and ctr < 2:
            score += 30
            issues.append(f"{impressions} impressions but {ctr:.1f}% CTR")
            actions.append("Improve title and meta description - high visibility, low clicks")
        elif impressions > 5000 and ctr < 2:
            score += 20
            issues.append(f"{impressions} impressions, {ctr:.1f}% CTR")
            actions.append("Optimize title for better CTR - good impressions, needs improvement")
        elif impressions > 5000:
            score += 10

        # 4. HISTORICAL PERFORMANCE (0-20 pts)
        if historical_data:
            if historical_data.get('was_top_30'):
                score += 20
                issues.append("Was in top 30, now dropped")
                actions.append("Priority recovery - proven winner that declined")

            old_views = historical_data.get('old_pageviews', 0)
            current_views = article.get('pageviews', 0)

            if old_views > 0:
                decline_pct = ((old_views - current_views) / old_views) * 100
                if decline_pct > 50:
                    score += 15
                    issues.append(f"Traffic declined {decline_pct:.0f}%")
                    actions.append(f"Investigate decline - lost {decline_pct:.0f}% traffic")
                elif decline_pct > 20:
                    score += 10
                    issues.append(f"Traffic declined {decline_pct:.0f}%")
                    actions.append("Monitor closely - showing traffic decline")
                elif decline_pct < -20:  # Growing
                    score += 5
                    issues.append(f"Traffic growing {abs(decline_pct):.0f}%")
                    actions.append("Capitalize on growth - optimize to accelerate")

            # Position changes
            old_pos = historical_data.get('old_position', 999)
            if old_pos < 999 and position < 999:
                pos_change = position - old_pos
                if pos_change < -5:  # Improving
                    score += 10
                    issues.append(f"Position improving (was {old_pos:.0f})")
                    actions.append("Momentum detected - continue optimization")
                elif pos_change > 5:  # Declining
                    issues.append(f"Position declining (was {old_pos:.0f})")
                    actions.append("Stop the decline - investigate ranking drop")

        # 5. READABILITY (bonus/penalty)
        readability = wp_data.get('readability_score', 0)
        if readability > 0 and readability < 60:
            score -= 5
            issues.append(f"Low readability ({readability})")
            actions.append("Improve readability - simplify content structure")

        return max(0, score), issues, actions

    def analyze_articles(self, ga_data, sc_data):
        """Analyze all articles and calculate priorities"""
        print("\n🧮 Analyzing articles and calculating priority scores...")

        # Combine GA and SC data
        all_pages = set(list(ga_data.keys()) + list(sc_data.keys()))

        # Exclude top 30
        pages_to_analyze = all_pages - self.top_30_paths
        print(f"✓ Analyzing {len(pages_to_analyze)} articles (excluding top 30)")

        # Get post names for WordPress lookup
        post_names = []
        for page_path in pages_to_analyze:
            post_name = extract_post_name_from_path(page_path)
            if post_name:
                post_names.append(post_name)

        # Fetch WordPress metadata
        print(f"📝 Fetching WordPress data for {len(post_names)} articles...")
        wp_metadata = get_post_metadata(post_names)

        # Get historical data
        historical_data = self.get_historical_data(list(pages_to_analyze))

        # Analyze each article
        analyzed = []
        for page_path in pages_to_analyze:
            post_name = extract_post_name_from_path(page_path)

            ga = ga_data.get(page_path, {})
            sc = sc_data.get(page_path, {})
            wp = wp_metadata.get(post_name, {})
            hist = historical_data.get(page_path, {})

            # Skip if no meaningful data
            if not ga and not sc:
                continue

            article_data = {
                'page_path': page_path,
                'post_name': post_name,
                'post_id': wp.get('post_id'),
                'post_title': wp.get('post_title', 'Unknown'),
                'pageviews': ga.get('pageviews', 0),
                'sessions': ga.get('sessions', 0),
                'clicks': sc.get('clicks', 0),
                'impressions': sc.get('impressions', 0),
                'ctr': sc.get('ctr', 0),
                'position': sc.get('position', 999),
                'days_since_update': wp.get('days_since_update', 0),
                'focus_keyword': wp.get('focus_keyword'),
                'readability_score': wp.get('readability_score', 0)
            }

            # Calculate priority score
            score, issues, actions = self.calculate_priority_score(
                article_data, wp, hist
            )

            # Only include if score > 20 (minimum threshold)
            if score > 20:
                article_data['priority_score'] = score
                article_data['issues'] = issues
                article_data['actions'] = actions
                analyzed.append(article_data)

        # Sort by priority score
        analyzed.sort(key=lambda x: x['priority_score'], reverse=True)

        self.attention_articles = analyzed[:50]  # Top 50
        print(f"✓ Found {len(analyzed)} articles needing attention (showing top 50)")

        return self.attention_articles

    def generate_report(self):
        """Generate console and CSV reports"""
        print("\n" + "=" * 80)
        print("🎯 ATTENTION NEEDED ARTICLES (Beyond Top 30)")
        print("=" * 80)

        if not self.attention_articles:
            print("\n✅ No articles need urgent attention!")
            return

        # Categorize by priority
        critical = [a for a in self.attention_articles if a['priority_score'] >= 80]
        high = [a for a in self.attention_articles if 50 <= a['priority_score'] < 80]
        medium = [a for a in self.attention_articles if 20 <= a['priority_score'] < 50]

        print(f"\nFound {len(self.attention_articles)} articles analyzed")
        print(f"  🔴 Critical: {len(critical)}")
        print(f"  🟡 High Priority: {len(high)}")
        print(f"  🟢 Medium Priority: {len(medium)}")

        # Show critical articles in detail
        if critical:
            print("\n" + "=" * 80)
            print("🔴 CRITICAL - Act This Week")
            print("=" * 80)

            for i, article in enumerate(critical, 1):
                dev_url = f"https://dev.linuxconfig.org{article['page_path']}"
                print(f"\n{i}. [Score: {article['priority_score']:.0f}] ID:{article['post_id']} {article['post_title'][:60]}")
                print(f"   URL: {dev_url}")
                print(f"   Metrics: {article['pageviews']} views, {article['clicks']} clicks, Pos {article['position']:.1f}")
                print(f"   Issues: {'; '.join(article['issues'])}")
                print(f"   Actions:")
                for action in article['actions']:
                    print(f"     → {action}")

        # Show high priority in table
        if high:
            print("\n" + "=" * 80)
            print("🟡 HIGH PRIORITY - Next 2 Weeks")
            print("=" * 80 + "\n")

            table_data = []
            for article in high[:10]:  # Top 10 high priority
                table_data.append([
                    f"{article['priority_score']:.0f}",
                    article['post_id'] or 'N/A',
                    article['post_title'][:40],
                    article['pageviews'],
                    article['clicks'],
                    f"{article['position']:.1f}",
                    article['days_since_update'] or 'N/A'
                ])

            print(tabulate(
                table_data,
                headers=['Score', 'ID', 'Title', 'Views', 'Clicks', 'Pos', 'Days'],
                tablefmt='simple'
            ))

            if len(high) > 10:
                print(f"\n   ... and {len(high) - 10} more (see CSV)")

        # Show medium priority summary
        if medium:
            print(f"\n🟢 MEDIUM PRIORITY: {len(medium)} articles (see CSV for details)")

        # Save CSV
        self.save_csv_report()

    def save_csv_report(self):
        """Save detailed CSV report"""
        import csv

        output_file = f'/app/reports/attention_needed_{self.snapshot_date}.csv'

        with open(output_file, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow([
                'Priority Score', 'Category', 'Post ID', 'Post Title', 'Dev URL',
                'Pageviews (90d)', 'Clicks (90d)', 'Impressions', 'CTR %',
                'Avg Position', 'Days Since Update', 'Focus Keyword',
                'Readability', 'Issues', 'Recommended Actions'
            ])

            for article in self.attention_articles:
                dev_url = f"https://dev.linuxconfig.org{article['page_path']}"

                # Categorize
                score = article['priority_score']
                if score >= 80:
                    category = 'CRITICAL'
                elif score >= 50:
                    category = 'HIGH'
                else:
                    category = 'MEDIUM'

                writer.writerow([
                    f"{article['priority_score']:.0f}",
                    category,
                    article['post_id'] or '',
                    article['post_title'],
                    dev_url,
                    article['pageviews'],
                    article['clicks'],
                    article['impressions'],
                    f"{article['ctr'] * 100:.2f}",
                    f"{article['position']:.1f}",
                    article['days_since_update'],
                    article['focus_keyword'] or 'MISSING',
                    article['readability_score'],
                    '; '.join(article['issues']),
                    ' | '.join(article['actions'])
                ])

        print(f"\n✓ CSV report saved: {output_file}")

    def complete_run(self, success=True):
        """Mark run as completed"""
        status = 'completed' if success else 'failed'

        with DatabaseConnection.get_toolkit_connection() as conn:
            execute_insert(
                conn,
                """UPDATE toolkit_runs
                   SET status = %s,
                       records_processed = %s,
                       execution_time_seconds = TIMESTAMPDIFF(SECOND, run_date, NOW())
                   WHERE id = %s""",
                (status, len(self.attention_articles), self.run_id)
            )

        print("\n" + "=" * 80)
        print(f"✅ Analysis completed!" if success else "❌ Analysis failed")
        print("=" * 80)


def main():
    """Main execution"""
    finder = AttentionFinder()

    try:
        # Start
        finder.start_run()

        # Get current top 30 to exclude
        finder.get_current_top_30()

        # Fetch all articles
        ga_data, sc_data = finder.fetch_all_articles()

        if not ga_data and not sc_data:
            print("\n❌ Failed to retrieve data from Google APIs")
            finder.complete_run(success=False)
            return

        # Analyze and prioritize
        finder.analyze_articles(ga_data, sc_data)

        # Generate reports
        finder.generate_report()

        # Complete
        finder.complete_run(success=True)

    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        finder.complete_run(success=False)
        sys.exit(1)


if __name__ == "__main__":
    main()
