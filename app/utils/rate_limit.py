from flask import request, jsonify
from functools import wraps
import time

# Simple in-memory rate limiting implementation
request_history = {}

def rate_limit(max_requests=10, window=60):
    def decorator(f):
        @wraps(f)
        def wrapped(*args, **kwargs):
            ip = request.remote_addr
            now = time.time()
            
            if ip not in request_history:
                request_history[ip] = []
            
            # Clean old requests
            request_history[ip] = [t for t in request_history[ip] if now - t < window]
            
            if len(request_history[ip]) >= max_requests:
                return jsonify({"error": "Rate limit exceeded"}), 429
            
            request_history[ip].append(now)
            return f(*args, **kwargs)
        return wrapped
    return decorator
