"""Serveur HTTP pour exporter les métriques Prometheus."""

from http.server import HTTPServer, BaseHTTPRequestHandler
import threading
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from main import Metrics

METRICS: "Metrics | None" = None
METRICS_LOCK = threading.Lock()


class MetricsHandler(BaseHTTPRequestHandler):
    def do_GET(self) -> None:  # noqa: N802
        if self.path == "/metrics":
            with METRICS_LOCK:
                if METRICS is None:
                    self.send_response(503)
                    self.end_headers()
                    return
                text = METRICS.render()
            self.send_response(200)
            self.send_header("Content-Type", "text/plain; version=0.0.4")
            self.end_headers()
            self.wfile.write(text.encode())
        else:
            self.send_response(404)
            self.end_headers()

    def log_message(self, *_args) -> None:  # type: ignore[override]
        pass  # Silence les logs HTTP


def register_metrics(metrics: "Metrics") -> None:
    """Enregistre la référence métriques pour le serveur."""
    global METRICS
    with METRICS_LOCK:
        METRICS = metrics


def start_server(port: int, host: str, metrics: "Metrics") -> None:
    """Démarre le serveur HTTP en thread daemon."""
    register_metrics(metrics)
    server = HTTPServer((host, port), MetricsHandler)
    server_thread = threading.Thread(target=server.serve_forever)
    server_thread.daemon = True
    server_thread.start()
    print(f"[METRICS] Serveur Prometheus démarré sur http://{host}:{port}/metrics")
