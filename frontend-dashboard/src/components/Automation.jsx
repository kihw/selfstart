import React from 'react';
import { Plus } from 'lucide-react';

const Automation = ({ rules }) => (
  <div className="space-y-6">
    <div className="flex items-center justify-between">
      <h2 className="text-2xl font-bold text-gray-900">Règles d'Automation</h2>
      <button className="bg-blue-600 text-white px-4 py-2 rounded-lg hover:bg-blue-700 flex items-center space-x-2">
        <Plus className="w-4 h-4" />
        <span>Nouvelle règle</span>
      </button>
    </div>
    <div className="bg-white rounded-lg shadow-md p-6">
      <p className="text-gray-500 mb-4">Gestion des règles d'extinction automatique des containers.</p>
      <div className="space-y-3">
        {rules?.map(rule => (
          <div key={rule.id} className="flex items-center justify-between p-3 bg-gray-50 rounded-lg">
            <div>
              <div className="font-medium text-gray-900">{rule.name}</div>
              <div className="text-sm text-gray-500">
                {rule.condition === 'inactivity' ? 'Inactivité' : 'Ressources faibles'} - 
                Seuil: {rule.threshold}{rule.condition === 'inactivity' ? 's' : '%'}
              </div>
            </div>
            <div className={`px-2 py-1 text-xs rounded-full ${
              rule.enabled ? 'bg-green-100 text-green-800' : 'bg-gray-100 text-gray-800'
            }`}>
              {rule.enabled ? 'Activé' : 'Désactivé'}
            </div>
          </div>
        ))}
      </div>
    </div>
  </div>
);

export default Automation;