#!/usr/bin/env python3
"""
SelfStart Worker - Tâches asynchrones pour v0.3
Gère les tâches longues en arrière-plan : scaling, monitoring, maintenance
"""

import os
import sys
import logging
from celery import Celery
from celery.signals import worker_ready, worker_shutdown

# Configuration du logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Configuration Celery
redis_url = os.getenv('REDIS_URL', 'redis://localhost:6379')
celery_app = Celery(
    'selfstart_worker',
    broker=f'{redis_url}/1',
    backend=f'{redis_url}/2',
    include=[
        'tasks.scaling_tasks',
        'tasks.monitoring_tasks', 
        'tasks.maintenance_tasks',
        'tasks.plugin_tasks'
    ]
)

# Configuration Celery
celery_app.conf.update(
    task_serializer='json',
    accept_content=['json'],
    result_serializer='json',
    timezone='UTC',
    enable_utc=True,
    task_track_started=True,
    task_time_limit=300,  # 5 minutes max par tâche
    task_soft_time_limit=240,  # Warning à 4 minutes
    worker_prefetch_multiplier=1,
    worker_max_tasks_per_child=1000,
)

# Configuration des routes de tâches
celery_app.conf.task_routes = {
    'tasks.scaling_tasks.*': {'queue': 'scaling'},
    'tasks.monitoring_tasks.*': {'queue': 'monitoring'},
    'tasks.maintenance_tasks.*': {'queue': 'maintenance'},
    'tasks.plugin_tasks.*': {'queue': 'plugins'},
}

@worker_ready.connect
def worker_ready_handler(sender=None, **kwargs):
    """Appelé quand le worker est prêt"""
    logger.info("🚀 SelfStart Worker v0.3 ready")

@worker_shutdown.connect  
def worker_shutdown_handler(sender=None, **kwargs):
    """Appelé quand le worker s'arrête"""
    logger.info("🛑 SelfStart Worker v0.3 shutdown")

if __name__ == '__main__':
    # Démarrer le worker
    celery_app.start()
