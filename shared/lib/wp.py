"""
WordPress data fetching utilities
Retrieves post metadata and Yoast SEO data
"""
import os
from datetime import datetime
from shared.lib.db import DatabaseConnection, execute_query


def get_post_metadata(post_names=None):
    """
    Get WordPress post metadata including Yoast SEO data
    
    Args:
        post_names: List of post slugs to fetch, or None for all published posts
        
    Returns:
        Dict mapping post_name to metadata dict
    """
    table_prefix = os.getenv('WP_TABLE_PREFIX', 'wp_')
    
    where_clause = ""
    params = ()
    
    if post_names:
        placeholders = ','.join(['%s'] * len(post_names))
        where_clause = f"AND p.post_name IN ({placeholders})"
        params = tuple(post_names)
    
    query = f"""
        SELECT 
            p.ID as post_id,
            p.post_name,
            p.post_title,
            p.post_modified,
            p.post_date,
            y.primary_focus_keyword,
            y.primary_focus_keyword_score,
            y.readability_score,
            y.is_cornerstone,
            DATEDIFF(NOW(), p.post_modified) as days_since_update
        FROM {table_prefix}posts p
        LEFT JOIN {table_prefix}yoast_indexable y 
            ON p.ID = y.object_id AND y.object_type = 'post'
        WHERE p.post_type = 'post' 
            AND p.post_status = 'publish'
            {where_clause}
    """
    
    with DatabaseConnection.get_wordpress_connection() as conn:
        results = execute_query(conn, query, params)
    
    # Convert to dict keyed by post_name
    metadata = {}
    for row in results:
        metadata[row['post_name']] = {
            'post_id': row['post_id'],
            'post_title': row['post_title'],
            'post_modified': row['post_modified'],
            'post_date': row['post_date'],
            'days_since_update': row['days_since_update'],
            'focus_keyword': row['primary_focus_keyword'],
            'keyword_score': row['primary_focus_keyword_score'] or 0,
            'readability_score': row['readability_score'] or 0,
            'is_cornerstone': row['is_cornerstone'] or 0
        }
    
    return metadata


def extract_post_name_from_path(page_path):
    """
    Extract post_name from GA/GSC page path
    
    Examples:
        '/linux-commands/' -> 'linux-commands'
        '/how-to-install-ubuntu/' -> 'how-to-install-ubuntu'
    """
    return page_path.strip('/').split('/')[-1]


def get_post_url(post_name):
    """Generate full URL for a post"""
    return f"https://linuxconfig.org/{post_name}/"
