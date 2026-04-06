# incident_forge/server/scenarios/hard.py
"""
5 Hard scenarios — hidden root causes, non-obvious correlation.
Requires diagnostics or config inspection to uncover.
"""

from typing import List
from .easy import Scenario


HARD_SCENARIOS: List[Scenario] = [
    # ── H1: DNS Cache Poisoning ──────────────────────────────────────
    Scenario(
        id="hard_01",
        name="DNS Cache Poisoning",
        difficulty="hard",
        description=(
            "🚨 ALERT: payment-service intermittently failing to connect to its database. "
            "Connection errors show correct hostname but connections are refused. "
            "Issue started after infrastructure migration 6 hours ago. Severity: HIGH."
        ),
        root_cause=(
            "After the infrastructure migration, the DNS cache on payment-service pods "
            "still resolves the database hostname to the OLD IP address (10.0.99.1) instead "
            "of the new IP (10.0.1.5). The stale DNS entry has a long TTL and hasn't been "
            "flushed. Logs show the correct hostname but the resolved IP is wrong."
        ),
        root_cause_keywords=[
            "DNS", "cache", "stale", "IP", "migration", "resolve", "TTL",
            "payment-service", "poisoning",
        ],
        contributing_factors=[
            "DNS TTL set to 3600s (too long for migration)",
            "no DNS cache flush in migration runbook",
        ],
        affected_services=["payment-service", "order-service"],
        primary_service="payment-service",
        service_modifications={
            "payment-service": {
                "health": "unhealthy",
                "error_rate_percent": 55.0,
                "latency_p99_ms": 5100.0,
                "error_pattern": "dns_cache_poisoning",
                "error_context": {
                    "target": "payments-db-primary.internal",
                    "wrong_ip": "10.0.99.1",
                    "correct_ip": "10.0.1.5",
                    "ttl": 3600,
                    "wrong_cn": "old-payments-db.internal",
                },
            },
            "order-service": {
                "health": "degraded",
                "error_rate_percent": 30.0,
                "error_pattern": "cascading_timeout",
                "error_context": {"target": "payment-service", "timeout": 5000},
            },
        },
        correct_remediation=[
            "restart_service:payment-service",
        ],
        optimal_step_count=8,
        red_herrings=[
            {"service": "auth-service", "hint": "Config shows correct DB_HOST"},
            {"service": "notification-service", "hint": "Minor latency spike (unrelated)"},
        ],
        postmortem_source=(
            "Inspired by: AWS Route53 DNS caching incident — stale DNS entries "
            "after failover causing persistent connection failures"
        ),
    ),

    # ── H2: Split-Brain Database ─────────────────────────────────────
    Scenario(
        id="hard_02",
        name="Split-Brain Database",
        difficulty="hard",
        description=(
            "🚨 ALERT: Data inconsistencies detected in order-service. "
            "Some orders showing conflicting states. Inventory counts diverging. "
            "No clear error spike — issue is subtle. Severity: CRITICAL."
        ),
        root_cause=(
            "A brief network partition caused the order-service database to enter "
            "split-brain state where both the primary and replica-02 accepted writes "
            "simultaneously. Data has diverged between nodes, causing conflicting "
            "order states and inventory mismatches."
        ),
        root_cause_keywords=[
            "split-brain", "partition", "dual-primary", "diverge", "conflicting",
            "writes", "order-service", "database", "consistency",
        ],
        contributing_factors=[
            "network partition between availability zones",
            "automatic failover promoted replica to primary",
            "original primary didn't detect the failover",
        ],
        affected_services=["order-service", "inventory-service", "payment-service"],
        primary_service="order-service",
        service_modifications={
            "order-service": {
                "health": "degraded",
                "error_rate_percent": 12.0,
                "error_pattern": "db_replication_lag",
                "error_context": {
                    "lag_s": -1,
                    "replica": "replica-02 (PROMOTED — dual primary!)",
                    "threshold": 0,
                },
            },
            "inventory-service": {
                "health": "degraded",
                "error_rate_percent": 8.0,
                "error_pattern": "db_replication_lag",
                "error_context": {"lag_s": 15, "replica": "replica-01"},
            },
            "payment-service": {
                "health": "degraded",
                "error_rate_percent": 5.0,
                "latency_p99_ms": 2000.0,
            },
        },
        correct_remediation=[
            "restart_service:order-service",
            "restart_service:inventory-service",
        ],
        optimal_step_count=10,
        red_herrings=[
            {"service": "api-gateway", "hint": "Error rate slightly up (from downstream)"},
            {"service": "notification-service", "hint": "Duplicate notifications being sent"},
        ],
        postmortem_source=(
            "Inspired by: GitHub 2018 database split-brain after network partition — "
            "https://github.blog/2018-10-30-oct21-post-incident-analysis/"
        ),
    ),

    # ── H3: Clock Skew ───────────────────────────────────────────────
    Scenario(
        id="hard_03",
        name="Clock Skew Causing Auth Failures",
        difficulty="hard",
        description=(
            "🚨 ALERT: auth-service rejecting valid JWT tokens intermittently. "
            "Users randomly logged out. Cache misses elevated on user-service. "
            "No recent deployments. Severity: HIGH."
        ),
        root_cause=(
            "NTP daemon on auth-service pods has stopped, causing system clock to "
            "drift +300 seconds ahead of actual time. JWT tokens are being rejected "
            "because the server thinks they're expired (or not yet valid). Cache "
            "entries on user-service are also expiring early due to clock-based TTLs."
        ),
        root_cause_keywords=[
            "clock", "skew", "NTP", "drift", "time", "JWT", "expired",
            "auth-service", "synchronization",
        ],
        contributing_factors=[
            "NTP daemon crashed after kernel update",
            "no monitoring on clock drift",
        ],
        affected_services=["auth-service", "user-service", "api-gateway"],
        primary_service="auth-service",
        service_modifications={
            "auth-service": {
                "health": "degraded",
                "error_rate_percent": 35.0,
                "error_pattern": "clock_skew",
                "error_context": {
                    "drift_s": 300,
                    "server_time": "2026-04-07T02:20:00Z",
                    "exp_time": "2026-04-07T02:15:00Z",
                },
            },
            "user-service": {
                "health": "degraded",
                "error_rate_percent": 10.0,
                "latency_p99_ms": 1800.0,
            },
            "api-gateway": {
                "health": "degraded",
                "error_rate_percent": 30.0,
                "error_pattern": "cascading_timeout",
                "error_context": {"target": "auth-service", "timeout": 3000},
            },
        },
        correct_remediation=[
            "restart_service:auth-service",
        ],
        optimal_step_count=9,
        red_herrings=[
            {"service": "order-service", "hint": "Fewer orders (caused by auth failures)"},
        ],
        postmortem_source=(
            "Inspired by: Google Spanner clock synchronization design — "
            "TrueTime API addressing clock skew in distributed systems"
        ),
    ),

    # ── H4: Slow Memory Leak (Hidden) ────────────────────────────────
    Scenario(
        id="hard_04",
        name="Slow Memory Leak with Delayed Symptoms",
        difficulty="hard",
        description=(
            "🚨 ALERT: notification-service latency increasing over last 4 hours. "
            "No deployment in 48 hours. Error rate gradually climbing: now 15%. "
            "System was stable yesterday. Severity: MEDIUM."
        ),
        root_cause=(
            "notification-service has a slow memory leak that takes hours to manifest. "
            "Memory has been climbing from 40% to 91% over the last 4 hours. "
            "The service is now spending excessive time in garbage collection, "
            "causing latency spikes and timeouts. Unlike an obvious leak, the "
            "memory growth is gradual and not immediately apparent from error logs."
        ),
        root_cause_keywords=[
            "memory", "leak", "slow", "gradual", "GC", "garbage collection",
            "notification-service", "heap",
        ],
        contributing_factors=[
            "leak introduced in deployment 48h ago but only manifests under sustained load",
            "no memory trending alerts configured",
        ],
        affected_services=["notification-service", "order-service"],
        primary_service="notification-service",
        service_modifications={
            "notification-service": {
                "health": "degraded",
                "memory_percent": 91.0,
                "latency_p50_ms": 800.0,
                "latency_p99_ms": 4500.0,
                "error_rate_percent": 15.0,
                "uptime_hours": 48.0,
                "error_pattern": "memory_leak",
                "error_context": {"mem_pct": 91, "mem_mb": 1862, "max_mb": 2048},
            },
            "order-service": {
                "health": "degraded",
                "error_rate_percent": 5.0,
                "latency_p99_ms": 5000.0,
                "error_pattern": "cascading_timeout",
                "error_context": {"target": "notification-service", "timeout": 3000},
            },
        },
        correct_remediation=[
            "restart_service:notification-service",
            "rollback_deploy:notification-service",
        ],
        optimal_step_count=9,
        red_herrings=[
            {"service": "payment-service", "hint": "Normal metrics"},
            {"service": "api-gateway", "hint": "Latency up slightly (downstream effect)"},
        ],
        postmortem_source=(
            "Inspired by: Discord 2024 — gradual memory leak in notification fanout "
            "service causing delayed message delivery"
        ),
    ),

    # ── H5: Partial Network Partition ────────────────────────────────
    Scenario(
        id="hard_05",
        name="Partial Network Partition",
        difficulty="hard",
        description=(
            "🚨 ALERT: Inconsistent behavior across services. Some user requests "
            "succeed, others fail with the same parameters. Pattern is not "
            "correlated with specific services or endpoints. Severity: HIGH."
        ),
        root_cause=(
            "A partial network partition exists between availability zones AZ-us-east-1a "
            "and AZ-us-east-1c. Pods in AZ-1a cannot reach pods in AZ-1c, but both "
            "can reach AZ-1b. This causes inconsistent behavior: requests that happen "
            "to route to pods in the same AZ succeed, cross-AZ requests fail."
        ),
        root_cause_keywords=[
            "network", "partition", "availability zone", "AZ", "pod",
            "inconsistent", "unreachable", "partial",
        ],
        contributing_factors=[
            "switch failure in the cross-AZ network fabric",
            "health checks don't test cross-AZ connectivity",
        ],
        affected_services=["api-gateway", "order-service", "payment-service", "auth-service"],
        primary_service="api-gateway",
        service_modifications={
            "api-gateway": {
                "health": "degraded",
                "error_rate_percent": 25.0,
                "error_pattern": "network_partition",
                "error_context": {
                    "pod_a": "gw-pod-az1a",
                    "pod_b": "gw-pod-az1c",
                    "az_a": "us-east-1a",
                    "az_b": "us-east-1c",
                    "target": "order-service",
                },
            },
            "order-service": {
                "health": "degraded",
                "error_rate_percent": 20.0,
                "error_pattern": "network_partition",
                "error_context": {
                    "pod_a": "order-pod-az1a",
                    "pod_b": "order-pod-az1c",
                    "az_a": "us-east-1a",
                    "az_b": "us-east-1c",
                    "target": "payment-service",
                },
            },
            "payment-service": {
                "health": "degraded",
                "error_rate_percent": 18.0,
                "error_pattern": "network_partition",
                "error_context": {
                    "pod_a": "pay-pod-az1a",
                    "pod_b": "pay-pod-az1c",
                    "az_a": "us-east-1a",
                    "az_b": "us-east-1c",
                    "target": "payments-db-primary",
                },
            },
            "auth-service": {
                "health": "degraded",
                "error_rate_percent": 15.0,
                "error_pattern": "network_partition",
                "error_context": {
                    "pod_a": "auth-pod-az1a",
                    "pod_b": "auth-pod-az1c",
                    "az_a": "us-east-1a",
                    "az_b": "us-east-1c",
                    "target": "auth-db-primary",
                },
            },
        },
        correct_remediation=[
            "scale_service:api-gateway",
            "scale_service:order-service",
        ],
        optimal_step_count=12,
        red_herrings=[
            {"service": "inventory-service", "hint": "All pods in AZ-1b — unaffected"},
            {"service": "user-service", "hint": "All pods in AZ-1b — unaffected"},
        ],
        postmortem_source=(
            "Inspired by: AWS us-east-1 partial AZ failure 2023 — "
            "network connectivity loss between specific availability zones"
        ),
    ),
]
