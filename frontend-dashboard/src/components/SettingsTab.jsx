import React from 'react';
import { Download, Upload, RefreshCw, Power } from 'lucide-react';

const SettingsTab = () => (
  <div className="space-y-6">
    <h2 className="text-2xl font-bold text-gray-900">Paramètres</h2>
    
    <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
      {/* Configuration générale */}
      <div className="bg-white rounded-lg shadow-md p-6">
        <h3 className="text-lg font-semibold text-gray-900 mb-4">Configuration Générale</h3>
        <div className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Domaine de base
            </label>
            <input
              type="text"
              defaultValue="exemple.com"
              className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
            />
          </div>
          
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Timeout de démarrage (secondes)
            </label>
            <input
              type="number"
              defaultValue="120"
              className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
            />
          </div>
          
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Intervalle de polling (ms)
            </label>
            <input
              type="number"
              defaultValue="2000"
              className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
            />
          </div>
        </div>
      </div>

      {/* Sécurité */}
      <div className="bg-white rounded-lg shadow-md p-6">
        <h3 className="text-lg font-semibold text-gray-900 mb-4">Sécurité</h3>
        <div className="space-y-4">
          <div className="flex items-center justify-between">
            <div>
              <div className="text-sm font-medium text-gray-900">Authentification basique</div>
              <div className="text-sm text-gray-500">Protéger l'interface d'administration</div>
            </div>
            <button className="relative inline-flex h-6 w-11 items-center rounded-full bg-blue-600">
              <span className="inline-block h-4 w-4 transform rounded-full bg-white transition translate-x-6" />
            </button>
          </div>
          
          <div className="flex items-center justify-between">
            <div>
              <div className="text-sm font-medium text-gray-900">Logs détaillés</div>
              <div className="text-sm text-gray-500">Enregistrer plus d'informations</div>
            </div>
            <button className="relative inline-flex h-6 w-11 items-center rounded-full bg-gray-200">
              <span className="inline-block h-4 w-4 transform rounded-full bg-white transition translate-x-1" />
            </button>
          </div>
        </div>
      </div>

      {/* Actions système */}
      <div className="bg-white rounded-lg shadow-md p-6">
        <h3 className="text-lg font-semibold text-gray-900 mb-4">Actions Système</h3>
        <div className="space-y-3">
          <button className="w-full bg-blue-600 text-white py-2 px-4 rounded-lg hover:bg-blue-700 flex items-center justify-center space-x-2">
            <Download className="w-4 h-4" />
            <span>Sauvegarder la configuration</span>
          </button>
          
          <button className="w-full bg-green-600 text-white py-2 px-4 rounded-lg hover:bg-green-700 flex items-center justify-center space-x-2">
            <Upload className="w-4 h-4" />
            <span>Restaurer la configuration</span>
          </button>
          
          <button className="w-full bg-yellow-600 text-white py-2 px-4 rounded-lg hover:bg-yellow-700 flex items-center justify-center space-x-2">
            <RefreshCw className="w-4 h-4" />
            <span>Redémarrer les services</span>
          </button>
          
          <button className="w-full bg-red-600 text-white py-2 px-4 rounded-lg hover:bg-red-700 flex items-center justify-center space-x-2">
            <Power className="w-4 h-4" />
            <span>Arrêter le système</span>
          </button>
        </div>
      </div>
    </div>
  </div>
);

export default SettingsTab;