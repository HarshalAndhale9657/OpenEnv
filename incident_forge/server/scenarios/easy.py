# incident_forge/server/scenarios/easy.py
"""
5 Easy scenarios — single root cause with obvious symptoms.
Each grounded in real-world postmortems.
"""

from dataclasses import dataclass, field
from typing import Any, Dict, List


@dataclass
class Scenario:
    """A single incident scenario definition."""

    id: str
    name: str
    difficulty: str
    description: str  # Alert message shown to agent
    root_cause: str  # Ground truth root cause
    root_cause_keywords: List[str]  # Keywords for diagnosis grading
    contributing_factors: List[str]  # Secondary causes
    affected_services: List[str]  # Services in the causal chain
    primary_service: str  # Where the root cause lives
    service_modifications: Dict[str, Dict[str, Any]]  # How to modify services
    correct_remediation: List[str]  # Expected remediation actions
    optimal_step_count: int  # Expert-level step count
    red_herrings: List[Dict[str, Any]] = field(default_factory=list)
    postmortem_source: str = ""


EASY_SCENARIOS: List[Scenario] = [
    # ── E1: Connection Pool Exhaustion ────────────────────────────────
    Scenario(
        id="easy_01",
        name="Connection Pool Exhaustion",
        difficulty="easy",
        description=(
            "🚨 ALERT: payment-service error rate at 45%. "
            "checkout-service reporting upstream timeouts. "
            "Multiple 503 errors detected. Severity: HIGH."
        ),
        root_cause=(
            "payment-service database connection pool is exhausted. "
            "DB_POOL_MAX_SIZE=10 is too small for current request load, "
            "causing all connections to be occupied and new requests to queue/timeout. "
            "This cascades to checkout timeouts via order-service."
        ),
        root_cause_keywords=[
            "connection pool", "exhausted", "pool size", "DB_POOL_MAX_SIZE",
            "payment-service", "database", "timeout",
        ],
        contributing_factors=[
            "traffic spike during flash sale",
            "pool size never increased from default",
        ],
        affected_services=["payment-service", "order-service"],
        primary_service="payment-service",
        service_modifications={
            "payment-service": {
                "health": "unhealthy",
                "error_rate_percent": 45.2,
                "latency_p50_ms": 4500.0,
                "latency_p99_ms": 12400.0,
                "db_connections_active": 10,
                "db_connections_max": 10,
                "error_pattern": "connection_pool_exhausted",
                "error_context": {"max_conn": 10, "timeout": 5000},
                "config_overrides": {"DB_POOL_MAX_SIZE": "10"},
            },
            "order-service": {
                "health": "degraded",
                "error_rate_percent": 38.0,
                "latency_p99_ms": 15200.0,
                "error_pattern": "cascading_timeout",
                "error_context": {"target": "payment-service", "timeout": 5000},
            },
        },
        correct_remediation=[
            "update_config:payment-service",
            "restart_service:payment-service",
        ],
        optimal_step_count=5,
        postmortem_source=(
            "Inspired by: GitLab database saturation incident 2022 — "
            "https://about.gitlab.com/blog/2022/01/23/the-jan-22-outage/"
        ),
    ),

    # ── E2: Disk Space Full ───────────────────────────────────────────
    Scenario(
        id="easy_02",
        name="Disk Space Full",
        difficulty="easy",
        description=(
            "🚨 ALERT: order-service returning 500 errors. "
            "Write operations failing. Error rate: 30%. Severity: HIGH."
        ),
        root_cause=(
            "order-service disk is full at 99.8%. Excessive log volume "
            "filled /var/log, preventing the service from writing temp files "
            "or processing requests that require disk I/O."
        ),
        root_cause_keywords=[
            "disk", "full", "space", "order-service", "log", "/var/log", "IOError",
        ],
        contributing_factors=[
            "log rotation was misconfigured",
            "debug logging was accidentally left on",
        ],
        affected_services=["order-service"],
        primary_service="order-service",
        service_modifications={
            "order-service": {
                "health": "unhealthy",
                "error_rate_percent": 30.0,
                "disk_usage_percent": 99.8,
                "error_pattern": "disk_full",
                "error_context": {"disk_pct": 99.8},
                "config_overrides": {"LOG_LEVEL": "DEBUG"},
            },
        },
        correct_remediation=[
            "update_config:order-service",
            "restart_service:order-service",
        ],
        optimal_step_count=4,
        postmortem_source=(
            "Inspired by: Spotify 2023 — log volume spike causing disk exhaustion on stateful services"
        ),
    ),

    # ── E3: Memory Leak ──────────────────────────────────────────────
    Scenario(
        id="easy_03",
        name="Obvious Memory Leak",
        difficulty="easy",
        description=(
            "🚨 ALERT: user-service responding slowly. "
            "Memory usage critical at 94%. OOM kill risk. "
            "Service uptime: 2.5 hours since last restart. Severity: HIGH."
        ),
        root_cause=(
            "user-service has a memory leak in the RequestHandler. Memory has been "
            "steadily climbing since the last deployment and is now at 94%. "
            "The service will OOM-crash soon without intervention."
        ),
        root_cause_keywords=[
            "memory", "leak", "OOM", "user-service", "heap", "RequestHandler",
        ],
        contributing_factors=[
            "recent deployment introduced the leak",
            "no memory limits configured",
        ],
        affected_services=["user-service"],
        primary_service="user-service",
        service_modifications={
            "user-service": {
                "health": "degraded",
                "memory_percent": 94.0,
                "latency_p99_ms": 3500.0,
                "uptime_hours": 2.5,
                "error_rate_percent": 12.0,
                "error_pattern": "memory_leak",
                "error_context": {"mem_pct": 94, "mem_mb": 1920, "max_mb": 2048},
            },
        },
        correct_remediation=[
            "restart_service:user-service",
            "rollback_deploy:user-service",
        ],
        optimal_step_count=5,
        postmortem_source=(
            "Inspired by: Node.js memory leak patterns documented in Netflix tech blog 2021"
        ),
    ),

    # ── E4: SSL Certificate Expired ──────────────────────────────────
    Scenario(
        id="easy_04",
        name="SSL Certificate Expired",
        difficulty="easy",
        description=(
            "🚨 ALERT: auth-service returning 502 errors. "
            "All authentication requests failing. "
            "Downstream services unable to validate tokens. Severity: CRITICAL."
        ),
        root_cause=(
            "auth-service TLS certificate expired on 2026-04-01. All HTTPS connections "
            "to auth-service fail SSL handshake. Since api-gateway requires auth for most "
            "endpoints, this causes widespread 502 errors."
        ),
        root_cause_keywords=[
            "SSL", "TLS", "certificate", "expired", "auth-service", "handshake",
        ],
        contributing_factors=[
            "certificate auto-renewal was not configured",
            "monitoring for cert expiry was not set up",
        ],
        affected_services=["auth-service", "api-gateway"],
        primary_service="auth-service",
        service_modifications={
            "auth-service": {
                "health": "unhealthy",
                "error_rate_percent": 100.0,
                "error_pattern": "ssl_expired",
                "error_context": {
                    "domain": "auth-service.prod.internal",
                    "exp_date": "2026-04-01T00:00:00Z",
                    "target": "auth-service.prod.internal",
                },
            },
            "api-gateway": {
                "health": "degraded",
                "error_rate_percent": 65.0,
                "latency_p99_ms": 2000.0,
                "error_pattern": "cascading_timeout",
                "error_context": {"target": "auth-service", "timeout": 3000},
            },
        },
        correct_remediation=[
            "restart_service:auth-service",
        ],
        optimal_step_count=4,
        postmortem_source=(
            "Inspired by: Let's Encrypt root certificate expiration Oct 2021 — "
            "widespread TLS failures across millions of sites"
        ),
    ),

    # ── E5: Wrong Environment Variable ───────────────────────────────
    Scenario(
        id="easy_05",
        name="Wrong Environment Variable",
        difficulty="easy",
        description=(
            "🚨 ALERT: inventory-service connection errors. "
            "All database queries failing. Service deployed 15 minutes ago. "
            "Severity: HIGH."
        ),
        root_cause=(
            "inventory-service was deployed with DB_HOST pointing to the staging "
            "database (db-staging.internal) instead of production (inventory-db-primary.internal). "
            "All database connections fail because the staging DB is not accessible from production."
        ),
        root_cause_keywords=[
            "environment variable", "DB_HOST", "staging", "wrong", "config",
            "inventory-service", "misconfigured",
        ],
        contributing_factors=[
            "deployment pipeline picked up staging config",
            "no config validation in CD pipeline",
        ],
        affected_services=["inventory-service", "order-service"],
        primary_service="inventory-service",
        service_modifications={
            "inventory-service": {
                "health": "unhealthy",
                "error_rate_percent": 100.0,
                "uptime_hours": 0.25,
                "error_pattern": "wrong_env_var",
                "error_context": {
                    "wrong_host": "db-staging.internal",
                    "port": 5432,
                },
                "config_overrides": {"DB_HOST": "db-staging.internal"},
            },
            "order-service": {
                "health": "degraded",
                "error_rate_percent": 25.0,
                "error_pattern": "cascading_timeout",
                "error_context": {"target": "inventory-service", "timeout": 5000},
            },
        },
        correct_remediation=[
            "rollback_deploy:inventory-service",
        ],
        optimal_step_count=4,
        postmortem_source=(
            "Inspired by: GitHub 2023 — accidental staging config deployed to production"
        ),
    ),
]
