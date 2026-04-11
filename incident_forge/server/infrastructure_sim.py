# incident_forge/server/infrastructure_sim.py
"""
7-service microservice infrastructure simulator for IncidentForge.

Simulates a realistic e-commerce architecture with queryable logs,
metrics, configuration, and dependency information per service.
"""

from __future__ import annotations

import copy
import random
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from .log_generator import LogGenerator


# ── Service dependency graph ─────────────────────────────────────────
# api-gateway → [auth-service, user-service, order-service, notification-service]
# auth-service → []
# user-service → []
# order-service → [payment-service, inventory-service, notification-service]
# payment-service → []
# inventory-service → []
# notification-service → []

SERVICE_GRAPH: Dict[str, Dict[str, Any]] = {
    "api-gateway": {
        "dependencies": ["auth-service", "user-service", "order-service", "notification-service"],
        "dependents": [],
        "port": 8080,
        "db": None,
        "description": "Entry point — routes requests to backend services",
    },
    "auth-service": {
        "dependencies": [],
        "dependents": ["api-gateway"],
        "port": 8081,
        "db": "auth-db",
        "description": "JWT authentication and authorization",
    },
    "user-service": {
        "dependencies": [],
        "dependents": ["api-gateway"],
        "port": 8082,
        "db": "users-db",
        "description": "User profiles and preferences",
    },
    "order-service": {
        "dependencies": ["payment-service", "inventory-service", "notification-service"],
        "dependents": ["api-gateway"],
        "port": 8083,
        "db": "orders-db",
        "description": "Order creation, management, and fulfillment",
    },
    "payment-service": {
        "dependencies": [],
        "dependents": ["order-service"],
        "port": 8084,
        "db": "payments-db",
        "description": "Payment processing and transaction management",
    },
    "inventory-service": {
        "dependencies": [],
        "dependents": ["order-service"],
        "port": 8085,
        "db": "inventory-db",
        "description": "Inventory tracking and stock management",
    },
    "notification-service": {
        "dependencies": [],
        "dependents": ["api-gateway", "order-service"],
        "port": 8086,
        "db": None,
        "description": "Email, SMS, and push notification delivery",
    },
}


@dataclass
class ServiceState:
    """Mutable state of a single service."""

    name: str
    health: str = "healthy"  # healthy / degraded / unhealthy / unreachable
    cpu_percent: float = 12.0
    memory_percent: float = 35.0
    latency_p50_ms: float = 25.0
    latency_p99_ms: float = 85.0
    error_rate_percent: float = 0.1
    request_rate_per_sec: float = 450.0
    db_connections_active: int = 5
    db_connections_max: int = 20
    disk_usage_percent: float = 42.0
    uptime_hours: float = 168.0
    replicas: int = 3
    config: Dict[str, str] = field(default_factory=dict)
    recent_deployments: List[Dict[str, str]] = field(default_factory=list)
    # Internal — populated during scenario injection
    _error_pattern: Optional[str] = None
    _error_context: Optional[Dict[str, Any]] = None
    _config_updated: bool = False


class InfrastructureSimulator:
    """Simulates a 7-service microservices architecture."""

    def __init__(self, seed: Optional[int] = None):
        self._rng = random.Random(seed)
        self._log_gen = LogGenerator(seed=seed)
        self.services: Dict[str, ServiceState] = self._init_services()
        self._alerts: List[str] = []

    # ── Initialisation ────────────────────────────────────────────────

    def _init_services(self) -> Dict[str, ServiceState]:
        """Create 7 services with realistic healthy baseline metrics."""
        services: Dict[str, ServiceState] = {}
        for name, meta in SERVICE_GRAPH.items():
            svc = ServiceState(
                name=name,
                cpu_percent=round(self._rng.uniform(8, 25), 1),
                memory_percent=round(self._rng.uniform(25, 50), 1),
                latency_p50_ms=round(self._rng.uniform(10, 45), 1),
                latency_p99_ms=round(self._rng.uniform(50, 150), 1),
                error_rate_percent=round(self._rng.uniform(0.01, 0.5), 2),
                request_rate_per_sec=round(self._rng.uniform(200, 800), 1),
                db_connections_active=self._rng.randint(2, 8) if meta["db"] else 0,
                db_connections_max=20 if meta["db"] else 0,
                disk_usage_percent=round(self._rng.uniform(30, 55), 1),
                uptime_hours=round(self._rng.uniform(48, 720), 1),
                config=self._default_config(name, meta),
                recent_deployments=[
                    {
                        "version": f"v1.{self._rng.randint(10, 30)}.{self._rng.randint(0, 9)}",
                        "timestamp": "2026-04-06T14:00:00Z",
                        "status": "success",
                    }
                ],
            )
            services[name] = svc
        return services

    def _default_config(self, name: str, meta: dict) -> Dict[str, str]:
        """Default healthy configuration for a service."""
        cfg: Dict[str, str] = {
            "SERVICE_NAME": name,
            "PORT": str(meta["port"]),
            "LOG_LEVEL": "INFO",
            "ENVIRONMENT": "production",
            "REQUEST_TIMEOUT_MS": "5000",
            "RETRY_COUNT": "3",
        }
        if meta["db"]:
            cfg.update({
                "DB_HOST": f"{meta['db']}-primary.internal",
                "DB_PORT": "5432",
                "DB_POOL_MAX_SIZE": "20",
                "DB_POOL_TIMEOUT_MS": "5000",
                "DB_NAME": meta["db"],
            })
        for dep in meta["dependencies"]:
            dep_meta = SERVICE_GRAPH[dep]
            key = dep.upper().replace("-", "_") + "_URL"
            cfg[key] = f"http://{dep}.internal:{dep_meta['port']}"
        return cfg

    # ── Scenario injection ────────────────────────────────────────────

    def inject_incident(self, scenario: Any) -> None:
        """Modify service states to simulate an incident from a scenario."""
        self._alerts.clear()

        for svc_name, mods in scenario.service_modifications.items():
            if svc_name not in self.services:
                continue
            svc = self.services[svc_name]
            for key, value in mods.items():
                if key == "config_overrides" and isinstance(value, dict):
                    svc.config.update(value)
                elif key == "error_pattern":
                    svc._error_pattern = value
                elif key == "error_context":
                    svc._error_context = value
                elif hasattr(svc, key):
                    setattr(svc, key, value)

        # Generate alerts from affected services
        for svc_name in scenario.affected_services:
            svc = self.services.get(svc_name)
            if svc and svc.health != "healthy":
                self._alerts.append(
                    f"🚨 {svc.name} — status: {svc.health}, error rate: {svc.error_rate_percent}%"
                )

        # Inject subtle anomalies for red herring services (misleading but realistic)
        for herring in getattr(scenario, "red_herrings", []):
            svc_name = herring.get("service", "")
            if svc_name in self.services:
                svc = self.services[svc_name]
                # Slightly elevated metrics — looks suspicious but is normal variance
                svc.latency_p99_ms = round(svc.latency_p99_ms * self._rng.uniform(1.1, 1.4), 1)
                svc.cpu_percent = round(min(55.0, svc.cpu_percent + self._rng.uniform(3, 12)), 1)
                svc.error_rate_percent = round(
                    min(3.0, svc.error_rate_percent + self._rng.uniform(0.2, 1.5)), 2
                )

    # ── Queries (what the agent calls) ────────────────────────────────

    def get_logs(self, service_name: str) -> str:
        """Return formatted logs for a service."""
        svc = self._get_service(service_name)
        if svc is None:
            return f"ERROR: Service '{service_name}' not found. Available: {', '.join(self.services.keys())}"

        if svc._error_pattern:
            logs = self._log_gen.generate_mixed_logs(
                service_name,
                svc._error_pattern,
                error_ratio=min(0.7, svc.error_rate_percent / 100 + 0.2),
                total=15,
                context=svc._error_context,
            )
        else:
            logs = self._log_gen.generate_healthy_logs(service_name, 12)

        return "\n".join(logs)

    def get_metrics(self, service_name: str) -> str:
        """Return formatted metrics for a service."""
        svc = self._get_service(service_name)
        if svc is None:
            return f"ERROR: Service '{service_name}' not found."

        lines = [
            f"=== Metrics: {svc.name} ===",
            f"Health:            {svc.health}",
            f"CPU:               {svc.cpu_percent}%",
            f"Memory:            {svc.memory_percent}%",
            f"Disk Usage:        {svc.disk_usage_percent}%",
            f"Latency p50:       {svc.latency_p50_ms}ms",
            f"Latency p99:       {svc.latency_p99_ms}ms",
            f"Error Rate:        {svc.error_rate_percent}%",
            f"Request Rate:      {svc.request_rate_per_sec}/s",
            f"Replicas:          {svc.replicas}",
            f"Uptime:            {svc.uptime_hours}h",
        ]
        if svc.db_connections_max > 0:
            fullness = "FULL" if svc.db_connections_active >= svc.db_connections_max else "OK"
            lines.append(
                f"DB Connections:    {svc.db_connections_active}/{svc.db_connections_max} ({fullness})"
            )
        return "\n".join(lines)

    def get_config(self, service_name: str) -> str:
        """Return configuration for a service."""
        svc = self._get_service(service_name)
        if svc is None:
            return f"ERROR: Service '{service_name}' not found."

        lines = [f"=== Config: {svc.name} ==="]
        for k, v in sorted(svc.config.items()):
            lines.append(f"{k}={v}")
        return "\n".join(lines)

    def get_dependencies(self, service_name: str) -> str:
        """Return dependency graph for a service."""
        if service_name not in SERVICE_GRAPH:
            return f"ERROR: Service '{service_name}' not found."

        meta = SERVICE_GRAPH[service_name]
        lines = [f"=== Dependencies: {service_name} ==="]

        if meta["dependencies"]:
            lines.append("Upstream (services this depends on):")
            for dep in meta["dependencies"]:
                dep_svc = self.services.get(dep)
                status = dep_svc.health if dep_svc else "unknown"
                lines.append(f"  → {dep} [{status}]")
        else:
            lines.append("Upstream: none (leaf service)")

        if meta["dependents"]:
            lines.append("Downstream (services that depend on this):")
            for dep in meta["dependents"]:
                dep_svc = self.services.get(dep)
                status = dep_svc.health if dep_svc else "unknown"
                lines.append(f"  ← {dep} [{status}]")
        else:
            lines.append("Downstream: none")

        return "\n".join(lines)

    def run_diagnostic(self, service_name: str, params: dict) -> str:
        """Simulate running a diagnostic command on a service."""
        svc = self._get_service(service_name)
        if svc is None:
            return f"ERROR: Service '{service_name}' not found."

        command = params.get("command", "health_check")

        if command == "health_check":
            return (
                f"Health check for {service_name}: {svc.health}\n"
                f"  Latency: {svc.latency_p99_ms}ms\n"
                f"  Error rate: {svc.error_rate_percent}%"
            )
        elif command == "connection_test":
            target = params.get("target", "")
            if svc.health == "unhealthy":
                return f"Connection test {service_name} → {target}: FAILED (timeout after 5000ms)"
            return f"Connection test {service_name} → {target}: OK (latency: {self._rng.randint(1, 50)}ms)"
        elif command == "dns_lookup":
            domain = params.get("domain", svc.config.get("DB_HOST", f"{service_name}.internal"))
            if svc._error_pattern == "dns_cache_poisoning":
                ctx = svc._error_context or {}
                return (
                    f"DNS lookup for {domain}:\n"
                    f"  Resolved: {ctx.get('wrong_ip', '10.0.99.1')} (CACHED — stale)\n"
                    f"  Expected: {ctx.get('correct_ip', '10.0.1.5')}\n"
                    f"  TTL remaining: {ctx.get('ttl', 3600)}s\n"
                    f"  ⚠️ WARNING: Resolved IP does not match expected"
                )
            return f"DNS lookup for {domain}:\n  Resolved: 10.0.1.{self._rng.randint(1, 254)} (OK)\n  TTL: 300s"
        elif command == "disk_check":
            return (
                f"Disk usage for {service_name}:\n"
                f"  /app:     {self._rng.randint(20, 40)}% used\n"
                f"  /var/log: {svc.disk_usage_percent}% used\n"
                f"  /tmp:     {self._rng.randint(5, 15)}% used"
            )
        elif command == "memory_dump":
            if svc._error_pattern and "memory" in svc._error_pattern:
                return (
                    f"Memory analysis for {service_name}:\n"
                    f"  Heap used: {svc.memory_percent}%\n"
                    f"  Top allocators:\n"
                    f"    1. RequestHandler  — 45% (LEAK SUSPECTED)\n"
                    f"    2. ConnectionPool  — 20%\n"
                    f"    3. CacheManager    — 15%\n"
                    f"  GC collections (last 5min): {self._rng.randint(40, 150)}"
                )
            return (
                f"Memory analysis for {service_name}:\n"
                f"  Heap used: {svc.memory_percent}%\n"
                f"  Top allocators:\n"
                f"    1. ConnectionPool  — 25%\n"
                f"    2. CacheManager    — 20%\n"
                f"    3. RequestHandler  — 15%\n"
                f"  GC collections (last 5min): {self._rng.randint(2, 10)}"
            )
        elif command == "replication_status":
            if svc._error_pattern == "db_replication_lag":
                ctx = svc._error_context or {}
                return (
                    f"Replication status for {service_name} DB:\n"
                    f"  Primary: {svc.config.get('DB_HOST', 'primary.internal')} — ONLINE\n"
                    f"  Replica-01: ONLINE — lag: 0.5s ✅\n"
                    f"  Replica-02: ONLINE — lag: {ctx.get('lag_s', 30)}s ⚠️ BEHIND\n"
                    f"  Replica-03: ONLINE — lag: 1.2s ✅"
                )
            return (
                f"Replication status for {service_name} DB:\n"
                f"  Primary: {svc.config.get('DB_HOST', 'primary.internal')} — ONLINE\n"
                f"  Replica-01: ONLINE — lag: 0.3s ✅\n"
                f"  Replica-02: ONLINE — lag: 0.5s ✅"
            )
        elif command == "clock_check":
            if svc._error_pattern == "clock_skew":
                ctx = svc._error_context or {}
                return (
                    f"Clock sync status for {service_name}:\n"
                    f"  System time: {ctx.get('server_time', '2026-04-07T02:15:00Z')}\n"
                    f"  NTP reference: 2026-04-07T02:10:00Z\n"
                    f"  Drift: +{ctx.get('drift_s', 300)}s ⚠️ CRITICAL\n"
                    f"  NTP daemon: STOPPED"
                )
            return (
                f"Clock sync status for {service_name}:\n"
                f"  System time: 2026-04-07T02:14:33Z\n"
                f"  NTP reference: 2026-04-07T02:14:33Z\n"
                f"  Drift: <0.1s ✅"
            )
        else:
            return f"Unknown diagnostic command: '{command}'. Available: health_check, connection_test, dns_lookup, disk_check, memory_dump, replication_status, clock_check"

    # ── Remediation actions ───────────────────────────────────────────

    def restart_service(self, service_name: str) -> str:
        """Simulate restarting a service."""
        svc = self._get_service(service_name)
        if svc is None:
            return f"ERROR: Service '{service_name}' not found."

        old_health = svc.health
        svc.uptime_hours = 0.0

        # ── Memory leak: restart clears heap ──────────────────────────
        if svc._error_pattern and "memory" in svc._error_pattern:
            svc.memory_percent = round(self._rng.uniform(25, 40), 1)
            svc.health = "healthy"
            svc.error_rate_percent = round(self._rng.uniform(0.1, 1.0), 2)
            return (
                f"Service {service_name} restarted successfully.\n"
                f"  Previous health: {old_health}\n"
                f"  Current health: {svc.health}\n"
                f"  Memory cleared: {svc.memory_percent}%\n"
                f"  ⚠️ Note: Memory leak may recur if root cause not addressed."
            )

        # ── Direct-restart patterns: restart itself fixes the issue ───
        elif svc._error_pattern in ("ssl_expired", "dns_cache_poisoning", "clock_skew"):
            heal_reasons = {
                "ssl_expired": "TLS certificate reloaded from renewed source",
                "dns_cache_poisoning": "DNS cache flushed — resolving to correct IP",
                "clock_skew": "NTP daemon restarted — clock synchronized",
            }
            reason = heal_reasons[svc._error_pattern]
            svc.health = "healthy"
            svc.error_rate_percent = round(self._rng.uniform(0.1, 1.0), 2)
            svc.latency_p50_ms = round(self._rng.uniform(10, 40), 1)
            svc.latency_p99_ms = round(self._rng.uniform(50, 150), 1)
            svc._error_pattern = None
            return (
                f"Service {service_name} restarted successfully.\n"
                f"  Previous health: {old_health}\n"
                f"  Current health: healthy ✅\n"
                f"  {reason}.\n"
                f"  Error rate: {svc.error_rate_percent}%"
            )

        # ── DB replication lag: restart reconnects to primary ─────────
        elif svc._error_pattern == "db_replication_lag":
            svc.health = "healthy"
            svc.error_rate_percent = round(self._rng.uniform(0.1, 1.0), 2)
            svc.latency_p99_ms = round(self._rng.uniform(50, 150), 1)
            svc._error_pattern = None
            return (
                f"Service {service_name} restarted successfully.\n"
                f"  Previous health: {old_health}\n"
                f"  Current health: healthy ✅\n"
                f"  Database connections re-established to primary.\n"
                f"  Stale replica connections cleared.\n"
                f"  Error rate: {svc.error_rate_percent}%"
            )

        # ── Config-dependent: restart heals ONLY if config was fixed ──
        elif svc._error_pattern == "connection_pool_exhausted" and svc._config_updated:
            new_pool = int(svc.config.get("DB_POOL_MAX_SIZE", "20"))
            svc.health = "healthy"
            svc.error_rate_percent = round(self._rng.uniform(0.1, 0.5), 2)
            svc.latency_p50_ms = round(self._rng.uniform(15, 35), 1)
            svc.latency_p99_ms = round(self._rng.uniform(50, 120), 1)
            svc.db_connections_active = self._rng.randint(5, max(6, new_pool // 2))
            svc.db_connections_max = new_pool
            svc._error_pattern = None
            return (
                f"Service {service_name} restarted successfully.\n"
                f"  Previous health: {old_health}\n"
                f"  Current health: healthy ✅\n"
                f"  Connection pool: {svc.db_connections_active}/{new_pool}\n"
                f"  Error rate: {svc.error_rate_percent}%\n"
                f"  Latency p99: {svc.latency_p99_ms}ms"
            )

        elif svc._error_pattern == "disk_full" and svc._config_updated:
            svc.health = "healthy"
            svc.error_rate_percent = round(self._rng.uniform(0.1, 0.5), 2)
            svc.disk_usage_percent = round(self._rng.uniform(40, 60), 1)
            svc._error_pattern = None
            return (
                f"Service {service_name} restarted successfully.\n"
                f"  Previous health: {old_health}\n"
                f"  Current health: healthy ✅\n"
                f"  Stale log files cleaned on restart.\n"
                f"  Disk usage: {svc.disk_usage_percent}%\n"
                f"  Log level updated — volume reduced."
            )

        elif svc._error_pattern == "rate_limiter_aggressive" and svc._config_updated:
            svc.health = "healthy"
            svc.error_rate_percent = round(self._rng.uniform(0.1, 1.0), 2)
            svc._error_pattern = None
            return (
                f"Service {service_name} restarted successfully.\n"
                f"  Previous health: {old_health}\n"
                f"  Current health: healthy ✅\n"
                f"  Rate limiter configuration reloaded.\n"
                f"  Legitimate traffic now flowing normally."
            )

        elif svc._error_pattern == "lb_misconfigured" and svc._config_updated:
            svc.health = "healthy"
            svc.error_rate_percent = round(self._rng.uniform(0.1, 0.5), 2)
            svc._error_pattern = None
            return (
                f"Service {service_name} restarted successfully.\n"
                f"  Previous health: {old_health}\n"
                f"  Current health: healthy ✅\n"
                f"  Load balancer configuration reloaded.\n"
                f"  All backends now active and receiving traffic."
            )

        # ── Cascading timeout: heals if config fixed OR upstream recovered ─
        elif svc._error_pattern == "cascading_timeout":
            upstream_target = (svc._error_context or {}).get("target", "")
            upstream_svc = self._get_service(upstream_target)
            upstream_fixed = upstream_svc is not None and upstream_svc.health == "healthy"
            if upstream_fixed or svc._config_updated:
                svc.health = "healthy"
                svc.error_rate_percent = round(self._rng.uniform(0.1, 1.0), 2)
                svc.latency_p50_ms = round(self._rng.uniform(15, 40), 1)
                svc.latency_p99_ms = round(self._rng.uniform(50, 200), 1)
                svc._error_pattern = None
                reason = "Upstream dependency recovered" if upstream_fixed else "Timeout configuration applied"
                return (
                    f"Service {service_name} restarted successfully.\n"
                    f"  Previous health: {old_health}\n"
                    f"  Current health: healthy ✅\n"
                    f"  {reason}.\n"
                    f"  Error rate: {svc.error_rate_percent}%"
                )

        # ── No error pattern but degraded (indirect downstream effect) ─
        elif svc.health != "healthy" and svc._error_pattern is None:
            svc.health = "healthy"
            svc.error_rate_percent = round(self._rng.uniform(0.1, 1.0), 2)
            svc.latency_p99_ms = round(self._rng.uniform(50, 150), 1)
            return (
                f"Service {service_name} restarted successfully.\n"
                f"  Previous health: {old_health}\n"
                f"  Current health: healthy ✅\n"
                f"  Downstream effects cleared — cached state reset."
            )

        # ── Fallback: root cause still present, restart doesn't help ──
        elif svc.health != "healthy":
            return (
                f"Service {service_name} restarted.\n"
                f"  Previous health: {old_health}\n"
                f"  Current health: {svc.health} (no change — underlying issue persists)\n"
                f"  ℹ️ Restart alone may not fix the root cause."
            )
        return f"Service {service_name} restarted. Health: healthy. Uptime reset to 0h."

    def scale_service(self, service_name: str, params: dict) -> str:
        """Simulate scaling a service."""
        svc = self._get_service(service_name)
        if svc is None:
            return f"ERROR: Service '{service_name}' not found."

        replicas = params.get("replicas", svc.replicas + 1)
        old_replicas = svc.replicas
        svc.replicas = replicas

        # Network partition: new pods in healthy AZs restore connectivity
        if svc._error_pattern == "network_partition" and replicas > old_replicas:
            svc.health = "healthy"
            svc.error_rate_percent = round(self._rng.uniform(1.0, 5.0), 2)
            svc._error_pattern = None
            return (
                f"Scaled {service_name}: {old_replicas} → {replicas} replicas.\n"
                f"  New pods scheduled across healthy availability zones.\n"
                f"  Health: healthy ✅\n"
                f"  Error rate: {svc.error_rate_percent}% (improving)\n"
                f"  ℹ️ Cross-AZ connectivity restored via new pod placement."
            )

        return (
            f"Scaled {service_name}: {old_replicas} → {replicas} replicas.\n"
            f"  ℹ️ New replicas may take 30-60s to be ready."
        )

    def rollback_deploy(self, service_name: str) -> str:
        """Simulate rolling back to previous deployment."""
        svc = self._get_service(service_name)
        if svc is None:
            return f"ERROR: Service '{service_name}' not found."

        if svc._error_pattern in ("api_version_mismatch", "wrong_env_var"):
            svc.health = "healthy"
            svc.error_rate_percent = round(self._rng.uniform(0.01, 0.5), 2)
            svc.latency_p99_ms = round(self._rng.uniform(50, 150), 1)
            return (
                f"Rolled back {service_name} to previous version.\n"
                f"  Health: healthy ✅\n"
                f"  Error rate: {svc.error_rate_percent}%\n"
                f"  ℹ️ Deployment issue resolved by rollback."
            )
        return (
            f"Rolled back {service_name} to previous version.\n"
            f"  Health: {svc.health} (unchanged — issue not deployment-related)"
        )

    def update_config(self, service_name: str, params: dict) -> str:
        """Simulate updating configuration."""
        svc = self._get_service(service_name)
        if svc is None:
            return f"ERROR: Service '{service_name}' not found."

        changes = {k: str(v) for k, v in params.items()}
        old_values = {k: svc.config.get(k, "<not set>") for k in changes}
        svc.config.update(changes)
        svc._config_updated = True  # Track that config was modified

        lines = [f"Config updated for {service_name}:"]
        for k, v in changes.items():
            lines.append(f"  {k}: {old_values[k]} → {v}")

        # Check if this fixes a config-related issue
        if svc._error_pattern == "connection_pool_exhausted":
            new_pool = int(svc.config.get("DB_POOL_MAX_SIZE", "20"))
            if new_pool > svc.db_connections_active:
                svc.db_connections_max = new_pool
                lines.append(f"  ℹ️ Pool size increased. Restart required to take effect.")
        elif svc._error_pattern == "wrong_env_var":
            lines.append(f"  ℹ️ Config applied. Restart required to reload.")
        elif svc._error_pattern == "rate_limiter_aggressive":
            lines.append(f"  ℹ️ Rate limit config updated. Restart required to take effect.")
        elif svc._error_pattern == "lb_misconfigured":
            lines.append(f"  ℹ️ Load balancer config updated. Restart required to take effect.")
        elif svc._error_pattern == "disk_full":
            lines.append(f"  ℹ️ Log config updated. Restart required to clear stale logs.")
        elif svc._error_pattern == "cascading_timeout":
            lines.append(f"  ℹ️ Timeout config updated. Restart required to take effect.")

        return "\n".join(lines)

    # ── Helper queries ────────────────────────────────────────────────

    def get_active_alerts(self) -> str:
        if not self._alerts:
            return "No active alerts."
        return "\n".join(self._alerts)

    def get_affected_service_names(self) -> List[str]:
        return [name for name, svc in self.services.items() if svc.health != "healthy"]

    def get_current_severity(self) -> str:
        unhealthy_count = sum(1 for s in self.services.values() if s.health != "healthy")
        if unhealthy_count == 0:
            return "low"
        elif unhealthy_count == 1:
            return "medium"
        elif unhealthy_count <= 3:
            return "high"
        return "critical"

    def _get_service(self, name: str) -> Optional[ServiceState]:
        return self.services.get(name)
