import { useState, useEffect, useCallback } from 'react';

const ContainerStatus = {
  RUNNING: 'running',
  STOPPED: 'stopped',
  STARTING: 'starting',
  ERROR: 'error'
};

const EventType = {
  CONTAINER_STARTED: 'container_started',
  CONTAINER_STOPPED: 'container_stopped',
  CONTAINER_FAILED: 'container_failed',
  SYSTEM_WARNING: 'system_warning'
};

export const useSimulatedData = () => {
  const [containers, setContainers] = useState([
    { 
      id: 1, 
      name: 'sonarr', 
      status: ContainerStatus.RUNNING, 
      uptime: '2h 15m', 
      cpu: 15.5, 
      memory: 256, 
      port: 8989,
      image: 'linuxserver/sonarr:latest',
      lastActivity: new Date(Date.now() - 300000),
      autoShutdown: true
    },
    { 
      id: 2, 
      name: 'radarr', 
      status: ContainerStatus.STOPPED, 
      uptime: '0m', 
      cpu: 0, 
      memory: 0, 
      port: 7878,
      image: 'linuxserver/radarr:latest',
      lastActivity: new Date(Date.now() - 3600000),
      autoShutdown: false
    },
    { 
      id: 3, 
      name: 'jellyfin', 
      status: ContainerStatus.RUNNING, 
      uptime: '5h 32m', 
      cpu: 45.2, 
      memory: 512, 
      port: 8096,
      image: 'linuxserver/jellyfin:latest',
      lastActivity: new Date(Date.now() - 60000),
      autoShutdown: true
    },
    { 
      id: 4, 
      name: 'portainer', 
      status: ContainerStatus.STARTING, 
      uptime: '0m', 
      cpu: 8.1, 
      memory: 128, 
      port: 9000,
      image: 'portainer/portainer-ce:latest',
      lastActivity: new Date(),
      autoShutdown: false
    }
  ]);

  const [systemMetrics, setSystemMetrics] = useState({
    totalContainers: 4,
    runningContainers: 2,
    cpuUsage: 35.8,
    memoryUsage: 68.4,
    diskUsage: 45.2,
    networkIn: 1.2,
    networkOut: 0.8
  });

  const [recentEvents] = useState([
    { id: 1, type: EventType.CONTAINER_STARTED, container: 'sonarr', message: 'Container démarré avec succès', timestamp: new Date(Date.now() - 300000) },
    { id: 2, type: EventType.CONTAINER_STOPPED, container: 'radarr', message: 'Arrêt automatique après inactivité', timestamp: new Date(Date.now() - 900000) },
    { id: 3, type: EventType.SYSTEM_WARNING, container: null, message: 'Utilisation CPU élevée détectée', timestamp: new Date(Date.now() - 1800000) },
    { id: 4, type: EventType.CONTAINER_FAILED, container: 'bazarr', message: 'Échec du démarrage - port déjà utilisé', timestamp: new Date(Date.now() - 2700000) }
  ]);

  const [shutdownRules] = useState([
    { 
      id: 1, 
      name: 'Inactivité nocturne', 
      enabled: true, 
      condition: 'inactivity', 
      threshold: 3600, 
      containers: ['sonarr', 'radarr'], 
      schedule: '0 2 * * *' 
    },
    { 
      id: 2, 
      name: 'Ressources faibles', 
      enabled: true, 
      condition: 'low_resources', 
      threshold: 5, 
      containers: ['*'], 
      schedule: null 
    }
  ]);

  const [webhooks] = useState([
    { 
      id: 1, 
      name: 'Discord Notifications', 
      provider: 'discord', 
      url: 'https://discord.com/api/webhooks/...', 
      enabled: true, 
      events: ['container_started', 'container_failed'] 
    },
    { 
      id: 2, 
      name: 'Slack Alerts', 
      provider: 'slack', 
      url: 'https://hooks.slack.com/services/...', 
      enabled: false, 
      events: ['system_warning'] 
    }
  ]);

  const handleContainerAction = useCallback(async (action, containerName) => {
    setContainers(prev => prev.map(container => 
      container.name === containerName 
        ? { ...container, status: action === 'start' ? ContainerStatus.STARTING : ContainerStatus.STOPPED }
        : container
    ));
    
    setTimeout(() => {
      if (action === 'start') {
        setContainers(prev => prev.map(container => 
          container.name === containerName 
            ? { ...container, status: ContainerStatus.RUNNING }
            : container
        ));
      }
    }, 2000);
  }, []);

  useEffect(() => {
    const interval = setInterval(() => {
      setSystemMetrics(prev => ({
        ...prev,
        cpuUsage: Math.max(0, Math.min(100, prev.cpuUsage + (Math.random() - 0.5) * 10)),
        memoryUsage: Math.max(0, Math.min(100, prev.memoryUsage + (Math.random() - 0.5) * 5)),
        networkIn: Math.max(0, prev.networkIn + (Math.random() - 0.5) * 0.5),
        networkOut: Math.max(0, prev.networkOut + (Math.random() - 0.5) * 0.3)
      }));

      setContainers(prev => prev.map(container => ({
        ...container,
        cpu: container.status === ContainerStatus.RUNNING ? 
          Math.max(0, Math.min(100, container.cpu + (Math.random() - 0.5) * 10)) : 0,
        memory: container.status === ContainerStatus.RUNNING ? 
          Math.max(0, container.memory + (Math.random() - 0.5) * 50) : 0
      })));
    }, 3000);

    return () => clearInterval(interval);
  }, []);

  return {
    containers,
    setContainers,
    systemMetrics,
    recentEvents,
    shutdownRules,
    webhooks,
    handleContainerAction,
    ContainerStatus,
    EventType
  };
};
