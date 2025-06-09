import React from 'react';
import { XCircle, ExternalLink, Cpu, MemoryStick } from 'lucide-react';
import { StatusBadge } from './UIComponents';

const ContainerModal = ({ container, onClose, onAction }) => {
  if (!container) return null;

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
      <div className="bg-white rounded-lg shadow-xl max-w-2xl w-full m-4 max-h-screen overflow-y-auto">
        <div className="flex items-center justify-between p-6 border-b">
          <h2 className="text-xl font-semibold text-gray-900">
            Détails - {container.name}
          </h2>
          <button
            onClick={onClose}
            className="text-gray-400 hover:text-gray-600"
          >
            <XCircle className="w-6 h-6" />
          </button>
        </div>
        
        <div className="p-6 space-y-6">
          {/* Informations générales */}
          <div>
            <h3 className="text-lg font-medium text-gray-900 mb-3">Informations générales</h3>
            <div className="grid grid-cols-2 gap-4">
              <div>
                <span className="text-sm text-gray-600">Nom:</span>
                <div className="font-medium">{container.name}</div>
              </div>
              <div>
                <span className="text-sm text-gray-600">Status:</span>
                <div className="mt-1">
                  <StatusBadge status={container.status}>
                    {container.status}
                  </StatusBadge>
                </div>
              </div>
              <div>
                <span className="text-sm text-gray-600">Image:</span>
                <div className="font-medium text-sm">{container.image}</div>
              </div>
              <div>
                <span className="text-sm text-gray-600">Port:</span>
                <div className="font-medium">{container.port}</div>
              </div>
              <div>
                <span className="text-sm text-gray-600">Uptime:</span>
                <div className="font-medium">{container.uptime}</div>
              </div>
              <div>
                <span className="text-sm text-gray-600">Auto-shutdown:</span>
                <div className="font-medium">
                  {container.autoShutdown ? 'Activé' : 'Désactivé'}
                </div>
              </div>
            </div>
          </div>

          {/* Métriques */}
          <div>
            <h3 className="text-lg font-medium text-gray-900 mb-3">Métriques</h3>
            <div className="grid grid-cols-2 gap-4">
              <div className="bg-gray-50 rounded-lg p-4">
                <div className="flex items-center justify-between mb-2">
                  <span className="text-sm text-gray-600">CPU</span>
                  <Cpu className="w-4 h-4 text-gray-400" />
                </div>
                <div className="text-2xl font-bold text-gray-900">
                  {container.cpu.toFixed(1)}%
                </div>
                <div className="w-full bg-gray-200 rounded-full h-2 mt-2">
                  <div 
                    className="bg-blue-500 h-2 rounded-full"
                    style={{ width: `${container.cpu}%` }}
                  />
                </div>
              </div>
              
              <div className="bg-gray-50 rounded-lg p-4">
                <div className="flex items-center justify-between mb-2">
                  <span className="text-sm text-gray-600">Mémoire</span>
                  <MemoryStick className="w-4 h-4 text-gray-400" />
                </div>
                <div className="text-2xl font-bold text-gray-900">
                  {container.memory}MB
                </div>
                <div className="text-sm text-gray-500 mt-1">
                  RAM utilisée
                </div>
              </div>
            </div>
          </div>

          {/* Actions */}
          <div>
            <h3 className="text-lg font-medium text-gray-900 mb-3">Actions</h3>
            <div className="flex space-x-3">
              <button
                onClick={() => {
                  onAction(
                    container.status === 'running' ? 'stop' : 'start',
                    container.name
                  );
                  onClose();
                }}
                className={`px-4 py-2 rounded-lg text-white font-medium ${
                  container.status === 'running'
                    ? 'bg-red-600 hover:bg-red-700' 
                    : 'bg-green-600 hover:bg-green-700'
                }`}
              >
                {container.status === 'running' ? 'Arrêter' : 'Démarrer'}
              </button>
              
              <button className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 font-medium">
                Redémarrer
              </button>
              
              <button className="px-4 py-2 bg-gray-600 text-white rounded-lg hover:bg-gray-700 font-medium">
                Voir les logs
              </button>
              
              {container.status === 'running' && (
                <button className="px-4 py-2 bg-purple-600 text-white rounded-lg hover:bg-purple-700 font-medium flex items-center space-x-2">
                  <ExternalLink className="w-4 h-4" />
                  <span>Ouvrir</span>
                </button>
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default ContainerModal;