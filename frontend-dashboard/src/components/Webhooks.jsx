import React from 'react';
import { Plus, Edit3, Trash2 } from 'lucide-react';

const Webhooks = ({ webhooks }) => (
  <div className="space-y-6">
    <div className="flex items-center justify-between">
      <h2 className="text-2xl font-bold text-gray-900">Webhooks & Notifications</h2>
      <button className="bg-blue-600 text-white px-4 py-2 rounded-lg hover:bg-blue-700 flex items-center space-x-2">
        <Plus className="w-4 h-4" />
        <span>Ajouter webhook</span>
      </button>
    </div>
    
    <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
      {webhooks?.map(webhook => (
        <div key={webhook.id} className="bg-white rounded-lg shadow-md p-6">
          <div className="flex items-center justify-between mb-4">
            <div className="flex items-center space-x-3">
              <div className={`w-3 h-3 rounded-full ${
                webhook.enabled ? 'bg-green-500' : 'bg-gray-400'
              }`} />
              <h3 className="text-lg font-semibold text-gray-900">{webhook.name}</h3>
            </div>
            <div className="flex items-center space-x-2">
              <button className="text-gray-600 hover:text-gray-900">
                <Edit3 className="w-4 h-4" />
              </button>
              <button className="text-red-600 hover:text-red-900">
                <Trash2 className="w-4 h-4" />
              </button>
            </div>
          </div>
          
          <div className="space-y-2 mb-4">
            <div className="text-sm">
              <span className="text-gray-600">Provider:</span>
              <span className="ml-1 font-medium text-gray-900 capitalize">{webhook.provider}</span>
            </div>
            <div className="text-sm">
              <span className="text-gray-600">URL:</span>
              <span className="ml-1 text-gray-900 text-xs break-all">
                {webhook.url.substring(0, 50)}...
              </span>
            </div>
            <div className="text-sm">
              <span className="text-gray-600">Événements:</span>
              <div className="mt-1 flex flex-wrap gap-1">
                {webhook.events.map(event => (
                  <span key={event} className="px-2 py-1 text-xs bg-blue-100 text-blue-800 rounded">
                    {event.replace('_', ' ')}
                  </span>
                ))}
              </div>
            </div>
          </div>

          <div className="flex items-center justify-between">
            <span className={`px-2 py-1 text-xs font-medium rounded-full ${
              webhook.enabled ? 'bg-green-100 text-green-800' : 'bg-gray-100 text-gray-800'
            }`}>
              {webhook.enabled ? 'Activé' : 'Désactivé'}
            </span>
            <button className="text-blue-600 hover:text-blue-900 text-sm font-medium">
              Tester
            </button>
          </div>
        </div>
      ))}
    </div>
  </div>
);

export default Webhooks;