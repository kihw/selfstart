import React from 'react';
import { Server, Cpu, MemoryStick, Network, Play, Square } from 'lucide-react';
import { StatusBadge, MetricCard } from './UIComponents';

const Overview = ({ containers, systemMetrics, recentEvents, onContainerAction }) => {
  const EventType = {
    CONTAINER_STARTED: 'container_started',
    CONTAINER_STOPPED: 'container_stopped',
    CONTAINER_FAILED: 'container_failed',
    SYSTEM_WARNING: 'system_warning'
  };

  return (
    <div className="space-y-6">
      {/* Métriques système */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        <MetricCard
          title="Containers Actifs"
          value={`${systemMetrics.runningContainers}/${systemMetrics.totalContainers}`}
          subtitle="En cours d'exécution"
          icon={Server}
          color="blue"
          trend={+12}
        />
        <MetricCard
          title="CPU"
          value={`${systemMetrics.cpuUsage.toFixed(1)}%`}
          subtitle="Utilisation moyenne"
          icon={Cpu}
          color="green"
          trend={-5}
        />
        <MetricCard
          title="Mémoire"
          value={`${systemMetrics.memoryUsage.toFixed(1)}%`}
          subtitle="RAM utilisée"
          icon={MemoryStick}
          color="yellow"
          trend={+2}
        />
        <MetricCard
          title="Réseau"
          value={`${systemMetrics.networkIn.toFixed(1)} MB/s`}
          subtitle="Trafic entrant"
          icon={Network}
          color="purple"
          trend={+18}
        />
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Status des containers */}
        <div className="bg-white rounded-lg shadow-md p-6">
          <h3 className="text-lg font-semibold text-gray-900 mb-4">Containers</h3>
          <div className="space-y-3">
            {containers.slice(0, 4).map(container => (
              <div key={container.id} className="flex items-center justify-between p-3 bg-gray-50 rounded-lg">
                <div className="flex items-center space-x-3">
                  <div className={`w-3 h-3 rounded-full ${
                    container.status === 'running' ? 'bg-green-500' :
                    container.status === 'starting' ? 'bg-blue-500' :
                    container.status === 'stopped' ? 'bg-gray-400' : 'bg-red-500'
                  }`} />
                  <div>
                    <p className="font-medium text-gray-900">{container.name}</p>
                    <p className="text-sm text-gray-500">Port {container.port}</p>
                  </div>
                </div>
                <div className="flex items-center space-x-2">
                  <StatusBadge status={container.status}>
                    {container.status}
                  </StatusBadge>
                  <button
                    onClick={() => onContainerAction(
                      container.status === 'running' ? 'stop' : 'start',
                      container.name
                    )}
                    className="p-1 hover:bg-gray-200 rounded"
                  >
                    {container.status === 'running' ? 
                      <Square className="w-4 h-4 text-gray-600" /> :
                      <Play className="w-4 h-4 text-gray-600" />
                    }
                  </button>
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Événements récents */}
        <div className="bg-white rounded-lg shadow-md p-6">
          <h3 className="text-lg font-semibold text-gray-900 mb-4">Événements récents</h3>
          <div className="space-y-3">
            {recentEvents.slice(0, 4).map(event => (
              <div key={event.id} className="flex items-start space-x-3 p-3 bg-gray-50 rounded-lg">
                <div className={`w-2 h-2 rounded-full mt-2 ${
                  event.type === EventType.CONTAINER_STARTED ? 'bg-green-500' :
                  event.type === EventType.CONTAINER_STOPPED ? 'bg-yellow-500' :
                  event.type === EventType.CONTAINER_FAILED ? 'bg-red-500' : 'bg-blue-500'
                }`} />
                <div className="flex-1">
                  <p className="text-sm font-medium text-gray-900">{event.message}</p>
                  <div className="flex items-center space-x-2 mt-1">
                    {event.container && (
                      <span className="text-xs bg-blue-100 text-blue-800 px-2 py-1 rounded">
                        {event.container}
                      </span>
                    )}
                    <span className="text-xs text-gray-500">
                      {event.timestamp.toLocaleTimeString()}
                    </span>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
};

export default Overview;
