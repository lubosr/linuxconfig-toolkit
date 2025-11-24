#!/usr/bin/env python3
"""
LinuxConfig.org - Enhanced Core Article Tracker
Identifies top 30 core articles and tracks performance bi-weekly
Combines GA, GSC, WordPress, and Yoast SEO data
"""
import os
import sys
from datetime import datetime, date
from tabulate import tabulate

# Add parent directory to path for shared imports
sys.path.insert(0, '/app')

from shared.lib.db import DatabaseConnection, execute_query, execute_insert
from shared.lib.wp import get_post_metadata, extract_post_name_from_path, get_post_url
from shared.lib.google_apis import (
    get_analytics_data,
    get_search_console_data,
    calculate_composite_score
)


class CoreArticleTracker:
    """Manages core article tracking and reporting"""

    def __init__(self):
        self.snapshot_date = date.today()
        self.run_id = None
        self.articles_data = []
        self.alerts = []

    def start_run(self):
        """Record script run start"""
        print("=" * 80)
        print("LinuxConfig.org - Enhanced Core Article Tracker")
        print("=" * 80)
        print(f"Snapshot Date: {self.snapshot_date}")
        print(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print()

        with DatabaseConnection.get_toolkit_connection() as conn:
            self.run_id = execute_insert(
                conn,
                """INSERT INTO toolkit_runs
                   (script_name, status, run_date)
                   VALUES (%s, %s, NOW())""",
                ('core-article-tracker', 'started')
            )

    def fetch_google_data(self):
        """Fetch data from Google Analytics and Search Console"""
        print("📊 Fetching Google Analytics data...")
        ga_data = get_analytics_data(days=90, limit=100)
        print(f"✓ Retrieved {len(ga_data)} pages from Analytics")

        print("\n🔍 Fetching Search Console data...")
        sc_data = get_search_console_data(days=90, limit=100)
        print(f"✓ Retrieved {len(sc_data)} pages from Search Console")

        return ga_data, sc_data

    def combine_and_score(self, ga_data, sc_data):
        """Combine GA and GSC data, calculate scores"""
        print("\n🧮 Calculating composite scores...")

        combined = {}
        all_pages = set(list(ga_data.keys()) + list(sc_data.keys()))

        for page in all_pages:
            ga = ga_data.get(page, {})
            sc = sc_data.get(page, {})

            score = calculate_composite_score(ga, sc)

            combined[page] = {
                'page_path': page,
                'score': score,
                'pageviews': ga.get('pageviews', 0),
                'sessions': ga.get('sessions', 0),
                'avg_duration': ga.get('avg_duration', 0),
                'clicks': sc.get('clicks', 0),
                'impressions': sc.get('impressions', 0),
                'ctr': sc.get('ctr', 0),
                'position': sc.get('position', 0)
            }

        # Sort by score
        sorted_articles = sorted(combined.items(), key=lambda x: x[1]['score'], reverse=True)
        print(f"✓ Scored {len(sorted_articles)} total pages")

        return sorted_articles

    def enrich_with_wordpress_data(self, sorted_articles, top_n=30):
        """Add WordPress and Yoast data to top articles"""
        print(f"\n📝 Fetching WordPress data for top {top_n} articles...")

        # Get top N articles
        top_articles = sorted_articles[:top_n]

        # Extract post names from page paths
        post_names = []
        for page_path, _ in top_articles:
            post_name = extract_post_name_from_path(page_path)
            if post_name:
                post_names.append(post_name)

        # Fetch WordPress metadata
        wp_metadata = get_post_metadata(post_names)
        print(f"✓ Retrieved metadata for {len(wp_metadata)} posts")

        # Combine data
        enriched = []
        for rank, (page_path, metrics) in enumerate(top_articles, 1):
            post_name = extract_post_name_from_path(page_path)
            wp_data = wp_metadata.get(post_name, {})

            article = {
                'rank': rank,
                'page_path': page_path,
                'post_name': post_name,
                'post_id': wp_data.get('post_id'),
                'post_title': wp_data.get('post_title', ''),
                'score': metrics['score'],
                'pageviews': metrics['pageviews'],
                'sessions': metrics['sessions'],
                'avg_duration': metrics['avg_duration'],
                'clicks': metrics['clicks'],
                'impressions': metrics['impressions'],
                'ctr': metrics['ctr'],
                'position': metrics['position'],
                'last_modified': wp_data.get('post_modified'),
                'days_since_update': wp_data.get('days_since_update', 0),
                'focus_keyword': wp_data.get('focus_keyword'),
                'keyword_score': wp_data.get('keyword_score', 0),
                'readability_score': wp_data.get('readability_score', 0),
                'is_cornerstone': wp_data.get('is_cornerstone', 0)
            }

            enriched.append(article)

        self.articles_data = enriched
        return enriched

    def generate_alerts(self):
        """Generate alerts based on article data and historical trends"""
        print("\n⚠️  Generating alerts...")

        with DatabaseConnection.get_toolkit_connection() as conn:
            # Get previous snapshot for comparison
            previous_snapshot = execute_query(
                conn,
                """SELECT snapshot_date FROM core_articles_snapshots
                   WHERE snapshot_date < %s
                   ORDER BY snapshot_date DESC LIMIT 1""",
                (self.snapshot_date,)
            )

            has_history = len(previous_snapshot) > 0

            for article in self.articles_data:
                page_path = article['page_path']

                # Alert: Missing focus keyword
                if not article['focus_keyword']:
                    self.alerts.append({
                        'page_path': page_path,
                        'type': 'missing_focus_keyword',
                        'severity': 'warning',
                        'message': 'Article has no focus keyword set',
                        'value': 'NULL'
                    })

                # Alert: Not updated in 6+ months
                if article['days_since_update'] and article['days_since_update'] >= 180:
                    self.alerts.append({
                        'page_path': page_path,
                        'type': 'content_outdated',
                        'severity': 'critical' if article['days_since_update'] >= 365 else 'warning',
                        'message': f'Not updated in {article["days_since_update"]} days',
                        'value': str(article['days_since_update'])
                    })

                # Alert: Low readability
                if article['readability_score'] and article['readability_score'] < 60:
                    self.alerts.append({
                        'page_path': page_path,
                        'type': 'low_readability',
                        'severity': 'info',
                        'message': f'Low readability score: {article["readability_score"]}',
                        'value': str(article['readability_score'])
                    })

                # Alert: Poor ranking position
                if article['position'] and article['position'] > 20:
                    self.alerts.append({
                        'page_path': page_path,
                        'type': 'poor_ranking',
                        'severity': 'warning',
                        'message': f'Average position: {article["position"]:.1f}',
                        'value': f'{article["position"]:.1f}'
                    })

                # Historical comparison alerts (if previous snapshot exists)
                if has_history:
                    prev_data = execute_query(
                        conn,
                        """SELECT rank_position, gsc_position, ga_pageviews
                           FROM core_articles_snapshots
                           WHERE snapshot_date = %s AND page_path = %s""",
                        (previous_snapshot[0]['snapshot_date'], page_path)
                    )

                    if prev_data:
                        prev = prev_data[0]

                        # Rank dropped
                        if prev['rank_position'] and article['rank'] > prev['rank_position'] + 5:
                            self.alerts.append({
                                'page_path': page_path,
                                'type': 'rank_declined',
                                'severity': 'warning',
                                'message': f'Rank dropped from {prev["rank_position"]} to {article["rank"]}',
                                'value': f'{prev["rank_position"]} → {article["rank"]}'
                            })

                        # Position worsened
                        if prev['gsc_position'] and article['position']:
                            position_change = article['position'] - prev['gsc_position']
                            if position_change > 5:
                                self.alerts.append({
                                    'page_path': page_path,
                                    'type': 'position_declined',
                                    'severity': 'warning',
                                    'message': f'Search position worsened by {position_change:.1f}',
                                    'value': f'{prev["gsc_position"]:.1f} → {article["position"]:.1f}'
                                })

                        # Traffic declined significantly
                        if prev['ga_pageviews']:
                            traffic_change = ((article['pageviews'] - prev['ga_pageviews']) / prev['ga_pageviews']) * 100
                            if traffic_change < -20:
                                self.alerts.append({
                                    'page_path': page_path,
                                    'type': 'traffic_declined',
                                    'severity': 'warning',
                                    'message': f'Traffic down {abs(traffic_change):.1f}%',
                                    'value': f'{traffic_change:.1f}%'
                                })

        print(f"✓ Generated {len(self.alerts)} alerts")
        return self.alerts

    def save_snapshot(self):
        """Save snapshot to database"""
        print(f"\n💾 Saving snapshot to database...")

        with DatabaseConnection.get_toolkit_connection() as conn:
            for article in self.articles_data:
                execute_insert(
                    conn,
                    """INSERT INTO core_articles_snapshots
                       (snapshot_date, page_path, post_name, post_id,
                        ga_pageviews, ga_sessions, ga_avg_duration,
                        gsc_clicks, gsc_impressions, gsc_ctr, gsc_position,
                        wp_last_modified, wp_days_since_update,
                        yoast_focus_keyword, yoast_keyword_score,
                        yoast_readability_score, yoast_is_cornerstone,
                        composite_score, rank_position)
                       VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
                               %s, %s, %s, %s, %s, %s, %s, %s)
                       ON DUPLICATE KEY UPDATE
                        ga_pageviews = VALUES(ga_pageviews),
                        gsc_clicks = VALUES(gsc_clicks),
                        composite_score = VALUES(composite_score),
                        rank_position = VALUES(rank_position)""",
                    (
                        self.snapshot_date, article['page_path'], article['post_name'],
                        article['post_id'], article['pageviews'], article['sessions'],
                        article['avg_duration'], article['clicks'], article['impressions'],
                        article['ctr'], article['position'], article['last_modified'],
                        article['days_since_update'], article['focus_keyword'],
                        article['keyword_score'], article['readability_score'],
                        article['is_cornerstone'], article['score'], article['rank']
                    )
                )

        print(f"✓ Saved {len(self.articles_data)} articles")

    def save_alerts(self):
        """Save alerts to database"""
        if not self.alerts:
            return

        print(f"💾 Saving {len(self.alerts)} alerts...")

        with DatabaseConnection.get_toolkit_connection() as conn:
            for alert in self.alerts:
                execute_insert(
                    conn,
                    """INSERT INTO core_articles_alerts
                       (snapshot_date, page_path, alert_type, alert_severity,
                        alert_message, metric_value)
                       VALUES (%s, %s, %s, %s, %s, %s)""",
                    (
                        self.snapshot_date, alert['page_path'], alert['type'],
                        alert['severity'], alert['message'], alert['value']
                    )
                )

        print(f"✓ Saved alerts")

    def generate_reports(self):
        """Generate console and CSV reports"""
        print("\n" + "=" * 80)
        print("📊 CORE ARTICLES REPORT")
        print("=" * 80)

        # All 30 articles
        print("\n🏆 Top 30 Core Articles:\n")

        table_data = []
        for article in self.articles_data:
            table_data.append([
                article['rank'],
                article['page_path'][:60],
                f"{article['score']:.0f}",
                article['pageviews'],
                article['clicks'],
                f"{article['position']:.1f}",
                article['days_since_update'] or 'N/A'
            ])

        print(tabulate(
            table_data,
            headers=['Rank', 'Page', 'Score', 'Views', 'Clicks', 'Pos', 'Days Old'],
            tablefmt='simple'
        ))

        # Alerts summary - show ALL alerts
        if self.alerts:
            print(f"\n⚠️  ALERTS SUMMARY ({len(self.alerts)} total):\n")

            # Group by severity
            critical = [a for a in self.alerts if a['severity'] == 'critical']
            warning = [a for a in self.alerts if a['severity'] == 'warning']
            info = [a for a in self.alerts if a['severity'] == 'info']

            if critical:
                print(f"🔴 CRITICAL ({len(critical)}):")
                for alert in critical:
                    print(f"   • {alert['page_path'][:60]}: {alert['message']}")

            if warning:
                print(f"\n🟡 WARNING ({len(warning)}):")
                for alert in warning:
                    print(f"   • {alert['page_path'][:60]}: {alert['message']}")

            if info:
                print(f"\n🔵 INFO ({len(info)}):")
                for alert in info:
                    print(f"   • {alert['page_path'][:60]}: {alert['message']}")

        # Save CSV
        self.save_csv_report()

    def save_csv_report(self):
        """Save detailed CSV report"""
        import csv

        output_file = f'/app/reports/core_articles_{self.snapshot_date}.csv'

        with open(output_file, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow([
                'Rank', 'Page Path', 'Post Title', 'Full URL', 'Score',
                'Pageviews (90d)', 'Sessions', 'GSC Clicks', 'GSC Impressions',
                'Avg Position', 'CTR', 'Avg Duration (sec)',
                'Last Modified', 'Days Since Update', 'Focus Keyword',
                'Keyword Score', 'Readability', 'Is Cornerstone', 'Alerts'
            ])

            for article in self.articles_data:
                # Get alerts for this article
                article_alerts = [a['message'] for a in self.alerts
                                if a['page_path'] == article['page_path']]
                alerts_str = '; '.join(article_alerts) if article_alerts else ''

                writer.writerow([
                    article['rank'],
                    article['page_path'],
                    article['post_title'],
                    get_post_url(article['post_name']) if article['post_name'] else '',
                    f"{article['score']:.2f}",
                    article['pageviews'],
                    article['sessions'],
                    article['clicks'],
                    article['impressions'],
                    f"{article['position']:.1f}",
                    f"{article['ctr']:.4f}",
                    f"{article['avg_duration']:.1f}",
                    article['last_modified'],
                    article['days_since_update'],
                    article['focus_keyword'] or '',
                    article['keyword_score'],
                    article['readability_score'],
                    'Yes' if article['is_cornerstone'] else 'No',
                    alerts_str
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
                       alerts_generated = %s,
                       execution_time_seconds = TIMESTAMPDIFF(SECOND, run_date, NOW())
                   WHERE id = %s""",
                (status, len(self.articles_data), len(self.alerts), self.run_id)
            )

        print("\n" + "=" * 80)
        print(f"✅ Run completed successfully!" if success else "❌ Run failed")
        print("=" * 80)


def main():
    """Main execution"""
    tracker = CoreArticleTracker()

    try:
        # Start tracking
        tracker.start_run()

        # Fetch Google data
        ga_data, sc_data = tracker.fetch_google_data()

        if not ga_data and not sc_data:
            print("\n❌ Failed to retrieve data from Google APIs")
            tracker.complete_run(success=False)
            return

        # Combine and score
        sorted_articles = tracker.combine_and_score(ga_data, sc_data)

        # Enrich with WordPress data
        tracker.enrich_with_wordpress_data(sorted_articles, top_n=30)

        # Generate alerts
        tracker.generate_alerts()

        # Save to database
        tracker.save_snapshot()
        tracker.save_alerts()

        # Generate reports
        tracker.generate_reports()

        # Complete
        tracker.complete_run(success=True)

    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        tracker.complete_run(success=False)
        sys.exit(1)


if __name__ == "__main__":
    main()
