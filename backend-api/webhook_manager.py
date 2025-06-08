import asyncio
import aiohttp
import json
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from enum import Enum
from pydantic import BaseModel, HttpUrl
import sqlite3
import os

logger = logging.getLogger(__name__)

class WebhookEvent(str, Enum):
    CONTAINER_STARTED = "container.started"
    CONTAINER_STOPPED = "container.stopped"
    CONTAINER_FAILED = "container.failed"
    CONTAINER_RESTARTED = "container.restarted"
    SYSTEM_ERROR = "system.error"
    SYSTEM_WARNING = "system.warning"

class WebhookProvider(str, Enum):
    DISCORD = "discord"
    SLACK = "slack"
    TEAMS = "teams"
    WEBHOOK = "webhook"
    EMAIL = "email"

class WebhookConfig(BaseModel):
    id: Optional[int] = None
    name: str
    provider: WebhookProvider
    url: HttpUrl
    events: List[WebhookEvent]
    enabled: bool = True
    retry_count: int = 3
    retry_delay: int = 60  # secondes
    filters: Dict[str, Any] = {}  # Filtres pour containers spécifiques
    template: Optional[str] = None  # Template personnalisé pour le message
    headers: Dict[str, str] = {}  # Headers supplémentaires
    created_at: Optional[datetime] = None
    last_triggered: Optional[datetime] = None

class WebhookLog(BaseModel):
    id: Optional[int] = None
    webhook_id: int
    event: WebhookEvent
    container_name: Optional[str] = None
    payload: Dict[str, Any]
    response_status: Optional[int] = None
    response_body: Optional[str] = None
    success: bool
    error_message: Optional[str] = None
    created_at: datetime
    retry_count: int = 0

class WebhookManager:
    def __init__(self, db_path: str = "data/webhooks.db"):
        self.db_path = db_path
        self.session: Optional[aiohttp.ClientSession] = None
        self._init_database()
        
    def _init_database(self):
        """Initialise la base de données SQLite pour les webhooks"""
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        
        with sqlite3.connect(self.db_path) as conn:
            # Table des configurations webhook
            conn.execute("""
                CREATE TABLE IF NOT EXISTS webhooks (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL,
                    provider TEXT NOT NULL,
                    url TEXT NOT NULL,
                    events TEXT NOT NULL,  -- JSON array
                    enabled BOOLEAN DEFAULT TRUE,
                    retry_count INTEGER DEFAULT 3,
                    retry_delay INTEGER DEFAULT 60,
                    filters TEXT DEFAULT '{}',  -- JSON object
                    template TEXT,
                    headers TEXT DEFAULT '{}',  -- JSON object
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    last_triggered TIMESTAMP
                )
            """)
            
            # Table des logs webhook
            conn.execute("""
                CREATE TABLE IF NOT EXISTS webhook_logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    webhook_id INTEGER NOT NULL,
                    event TEXT NOT NULL,
                    container_name TEXT,
                    payload TEXT NOT NULL,  -- JSON
                    response_status INTEGER,
                    response_body TEXT,
                    success BOOLEAN NOT NULL,
                    error_message TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    retry_count INTEGER DEFAULT 0,
                    FOREIGN KEY (webhook_id) REFERENCES webhooks (id)
                )
            """)
            
            conn.commit()

    async def get_session(self) -> aiohttp.ClientSession:
        """Récupère ou crée une session HTTP"""
        if self.session is None or self.session.closed:
            timeout = aiohttp.ClientTimeout(total=30)
            self.session = aiohttp.ClientSession(timeout=timeout)
        return self.session

    async def close(self):
        """Ferme la session HTTP"""
        if self.session and not self.session.closed:
            await self.session.close()

    async def create_webhook(self, webhook: WebhookConfig) -> int:
        """Crée un nouveau webhook"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("""
                INSERT INTO webhooks (name, provider, url, events, enabled, 
                                    retry_count, retry_delay, filters, template, headers)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                webhook.name,
                webhook.provider.value,
                str(webhook.url),
                json.dumps([event.value for event in webhook.events]),
                webhook.enabled,
                webhook.retry_count,
                webhook.retry_delay,
                json.dumps(webhook.filters),
                webhook.template,
                json.dumps(webhook.headers)
            ))
            conn.commit()
            return cursor.lastrowid

    async def get_webhooks(self, enabled_only: bool = False) -> List[WebhookConfig]:
        """Récupère tous les webhooks"""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            query = "SELECT * FROM webhooks"
            params = []
            
            if enabled_only:
                query += " WHERE enabled = ?"
                params.append(True)
                
            rows = conn.execute(query, params).fetchall()
            
            webhooks = []
            for row in rows:
                webhook = WebhookConfig(
                    id=row['id'],
                    name=row['name'],
                    provider=WebhookProvider(row['provider']),
                    url=row['url'],
                    events=[WebhookEvent(event) for event in json.loads(row['events'])],
                    enabled=bool(row['enabled']),
                    retry_count=row['retry_count'],
                    retry_delay=row['retry_delay'],
                    filters=json.loads(row['filters']),
                    template=row['template'],
                    headers=json.loads(row['headers']),
                    created_at=datetime.fromisoformat(row['created_at']) if row['created_at'] else None,
                    last_triggered=datetime.fromisoformat(row['last_triggered']) if row['last_triggered'] else None
                )
                webhooks.append(webhook)
                
            return webhooks

    async def update_webhook(self, webhook_id: int, webhook: WebhookConfig) -> bool:
        """Met à jour un webhook"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("""
                UPDATE webhooks SET 
                    name = ?, provider = ?, url = ?, events = ?, enabled = ?,
                    retry_count = ?, retry_delay = ?, filters = ?, template = ?, headers = ?
                WHERE id = ?
            """, (
                webhook.name,
                webhook.provider.value,
                str(webhook.url),
                json.dumps([event.value for event in webhook.events]),
                webhook.enabled,
                webhook.retry_count,
                webhook.retry_delay,
                json.dumps(webhook.filters),
                webhook.template,
                json.dumps(webhook.headers),
                webhook_id
            ))
            conn.commit()
            return cursor.rowcount > 0

    async def delete_webhook(self, webhook_id: int) -> bool:
        """Supprime un webhook"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("DELETE FROM webhooks WHERE id = ?", (webhook_id,))
            conn.commit()
            return cursor.rowcount > 0

    async def trigger_event(self, event: WebhookEvent, container_name: str = None, 
                          additional_data: Dict[str, Any] = None):
        """Déclenche un événement webhook"""
        try:
            webhooks = await self.get_webhooks(enabled_only=True)
            
            for webhook in webhooks:
                if event in webhook.events:
                    # Vérifier les filtres
                    if self._should_trigger_webhook(webhook, container_name, additional_data):
                        await self._send_webhook(webhook, event, container_name, additional_data)
                        
        except Exception as e:
            logger.error(f"Erreur lors du déclenchement des webhooks: {str(e)}")

    def _should_trigger_webhook(self, webhook: WebhookConfig, container_name: str, 
                               additional_data: Dict[str, Any]) -> bool:
        """Vérifie si le webhook doit être déclenché selon les filtres"""
        filters = webhook.filters
        
        # Filtre par nom de container
        if 'containers' in filters:
            allowed_containers = filters['containers']
            if isinstance(allowed_containers, list) and container_name:
                if container_name not in allowed_containers:
                    return False
        
        # Filtre par tags/labels
        if 'tags' in filters and additional_data:
            required_tags = filters['tags']
            container_tags = additional_data.get('tags', [])
            if not all(tag in container_tags for tag in required_tags):
                return False
        
        return True

    async def _send_webhook(self, webhook: WebhookConfig, event: WebhookEvent, 
                          container_name: str, additional_data: Dict[str, Any]):
        """Envoie un webhook"""
        payload = self._build_payload(webhook, event, container_name, additional_data)
        
        for attempt in range(webhook.retry_count + 1):
            try:
                success = await self._make_http_request(webhook, payload)
                
                # Logger le résultat
                await self._log_webhook(webhook.id, event, container_name, payload, 
                                      success, None, attempt)
                
                if success:
                    # Mettre à jour last_triggered
                    await self._update_last_triggered(webhook.id)
                    break
                    
            except Exception as e:
                error_msg = str(e)
                logger.error(f"Erreur webhook {webhook.name} (tentative {attempt + 1}): {error_msg}")
                
                await self._log_webhook(webhook.id, event, container_name, payload, 
                                      False, error_msg, attempt)
                
                if attempt < webhook.retry_count:
                    await asyncio.sleep(webhook.retry_delay)

    def _build_payload(self, webhook: WebhookConfig, event: WebhookEvent, 
                      container_name: str, additional_data: Dict[str, Any]) -> Dict[str, Any]:
        """Construit le payload du webhook"""
        base_payload = {
            "event": event.value,
            "container_name": container_name,
            "timestamp": datetime.now().isoformat(),
            "source": "selfstart",
            **additional_data or {}
        }
        
        # Appliquer le template personnalisé si défini
        if webhook.template:
            try:
                # Template simple avec remplacement de variables
                message = webhook.template.format(
                    event=event.value,
                    container_name=container_name or "unknown",
                    timestamp=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    **additional_data or {}
                )
                
                # Format spécifique selon le provider
                if webhook.provider == WebhookProvider.DISCORD:
                    return {"content": message}
                elif webhook.provider == WebhookProvider.SLACK:
                    return {"text": message}
                elif webhook.provider == WebhookProvider.TEAMS:
                    return {"text": message}
                
            except Exception as e:
                logger.warning(f"Erreur dans le template webhook {webhook.name}: {str(e)}")
        
        # Format par défaut selon le provider
        if webhook.provider == WebhookProvider.DISCORD:
            return {
                "content": f"🐳 **SelfStart Event**: `{event.value}`",
                "embeds": [{
                    "title": f"Container: {container_name or 'System'}",
                    "description": f"Event: {event.value}",
                    "color": self._get_color_for_event(event),
                    "timestamp": datetime.now().isoformat(),
                    "fields": [
                        {"name": key, "value": str(value), "inline": True}
                        for key, value in (additional_data or {}).items()
                    ]
                }]
            }
        elif webhook.provider == WebhookProvider.SLACK:
            return {
                "text": f"SelfStart Event: {event.value}",
                "attachments": [{
                    "color": "good" if "started" in event.value else "warning",
                    "fields": [
                        {"title": "Container", "value": container_name or "System", "short": True},
                        {"title": "Event", "value": event.value, "short": True},
                        *[
                            {"title": key, "value": str(value), "short": True}
                            for key, value in (additional_data or {}).items()
                        ]
                    ],
                    "ts": datetime.now().timestamp()
                }]
            }
        
        return base_payload

    def _get_color_for_event(self, event: WebhookEvent) -> int:
        """Retourne une couleur pour l'événement (Discord)"""
        color_map = {
            WebhookEvent.CONTAINER_STARTED: 0x00ff00,    # Vert
            WebhookEvent.CONTAINER_STOPPED: 0xffa500,    # Orange
            WebhookEvent.CONTAINER_FAILED: 0xff0000,     # Rouge
            WebhookEvent.CONTAINER_RESTARTED: 0x0000ff,  # Bleu
            WebhookEvent.SYSTEM_ERROR: 0xff0000,         # Rouge
            WebhookEvent.SYSTEM_WARNING: 0xffff00,       # Jaune
        }
        return color_map.get(event, 0x808080)  # Gris par défaut

    async def _make_http_request(self, webhook: WebhookConfig, payload: Dict[str, Any]) -> bool:
        """Effectue la requête HTTP"""
        session = await self.get_session()
        
        headers = {
            "Content-Type": "application/json",
            "User-Agent": "SelfStart-Webhook/1.0",
            **webhook.headers
        }
        
        async with session.post(str(webhook.url), 
                               json=payload, 
                               headers=headers) as response:
            
            success = 200 <= response.status < 300
            
            if not success:
                response_text = await response.text()
                logger.warning(f"Webhook {webhook.name} failed: {response.status} - {response_text}")
            
            return success

    async def _log_webhook(self, webhook_id: int, event: WebhookEvent, 
                         container_name: str, payload: Dict[str, Any], 
                         success: bool, error_message: str, retry_count: int):
        """Enregistre un log de webhook"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                INSERT INTO webhook_logs 
                (webhook_id, event, container_name, payload, success, error_message, retry_count)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                webhook_id,
                event.value,
                container_name,
                json.dumps(payload),
                success,
                error_message,
                retry_count
            ))
            conn.commit()

    async def _update_last_triggered(self, webhook_id: int):
        """Met à jour la date de dernier déclenchement"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                UPDATE webhooks SET last_triggered = CURRENT_TIMESTAMP WHERE id = ?
            """, (webhook_id,))
            conn.commit()

    async def get_webhook_logs(self, webhook_id: int = None, limit: int = 100) -> List[WebhookLog]:
        """Récupère les logs des webhooks"""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            
            query = "SELECT * FROM webhook_logs"
            params = []
            
            if webhook_id:
                query += " WHERE webhook_id = ?"
                params.append(webhook_id)
            
            query += " ORDER BY created_at DESC LIMIT ?"
            params.append(limit)
            
            rows = conn.execute(query, params).fetchall()
            
            logs = []
            for row in rows:
                log = WebhookLog(
                    id=row['id'],
                    webhook_id=row['webhook_id'],
                    event=WebhookEvent(row['event']),
                    container_name=row['container_name'],
                    payload=json.loads(row['payload']),
                    response_status=row['response_status'],
                    response_body=row['response_body'],
                    success=bool(row['success']),
                    error_message=row['error_message'],
                    created_at=datetime.fromisoformat(row['created_at']),
                    retry_count=row['retry_count']
                )
                logs.append(log)
            
            return logs

    async def test_webhook(self, webhook_id: int) -> bool:
        """Teste un webhook"""
        webhooks = await self.get_webhooks()
        webhook = next((w for w in webhooks if w.id == webhook_id), None)
        
        if not webhook:
            return False
        
        await self._send_webhook(
            webhook, 
            WebhookEvent.SYSTEM_WARNING, 
            "test", 
            {"message": "Test webhook from SelfStart"}
        )
        
        return True
