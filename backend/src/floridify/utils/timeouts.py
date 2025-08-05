"""Centralized timeout constants for the application."""

# API endpoint timeouts (seconds)
API_DEFAULT_TIMEOUT = 120  # 2 minutes - default for most endpoints
API_LOOKUP_TIMEOUT = 180  # 3 minutes - lookup can take longer with AI synthesis
API_BATCH_TIMEOUT = 600  # 10 minutes - batch operations need more time

# HTTP client timeouts (seconds)
HTTP_DEFAULT_TIMEOUT = 120.0  # 2 minutes - general HTTP requests
HTTP_PROVIDER_TIMEOUT = 120.0  # 2 minutes - dictionary provider requests
HTTP_RETRY_TIMEOUT = 30.0  # 30 seconds - retry attempts

# Database timeouts (seconds)
DB_CONNECTION_TIMEOUT = 120  # 2 minutes - connection establishment
DB_OPERATION_TIMEOUT = 60  # 1 minute - individual operations

# Cache and deduplication timeouts (seconds)
CACHE_DEDUP_WAIT_TIME = 120.0  # 2 minutes - max wait for deduplication

# Streaming timeouts (seconds)
STREAM_KEEPALIVE_INTERVAL = 15.0  # 15 seconds - SSE keepalive
STREAM_MAX_DURATION = 300.0  # 5 minutes - max streaming duration
