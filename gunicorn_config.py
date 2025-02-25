bind = "0.0.0.0:10000"
workers = 2  # Reduced from 4 to lower memory usage
threads = 2  # Reduced from 4 to lower memory usage
timeout = 300  # Increased timeout
max_requests = 1000
max_requests_jitter = 50
worker_class = 'gthread'
preload_app = True
