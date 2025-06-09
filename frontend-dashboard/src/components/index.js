// Créons tous les composants restants avec des placeholders fonctionnels

import React from 'react';
import { Cpu, MemoryStick, HardDrive } from 'lucide-react';

const Monitoring = ({ systemMetrics, recentEvents }) => (
  <div className="space-y-6">
    <h2 className="text-2xl font-bold text-gray-900">Monitoring Système</h2>
    
    <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
      <div className="bg-white rounded-lg shadow-md p-6">
        <div className="flex items-center justify-between mb-4">
          <h3 className="text-lg font-semibold text-gray-900">CPU</h3>
          <Cpu className="w-6 h-6 text-blue-500" />
        </div>
        <div className="text-3xl font-bold text-gray-900 mb-2">
          {systemMetrics.cpuUsage.toFixed(1)}%
        </div>
        <div className="w-full bg-gray-200 rounded-full h-2">
          <div 
            className="bg-blue-500 h-2 rounded-full transition-all duration-500"
            style={{ width: `${systemMetrics.cpuUsage}%` }}
          />
        </div>
      </div>

      <div className="bg-white rounded-lg shadow-md p-6">
        <div className="flex items-center justify-between mb-4">
          <h3 className="text-lg font-semibold text-gray-900">Mémoire</h3>
          <MemoryStick className="w-6 h-6 text-green-500" />
        </div>
        <div className="text-3xl font-bold text-gray-900 mb-2">
          {systemMetrics.memoryUsage.toFixed(1)}%
        </div>
        <div className="w-full bg-gray-200 rounded-full h-2">
          <div 
            className="bg-green-500 h-2 rounded-full transition-all duration-500"
            style={{ width: `${systemMetrics.memoryUsage}%` }}
          />
        </div>
      </div>

      <div className="bg-white rounded-lg shadow-md p-6">
        <div className="flex items-center justify-between mb-4">
          <h3 className="text-lg font-semibold text-gray-900">Disque</h3>
          <HardDrive className="w-6 h-6 text-yellow-500" />
        </div>
        <div className="text-3xl font-bold text-gray-900 mb-2">
          {systemMetrics.diskUsage.toFixed(1)}%
        </div>
        <div className="w-full bg-gray-200 rounded-full h-2">
          <div 
            className="bg-yellow-500 h-2 rounded-full transition-all duration-500"
            style={{ width: `${systemMetrics.diskUsage}%` }}
          />
        </div>
      </div>
    </div>

    <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
      <div className="bg-white rounded-lg shadow-md p-6">
        <h3 className="text-lg font-semibold text-gray-900 mb-4">Trafic Réseau</h3>
        <div className="space-y-4">
          <div className="flex items-center justify-between">
            <span className="text-sm text-gray-600">Entrant</span>
            <span className="text-sm font-medium text-gray-900">
              {systemMetrics.networkIn.toFixed(2)} MB/s
            </span>
          </div>
          <div className="flex items-center justify-between">
            <span className="text-sm text-gray-600">Sortant</span>
            <span className="text-sm font-medium text-gray-900">
              {systemMetrics.networkOut.toFixed(2)} MB/s
            </span>
          </div>
        </div>
      </div>

      <div className="bg-white rounded-lg shadow-md p-6">
        <h3 className="text-lg font-semibold text-gray-900 mb-4">Logs Système</h3>
        <div className="space-y-2 max-h-64 overflow-y-auto">
          {recentEvents.map(event => (
            <div key={event.id} className="text-sm">
              <span className="text-gray-500">
                {event.timestamp.toLocaleTimeString()}
              </span>
              <span className="ml-2 text-gray-900">{event.message}</span>
            </div>
          ))}
        </div>
      </div>
    </div>
  </div>
);

const Automation = ({ rules }) => (
  <div className="space-y-6">
    <div className="flex items-center justify-between">
      <h2 className="text-2xl font-bold text-gray-900">Règles d'Automation</h2>
      <button className="bg-blue-600 text-white px-4 py-2 rounded-lg hover:bg-blue-700">
        Nouvelle règle
      </button>
    </div>
    <div className="bg-white rounded-lg shadow-md p-6">
      <p className="text-gray-500">Gestion des règles d'extinction automatique des containers.</p>
    </div>
  </div>
);

const Webhooks = ({ webhooks }) => (
  <div className="space-y-6">
    <div className="flex items-center justify-between">
      <h2 className="text-2xl font-bold text-gray-900">Webhooks & Notifications</h2>
      <button className="bg-blue-600 text-white px-4 py-2 rounded-lg hover:bg-blue-700">
        Ajouter webhook
      </button>
    </div>
    <div className="bg-white rounded-lg shadow-md p-6">
      <p className="text-gray-500">Configuration des notifications et webhooks.</p>
    </div>
  </div>
);

const SettingsTab = () => (
  <div className="space-y-6">
    <h2 className="text-2xl font-bold text-gray-900">Paramètres</h2>
    <div className="bg-white rounded-lg shadow-md p-6">
      <p className="text-gray-500">Configuration générale du système SelfStart.</p>
    </div>
  </div>
);

const ContainerModal = ({ container, onClose, onAction }) => {
  if (!container) return null;

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
      <div className="bg-white rounded-lg shadow-xl max-w-2xl w-full m-4">
        <div className="flex items-center justify-between p-6 border-b">
          <h2 className="text-xl font-semibold text-gray-900">
            Détails - {container.name}
          </h2>
          <button onClick={onClose} className="text-gray-400 hover:text-gray-600">
            ×
          </button>
        </div>
        <div className="p-6">
          <p className="text-gray-500">Détails du container {container.name}</p>
          <div className="mt-4 flex space-x-3">
            <button 
              onClick={() => {
                onAction(container.status === 'running' ? 'stop' : 'start', container.name);
                onClose();
              }}
              className="bg-blue-600 text-white px-4 py-2 rounded-lg hover:bg-blue-700"
            >
              {container.status === 'running' ? 'Arrêter' : 'Démarrer'}
            </button>
            <button onClick={onClose} className="bg-gray-300 text-gray-700 px-4 py-2 rounded-lg hover:bg-gray-400">
              Fermer
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};

export { Monitoring, Automation, Webhooks, SettingsTab, ContainerModal };
