"""Analytics module for sending metrics to Datadog.

This module implements fail-open analytics integration with Datadog HTTP API.
Metric failures are logged but do not block user flow.
"""

import logging
import time
from typing import Optional

import requests

logger = logging.getLogger(__name__)

DATADOG_API_URL = "https://api.datadoghq.com/api/v1/series"


def send_stage_metric(stage_name: str, datadog_api_key: str) -> bool:
    """Send stage completion metric to Datadog.
    
    Sends a COUNT metric to Datadog with the name "hackquest.stage_completed"
    and a stage tag. Uses fail-open design: logs errors but returns False
    instead of raising exceptions.
    
    Args:
        stage_name: The stage name (idea, team, mvp, pitch)
        datadog_api_key: Datadog API key for authentication
        
    Returns:
        True if metric was sent successfully, False otherwise
        
    Example:
        >>> send_stage_metric("idea", "your-api-key")
        True
    """
    try:
        # Generate Unix timestamp
        timestamp = int(time.time())
        
        # Build metric payload
        payload = {
            "series": [{
                "metric": "hackquest.stage_completed",
                "type": "count",
                "points": [[timestamp, 1]],
                "tags": [f"stage:{stage_name}"]
            }]
        }
        
        # Send to Datadog
        headers = {
            "Content-Type": "application/json",
            "DD-API-KEY": datadog_api_key
        }
        
        response = requests.post(
            DATADOG_API_URL,
            json=payload,
            headers=headers,
            timeout=5  # 5 second timeout
        )
        
        response.raise_for_status()
        logger.info(f"Successfully sent stage metric: {stage_name}")
        return True
        
    except requests.exceptions.RequestException as e:
        logger.error(f"Failed to send Datadog metric for stage {stage_name}: {e}")
        return False
    except Exception as e:
        logger.error(f"Unexpected error sending Datadog metric for stage {stage_name}: {e}")
        return False
