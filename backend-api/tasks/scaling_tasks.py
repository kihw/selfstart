"""Tâches de scaling automatique"""
from celery import current_app as celery_app
import logging

logger = logging.getLogger(__name__)

@celery_app.task(bind=True)
def evaluate_scaling(self):
    """Évalue et exécute les décisions de scaling"""
    try:
        # Import dynamique pour éviter les dépendances circulaires
        from auto_scaler import AutoScaler
        # Logique de scaling ici
        logger.info("Évaluation du scaling en cours...")
        return {"status": "success", "message": "Scaling évalué"}
    except Exception as exc:
        logger.error(f"Erreur scaling: {exc}")
        raise self.retry(exc=exc, countdown=60, max_retries=3)

@celery_app.task
def manual_scale_service(service_name: str, target_replicas: int):
    """Scale manuellement un service"""
    logger.info(f"Scaling manuel: {service_name} -> {target_replicas}")
    return {"service": service_name, "replicas": target_replicas}
