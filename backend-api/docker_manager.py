import docker
import asyncio
import time
import os
import logging
from typing import Dict, List, Optional
from docker.errors import NotFound, APIError

logger = logging.getLogger(__name__)

class DockerManager:
    def __init__(self):
        """
        Initialise le gestionnaire Docker avec connexion au socket Docker
        """
        try:
            self.client = docker.from_env()
            # Test de connexion
            self.client.ping()
            logger.info("Connexion Docker établie avec succès")
        except Exception as e:
            logger.error(f"Erreur de connexion Docker: {str(e)}")
            raise
        
        # Configuration
        self.startup_timeout = int(os.getenv("STARTUP_TIMEOUT", 120))
        
    async def get_container_status(self, container_name: str) -> Dict:
        """
        Récupère l'état d'un container
        
        Args:
            container_name: Nom du container
            
        Returns:
            Dict: Informations sur l'état du container
        """
        try:
            container = self.client.containers.get(container_name)
            
            # Calculer l'uptime si le container est en cours d'exécution
            uptime = None
            if container.status == "running":
                # Récupérer les stats du container
                stats = container.stats(stream=False)
                started_at = container.attrs['State']['StartedAt']
                if started_at:
                    # Calculer l'uptime approximatif
                    uptime = int(time.time() - time.mktime(time.strptime(
                        started_at.split('.')[0], "%Y-%m-%dT%H:%M:%S"
                    )))
            
            # Récupérer le port exposé
            port = None
            if container.ports:
                for container_port, host_configs in container.ports.items():
                    if host_configs:
                        port = int(host_configs[0]['HostPort'])
                        break
            
            status_map = {
                "running": "running",
                "exited": "stopped",
                "created": "stopped",
                "restarting": "starting",
                "removing": "stopping",
                "paused": "paused",
                "dead": "stopped"
            }
            
            return {
                "status": status_map.get(container.status, "unknown"),
                "uptime": uptime,
                "port": port,
                "message": f"Container {container_name} est {container.status}"
            }
            
        except NotFound:
            logger.warning(f"Container {container_name} introuvable")
            return {
                "status": "not_found",
                "message": f"Container {container_name} introuvable"
            }
        except Exception as e:
            logger.error(f"Erreur lors de la vérification du container {container_name}: {str(e)}")
            return {
                "status": "error",
                "message": f"Erreur: {str(e)}"
            }
    
    async def start_container(self, container_name: str) -> Dict:
        """
        Démarre un container Docker
        
        Args:
            container_name: Nom du container à démarrer
            
        Returns:
            Dict: Résultat de l'opération
        """
        try:
            container = self.client.containers.get(container_name)
            
            if container.status == "running":
                return {
                    "success": True,
                    "message": "Container déjà en cours d'exécution"
                }
            
            logger.info(f"Démarrage du container {container_name}...")
            container.start()
            
            # Attendre que le container soit complètement démarré
            await self._wait_for_container_ready(container_name)
            
            return {
                "success": True,
                "message": "Container démarré avec succès"
            }
            
        except NotFound:
            logger.error(f"Container {container_name} introuvable")
            return {
                "success": False,
                "message": f"Container {container_name} introuvable"
            }
        except Exception as e:
            logger.error(f"Erreur lors du démarrage du container {container_name}: {str(e)}")
            return {
                "success": False,
                "message": f"Erreur lors du démarrage: {str(e)}"
            }
    
    async def stop_container(self, container_name: str) -> Dict:
        """
        Arrête un container Docker
        
        Args:
            container_name: Nom du container à arrêter
            
        Returns:
            Dict: Résultat de l'opération
        """
        try:
            container = self.client.containers.get(container_name)
            
            if container.status != "running":
                return {
                    "success": True,
                    "message": "Container déjà arrêté"
                }
            
            logger.info(f"Arrêt du container {container_name}...")
            container.stop(timeout=30)
            
            return {
                "success": True,
                "message": "Container arrêté avec succès"
            }
            
        except NotFound:
            logger.error(f"Container {container_name} introuvable")
            return {
                "success": False,
                "message": f"Container {container_name} introuvable"
            }
        except Exception as e:
            logger.error(f"Erreur lors de l'arrêt du container {container_name}: {str(e)}")
            return {
                "success": False,
                "message": f"Erreur lors de l'arrêt: {str(e)}"
            }
    
    async def _wait_for_container_ready(self, container_name: str, timeout: int = None) -> bool:
        """
        Attend qu'un container soit prêt à recevoir des connexions
        
        Args:
            container_name: Nom du container
            timeout: Timeout en secondes (utilise self.startup_timeout par défaut)
            
        Returns:
            bool: True si le container est prêt, False sinon
        """
        if timeout is None:
            timeout = self.startup_timeout
        
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            try:
                container = self.client.containers.get(container_name)
                
                if container.status == "running":
                    # Attendre un peu plus pour que l'application soit prête
                    await asyncio.sleep(2)
                    
                    # Optionnel: Test de santé personnalisé ici
                    # Par exemple, vérifier si le port répond
                    
                    logger.info(f"Container {container_name} prêt après {int(time.time() - start_time)}s")
                    return True
                    
                elif container.status in ["exited", "dead"]:
                    logger.error(f"Container {container_name} a échoué au démarrage")
                    return False
                
                # Attendre avant la prochaine vérification
                await asyncio.sleep(1)
                
            except NotFound:
                logger.error(f"Container {container_name} introuvable pendant l'attente")
                return False
            except Exception as e:
                logger.error(f"Erreur pendant l'attente du container {container_name}: {str(e)}")
                await asyncio.sleep(1)
        
        logger.warning(f"Timeout atteint pour le container {container_name} après {timeout}s")
        return False
    
    async def list_all_containers(self) -> List[Dict]:
        """
        Liste tous les containers Docker
        
        Returns:
            List[Dict]: Liste des containers avec leurs informations
        """
        try:
            containers = self.client.containers.list(all=True)
            
            result = []
            for container in containers:
                # Récupérer le port principal
                port = None
                if container.ports:
                    for container_port, host_configs in container.ports.items():
                        if host_configs:
                            port = int(host_configs[0]['HostPort'])
                            break
                
                result.append({
                    "name": container.name,
                    "status": container.status,
                    "image": container.image.tags[0] if container.image.tags else "unknown",
                    "port": port,
                    "created": container.attrs['Created']
                })
            
            return result
            
        except Exception as e:
            logger.error(f"Erreur lors de la récupération des containers: {str(e)}")
            return []
    
    async def get_container_logs(self, container_name: str, lines: int = 100) -> str:
        """
        Récupère les logs d'un container
        
        Args:
            container_name: Nom du container
            lines: Nombre de lignes à récupérer
            
        Returns:
            str: Logs du container
        """
        try:
            container = self.client.containers.get(container_name)
            logs = container.logs(tail=lines, timestamps=True).decode('utf-8')
            return logs
            
        except NotFound:
            return f"Container {container_name} introuvable"
        except Exception as e:
            logger.error(f"Erreur lors de la récupération des logs {container_name}: {str(e)}")
            return f"Erreur: {str(e)}"