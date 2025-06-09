from plugin_manager import SelfStartPlugin
from prometheus_client import start_http_server, Counter, Gauge, Histogram
import logging

class PrometheusMetricsPlugin(SelfStartPlugin):
    """Plugin pour exposer les métriques Prometheus"""
    
    async def initialize(self) -> bool:
        try:
            # Initialiser les métriques
            self.request_counter = Counter('selfstart_requests_total', 'Total requests', ['method', 'endpoint'])
            self.container_gauge = Gauge('selfstart_containers_total', 'Total containers', ['status'])
            self.response_time = Histogram('selfstart_response_time_seconds', 'Response time')
            
            # Démarrer le serveur Prometheus
            port = self.config.get('port', 9090)
            start_http_server(port)
            
            self.logger.info(f"Serveur Prometheus démarré sur le port {port}")
            return True
        except Exception as e:
            self.logger.error(f"Erreur initialisation Prometheus: {e}")
            return False
    
    async def cleanup(self) -> bool:
        # Le serveur Prometheus se ferme automatiquement
        return True
    
    async def hook_on_api_request(self, method: str, endpoint: str, response_time: float):
        """Hook appelé sur chaque requête API"""
        self.request_counter.labels(method=method, endpoint=endpoint).inc()
        self.response_time.observe(response_time)
    
    async def hook_on_service_discovery(self, services: list):
        """Hook appelé lors de la découverte de services"""
        status_counts = {}
        for service in services:
            status = service['status']
            status_counts[status] = status_counts.get(status, 0) + 1
        
        for status, count in status_counts.items():
            self.container_gauge.labels(status=status).set(count)
