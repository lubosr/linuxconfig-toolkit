"""
Google Analytics and Search Console API utilities
Handles authentication and data fetching
"""
import os
from datetime import datetime, timedelta
from google.oauth2.credentials import Credentials
from google.oauth2 import service_account
from googleapiclient.discovery import build
from google.analytics.data_v1beta import BetaAnalyticsDataClient
from google.analytics.data_v1beta.types import (
    DateRange,
    Dimension,
    Metric,
    RunReportRequest,
)


# Paths from environment or defaults
GA_KEY_FILE = os.getenv('GA_KEY_FILE', '/app/shared/config/credentials/linuxconfig-org-ed3c209ed133.json')
SC_TOKEN_PATH = os.getenv('SC_TOKEN_PATH', '/app/shared/config/credentials/token.json')
GA_PROPERTY_ID = os.getenv('GA_PROPERTY_ID', '354741599')
SC_PROPERTY = os.getenv('SC_PROPERTY', 'https://linuxconfig.org/')


def get_date_range(days=90):
    """Get start and end dates for queries"""
    end_date = datetime.now().strftime('%Y-%m-%d')
    start_date = (datetime.now() - timedelta(days=days)).strftime('%Y-%m-%d')
    return start_date, end_date


def get_analytics_data(days=90, limit=100):
    """
    Fetch Google Analytics data
    
    Returns:
        Dict mapping page_path to metrics dict
    """
    start_date, end_date = get_date_range(days)
    
    credentials = service_account.Credentials.from_service_account_file(GA_KEY_FILE)
    client = BetaAnalyticsDataClient(credentials=credentials)
    
    request = RunReportRequest(
        property=f"properties/{GA_PROPERTY_ID}",
        date_ranges=[DateRange(start_date=start_date, end_date=end_date)],
        dimensions=[Dimension(name="pagePath")],
        metrics=[
            Metric(name="screenPageViews"),
            Metric(name="sessions"),
            Metric(name="averageSessionDuration")
        ],
        limit=limit,
        order_bys=[{
            "metric": {
                "metric_name": "screenPageViews"
            },
            "desc": True
        }]
    )
    
    response = client.run_report(request)
    
    ga_data = {}
    for row in response.rows:
        page_path = row.dimension_values[0].value
        
        # Filter out non-article pages
        if page_path not in ['/', '/index.html', '/about', '/contact']:
            ga_data[page_path] = {
                'pageviews': int(row.metric_values[0].value),
                'sessions': int(row.metric_values[1].value),
                'avg_duration': float(row.metric_values[2].value)
            }
    
    return ga_data


def get_search_console_data(days=90, limit=100):
    """
    Fetch Search Console data
    
    Returns:
        Dict mapping page_path to metrics dict
    """
    start_date, end_date = get_date_range(days)
    
    creds = Credentials.from_authorized_user_file(SC_TOKEN_PATH)
    service = build('searchconsole', 'v1', credentials=creds)
    
    request = {
        'startDate': start_date,
        'endDate': end_date,
        'dimensions': ['page'],
        'rowLimit': limit
    }
    
    response = service.searchanalytics().query(
        siteUrl=SC_PROPERTY,
        body=request
    ).execute()
    
    sc_data = {}
    if 'rows' in response:
        for row in response['rows']:
            page_url = row['keys'][0]
            page_path = page_url.replace(SC_PROPERTY, '/')
            
            sc_data[page_path] = {
                'clicks': row['clicks'],
                'impressions': row['impressions'],
                'ctr': row['ctr'],
                'position': row['position']
            }
    
    return sc_data


def calculate_composite_score(ga_metrics, sc_metrics):
    """
    Calculate composite score from GA and GSC metrics
    
    Weighting:
    - Pageviews: 40%
    - Sessions: 20%
    - Clicks: 30%
    - Impressions: 10%
    - Bonus for top 10 position
    """
    score = 0
    
    # Analytics metrics (60% weight)
    pageviews = ga_metrics.get('pageviews', 0)
    sessions = ga_metrics.get('sessions', 0)
    score += (pageviews * 0.4)
    score += (sessions * 0.2)
    
    # Search Console metrics (40% weight)
    clicks = sc_metrics.get('clicks', 0)
    impressions = sc_metrics.get('impressions', 0)
    position = sc_metrics.get('position', 100)
    
    score += (clicks * 0.3)
    score += (impressions * 0.01)
    
    # Bonus for good ranking position
    if position <= 10:
        score += (10 - position) * 10
    
    return round(score, 2)
