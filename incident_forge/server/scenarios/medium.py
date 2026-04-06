# incident_forge/server/scenarios/medium.py
"""
5 Medium scenarios — cascading failures, correlated issues.
Root cause in one service, symptoms in 2-3 others.
"""

from typing import List
from .easy import Scenario


MEDIUM_SCENARIOS: List[Scenario] = [
    # ── M1: Cascading Timeout Chain ───────────────────────────────────
    Scenario(
        id="medium_01",
        name="Cascading Timeout Chain",
        difficulty="medium",
        description=(
            "🚨 ALERT: api-gateway error rate at 35%. Multiple services reporting "
            "elevated latency. order-service p99 latency: 18000ms. "
            "payment-service health: degraded. Severity: HIGH."
        ),
        root_cause=(
            "payment-service has a slow downstream dependency (external payment provider) "
            "that is responding in 8000ms instead of the normal 200ms. This causes "
            "payment-service to hold connections, which causes order-service to timeout "
            "waiting for payment, which causes api-gateway to return 504s."
        ),
        root_cause_keywords=[
            "timeout", "cascade", "payment-service", "slow", "upstream",
            "downstream", "latency", "chain",
        ],
        contributing_factors=[
            "no circuit breaker configured between services",
            "timeout values too high (5000ms), allowing cascading delays",
        ],
        affected_services=["payment-service", "order-service", "api-gateway"],
        primary_service="payment-service",
        service_modifications={
            "payment-service": {
                "health": "degraded",
                "latency_p50_ms": 4200.0,
                "latency_p99_ms": 8500.0,
                "error_rate_percent": 22.0,
                "error_pattern": "cascading_timeout",
                "error_context": {"target": "external-payment-provider.com", "timeout": 8000},
            },
            "order-service": {
                "health": "degraded",
                "latency_p99_ms": 18000.0,
                "error_rate_percent": 28.0,
                "error_pattern": "cascading_timeout",
                "error_context": {"target": "payment-service", "timeout": 5000},
            },
            "api-gateway": {
                "health": "degraded",
                "error_rate_percent": 35.0,
                "latency_p99_ms": 20000.0,
                "error_pattern": "cascading_timeout",
                "error_context": {"target": "order-service", "timeout": 5000},
            },
        },
        correct_remediation=[
            "update_config:payment-service",
            "restart_service:payment-service",
        ],
        optimal_step_count=7,
        red_herrings=[
            {"service": "auth-service", "hint": "Slightly elevated latency (normal variance)"},
        ],
        postmortem_source=(
            "Inspired by: Cloudflare API gateway cascade 2023 — "
            "https://blog.cloudflare.com/post-mortem-on-cloudflare-control-plane-and-analytics-outage/"
        ),
    ),

    # ── M2: Database Replication Lag ──────────────────────────────────
    Scenario(
        id="medium_02",
        name="Database Replication Lag",
        difficulty="medium",
        description=(
            "🚨 ALERT: Intermittent 409 Conflict errors in order-service. "
            "Some users seeing stale data. Payment confirmations delayed. "
            "Error rate: 18%. Severity: MEDIUM."
        ),
        root_cause=(
            "order-service read replica (replica-02) has 30+ seconds of replication "
            "lag behind the primary database. Read-after-write operations are returning "
            "stale data, causing order state conflicts and payment mismatches."
        ),
        root_cause_keywords=[
            "replication", "lag", "replica", "stale", "read", "primary",
            "order-service", "database", "consistency",
        ],
        contributing_factors=[
            "heavy batch job running on primary consuming I/O",
            "replica disk I/O saturated",
        ],
        affected_services=["order-service", "payment-service"],
        primary_service="order-service",
        service_modifications={
            "order-service": {
                "health": "degraded",
                "error_rate_percent": 18.0,
                "error_pattern": "db_replication_lag",
                "error_context": {"lag_s": 32, "replica": "replica-02", "threshold": 5},
            },
            "payment-service": {
                "health": "degraded",
                "error_rate_percent": 8.0,
                "latency_p99_ms": 3000.0,
                "error_pattern": "cascading_timeout",
                "error_context": {"target": "order-service", "timeout": 5000},
            },
        },
        correct_remediation=[
            "restart_service:order-service",
        ],
        optimal_step_count=7,
        red_herrings=[
            {"service": "user-service", "hint": "Normal operation — red herring"},
        ],
        postmortem_source=(
            "Inspired by: GitHub MySQL replication lag incident 2022 — "
            "https://github.blog/2022-03-23-an-update-on-recent-service-disruptions/"
        ),
    ),

    # ── M3: Load Balancer Misconfiguration ────────────────────────────
    Scenario(
        id="medium_03",
        name="Load Balancer Misconfiguration",
        difficulty="medium",
        description=(
            "🚨 ALERT: Intermittent 502 errors on api-gateway — affecting ~33% of "
            "requests. Some users experience normal service, others get errors. "
            "Pattern: errors are consistent per-user session. Severity: HIGH."
        ),
        root_cause=(
            "api-gateway load balancer has 3 backends but backend-03 was drained for "
            "maintenance and never re-enabled. Traffic is being routed to a drained "
            "node, causing 502 errors for roughly 1/3 of requests."
        ),
        root_cause_keywords=[
            "load balancer", "backend", "drained", "misconfigured", "502",
            "api-gateway", "routing",
        ],
        contributing_factors=[
            "maintenance window completed but LB not updated",
            "health checks passing because the node responds to /health but rejects traffic",
        ],
        affected_services=["api-gateway", "auth-service"],
        primary_service="api-gateway",
        service_modifications={
            "api-gateway": {
                "health": "degraded",
                "error_rate_percent": 33.0,
                "error_pattern": "lb_misconfigured",
                "error_context": {
                    "backend": "backend-03",
                    "active_backends": 2,
                    "total_backends": 3,
                    "port": 8080,
                    "fail_count": 45,
                },
            },
            "auth-service": {
                "health": "degraded",
                "error_rate_percent": 15.0,
                "error_pattern": "cascading_timeout",
                "error_context": {"target": "api-gateway-backend-03", "timeout": 3000},
            },
        },
        correct_remediation=[
            "update_config:api-gateway",
            "restart_service:api-gateway",
        ],
        optimal_step_count=6,
        postmortem_source=(
            "Inspired by: AWS ALB target group deregistration issues — "
            "common production incident pattern across multiple AWS customers"
        ),
    ),

    # ── M4: API Version Mismatch ─────────────────────────────────────
    Scenario(
        id="medium_04",
        name="API Version Mismatch",
        difficulty="medium",
        description=(
            "🚨 ALERT: payment-service returning 400/422 errors on charge requests. "
            "order-service deployed new version 20 minutes ago. "
            "Error rate: 40%. Severity: HIGH."
        ),
        root_cause=(
            "order-service was deployed with an updated API client that sends v2 payload "
            "format to payment-service, but payment-service still expects v1 format. "
            "Fields like 'payment_method_v2' and 'currency_code' cause deserialization "
            "errors on the payment side."
        ),
        root_cause_keywords=[
            "API", "version", "mismatch", "v2", "v1", "deserialization",
            "order-service", "payment-service", "schema",
        ],
        contributing_factors=[
            "no API versioning strategy",
            "order-service deployed ahead of payment-service upgrade",
        ],
        affected_services=["payment-service", "order-service"],
        primary_service="order-service",
        service_modifications={
            "order-service": {
                "health": "degraded",
                "error_rate_percent": 40.0,
                "uptime_hours": 0.33,
                "error_pattern": "api_version_mismatch",
                "error_context": {},
            },
            "payment-service": {
                "health": "degraded",
                "error_rate_percent": 40.0,
                "error_pattern": "api_version_mismatch",
                "error_context": {},
            },
        },
        correct_remediation=[
            "rollback_deploy:order-service",
        ],
        optimal_step_count=6,
        red_herrings=[
            {"service": "inventory-service", "hint": "Slightly elevated p99 (noise)"},
        ],
        postmortem_source=(
            "Inspired by: Stripe API versioning lessons — "
            "https://stripe.com/blog/api-versioning"
        ),
    ),

    # ── M5: Rate Limiter Too Aggressive ──────────────────────────────
    Scenario(
        id="medium_05",
        name="Rate Limiter Too Aggressive",
        difficulty="medium",
        description=(
            "🚨 ALERT: api-gateway returning 429 Too Many Requests for ~60% of traffic. "
            "All backend services report healthy. Customer complaints surging. "
            "Severity: HIGH."
        ),
        root_cause=(
            "api-gateway rate limiter was reconfigured 30 minutes ago with a max_requests "
            "of 100/s, down from 2000/s. Normal traffic (~800/s) is being throttled. "
            "The service itself is healthy — it's the rate limiter blocking legitimate requests."
        ),
        root_cause_keywords=[
            "rate limit", "throttle", "429", "too many requests", "api-gateway",
            "max_requests", "configuration",
        ],
        contributing_factors=[
            "config change during maintenance window",
            "rate limit value was set for per-user instead of global",
        ],
        affected_services=["api-gateway"],
        primary_service="api-gateway",
        service_modifications={
            "api-gateway": {
                "health": "degraded",
                "error_rate_percent": 60.0,
                "error_pattern": "rate_limiter_aggressive",
                "error_context": {
                    "limit": 100,
                    "rate": 800,
                    "burst": 120,
                    "throttled_pct": 60,
                },
                "config_overrides": {"RATE_LIMIT_MAX_RPS": "100"},
            },
        },
        correct_remediation=[
            "update_config:api-gateway",
            "restart_service:api-gateway",
        ],
        optimal_step_count=5,
        red_herrings=[
            {"service": "payment-service", "hint": "Metrics look normal"},
            {"service": "order-service", "hint": "Lower traffic (caused by rate limiting upstream)"},
        ],
        postmortem_source=(
            "Inspired by: Shopify rate limiting incident during Black Friday — "
            "misconfigured rate limits blocking legitimate merchant API calls"
        ),
    ),
]
