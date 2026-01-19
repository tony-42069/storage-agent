"""Application metrics collection for Prometheus."""
import time
from typing import Dict, Any, Optional
from collections import defaultdict
from datetime import datetime, timedelta
import threading
from dataclasses import dataclass, field

from src.utils.logger import get_logger

logger = get_logger(__name__)


@dataclass
class CallMetrics:
    """Metrics for a Twilio call."""
    call_sid: str
    start_time: datetime = field(default_factory=datetime.utcnow)
    end_time: Optional[datetime] = None
    duration_seconds: float = 0
    speech_inputs: int = 0
    dtmf_inputs: int = 0
    errors: int = 0
    intents: Dict[str, int] = field(default_factory=dict)
    status: str = "in_progress"


class MetricsCollector:
    """In-memory metrics collector."""
    
    def __init__(self):
        self._requests_total: Dict[str, int] = defaultdict(int)
        self._request_duration_ms: Dict[str, list] = defaultdict(list)
        self._errors_total: Dict[str, int] = defaultdict(int)
        self._conversations_total: Dict[str, int] = defaultdict(int)
        self._intents_total: Dict[str, int] = defaultdict(int)
        self._active_calls: Dict[str, CallMetrics] = {}
        self._completed_calls: Dict[str, CallMetrics] = {}
        self._start_time = datetime.utcnow()
        self._lock = threading.Lock()
        
        logger.info("Metrics collector initialized")
    
    def record_request(self, endpoint: str, method: str, status_code: int, duration_ms: int):
        """Record a request metric."""
        with self._lock:
            self._requests_total[f"{method}_{endpoint}_{status_code}"] += 1
            self._request_duration_ms[endpoint].append(duration_ms)
    
    def record_error(self, error_type: str, component: str = "general"):
        """Record an error."""
        with self._lock:
            self._errors_total[f"{component}_{error_type}"] += 1
    
    def record_conversation(self, session_id: str, intent: str):
        """Record a conversation event."""
        with self._lock:
            self._conversations_total[session_id] += 1
            if intent:
                self._intents_total[intent] += 1
    
    def start_call(self, call_sid: str) -> CallMetrics:
        """Start tracking a call."""
        with self._lock:
            metrics = CallMetrics(call_sid=call_sid)
            self._active_calls[call_sid] = metrics
            return metrics
    
    def end_call(self, call_sid: str, status: str = "completed"):
        """End tracking a call."""
        with self._lock:
            if call_sid in self._active_calls:
                call = self._active_calls[call_sid]
                call.end_time = datetime.utcnow()
                call.duration_seconds = (call.end_time - call.start_time).total_seconds()
                call.status = status
                self._completed_calls[call_sid] = call
                del self._active_calls[call_sid]
    
    def record_call_input(self, call_sid: str, input_type: str, intent: str):
        """Record call input (speech or DTMF)."""
        with self._lock:
            if call_sid in self._active_calls:
                call = self._active_calls[call_sid]
                if input_type == "speech":
                    call.speech_inputs += 1
                elif input_type == "dtmf":
                    call.dtmf_inputs += 1
                if intent:
                    call.intents[intent] = call.intents.get(intent, 0) + 1
    
    def record_call_error(self, call_sid: str):
        """Record a call error."""
        with self._lock:
            if call_sid in self._active_calls:
                self._active_calls[call_sid].errors += 1
    
    def get_prometheus_metrics(self) -> str:
        """Get metrics in Prometheus format."""
        metrics = self.get_metrics()
        
        lines = [
            "# TYPE storage_agent_uptime_seconds gauge",
            f"storage_agent_uptime_seconds {metrics['app_uptime_seconds']}",
            "",
            "# TYPE storage_agent_requests_total counter",
            f"storage_agent_requests_total {metrics['app_requests_total']}",
            "",
            "# TYPE storage_agent_errors_total counter",
            f"storage_agent_errors_total {metrics['app_errors_total']}",
            "",
            "# TYPE storage_agent_conversations_total counter",
            f"storage_agent_conversations_total {metrics['app_conversations_total']}",
            "",
            "# TYPE storage_agent_call_duration_seconds gauge",
        ]
        
        for call_sid, call in self._completed_calls.items():
            lines.append(f'storage_agent_call_duration_seconds{{call_sid="{call_sid}"}} {call.duration_seconds}')
        
        lines.extend([
            "",
            "# TYPE storage_agent_call_inputs_total counter",
        ])
        
        for call_sid, call in self._completed_calls.items():
            lines.append(f'storage_agent_call_inputs_total{{call_sid="{call_sid}",type="speech"}} {call.speech_inputs}')
            lines.append(f'storage_agent_call_inputs_total{{call_sid="{call_sid}",type="dtmf"}} {call.dtmf_inputs}')
        
        lines.extend([
            "",
            "# TYPE storage_agent_intents_total counter",
        ])
        
        for intent, count in metrics.get('intents_total', {}).items():
            lines.append(f'storage_agent_intents_total{{intent="{intent}"}} {count}')
        
        return "\n".join(lines)
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get all metrics."""
        with self._lock:
            uptime_seconds = (datetime.utcnow() - self._start_time).total_seconds()
            
            avg_durations = {}
            for endpoint, durations in self._request_duration_ms.items():
                if durations:
                    avg_durations[endpoint] = sum(durations) / len(durations)
            
            total_call_duration = sum(
                c.duration_seconds for c in self._completed_calls.values()
            )
            
            avg_call_duration = 0
            if self._completed_calls:
                avg_call_duration = total_call_duration / len(self._completed_calls)
            
            error_rate = 0
            if metrics.get('app_requests_total', 0) > 0:
                error_rate = metrics.get('app_errors_total', 0) / metrics.get('app_requests_total', 1)
            
            return {
                "app_uptime_seconds": uptime_seconds,
                "app_requests_total": sum(self._requests_total.values()),
                "app_errors_total": sum(self._errors_total.values()),
                "app_conversations_total": len(self._conversations_total),
                "app_error_rate": error_rate,
                "http_request_duration_ms_avg": avg_durations,
                "requests_by_endpoint": dict(self._requests_total),
                "errors_by_type": dict(self._errors_total),
                "intents_total": dict(self._intents_total),
                "calls": {
                    "active": len(self._active_calls),
                    "completed": len(self._completed_calls),
                    "total_duration_seconds": total_call_duration,
                    "avg_duration_seconds": avg_call_duration,
                    "total_errors": sum(c.errors for c in self._completed_calls.values()),
                    "total_speech_inputs": sum(c.speech_inputs for c in self._completed_calls.values()),
                    "total_dtmf_inputs": sum(c.dtmf_inputs for c in self._completed_calls.values()),
                },
            }
    
    def reset(self):
        """Reset all metrics."""
        with self._lock:
            self._requests_total.clear()
            self._request_duration_ms.clear()
            self._errors_total.clear()
            self._conversations_total.clear()
            self._intents_total.clear()
            self._active_calls.clear()
            self._completed_calls.clear()
            self._start_time = datetime.utcnow()
            logger.info("Metrics reset")


_metrics_collector = MetricsCollector()


def get_metrics() -> Dict[str, Any]:
    """Get current metrics."""
    return _metrics_collector.get_metrics()


def get_prometheus_metrics() -> str:
    """Get metrics in Prometheus format."""
    return _metrics_collector.get_prometheus_metrics()


def record_request(endpoint: str, method: str, status_code: int, duration_ms: int):
    """Record a request metric."""
    _metrics_collector.record_request(endpoint, method, status_code, duration_ms)


def record_error(error_type: str, component: str = "general"):
    """Record an error."""
    _metrics_collector.record_error(error_type, component)


def record_conversation(session_id: str, intent: str):
    """Record a conversation event."""
    _metrics_collector.record_conversation(session_id, intent)


def start_call(call_sid: str):
    """Start tracking a call."""
    return _metrics_collector.start_call(call_sid)


def end_call(call_sid: str, status: str = "completed"):
    """End tracking a call."""
    _metrics_collector.end_call(call_sid, status)


def record_call_input(call_sid: str, input_type: str, intent: str):
    """Record call input (speech or DTMF)."""
    _metrics_collector.record_call_input(call_sid, input_type, intent)


def record_call_error(call_sid: str):
    """Record a call error."""
    _metrics_collector.record_call_error(call_sid)


def reset_metrics():
    """Reset all metrics."""
    _metrics_collector.reset()
