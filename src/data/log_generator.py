"""Synthetic log generator for LogSleuth demo.

Generates realistic microservice logs for an e-commerce platform including:
- Normal operation logs
- Error cascades and incident scenarios
- Distributed traces across services
"""

import uuid
import random
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, field


# Service definitions for our e-commerce platform
SERVICES = {
    "api-gateway": {
        "version": "2.1.0",
        "hosts": ["prod-gateway-01", "prod-gateway-02"],
        "endpoints": ["/api/v1/users", "/api/v1/checkout", "/api/v1/products", "/api/v1/orders"],
    },
    "user-service": {
        "version": "1.5.2",
        "hosts": ["prod-user-01", "prod-user-02"],
        "endpoints": ["/users", "/users/auth", "/users/profile"],
    },
    "checkout-service": {
        "version": "3.0.1",
        "hosts": ["prod-checkout-01", "prod-checkout-02"],
        "endpoints": ["/checkout", "/checkout/validate", "/checkout/complete"],
    },
    "payment-service": {
        "version": "2.2.0",
        "hosts": ["prod-payment-01"],
        "endpoints": ["/payments/process", "/payments/verify", "/payments/refund"],
    },
    "inventory-service": {
        "version": "1.8.3",
        "hosts": ["prod-inventory-01", "prod-inventory-02"],
        "endpoints": ["/inventory/check", "/inventory/reserve", "/inventory/release"],
    },
}

# Log levels
LOG_LEVELS = ["debug", "info", "warn", "error"]

# Cloud configuration
CLOUD_CONFIG = {
    "provider": "aws",
    "region": "us-east-1",
    "availability_zones": ["us-east-1a", "us-east-1b"],
}


@dataclass
class LogEntry:
    """Represents a single log entry in ECS format."""
    timestamp: datetime
    service_name: str
    log_level: str
    message: str
    trace_id: Optional[str] = None
    span_id: Optional[str] = None
    host_name: Optional[str] = None
    error_type: Optional[str] = None
    error_message: Optional[str] = None
    error_stack_trace: Optional[str] = None
    http_method: Optional[str] = None
    http_path: Optional[str] = None
    http_status_code: Optional[int] = None
    event_duration: Optional[int] = None  # nanoseconds
    event_outcome: Optional[str] = None
    user_id: Optional[str] = None
    labels: Dict[str, str] = field(default_factory=dict)

    def to_ecs_dict(self) -> Dict[str, Any]:
        """Convert to ECS-compatible dictionary."""
        service_config = SERVICES.get(self.service_name, {})
        host = self.host_name or random.choice(service_config.get("hosts", ["unknown"]))

        doc = {
            "@timestamp": self.timestamp.isoformat(),
            "log": {"level": self.log_level},
            "message": self.message,
            "service": {
                "name": self.service_name,
                "version": service_config.get("version", "1.0.0"),
                "environment": "production",
            },
            "host": {
                "name": host,
                "hostname": f"{host}.internal",
            },
            "cloud": {
                "provider": CLOUD_CONFIG["provider"],
                "region": CLOUD_CONFIG["region"],
                "availability_zone": random.choice(CLOUD_CONFIG["availability_zones"]),
            },
            "event": {},
        }

        # Add trace context
        if self.trace_id:
            doc["trace"] = {"id": self.trace_id}
        if self.span_id:
            doc["span"] = {"id": self.span_id}

        # Add error information
        if self.error_type:
            doc["error"] = {
                "type": self.error_type,
                "message": self.error_message or self.message,
            }
            if self.error_stack_trace:
                doc["error"]["stack_trace"] = self.error_stack_trace

        # Add HTTP information
        if self.http_method:
            doc["http"] = {
                "request": {
                    "method": self.http_method,
                    "path": self.http_path or "/",
                },
            }
            if self.http_status_code:
                doc["http"]["response"] = {"status_code": self.http_status_code}

        # Add event information
        if self.event_duration:
            doc["event"]["duration"] = self.event_duration
        if self.event_outcome:
            doc["event"]["outcome"] = self.event_outcome

        # Add user information
        if self.user_id:
            doc["user"] = {"id": self.user_id}

        # Add labels
        if self.labels:
            doc["labels"] = self.labels

        return doc


def generate_trace_id() -> str:
    """Generate a trace ID."""
    return uuid.uuid4().hex[:32]


def generate_span_id() -> str:
    """Generate a span ID."""
    return uuid.uuid4().hex[:16]


def generate_normal_logs(
    base_time: datetime,
    duration_minutes: int = 60,
    logs_per_minute: int = 50,
) -> List[LogEntry]:
    """
    Generate normal operation logs across all services.

    Args:
        base_time: Starting timestamp
        duration_minutes: How many minutes of logs to generate
        logs_per_minute: Average logs per minute

    Returns:
        List of LogEntry objects
    """
    logs = []
    current_time = base_time

    for minute in range(duration_minutes):
        num_logs = random.randint(logs_per_minute - 10, logs_per_minute + 10)

        for _ in range(num_logs):
            # Random time within this minute
            timestamp = current_time + timedelta(seconds=random.uniform(0, 60))

            # Pick a random service
            service_name = random.choice(list(SERVICES.keys()))
            service_config = SERVICES[service_name]

            # Generate a trace for this request
            trace_id = generate_trace_id()
            user_id = f"user-{random.randint(1000, 9999)}"

            # Most logs are info level during normal operation
            log_level = random.choices(
                ["debug", "info", "warn"],
                weights=[0.1, 0.85, 0.05]
            )[0]

            endpoint = random.choice(service_config["endpoints"])
            duration_ms = random.randint(10, 200)

            message = f"Handled request to {endpoint} in {duration_ms}ms"

            logs.append(LogEntry(
                timestamp=timestamp,
                service_name=service_name,
                log_level=log_level,
                message=message,
                trace_id=trace_id,
                span_id=generate_span_id(),
                http_method="GET" if "check" in endpoint else random.choice(["GET", "POST"]),
                http_path=endpoint,
                http_status_code=200,
                event_duration=duration_ms * 1_000_000,  # Convert to nanoseconds
                event_outcome="success",
                user_id=user_id,
            ))

        current_time += timedelta(minutes=1)

    return logs


def generate_database_failure_incident(
    incident_time: datetime,
) -> List[LogEntry]:
    """
    Generate logs for a database connection failure incident.

    Scenario: Database primary failover causes connection pool exhaustion,
    cascading through payment-service → checkout-service → api-gateway.

    Args:
        incident_time: When the incident starts

    Returns:
        List of LogEntry objects representing the incident
    """
    logs = []

    # Phase 1: Database failover begins (payment-service notices first)
    # T+0: First connection errors
    for i in range(5):
        trace_id = generate_trace_id()
        timestamp = incident_time + timedelta(seconds=i * 0.5)

        logs.append(LogEntry(
            timestamp=timestamp,
            service_name="payment-service",
            log_level="error",
            message="Failed to acquire database connection from pool",
            trace_id=trace_id,
            span_id=generate_span_id(),
            error_type="ConnectionPoolExhaustedException",
            error_message="Cannot acquire connection from pool - pool exhausted",
            error_stack_trace="""com.zaxxer.hikari.pool.HikariPool.connectionException(HikariPool.java:128)
    at com.zaxxer.hikari.pool.HikariPool.getConnection(HikariPool.java:186)
    at com.ecommerce.payment.repository.PaymentRepository.processPayment(PaymentRepository.java:45)
    at com.ecommerce.payment.service.PaymentService.process(PaymentService.java:78)""",
            http_method="POST",
            http_path="/payments/process",
            http_status_code=500,
            event_outcome="failure",
            user_id=f"user-{random.randint(1000, 9999)}",
            labels={"db_pool_size": "10", "active_connections": "10"},
        ))

    # T+3s: Database connection refused errors
    for i in range(10):
        trace_id = generate_trace_id()
        timestamp = incident_time + timedelta(seconds=3 + i * 0.3)

        logs.append(LogEntry(
            timestamp=timestamp,
            service_name="payment-service",
            log_level="error",
            message="Connection refused to database primary",
            trace_id=trace_id,
            span_id=generate_span_id(),
            error_type="ConnectionException",
            error_message="Connection refused: connect",
            error_stack_trace="""java.net.ConnectException: Connection refused: connect
    at java.net.PlainSocketImpl.socketConnect(PlainSocketImpl.java:130)
    at com.mysql.jdbc.ConnectionImpl.createNewIO(ConnectionImpl.java:836)
    at com.ecommerce.payment.repository.PaymentRepository.getConnection(PaymentRepository.java:32)""",
            http_method="POST",
            http_path="/payments/process",
            http_status_code=500,
            event_outcome="failure",
            user_id=f"user-{random.randint(1000, 9999)}",
            labels={"db_host": "db-primary.internal", "db_port": "3306"},
        ))

    # T+5s: Warning about database failover detected
    logs.append(LogEntry(
        timestamp=incident_time + timedelta(seconds=5),
        service_name="payment-service",
        log_level="warn",
        message="Database primary appears to be down, attempting reconnection",
        trace_id=generate_trace_id(),
        span_id=generate_span_id(),
        labels={"failover_detected": "true"},
    ))

    # Phase 2: Cascade to checkout-service (T+8s)
    for i in range(15):
        trace_id = generate_trace_id()
        timestamp = incident_time + timedelta(seconds=8 + i * 0.4)

        # First log: checkout-service trying to call payment-service
        logs.append(LogEntry(
            timestamp=timestamp,
            service_name="checkout-service",
            log_level="error",
            message="Payment service call failed - upstream service error",
            trace_id=trace_id,
            span_id=generate_span_id(),
            error_type="UpstreamServiceException",
            error_message="Payment service returned 500 Internal Server Error",
            http_method="POST",
            http_path="/checkout/complete",
            http_status_code=500,
            event_duration=5000 * 1_000_000,  # 5 second timeout
            event_outcome="failure",
            user_id=f"user-{random.randint(1000, 9999)}",
            labels={"upstream_service": "payment-service", "retry_count": str(random.randint(0, 3))},
        ))

    # Phase 3: Cascade to api-gateway (T+15s)
    for i in range(20):
        trace_id = generate_trace_id()
        timestamp = incident_time + timedelta(seconds=15 + i * 0.3)

        logs.append(LogEntry(
            timestamp=timestamp,
            service_name="api-gateway",
            log_level="error",
            message="Request failed - checkout service unavailable",
            trace_id=trace_id,
            span_id=generate_span_id(),
            error_type="ServiceUnavailableException",
            error_message="Checkout service is not responding",
            http_method="POST",
            http_path="/api/v1/checkout",
            http_status_code=503,
            event_duration=30000 * 1_000_000,  # 30 second timeout
            event_outcome="failure",
            user_id=f"user-{random.randint(1000, 9999)}",
            labels={"downstream_service": "checkout-service"},
        ))

    # Phase 4: Circuit breaker kicks in (T+25s)
    logs.append(LogEntry(
        timestamp=incident_time + timedelta(seconds=25),
        service_name="checkout-service",
        log_level="warn",
        message="Circuit breaker OPEN for payment-service - failing fast",
        trace_id=generate_trace_id(),
        span_id=generate_span_id(),
        labels={"circuit_breaker_state": "OPEN", "failure_count": "15"},
    ))

    # T+30s: More circuit breaker rejections
    for i in range(10):
        trace_id = generate_trace_id()
        timestamp = incident_time + timedelta(seconds=30 + i * 0.5)

        logs.append(LogEntry(
            timestamp=timestamp,
            service_name="checkout-service",
            log_level="warn",
            message="Request rejected by circuit breaker for payment-service",
            trace_id=trace_id,
            span_id=generate_span_id(),
            error_type="CircuitBreakerOpenException",
            error_message="Circuit breaker is OPEN",
            http_method="POST",
            http_path="/checkout/complete",
            http_status_code=503,
            event_outcome="failure",
            user_id=f"user-{random.randint(1000, 9999)}",
            labels={"circuit_breaker_state": "OPEN"},
        ))

    # Phase 5: Recovery begins (T+60s)
    logs.append(LogEntry(
        timestamp=incident_time + timedelta(seconds=60),
        service_name="payment-service",
        log_level="info",
        message="Database connection restored - connected to new primary",
        trace_id=generate_trace_id(),
        span_id=generate_span_id(),
        labels={"db_host": "db-primary-new.internal", "failover_complete": "true"},
    ))

    # T+65s: Circuit breaker half-open
    logs.append(LogEntry(
        timestamp=incident_time + timedelta(seconds=65),
        service_name="checkout-service",
        log_level="info",
        message="Circuit breaker HALF-OPEN for payment-service - testing connection",
        trace_id=generate_trace_id(),
        span_id=generate_span_id(),
        labels={"circuit_breaker_state": "HALF-OPEN"},
    ))

    # T+70s: Recovery confirmed
    logs.append(LogEntry(
        timestamp=incident_time + timedelta(seconds=70),
        service_name="checkout-service",
        log_level="info",
        message="Circuit breaker CLOSED for payment-service - service recovered",
        trace_id=generate_trace_id(),
        span_id=generate_span_id(),
        labels={"circuit_breaker_state": "CLOSED"},
    ))

    return logs


def generate_timeout_cascade_incident(
    incident_time: datetime,
) -> List[LogEntry]:
    """
    Generate logs for a timeout cascade incident.

    Scenario: Inventory service becomes slow due to high load,
    causing timeouts that cascade through the system.
    """
    logs = []

    # Phase 1: Inventory service starts slowing down
    for i in range(10):
        trace_id = generate_trace_id()
        timestamp = incident_time + timedelta(seconds=i * 0.5)
        duration_ms = 2000 + random.randint(0, 3000)  # 2-5 seconds

        logs.append(LogEntry(
            timestamp=timestamp,
            service_name="inventory-service",
            log_level="warn",
            message=f"Slow query detected - inventory check took {duration_ms}ms",
            trace_id=trace_id,
            span_id=generate_span_id(),
            http_method="GET",
            http_path="/inventory/check",
            http_status_code=200,
            event_duration=duration_ms * 1_000_000,
            event_outcome="success",
            labels={"slow_query": "true", "threshold_ms": "1000"},
        ))

    # Phase 2: Timeouts begin (T+10s)
    for i in range(20):
        trace_id = generate_trace_id()
        timestamp = incident_time + timedelta(seconds=10 + i * 0.4)

        logs.append(LogEntry(
            timestamp=timestamp,
            service_name="checkout-service",
            log_level="error",
            message="Timeout waiting for inventory service response",
            trace_id=trace_id,
            span_id=generate_span_id(),
            error_type="TimeoutException",
            error_message="Read timed out after 5000ms",
            http_method="GET",
            http_path="/checkout/validate",
            http_status_code=504,
            event_duration=5000 * 1_000_000,
            event_outcome="failure",
            user_id=f"user-{random.randint(1000, 9999)}",
            labels={"upstream_service": "inventory-service", "timeout_ms": "5000"},
        ))

    # Phase 3: Thread pool exhaustion (T+20s)
    logs.append(LogEntry(
        timestamp=incident_time + timedelta(seconds=20),
        service_name="inventory-service",
        log_level="error",
        message="Thread pool exhausted - rejecting new requests",
        trace_id=generate_trace_id(),
        span_id=generate_span_id(),
        error_type="RejectedExecutionException",
        error_message="Task rejected from ThreadPoolExecutor",
        labels={"pool_size": "50", "queue_size": "100", "active_threads": "50"},
    ))

    # More rejections
    for i in range(15):
        trace_id = generate_trace_id()
        timestamp = incident_time + timedelta(seconds=22 + i * 0.3)

        logs.append(LogEntry(
            timestamp=timestamp,
            service_name="inventory-service",
            log_level="error",
            message="Request rejected - server overloaded",
            trace_id=trace_id,
            span_id=generate_span_id(),
            error_type="ServerOverloadException",
            error_message="Server is overloaded, please try again later",
            http_method="GET",
            http_path="/inventory/check",
            http_status_code=503,
            event_outcome="failure",
        ))

    return logs


def generate_payment_outage_cascade(
    incident_time: datetime,
) -> List[LogEntry]:
    """
    Generate a compelling payment outage cascade scenario for hackathon demo.

    This scenario shows:
    1. Third-party payment processor goes down
    2. Payment service starts failing
    3. Retry storms overwhelm the payment service
    4. Checkout service sees failures cascade
    5. API gateway returns 500s to users
    6. Clear trace showing the entire cascade

    This is THE demo scenario that shows LogSleuth's value.
    """
    logs = []

    # Create a few traces that will show the full cascade
    demo_traces = [generate_trace_id() for _ in range(5)]

    # Phase 1: Payment processor starts returning errors (T+0)
    logs.append(LogEntry(
        timestamp=incident_time,
        service_name="payment-service",
        log_level="warn",
        message="Payment processor returned non-200 status: 503 Service Unavailable",
        trace_id=demo_traces[0],
        span_id=generate_span_id(),
        error_type="PaymentProcessorException",
        error_message="External payment gateway returned 503",
        http_method="POST",
        http_path="/payments/process",
        http_status_code=503,
        event_outcome="failure",
        user_id="user-8472",
        labels={"processor": "stripe", "amount": "149.99", "currency": "USD"},
    ))

    # More immediate failures
    for i in range(8):
        logs.append(LogEntry(
            timestamp=incident_time + timedelta(seconds=1 + i * 0.3),
            service_name="payment-service",
            log_level="error",
            message=f"Payment processing failed - processor unavailable (attempt {i+1}/3)",
            trace_id=demo_traces[min(i % 3, 2)],
            span_id=generate_span_id(),
            error_type="PaymentProcessorException",
            error_message="Connection to payment processor refused",
            http_method="POST",
            http_path="/payments/process",
            http_status_code=503,
            event_outcome="failure",
            user_id=f"user-{8400 + i}",
            labels={"retry_attempt": str((i % 3) + 1), "processor": "stripe"},
        ))

    # Phase 2: Retry storms begin (T+5s)
    logs.append(LogEntry(
        timestamp=incident_time + timedelta(seconds=5),
        service_name="payment-service",
        log_level="warn",
        message="High retry rate detected - 50 retries/sec exceeds threshold of 20/sec",
        trace_id=generate_trace_id(),
        span_id=generate_span_id(),
        labels={"retry_rate": "50", "threshold": "20", "alert": "retry_storm"},
    ))

    # Phase 3: Connection pool exhaustion (T+10s)
    logs.append(LogEntry(
        timestamp=incident_time + timedelta(seconds=10),
        service_name="payment-service",
        log_level="error",
        message="HTTP connection pool exhausted - cannot create new connections to payment processor",
        trace_id=generate_trace_id(),
        span_id=generate_span_id(),
        error_type="ConnectionPoolExhaustedException",
        error_message="Timeout waiting for connection from pool (max=100)",
        error_stack_trace="""java.util.concurrent.TimeoutException: Timeout waiting for connection from pool
    at org.apache.http.pool.AbstractConnPool.getPoolEntryBlocking(AbstractConnPool.java:393)
    at com.payment.service.PaymentClient.processPayment(PaymentClient.java:142)
    at com.payment.service.PaymentHandler.handle(PaymentHandler.java:67)""",
        labels={"pool_size": "100", "active_connections": "100", "waiting_threads": "45"},
    ))

    # Phase 4: Cascade to checkout (T+12s) - Create a clear trace showing the cascade
    main_trace = demo_traces[0]

    # This trace will show the full flow from api-gateway -> checkout -> payment
    logs.append(LogEntry(
        timestamp=incident_time + timedelta(seconds=12, milliseconds=0),
        service_name="api-gateway",
        log_level="info",
        message="Received POST /api/v1/checkout - starting checkout flow",
        trace_id=main_trace,
        span_id=generate_span_id(),
        http_method="POST",
        http_path="/api/v1/checkout",
        event_outcome="success",
        user_id="user-9123",
        labels={"cart_items": "3", "total": "299.97"},
    ))

    logs.append(LogEntry(
        timestamp=incident_time + timedelta(seconds=12, milliseconds=50),
        service_name="checkout-service",
        log_level="info",
        message="Processing checkout request for user-9123",
        trace_id=main_trace,
        span_id=generate_span_id(),
        http_method="POST",
        http_path="/checkout/complete",
        user_id="user-9123",
        labels={"cart_value": "299.97", "items": "3"},
    ))

    logs.append(LogEntry(
        timestamp=incident_time + timedelta(seconds=12, milliseconds=100),
        service_name="checkout-service",
        log_level="info",
        message="Calling payment service to process payment",
        trace_id=main_trace,
        span_id=generate_span_id(),
        labels={"amount": "299.97", "payment_method": "credit_card"},
    ))

    logs.append(LogEntry(
        timestamp=incident_time + timedelta(seconds=12, milliseconds=150),
        service_name="payment-service",
        log_level="error",
        message="Failed to process payment - connection pool exhausted",
        trace_id=main_trace,
        span_id=generate_span_id(),
        error_type="ConnectionPoolExhaustedException",
        error_message="Cannot acquire connection from pool",
        http_method="POST",
        http_path="/payments/process",
        http_status_code=503,
        event_outcome="failure",
        user_id="user-9123",
        labels={"amount": "299.97"},
    ))

    logs.append(LogEntry(
        timestamp=incident_time + timedelta(seconds=12, milliseconds=200),
        service_name="checkout-service",
        log_level="error",
        message="Payment service call failed - checkout cannot be completed",
        trace_id=main_trace,
        span_id=generate_span_id(),
        error_type="PaymentFailedException",
        error_message="Upstream payment service returned 503",
        http_method="POST",
        http_path="/checkout/complete",
        http_status_code=500,
        event_outcome="failure",
        user_id="user-9123",
        labels={"failure_reason": "payment_service_unavailable"},
    ))

    logs.append(LogEntry(
        timestamp=incident_time + timedelta(seconds=12, milliseconds=250),
        service_name="api-gateway",
        log_level="error",
        message="Checkout request failed - returning 500 to client",
        trace_id=main_trace,
        span_id=generate_span_id(),
        error_type="UpstreamServiceException",
        error_message="Checkout service returned error",
        http_method="POST",
        http_path="/api/v1/checkout",
        http_status_code=500,
        event_outcome="failure",
        user_id="user-9123",
        labels={"client_ip": "192.168.1.100", "user_agent": "Mozilla/5.0"},
    ))

    # Phase 5: Many more failures across different traces (T+15s - T+45s)
    for i in range(25):
        trace = generate_trace_id()
        base_ts = incident_time + timedelta(seconds=15 + i * 1.2)

        # Each request shows the cascade
        logs.append(LogEntry(
            timestamp=base_ts,
            service_name="payment-service",
            log_level="error",
            message="Payment processing failed - connection pool exhausted",
            trace_id=trace,
            span_id=generate_span_id(),
            error_type="ConnectionPoolExhaustedException",
            error_message="Cannot acquire connection from pool",
            http_method="POST",
            http_path="/payments/process",
            http_status_code=503,
            event_outcome="failure",
            user_id=f"user-{9200 + i}",
        ))

        logs.append(LogEntry(
            timestamp=base_ts + timedelta(milliseconds=50),
            service_name="checkout-service",
            log_level="error",
            message="Checkout failed due to payment service error",
            trace_id=trace,
            span_id=generate_span_id(),
            error_type="PaymentFailedException",
            error_message="Payment processing unavailable",
            http_method="POST",
            http_path="/checkout/complete",
            http_status_code=500,
            event_outcome="failure",
            user_id=f"user-{9200 + i}",
        ))

    # Phase 6: Alert and impact metrics (T+30s)
    logs.append(LogEntry(
        timestamp=incident_time + timedelta(seconds=30),
        service_name="api-gateway",
        log_level="error",
        message="CRITICAL: Error rate exceeded 10% threshold - 23.5% of requests failing",
        trace_id=generate_trace_id(),
        span_id=generate_span_id(),
        labels={"error_rate": "23.5%", "affected_endpoint": "/api/v1/checkout", "alert_severity": "critical"},
    ))

    logs.append(LogEntry(
        timestamp=incident_time + timedelta(seconds=35),
        service_name="checkout-service",
        log_level="error",
        message="INCIDENT DETECTED: 89 failed checkouts in last 60 seconds - potential revenue loss $26,847",
        trace_id=generate_trace_id(),
        span_id=generate_span_id(),
        labels={"failed_checkouts": "89", "estimated_revenue_loss": "26847", "alert": "incident_detected"},
    ))

    return logs


def generate_full_dataset(
    base_time: Optional[datetime] = None,
    include_incidents: bool = True,
) -> List[Dict[str, Any]]:
    """
    Generate a full dataset of logs including normal operation and incidents.

    Args:
        base_time: Starting timestamp (defaults to 2 hours ago)
        include_incidents: Whether to include incident scenarios

    Returns:
        List of ECS-formatted log dictionaries
    """
    if base_time is None:
        base_time = datetime.utcnow() - timedelta(hours=2)

    all_logs = []

    # Generate 2 hours of normal logs (before incidents)
    print("Generating normal operation logs...")
    normal_logs = generate_normal_logs(
        base_time=base_time,
        duration_minutes=90,
        logs_per_minute=30,
    )
    all_logs.extend(normal_logs)

    if include_incidents:
        # Incident 1: Database failure at T+60 minutes
        print("Generating database failure incident...")
        incident_time_1 = base_time + timedelta(minutes=60)
        db_incident_logs = generate_database_failure_incident(incident_time_1)
        all_logs.extend(db_incident_logs)

        # Incident 2: Payment outage cascade at T+75 minutes (THE DEMO SCENARIO)
        print("Generating payment outage cascade (demo scenario)...")
        incident_time_2 = base_time + timedelta(minutes=75)
        payment_incident_logs = generate_payment_outage_cascade(incident_time_2)
        all_logs.extend(payment_incident_logs)

        # Incident 3: Timeout cascade at T+90 minutes
        print("Generating timeout cascade incident...")
        incident_time_3 = base_time + timedelta(minutes=90)
        timeout_incident_logs = generate_timeout_cascade_incident(incident_time_3)
        all_logs.extend(timeout_incident_logs)

    # Sort all logs by timestamp
    all_logs.sort(key=lambda x: x.timestamp)

    # Convert to ECS dictionaries
    print(f"Converting {len(all_logs)} logs to ECS format...")
    return [log.to_ecs_dict() for log in all_logs]


if __name__ == "__main__":
    # Generate sample dataset
    logs = generate_full_dataset()
    print(f"Generated {len(logs)} log entries")

    # Print a few samples
    print("\nSample logs:")
    for i, log in enumerate(logs[:3]):
        print(f"\n--- Log {i+1} ---")
        print(f"Timestamp: {log['@timestamp']}")
        print(f"Service: {log['service']['name']}")
        print(f"Level: {log['log']['level']}")
        print(f"Message: {log['message']}")
