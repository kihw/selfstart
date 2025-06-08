import asyncio
import json
import logging
import sqlite3
import os
from datetime import datetime, timedelta, time
from typing import Dict, List, Optional, Any, Union
from enum import Enum
from pydantic import BaseModel
import psutil

logger = logging.getLogger(__name__)

class ShutdownCondition(str, Enum):
    INACTIVITY = "inactivity"          # Pas de trafic réseau
    SCHEDULE = "schedule"              # Horaires programmés
    LOW_RESOURCES = "low_resources"    # CPU/RAM faibles
    IDLE_TIME = "idle_time"           # Temps d'inactivité
    CUSTOM = "custom"                 # Condition personnalisée

class ShutdownAction(str, Enum):
    STOP = "stop"                     # Arrêter le container
    PAUSE = "pause"                   # Mettre en pause
    RESTART = "restart"               # Redémarrer
    SCALE_DOWN = "scale_down"         # Réduire les ressources

class ShutdownRule(BaseModel):
    id: Optional[int] = None
    name: str
    enabled: bool = True
    condition: ShutdownCondition
    action: ShutdownAction
    
    # Filtres containers
    containers: List[str] = []         # Containers spécifiques
    exclude_containers: List[str] = [] # Containers à exclure
    tags: List[str] = []              # Tags/labels requis
    
    # Conditions spécifiques
    inactivity_threshold: int = 3600   # Secondes d'inactivité
    cpu_threshold: float = 5.0         # % CPU en dessous duquel arrêter
    memory_threshold: float = 100      # MB RAM utilisée en dessous
    network_threshold: int = 1024      # Bytes/sec réseau minimum
    
    # Programmation
    cron_schedule: Optional[str] = None      # Expression cron
    time_ranges: List[Dict[str, str]] = []   # Plages horaires
    days_of_week: List[int] = []            # 0=lundi, 6=dimanche
    
    # Options avancées
    grace_period: int = 30             # Délai avant arrêt (secondes)
    notification: bool = True          # Notifier avant arrêt
    auto_restart: bool = False         # Redémarrage automatique
    restart_schedule: Optional[str] = None  # Quand redémarrer
    
    # Conditions de protection
    protect_if_connected: bool = True   # Protéger si connexions actives
    protect_if_uploading: bool = True   # Protéger si upload en cours
    min_uptime: int = 300              # Temps minimum avant arrêt possible
    
    created_at: Optional[datetime] = None
    last_triggered: Optional[datetime] = None
    last_checked: Optional[datetime] = None

class ContainerStats(BaseModel):
    name: str
    cpu_percent: float
    memory_usage: int  # MB
    network_rx_bytes: int
    network_tx_bytes: int
    uptime: int  # secondes
    connections: int
    last_activity: datetime
    is_protected: bool = False

class ShutdownLog(BaseModel):
    id: Optional[int] = None
    rule_id: int
    container_name: str
    action: ShutdownAction
    reason: str
    success: bool
    error_message: Optional[str] = None
    created_at: datetime
    scheduled_restart: Optional[datetime] = None

class AutoShutdownManager:
    def __init__(self, db_path: str = "data/autoshutdown.db"):
        self.db_path = db_path
        self.running = False
        self.check_interval = 60  # Vérifier toutes les minutes
        self.container_stats: Dict[str, ContainerStats] = {}
        self._init_database()
        
    def _init_database(self):
        """Initialise la base de données SQLite"""
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        
        with sqlite3.connect(self.db_path) as conn:
            # Table des règles d'extinction
            conn.execute("""
                CREATE TABLE IF NOT EXISTS shutdown_rules (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL,
                    enabled BOOLEAN DEFAULT TRUE,
                    condition TEXT NOT NULL,
                    action TEXT NOT NULL,
                    containers TEXT DEFAULT '[]',
                    exclude_containers TEXT DEFAULT '[]',
                    tags TEXT DEFAULT '[]',
                    inactivity_threshold INTEGER DEFAULT 3600,
                    cpu_threshold REAL DEFAULT 5.0,
                    memory_threshold REAL DEFAULT 100,
                    network_threshold INTEGER DEFAULT 1024,
                    cron_schedule TEXT,
                    time_ranges TEXT DEFAULT '[]',
                    days_of_week TEXT DEFAULT '[]',
                    grace_period INTEGER DEFAULT 30,
                    notification BOOLEAN DEFAULT TRUE,
                    auto_restart BOOLEAN DEFAULT FALSE,
                    restart_schedule TEXT,
                    protect_if_connected BOOLEAN DEFAULT TRUE,
                    protect_if_uploading BOOLEAN DEFAULT TRUE,
                    min_uptime INTEGER DEFAULT 300,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    last_triggered TIMESTAMP,
                    last_checked TIMESTAMP
                )
            """)
            
            # Table des logs d'extinction
            conn.execute("""
                CREATE TABLE IF NOT EXISTS shutdown_logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    rule_id INTEGER NOT NULL,
                    container_name TEXT NOT NULL,
                    action TEXT NOT NULL,
                    reason TEXT NOT NULL,
                    success BOOLEAN NOT NULL,
                    error_message TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    scheduled_restart TIMESTAMP,
                    FOREIGN KEY (rule_id) REFERENCES shutdown_rules (id)
                )
            """)
            
            conn.commit()

    async def create_rule(self, rule: ShutdownRule) -> int:
        """Crée une nouvelle règle d'extinction"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("""
                INSERT INTO shutdown_rules 
                (name, enabled, condition, action, containers, exclude_containers, tags,
                 inactivity_threshold, cpu_threshold, memory_threshold, network_threshold,
                 cron_schedule, time_ranges, days_of_week, grace_period, notification,
                 auto_restart, restart_schedule, protect_if_connected, protect_if_uploading, min_uptime)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                rule.name, rule.enabled, rule.condition.value, rule.action.value,
                json.dumps(rule.containers), json.dumps(rule.exclude_containers), json.dumps(rule.tags),
                rule.inactivity_threshold, rule.cpu_threshold, rule.memory_threshold, rule.network_threshold,
                rule.cron_schedule, json.dumps(rule.time_ranges), json.dumps(rule.days_of_week),
                rule.grace_period, rule.notification, rule.auto_restart, rule.restart_schedule,
                rule.protect_if_connected, rule.protect_if_uploading, rule.min_uptime
            ))
            conn.commit()
            return cursor.lastrowid

    async def get_rules(self, enabled_only: bool = False) -> List[ShutdownRule]:
        """Récupère toutes les règles"""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            
            query = "SELECT * FROM shutdown_rules"
            params = []
            
            if enabled_only:
                query += " WHERE enabled = ?"
                params.append(True)
                
            rows = conn.execute(query, params).fetchall()
            
            rules = []
            for row in rows:
                rule = ShutdownRule(
                    id=row['id'],
                    name=row['name'],
                    enabled=bool(row['enabled']),
                    condition=ShutdownCondition(row['condition']),
                    action=ShutdownAction(row['action']),
                    containers=json.loads(row['containers']),
                    exclude_containers=json.loads(row['exclude_containers']),
                    tags=json.loads(row['tags']),
                    inactivity_threshold=row['inactivity_threshold'],
                    cpu_threshold=row['cpu_threshold'],
                    memory_threshold=row['memory_threshold'],
                    network_threshold=row['network_threshold'],
                    cron_schedule=row['cron_schedule'],
                    time_ranges=json.loads(row['time_ranges']),
                    days_of_week=json.loads(row['days_of_week']),
                    grace_period=row['grace_period'],
                    notification=bool(row['notification']),
                    auto_restart=bool(row['auto_restart']),
                    restart_schedule=row['restart_schedule'],
                    protect_if_connected=bool(row['protect_if_connected']),
                    protect_if_uploading=bool(row['protect_if_uploading']),
                    min_uptime=row['min_uptime'],
                    created_at=datetime.fromisoformat(row['created_at']) if row['created_at'] else None,
                    last_triggered=datetime.fromisoformat(row['last_triggered']) if row['last_triggered'] else None,
                    last_checked=datetime.fromisoformat(row['last_checked']) if row['last_checked'] else None
                )
                rules.append(rule)
                
            return rules

    async def update_rule(self, rule_id: int, rule: ShutdownRule) -> bool:
        """Met à jour une règle"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("""
                UPDATE shutdown_rules SET 
                    name = ?, enabled = ?, condition = ?, action = ?, containers = ?,
                    exclude_containers = ?, tags = ?, inactivity_threshold = ?, cpu_threshold = ?,
                    memory_threshold = ?, network_threshold = ?, cron_schedule = ?, time_ranges = ?,
                    days_of_week = ?, grace_period = ?, notification = ?, auto_restart = ?,
                    restart_schedule = ?, protect_if_connected = ?, protect_if_uploading = ?, min_uptime = ?
                WHERE id = ?
            """, (
                rule.name, rule.enabled, rule.condition.value, rule.action.value,
                json.dumps(rule.containers), json.dumps(rule.exclude_containers), json.dumps(rule.tags),
                rule.inactivity_threshold, rule.cpu_threshold, rule.memory_threshold, rule.network_threshold,
                rule.cron_schedule, json.dumps(rule.time_ranges), json.dumps(rule.days_of_week),
                rule.grace_period, rule.notification, rule.auto_restart, rule.restart_schedule,
                rule.protect_if_connected, rule.protect_if_uploading, rule.min_uptime,
                rule_id
            ))
            conn.commit()
            return cursor.rowcount > 0

    async def delete_rule(self, rule_id: int) -> bool:
        """Supprime une règle"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("DELETE FROM shutdown_rules WHERE id = ?", (rule_id,))
            conn.commit()
            return cursor.rowcount > 0

    async def start_monitoring(self):
        """Démarre le monitoring automatique"""
        self.running = True
        logger.info("Démarrage du monitoring auto-shutdown")
        
        while self.running:
            try:
                await self._check_all_rules()
                await asyncio.sleep(self.check_interval)
            except Exception as e:
                logger.error(f"Erreur dans le monitoring auto-shutdown: {str(e)}")
                await asyncio.sleep(self.check_interval)

    async def stop_monitoring(self):
        """Arrête le monitoring"""
        self.running = False
        logger.info("Arrêt du monitoring auto-shutdown")

    async def _check_all_rules(self):
        """Vérifie toutes les règles actives"""
        rules = await self.get_rules(enabled_only=True)
        
        # Mettre à jour les statistiques des containers
        await self._update_container_stats()
        
        for rule in rules:
            try:
                await self._check_rule(rule)
                await self._update_rule_last_checked(rule.id)
            except Exception as e:
                logger.error(f"Erreur lors de la vérification de la règle {rule.name}: {str(e)}")

    async def _update_container_stats(self):
        """Met à jour les statistiques des containers"""
        try:
            # Ici on utiliserait le DockerManager pour récupérer les stats
            # Pour l'exemple, on simule
            from docker_manager import DockerManager
            
            docker_manager = DockerManager()
            containers = await docker_manager.list_all_containers()
            
            for container in containers:
                if container['status'] == 'running':
                    stats = await self._get_container_detailed_stats(container['name'])
                    self.container_stats[container['name']] = stats
                    
        except Exception as e:
            logger.error(f"Erreur lors de la mise à jour des stats: {str(e)}")

    async def _get_container_detailed_stats(self, container_name: str) -> ContainerStats:
        """Récupère les statistiques détaillées d'un container"""
        try:
            # Simulation des stats - dans la vraie implémentation,
            # on utiliserait docker.containers.get(name).stats()
            import random
            
            return ContainerStats(
                name=container_name,
                cpu_percent=random.uniform(0, 10),
                memory_usage=random.randint(50, 500),
                network_rx_bytes=random.randint(0, 10000),
                network_tx_bytes=random.randint(0, 10000),
                uptime=random.randint(300, 86400),
                connections=random.randint(0, 5),
                last_activity=datetime.now() - timedelta(seconds=random.randint(0, 3600)),
                is_protected=False
            )
        except Exception as e:
            logger.error(f"Erreur stats container {container_name}: {str(e)}")
            return None

    async def _check_rule(self, rule: ShutdownRule):
        """Vérifie une règle spécifique"""
        # Récupérer les containers concernés
        target_containers = await self._get_target_containers(rule)
        
        for container_name in target_containers:
            if await self._should_shutdown_container(rule, container_name):
                await self._execute_shutdown(rule, container_name)

    async def _get_target_containers(self, rule: ShutdownRule) -> List[str]:
        """Récupère la liste des containers concernés par une règle"""
        all_containers = list(self.container_stats.keys())
        
        # Filtrer selon les critères de la règle
        target_containers = []
        
        for container_name in all_containers:
            # Containers spécifiques
            if rule.containers and container_name not in rule.containers:
                continue
                
            # Containers exclus
            if container_name in rule.exclude_containers:
                continue
                
            # Tags (simulation - dans la vraie implémentation, on vérifierait les labels Docker)
            if rule.tags:
                # Ici on vérifierait les labels du container
                pass
                
            target_containers.append(container_name)
            
        return target_containers

    async def _should_shutdown_container(self, rule: ShutdownRule, container_name: str) -> bool:
        """Détermine si un container doit être arrêté selon une règle"""
        stats = self.container_stats.get(container_name)
        if not stats:
            return False
            
        # Vérifier les conditions de protection
        if await self._is_container_protected(rule, stats):
            return False
            
        # Vérifier la condition spécifique
        if rule.condition == ShutdownCondition.INACTIVITY:
            return await self._check_inactivity_condition(rule, stats)
        elif rule.condition == ShutdownCondition.SCHEDULE:
            return await self._check_schedule_condition(rule)
        elif rule.condition == ShutdownCondition.LOW_RESOURCES:
            return await self._check_low_resources_condition(rule, stats)
        elif rule.condition == ShutdownCondition.IDLE_TIME:
            return await self._check_idle_time_condition(rule, stats)
            
        return False

    async def _is_container_protected(self, rule: ShutdownRule, stats: ContainerStats) -> bool:
        """Vérifie si un container est protégé contre l'arrêt"""
        # Protection explicite
        if stats.is_protected:
            return True
            
        # Temps minimum d'uptime
        if stats.uptime < rule.min_uptime:
            return True
            
        # Protection si connexions actives
        if rule.protect_if_connected and stats.connections > 0:
            return True
            
        # Protection si upload en cours (simulation basée sur le trafic réseau)
        if rule.protect_if_uploading and stats.network_tx_bytes > rule.network_threshold * 10:
            return True
            
        return False

    async def _check_inactivity_condition(self, rule: ShutdownRule, stats: ContainerStats) -> bool:
        """Vérifie la condition d'inactivité"""
        inactivity_seconds = (datetime.now() - stats.last_activity).total_seconds()
        return inactivity_seconds >= rule.inactivity_threshold

    async def _check_schedule_condition(self, rule: ShutdownRule) -> bool:
        """Vérifie la condition de programmation"""
        now = datetime.now()
        
        # Vérifier les jours de la semaine
        if rule.days_of_week and now.weekday() not in rule.days_of_week:
            return False
            
        # Vérifier les plages horaires
        if rule.time_ranges:
            current_time = now.time()
            for time_range in rule.time_ranges:
                start_time = time.fromisoformat(time_range['start'])
                end_time = time.fromisoformat(time_range['end'])
                
                if start_time <= current_time <= end_time:
                    return True
            return False
            
        # Expression cron
        if rule.cron_schedule:
            try:
                from croniter import croniter
                cron = croniter(rule.cron_schedule, now)
                # Vérifier si on est dans une fenêtre de 1 minute de l'exécution prévue
                next_run = cron.get_next(datetime)
                if (next_run - now).total_seconds() <= 60:
                    return True
            except:
                logger.warning(f"Expression cron invalide: {rule.cron_schedule}")
                
        return False

    async def _check_low_resources_condition(self, rule: ShutdownRule, stats: ContainerStats) -> bool:
        """Vérifie la condition de ressources faibles"""
        return (stats.cpu_percent <= rule.cpu_threshold and 
                stats.memory_usage <= rule.memory_threshold)

    async def _check_idle_time_condition(self, rule: ShutdownRule, stats: ContainerStats) -> bool:
        """Vérifie la condition de temps d'inactivité"""
        # Combine plusieurs facteurs pour déterminer l'inactivité
        low_cpu = stats.cpu_percent <= rule.cpu_threshold
        low_network = (stats.network_rx_bytes + stats.network_tx_bytes) <= rule.network_threshold
        no_connections = stats.connections == 0
        
        return low_cpu and low_network and no_connections

    async def _execute_shutdown(self, rule: ShutdownRule, container_name: str):
        """Exécute l'arrêt d'un container"""
        try:
            # Notification préalable
            if rule.notification:
                await self._send_shutdown_notification(rule, container_name)
                
            # Période de grâce
            if rule.grace_period > 0:
                logger.info(f"Période de grâce de {rule.grace_period}s pour {container_name}")
                await asyncio.sleep(rule.grace_period)
                
            # Exécuter l'action
            success = await self._perform_shutdown_action(rule.action, container_name)
            
            # Programmer le redémarrage si nécessaire
            restart_time = None
            if rule.auto_restart and rule.restart_schedule:
                restart_time = await self._schedule_restart(rule, container_name)
                
            # Logger l'action
            await self._log_shutdown(
                rule.id, container_name, rule.action, 
                f"Condition: {rule.condition.value}", 
                success, None, restart_time
            )
            
            # Mettre à jour la règle
            await self._update_rule_last_triggered(rule.id)
            
        except Exception as e:
            logger.error(f"Erreur lors de l'arrêt de {container_name}: {str(e)}")
            await self._log_shutdown(
                rule.id, container_name, rule.action,
                f"Condition: {rule.condition.value}",
                False, str(e), None
            )

    async def _perform_shutdown_action(self, action: ShutdownAction, container_name: str) -> bool:
        """Effectue l'action d'arrêt"""
        try:
            from docker_manager import DockerManager
            docker_manager = DockerManager()
            
            if action == ShutdownAction.STOP:
                result = await docker_manager.stop_container(container_name)
                return result.get('success', False)
            elif action == ShutdownAction.PAUSE:
                # Implémenter la pause
                logger.info(f"Pause du container {container_name}")
                return True
            elif action == ShutdownAction.RESTART:
                # Redémarrer
                stop_result = await docker_manager.stop_container(container_name)
                if stop_result.get('success', False):
                    await asyncio.sleep(5)
                    start_result = await docker_manager.start_container(container_name)
                    return start_result.get('success', False)
                return False
            elif action == ShutdownAction.SCALE_DOWN:
                # Réduire les ressources (Docker Swarm/Kubernetes)
                logger.info(f"Scale down du container {container_name}")
                return True
                
        except Exception as e:
            logger.error(f"Erreur action {action.value} sur {container_name}: {str(e)}")
            return False

    async def _send_shutdown_notification(self, rule: ShutdownRule, container_name: str):
        """Envoie une notification avant arrêt"""
        try:
            # Utiliser le webhook manager pour envoyer une notification
            from webhook_manager import WebhookManager, WebhookEvent
            
            webhook_manager = WebhookManager()
            await webhook_manager.trigger_event(
                WebhookEvent.SYSTEM_WARNING,
                container_name,
                {
                    "message": f"Container {container_name} va être arrêté dans {rule.grace_period}s",
                    "rule": rule.name,
                    "action": rule.action.value,
                    "reason": rule.condition.value
                }
            )
        except Exception as e:
            logger.error(f"Erreur notification arrêt: {str(e)}")

    async def _schedule_restart(self, rule: ShutdownRule, container_name: str) -> datetime:
        """Programme le redémarrage automatique"""
        if rule.restart_schedule:
            try:
                from croniter import croniter
                cron = croniter(rule.restart_schedule, datetime.now())
                restart_time = cron.get_next(datetime)
                
                # Ici on programmerait une tâche pour redémarrer
                # Pour l'instant, on retourne juste l'heure prévue
                logger.info(f"Redémarrage de {container_name} programmé à {restart_time}")
                return restart_time
            except Exception as e:
                logger.error(f"Erreur programmation redémarrage: {str(e)}")
        
        return None

    async def _log_shutdown(self, rule_id: int, container_name: str, action: ShutdownAction,
                          reason: str, success: bool, error_message: str, 
                          scheduled_restart: datetime):
        """Enregistre un log d'arrêt"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                INSERT INTO shutdown_logs 
                (rule_id, container_name, action, reason, success, error_message, scheduled_restart)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                rule_id, container_name, action.value, reason, success, 
                error_message, scheduled_restart.isoformat() if scheduled_restart else None
            ))
            conn.commit()

    async def _update_rule_last_triggered(self, rule_id: int):
        """Met à jour la date de dernier déclenchement d'une règle"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                UPDATE shutdown_rules SET last_triggered = CURRENT_TIMESTAMP WHERE id = ?
            """, (rule_id,))
            conn.commit()

    async def _update_rule_last_checked(self, rule_id: int):
        """Met à jour la date de dernière vérification d'une règle"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                UPDATE shutdown_rules SET last_checked = CURRENT_TIMESTAMP WHERE id = ?
            """, (rule_id,))
            conn.commit()

    async def get_shutdown_logs(self, rule_id: int = None, container_name: str = None, 
                              limit: int = 100) -> List[ShutdownLog]:
        """Récupère les logs d'extinction"""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            
            query = "SELECT * FROM shutdown_logs"
            params = []
            conditions = []
            
            if rule_id:
                conditions.append("rule_id = ?")
                params.append(rule_id)
                
            if container_name:
                conditions.append("container_name = ?")
                params.append(container_name)
                
            if conditions:
                query += " WHERE " + " AND ".join(conditions)
                
            query += " ORDER BY created_at DESC LIMIT ?"
            params.append(limit)
            
            rows = conn.execute(query, params).fetchall()
            
            logs = []
            for row in rows:
                log = ShutdownLog(
                    id=row['id'],
                    rule_id=row['rule_id'],
                    container_name=row['container_name'],
                    action=ShutdownAction(row['action']),
                    reason=row['reason'],
                    success=bool(row['success']),
                    error_message=row['error_message'],
                    created_at=datetime.fromisoformat(row['created_at']),
                    scheduled_restart=datetime.fromisoformat(row['scheduled_restart']) if row['scheduled_restart'] else None
                )
                logs.append(log)
                
            return logs

    async def get_container_stats(self, container_name: str = None) -> Union[ContainerStats, Dict[str, ContainerStats]]:
        """Récupère les statistiques des containers"""
        if container_name:
            return self.container_stats.get(container_name)
        return self.container_stats.copy()
