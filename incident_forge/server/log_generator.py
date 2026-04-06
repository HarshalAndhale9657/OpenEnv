# incident_forge/server/log_generator.py
"""
Realistic production-style log generator for IncidentForge.

Generates timestamped, leveled log entries that look like real
production service logs from a microservices environment.
"""

import random
from datetime import datetime, timedelta, timezone
from typing import List, Optional


class LogGenerator:
    """Generates realistic production-style log entries."""

    # Common request paths per service
    _PATHS = {
        "api-gateway": [
            "GET /api/v1/products", "POST /api/v1/orders", "GET /api/v1/users/me",
            "POST /api/v1/auth/login", "GET /api/v1/orders/{id}", "GET /api/v1/health",
            "POST /api/v1/checkout", "GET /api/v1/inventory/{sku}",
        ],
        "auth-service": [
            "POST /auth/login", "POST /auth/refresh", "GET /auth/validate",
            "POST /auth/logout", "GET /auth/jwks", "POST /auth/register",
        ],
        "user-service": [
            "GET /users/{id}", "PUT /users/{id}", "GET /users/{id}/profile",
            "POST /users/search", "GET /users/{id}/preferences",
        ],
        "order-service": [
            "POST /orders", "GET /orders/{id}", "PUT /orders/{id}/status",
            "GET /orders/recent", "POST /orders/{id}/cancel",
        ],
        "payment-service": [
            "POST /api/v1/charge", "POST /api/v1/refund", "GET /api/v1/balance",
            "POST /api/v1/validate-card", "GET /api/v1/transactions/{id}",
        ],
        "inventory-service": [
            "GET /inventory/{sku}", "PUT /inventory/{sku}/reserve",
            "POST /inventory/bulk-check", "PUT /inventory/{sku}/release",
            "GET /inventory/low-stock",
        ],
        "notification-service": [
            "POST /notify/email", "POST /notify/sms", "POST /notify/push",
            "GET /notify/status/{id}", "POST /notify/batch",
        ],
    }

    # Healthy log templates
    _HEALTHY_TEMPLATES = [
        "{ts} [INFO]  {svc} | req_id={rid} | {path} | {status} | {latency}ms",
        "{ts} [INFO]  {svc} | Health check passed | uptime={uptime}h",
        "{ts} [DEBUG] {svc} | req_id={rid} | Cache hit for key={key}",
        "{ts} [INFO]  {svc} | req_id={rid} | {path} | {status} | {latency}ms | user={uid}",
        "{ts} [INFO]  {svc} | Connection pool stats: active={active}/{max}, idle={idle}",
        "{ts} [INFO]  {svc} | req_id={rid} | Processed batch of {batch} items in {latency}ms",
    ]

    # Error log templates per error pattern
    _ERROR_TEMPLATES = {
        "connection_pool_exhausted": [
            "{ts} [ERROR] {svc} | req_id={rid} | Connection pool exhausted. Max: {max_conn}, Active: {max_conn}, Waiting: {waiting}",
            "{ts} [ERROR] {svc} | req_id={rid} | Cannot acquire connection within {timeout}ms timeout",
            "{ts} [WARN]  {svc} | Health check degraded. Error rate: {error_rate}%",
            "{ts} [ERROR] {svc} | req_id={rid} | {path} | 503 | DB connection unavailable",
            "{ts} [ERROR] {svc} | req_id={rid} | java.sql.SQLException: Cannot get a connection, pool error Timeout waiting for idle object",
        ],
        "disk_full": [
            "{ts} [ERROR] {svc} | req_id={rid} | Failed to write log: No space left on device",
            "{ts} [ERROR] {svc} | CRITICAL: Disk usage at {disk_pct}% on /var/log",
            "{ts} [ERROR] {svc} | req_id={rid} | {path} | 500 | IOError: [Errno 28] No space left on device",
            "{ts} [WARN]  {svc} | Log rotation failed: insufficient disk space",
            "{ts} [ERROR] {svc} | Cannot create temp file for request processing",
        ],
        "memory_leak": [
            "{ts} [WARN]  {svc} | Memory usage: {mem_pct}% (threshold: 85%)",
            "{ts} [WARN]  {svc} | GC pressure high: {gc_count} collections in last 60s",
            "{ts} [ERROR] {svc} | req_id={rid} | {path} | 500 | java.lang.OutOfMemoryError: Java heap space",
            "{ts} [WARN]  {svc} | Heap usage trending up: {mem_mb}MB / {max_mb}MB",
            "{ts} [ERROR] {svc} | OOM kill imminent, memory at {mem_pct}%",
        ],
        "ssl_expired": [
            "{ts} [ERROR] {svc} | req_id={rid} | SSL handshake failed: certificate has expired",
            "{ts} [ERROR] {svc} | TLS error connecting to {target}: certificate verify failed (expired)",
            "{ts} [ERROR] {svc} | req_id={rid} | {path} | 502 | upstream SSL error",
            "{ts} [WARN]  {svc} | Certificate for {domain} expired at {exp_date}",
            "{ts} [ERROR] {svc} | HTTPS connection to {target}:443 failed: CERTIFICATE_EXPIRED",
        ],
        "wrong_env_var": [
            "{ts} [ERROR] {svc} | req_id={rid} | Connection refused to {wrong_host}:{port}",
            "{ts} [ERROR] {svc} | req_id={rid} | {path} | 500 | ECONNREFUSED {wrong_host}:{port}",
            "{ts} [WARN]  {svc} | Failed health check for dependency at {wrong_host}",
            "{ts} [ERROR] {svc} | DNS resolution failed for {wrong_host}",
            "{ts} [ERROR] {svc} | req_id={rid} | Timeout connecting to {wrong_host}:{port} after 5000ms",
        ],
        "cascading_timeout": [
            "{ts} [ERROR] {svc} | req_id={rid} | {path} | 504 | Upstream timeout after {timeout}ms",
            "{ts} [WARN]  {svc} | Circuit breaker OPEN for {target} — {fail_count} consecutive failures",
            "{ts} [ERROR] {svc} | req_id={rid} | HttpTimeoutException: request timed out after {timeout}ms to {target}",
            "{ts} [WARN]  {svc} | Retry exhausted for {target} (attempt {attempt}/3)",
            "{ts} [ERROR] {svc} | req_id={rid} | {path} | 502 | upstream connect error or disconnect/reset before headers",
        ],
        "db_replication_lag": [
            "{ts} [WARN]  {svc} | Replication lag: {lag_s}s (threshold: 5s)",
            "{ts} [ERROR] {svc} | req_id={rid} | Stale read detected: record updated {lag_s}s ago not visible on replica",
            "{ts} [WARN]  {svc} | Read replica {replica} behind primary by {lag_s} seconds",
            "{ts} [ERROR] {svc} | req_id={rid} | {path} | 409 | Conflict: order state mismatch (stale read from replica)",
            "{ts} [INFO]  {svc} | Failover: routing reads to primary due to replica lag > {threshold}s",
        ],
        "lb_misconfigured": [
            "{ts} [ERROR] {svc} | req_id={rid} | {path} | 502 | no healthy upstream",
            "{ts} [WARN]  {svc} | Backend {backend} marked DOWN — health check failed {fail_count} times",
            "{ts} [ERROR] {svc} | req_id={rid} | Connection refused by backend {backend}:{port}",
            "{ts} [INFO]  {svc} | Load balancer routing: {active_backends}/{total_backends} backends active",
            "{ts} [WARN]  {svc} | Uneven traffic distribution detected: {backend} receiving 0 requests",
        ],
        "api_version_mismatch": [
            "{ts} [ERROR] {svc} | req_id={rid} | {path} | 400 | Deserialization error: unknown field 'payment_method_v2'",
            "{ts} [ERROR] {svc} | req_id={rid} | Schema validation failed: expected 'amount' as integer, got object",
            "{ts} [WARN]  {svc} | API version mismatch: client sending v2 payload to v1 endpoint",
            "{ts} [ERROR] {svc} | req_id={rid} | {path} | 422 | Unprocessable Entity: missing required field 'currency_code'",
            "{ts} [WARN]  {svc} | Deprecation: /api/v1/charge will be removed. Use /api/v2/charge",
        ],
        "rate_limiter_aggressive": [
            "{ts} [WARN]  {svc} | Rate limit exceeded for client {client_ip}: {rate}/s > {limit}/s",
            "{ts} [ERROR] {svc} | req_id={rid} | {path} | 429 | Too Many Requests. Retry after {retry_after}s",
            "{ts} [INFO]  {svc} | Rate limiter config: max_requests={limit}/s, window=60s, burst={burst}",
            "{ts} [WARN]  {svc} | {throttled_pct}% of requests throttled in last 60s",
            "{ts} [ERROR] {svc} | req_id={rid} | Legitimate traffic blocked by rate limiter — threshold too low",
        ],
        "dns_cache_poisoning": [
            "{ts} [ERROR] {svc} | req_id={rid} | Connection to {target} ({wrong_ip}) failed: connection refused",
            "{ts} [WARN]  {svc} | DNS resolution for {target}: {wrong_ip} (TTL: {ttl}s, cached)",
            "{ts} [ERROR] {svc} | req_id={rid} | {path} | 502 | upstream host {wrong_ip} unreachable",
            "{ts} [DEBUG] {svc} | DNS cache entry for {target}: {wrong_ip} (stale, last refresh {age}s ago)",
            "{ts} [ERROR] {svc} | req_id={rid} | TLS certificate mismatch: expected CN={target}, got CN={wrong_cn}",
        ],
        "clock_skew": [
            "{ts} [ERROR] {svc} | req_id={rid} | JWT validation failed: token not yet valid (nbf claim in future)",
            "{ts} [WARN]  {svc} | System clock drift detected: {drift_s}s ahead of NTP reference",
            "{ts} [ERROR] {svc} | req_id={rid} | {path} | 401 | Token expired (clock skew: server time {server_time}, token exp {exp_time})",
            "{ts} [WARN]  {svc} | Cache entries expiring {drift_s}s early due to clock drift",
            "{ts} [ERROR] {svc} | req_id={rid} | Distributed lock acquisition failed: timestamp disagreement between nodes",
        ],
        "network_partition": [
            "{ts} [ERROR] {svc} | req_id={rid} | Connection to {target} timed out (partial network failure)",
            "{ts} [WARN]  {svc} | Inconsistent health checks: pod {pod_a} can reach {target}, pod {pod_b} cannot",
            "{ts} [ERROR] {svc} | req_id={rid} | {path} | 503 | Intermittent: request succeeded on retry (different pod)",
            "{ts} [WARN]  {svc} | Network partition suspected between AZ-{az_a} and AZ-{az_b}",
            "{ts} [ERROR] {svc} | Gossip protocol: {unreachable_count} nodes unreachable from this pod",
        ],
    }

    def __init__(self, base_time: Optional[datetime] = None, seed: Optional[int] = None):
        self._rng = random.Random(seed)
        self._base_time = base_time or datetime.now(timezone.utc)
        self._log_counter = 0

    def _next_ts(self) -> str:
        """Generate the next timestamp, advancing slightly each call."""
        self._log_counter += 1
        offset = timedelta(
            milliseconds=self._rng.randint(50, 2000) * self._log_counter
        )
        ts = self._base_time + offset
        return ts.strftime("%Y-%m-%dT%H:%M:%S.") + f"{ts.microsecond // 1000:03d}Z"

    def _req_id(self) -> str:
        return f"{self._rng.randint(0x10000000, 0xFFFFFFFF):08x}"

    def _user_id(self) -> str:
        return f"usr_{self._rng.randint(10000, 99999)}"

    def generate_healthy_logs(self, service_name: str, count: int = 10) -> List[str]:
        """Generate normal/healthy operation logs."""
        paths = self._PATHS.get(service_name, ["GET /health"])
        logs = []
        for _ in range(count):
            template = self._rng.choice(self._HEALTHY_TEMPLATES)
            log = template.format(
                ts=self._next_ts(),
                svc=service_name,
                rid=self._req_id(),
                path=self._rng.choice(paths),
                status=self._rng.choice(["200", "200", "200", "201", "204"]),
                latency=self._rng.randint(5, 120),
                uptime=self._rng.randint(24, 720),
                key=f"cache:{self._rng.choice(['user', 'product', 'session'])}:{self._rng.randint(1000, 9999)}",
                uid=self._user_id(),
                active=self._rng.randint(2, 8),
                max=20,
                idle=self._rng.randint(10, 18),
                batch=self._rng.randint(10, 100),
            )
            logs.append(log)
        return logs

    def generate_error_logs(
        self,
        service_name: str,
        error_pattern: str,
        count: int = 8,
        context: Optional[dict] = None,
    ) -> List[str]:
        """Generate error logs matching a specific incident pattern."""
        ctx = context or {}
        templates = self._ERROR_TEMPLATES.get(error_pattern, [])
        if not templates:
            return [f"[ERROR] {service_name} | Unknown error pattern: {error_pattern}"]

        paths = self._PATHS.get(service_name, ["GET /health"])
        logs = []
        for _ in range(count):
            template = self._rng.choice(templates)
            log = template.format(
                ts=self._next_ts(),
                svc=service_name,
                rid=self._req_id(),
                path=self._rng.choice(paths),
                # Connection pool
                max_conn=ctx.get("max_conn", 10),
                waiting=self._rng.randint(200, 1500),
                timeout=ctx.get("timeout", 5000),
                error_rate=ctx.get("error_rate", self._rng.uniform(30, 60)),
                # Disk
                disk_pct=ctx.get("disk_pct", self._rng.uniform(95, 100)),
                # Memory
                mem_pct=ctx.get("mem_pct", self._rng.uniform(88, 99)),
                gc_count=self._rng.randint(50, 200),
                mem_mb=ctx.get("mem_mb", self._rng.randint(1800, 2000)),
                max_mb=ctx.get("max_mb", 2048),
                # SSL
                target=ctx.get("target", "upstream-service.internal"),
                domain=ctx.get("domain", f"{service_name}.prod.internal"),
                exp_date=ctx.get("exp_date", "2026-04-01T00:00:00Z"),
                # Env var / DNS
                wrong_host=ctx.get("wrong_host", "db-staging.internal"),
                port=ctx.get("port", 5432),
                wrong_ip=ctx.get("wrong_ip", "10.0.99.1"),
                ttl=ctx.get("ttl", 3600),
                age=self._rng.randint(3600, 86400),
                wrong_cn=ctx.get("wrong_cn", "old-server.internal"),
                # Timeout / cascade
                fail_count=self._rng.randint(5, 30),
                attempt=self._rng.randint(1, 3),
                # Replication
                lag_s=ctx.get("lag_s", self._rng.randint(15, 60)),
                replica=ctx.get("replica", "replica-02"),
                threshold=ctx.get("threshold", 5),
                # Load balancer
                backend=ctx.get("backend", "backend-03"),
                active_backends=ctx.get("active_backends", 2),
                total_backends=ctx.get("total_backends", 3),
                # Rate limiter
                client_ip=f"10.0.{self._rng.randint(1, 255)}.{self._rng.randint(1, 255)}",
                rate=ctx.get("rate", self._rng.randint(500, 2000)),
                limit=ctx.get("limit", 100),
                retry_after=self._rng.randint(5, 60),
                burst=ctx.get("burst", 150),
                throttled_pct=ctx.get("throttled_pct", self._rng.randint(40, 80)),
                # Clock skew
                drift_s=ctx.get("drift_s", self._rng.randint(30, 300)),
                server_time=ctx.get("server_time", "2026-04-07T02:15:00Z"),
                exp_time=ctx.get("exp_time", "2026-04-07T02:10:00Z"),
                # Network partition
                pod_a=ctx.get("pod_a", "pod-abc12"),
                pod_b=ctx.get("pod_b", "pod-def34"),
                az_a=ctx.get("az_a", "us-east-1a"),
                az_b=ctx.get("az_b", "us-east-1c"),
                unreachable_count=self._rng.randint(2, 5),
            )
            logs.append(log)
        return logs

    def generate_mixed_logs(
        self,
        service_name: str,
        error_pattern: str,
        error_ratio: float = 0.4,
        total: int = 15,
        context: Optional[dict] = None,
    ) -> List[str]:
        """Generate a realistic mix of healthy and error logs."""
        error_count = max(1, int(total * error_ratio))
        healthy_count = total - error_count

        healthy = self.generate_healthy_logs(service_name, healthy_count)
        errors = self.generate_error_logs(service_name, error_pattern, error_count, context)

        combined = healthy + errors
        self._rng.shuffle(combined)
        return combined
