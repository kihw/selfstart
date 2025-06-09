import React from 'react';
import { Plus, Search, Filter, RefreshCw, Play, Square, RotateCcw, Eye, MoreVertical } from 'lucide-react';
import { StatusBadge } from './UIComponents';

const Containers = ({ containers, searchTerm, setSearchTerm, onContainerAction, onSelectContainer }) => {
  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h2 className="text-2xl font-bold text-gray-900">Gestion des Containers</h2>
        <button className="bg-blue-600 text-white px-4 py-2 rounded-lg hover:bg-blue-700 flex items-center space-x-2">
          <Plus className="w-4 h-4" />
          <span>Ajouter</span>
        </button>
      </div>

      {/* Barre de recherche et filtres */}
      <div className="flex items-center space-x-4">
        <div className="flex-1 relative">
          <Search className="w-5 h-5 absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400" />
          <input
            type="text"
            placeholder="Rechercher un container..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            className="w-full pl-10 pr-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
          />
        </div>
        <button className="p-2 border border-gray-300 rounded-lg hover:bg-gray-50">
          <Filter className="w-5 h-5 text-gray-600" />
        </button>
        <button className="p-2 border border-gray-300 rounded-lg hover:bg-gray-50">
          <RefreshCw className="w-5 h-5 text-gray-600" />
        </button>
      </div>

      {/* Table des containers */}
      <div className="bg-white rounded-lg shadow-md overflow-hidden">
        <table className="min-w-full divide-y divide-gray-200">
          <thead className="bg-gray-50">
            <tr>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Container
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Status
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Ressources
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Uptime
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Actions
              </th>
            </tr>
          </thead>
          <tbody className="bg-white divide-y divide-gray-200">
            {containers.map(container => (
              <tr key={container.id} className="hover:bg-gray-50">
                <td className="px-6 py-4 whitespace-nowrap">
                  <div className="flex items-center">
                    <div className={`w-3 h-3 rounded-full mr-3 ${
                      container.status === 'running' ? 'bg-green-500' :
                      container.status === 'starting' ? 'bg-blue-500' :
                      container.status === 'stopped' ? 'bg-gray-400' : 'bg-red-500'
                    }`} />
                    <div>
                      <div className="text-sm font-medium text-gray-900">{container.name}</div>
                      <div className="text-sm text-gray-500">Port {container.port}</div>
                    </div>
                  </div>
                </td>
                <td className="px-6 py-4 whitespace-nowrap">
                  <StatusBadge status={container.status}>
                    {container.status}
                  </StatusBadge>
                </td>
                <td className="px-6 py-4 whitespace-nowrap">
                  <div className="text-sm text-gray-900">
                    CPU: {container.cpu.toFixed(1)}%
                  </div>
                  <div className="text-sm text-gray-500">
                    RAM: {container.memory}MB
                  </div>
                </td>
                <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                  {container.uptime}
                </td>
                <td className="px-6 py-4 whitespace-nowrap text-sm font-medium">
                  <div className="flex items-center space-x-2">
                    <button
                      onClick={() => onContainerAction(
                        container.status === 'running' ? 'stop' : 'start',
                        container.name
                      )}
                      className={`p-2 rounded hover:bg-gray-100 ${
                        container.status === 'running' ? 'text-red-600' : 'text-green-600'
                      }`}
                    >
                      {container.status === 'running' ? 
                        <Square className="w-4 h-4" /> :
                        <Play className="w-4 h-4" />
                      }
                    </button>
                    <button className="p-2 rounded hover:bg-gray-100 text-blue-600">
                      <RotateCcw className="w-4 h-4" />
                    </button>
                    <button 
                      onClick={() => onSelectContainer(container)}
                      className="p-2 rounded hover:bg-gray-100 text-gray-600"
                    >
                      <Eye className="w-4 h-4" />
                    </button>
                    <button className="p-2 rounded hover:bg-gray-100 text-gray-600">
                      <MoreVertical className="w-4 h-4" />
                    </button>
                  </div>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
};

export default Containers;
