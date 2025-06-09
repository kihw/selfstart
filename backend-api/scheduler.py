#!/usr/bin/env python3
"""
SelfStart Scheduler - Planificateur de tâches pour v0.3
Gère les tâches périodiques : nettoyage, monitoring, sauvegardes
"""

import os
import logging
from celery import Celery
from celery.schedules import crontab
from datetime import timedelta

# Configuration du logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Configuration Celery
redis_url = os.getenv('REDIS_URL', 'redis://localhost:6379')
celery_app = Celery(
    'selfstart_scheduler',
    broker=f'{redis_url}/1',
    backend=f'{redis_url}/2'
)

# Configuration du scheduler (Celery Beat)
celery_app.conf.update(
    timezone='UTC',
    enable_utc=True,
    beat_schedule={
        # Monitoring système toutes les 30 secondes
        'system-monitoring': {
            'task': 'tasks.monitoring_tasks.collect_system_metrics',
            'schedule': timedelta(seconds=30),
            'options': {'queue': 'monitoring'}
        },
        
        # Service discovery toutes les minutes
        'service-discovery': {
            'task': 'tasks.monitoring_tasks.discover_services',
            'schedule': timedelta(minutes=1),
            'options': {'queue': 'monitoring'}
        },
        
        # Auto-scaling check toutes les 2 minutes
        'auto-scaling-check': {
            'task': 'tasks.scaling_tasks.evaluate_scaling',
            'schedule': timedelta(minutes=2),
            'options': {'queue': 'scaling'}
        },
        
        # Nettoyage des métriques anciennes toutes les heures
        'cleanup-old-metrics': {
            'task': 'tasks.maintenance_tasks.cleanup_old_metrics',
            'schedule': crontab(minute=0),
            'options': {'queue': 'maintenance'}
        },
        
        # Backup de configuration tous les jours à 3h
        'daily-backup': {
            'task': 'tasks.maintenance_tasks.backup_configuration',
            'schedule': crontab(hour=3, minute=0),
            'options': {'queue': 'maintenance'}
        },
        
        # Vérification des plugins toutes les 15 minutes
        'plugin-health-check': {
            'task': 'tasks.plugin_tasks.check_plugin_health',
            'schedule': timedelta(minutes=15),
            'options': {'queue': 'plugins'}
        },
        
        # Nettoyage des logs Docker tous les dimanches à 2h
        'weekly-docker-cleanup': {
            'task': 'tasks.maintenance_tasks.cleanup_docker_logs',
            'schedule': crontab(hour=2, minute=0, day_of_week=0),
            'options': {'queue': 'maintenance'}
        },
        
        # Vérification des mise à jour des containers tous les jours à 4h
        'check-container-updates': {
            'task': 'tasks.maintenance_tasks.check_container_updates',
            'schedule': crontab(hour=4, minute=0),
            'options': {'queue': 'maintenance'}
        },
        
        # Génération de rapports de santé tous les lundis à 9h
        'weekly-health-report': {
            'task': 'tasks.monitoring_tasks.generate_health_report',
            'schedule': crontab(hour=9, minute=0, day_of_week=1),
            'options': {'queue': 'monitoring'}
        },
        
        # Optimisation de Redis toutes les 6 heures
        'redis-optimization': {
            'task': 'tasks.maintenance_tasks.optimize_redis',
            'schedule': timedelta(hours=6),
            'options': {'queue': 'maintenance'}
        }
    },
    
    # Configuration des queues
    task_routes={
        'tasks.monitoring_tasks.*': {'queue': 'monitoring'},
        'tasks.scaling_tasks.*': {'queue': 'scaling'},
        'tasks.maintenance_tasks.*': {'queue': 'maintenance'},
        'tasks.plugin_tasks.*': {'queue': 'plugins'},
    }
)

# Configuration avancée pour le scheduler
celery_app.conf.beat_scheduler = 'celery.beat:PersistentScheduler'
celery_app.conf.beat_schedule_filename = '/app/data/celerybeat-schedule'
celery_app.conf.beat_max_loop_interval = 300  # 5 minutes max entre les vérifications

if __name__ == '__main__':
    logger.info("🕒 Starting SelfStart Scheduler v0.3...")
    # Démarrer le scheduler
    celery_app.start(['celery', 'beat', '--loglevel=info'])
