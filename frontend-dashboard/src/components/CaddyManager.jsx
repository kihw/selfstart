import React, { useState, useEffect } from 'react';
import { 
  Plus, 
  Edit3, 
  Trash2, 
  Power, 
  PowerOff, 
  TestTube, 
  Download, 
  Upload, 
  RefreshCw,
  Globe,
  Server,
  Shield,
  Settings,
  CheckCircle,
  XCircle,
  AlertTriangle,
  Eye,
  Save
} from 'lucide-react';
import axios from 'axios';

const CaddyManager = () => {
  const [routes, setRoutes] = useState([]);
  const [globalConfig, setGlobalConfig] = useState({});
  const [status, setStatus] = useState({});
  const [loading, setLoading] = useState(true);
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [showEditModal, setShowEditModal] = useState(false);
  const [showConfigModal, setShowConfigModal] = useState(false);
  const [selectedRoute, setSelectedRoute] = useState(null);
  const [testResults, setTestResults] = useState({});

  const API_BASE = import.meta.env.VITE_API_URL || 'http://localhost:8000';

  useEffect(() => {
    loadData();
    const interval = setInterval(loadData, 30000); // Refresh toutes les 30s
    return () => clearInterval(interval);
  }, []);

  const loadData = async () => {
    try {
      const [routesRes, statusRes, configRes] = await Promise.all([
        axios.get(`${API_BASE}/api/caddy/routes`),
        axios.get(`${API_BASE}/api/caddy/status`),
        axios.get(`${API_BASE}/api/caddy/global-config`)
      ]);

      setRoutes(routesRes.data.routes || []);
      setStatus(statusRes.data);
      setGlobalConfig(configRes.data);
    } catch (error) {
      console.error('Erreur chargement données Caddy:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleCreateRoute = async (routeData) => {
    try {
      await axios.post(`${API_BASE}/api/caddy/routes`, routeData);
      setShowCreateModal(false);
      loadData();
    } catch (error) {
      console.error('Erreur création route:', error);
    }
  };

  const handleUpdateRoute = async (routeId, routeData) => {
    try {
      await axios.put(`${API_BASE}/api/caddy/routes/${routeId}`, routeData);
      setShowEditModal(false);
      setSelectedRoute(null);
      loadData();
    } catch (error) {
      console.error('Erreur mise à jour route:', error);
    }
  };

  const handleDeleteRoute = async (routeId) => {
    if (!confirm('Êtes-vous sûr de vouloir supprimer cette route ?')) return;
    
    try {
      await axios.delete(`${API_BASE}/api/caddy/routes/${routeId}`);
      loadData();
    } catch (error) {
      console.error('Erreur suppression route:', error);
    }
  };

  const handleToggleRoute = async (routeId) => {
    try {
      await axios.post(`${API_BASE}/api/caddy/routes/${routeId}/toggle`);
      loadData();
    } catch (error) {
      console.error('Erreur toggle route:', error);
    }
  };

  const handleTestRoute = async (routeId) => {
    try {
      const response = await axios.post(`${API_BASE}/api/caddy/routes/${routeId}/test`);
      setTestResults(prev => ({ ...prev, [routeId]: response.data }));
    } catch (error) {
      console.error('Erreur test route:', error);
    }
  };

  const handleBackup = async () => {
    try {
      const response = await axios.post(`${API_BASE}/api/caddy/backup`);
      alert(`Configuration sauvegardée: ${response.data.backup_path}`);
    } catch (error) {
      console.error('Erreur sauvegarde:', error);
    }
  };

  const handleReload = async () => {
    try {
      await axios.post(`${API_BASE}/api/caddy/reload`);
      alert('Configuration rechargée avec succès');
      loadData();
    } catch (error) {
      console.error('Erreur rechargement:', error);
    }
  };

  const handleUpdateGlobalConfig = async (config) => {
    try {
      await axios.put(`${API_BASE}/api/caddy/global-config`, config);
      setShowConfigModal(false);
      loadData();
    } catch (error) {
      console.error('Erreur mise à jour config globale:', error);
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600"></div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-bold text-gray-900">Configuration Caddy</h2>
          <p className="text-gray-600">Gestion du reverse proxy et load balancer</p>
        </div>
        
        <div className="flex items-center space-x-3">
          <button
            onClick={() => setShowConfigModal(true)}
            className="bg-gray-600 text-white px-4 py-2 rounded-lg hover:bg-gray-700 flex items-center space-x-2"
          >
            <Settings className="w-4 h-4" />
            <span>Config Globale</span>
          </button>
          
          <button
            onClick={handleBackup}
            className="bg-yellow-600 text-white px-4 py-2 rounded-lg hover:bg-yellow-700 flex items-center space-x-2"
          >
            <Download className="w-4 h-4" />
            <span>Sauvegarder</span>
          </button>
          
          <button
            onClick={handleReload}
            className="bg-green-600 text-white px-4 py-2 rounded-lg hover:bg-green-700 flex items-center space-x-2"
          >
            <RefreshCw className="w-4 h-4" />
            <span>Recharger</span>
          </button>
          
          <button
            onClick={() => setShowCreateModal(true)}
            className="bg-blue-600 text-white px-4 py-2 rounded-lg hover:bg-blue-700 flex items-center space-x-2"
          >
            <Plus className="w-4 h-4" />
            <span>Nouvelle Route</span>
          </button>
        </div>
      </div>

      {/* Status Cards */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-6">
        <div className="bg-white rounded-lg shadow-md p-6">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm text-gray-600">Statut Caddy</p>
              <p className="text-2xl font-bold text-gray-900">
                {status.status === 'running' ? 'Actif' : 'Inactif'}
              </p>
            </div>
            <div className={`p-3 rounded-lg ${
              status.status === 'running' ? 'bg-green-100' : 'bg-red-100'
            }`}>
              {status.status === 'running' ? 
                <CheckCircle className="w-6 h-6 text-green-600" /> :
                <XCircle className="w-6 h-6 text-red-600" />
              }
            </div>
          </div>
        </div>

        <div className="bg-white rounded-lg shadow-md p-6">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm text-gray-600">Routes Totales</p>
              <p className="text-2xl font-bold text-gray-900">{routes.length}</p>
            </div>
            <div className="p-3 rounded-lg bg-blue-100">
              <Globe className="w-6 h-6 text-blue-600" />
            </div>
          </div>
        </div>

        <div className="bg-white rounded-lg shadow-md p-6">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm text-gray-600">Routes Actives</p>
              <p className="text-2xl font-bold text-gray-900">
                {routes.filter(r => r.enabled).length}
              </p>
            </div>
            <div className="p-3 rounded-lg bg-green-100">
              <Power className="w-6 h-6 text-green-600" />
            </div>
          </div>
        </div>

        <div className="bg-white rounded-lg shadow-md p-6">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm text-gray-600">Upstreams</p>
              <p className="text-2xl font-bold text-gray-900">
                {routes.reduce((acc, route) => acc + route.upstreams_count, 0)}
              </p>
            </div>
            <div className="p-3 rounded-lg bg-purple-100">
              <Server className="w-6 h-6 text-purple-600" />
            </div>
          </div>
        </div>
      </div>

      {/* Routes Table */}
      <div className="bg-white rounded-lg shadow-md overflow-hidden">
        <div className="px-6 py-4 border-b border-gray-200">
          <h3 className="text-lg font-semibold text-gray-900">Routes Configurées</h3>
        </div>
        
        <div className="overflow-x-auto">
          <table className="min-w-full divide-y divide-gray-200">
            <thead className="bg-gray-50">
              <tr>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Domaine
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Upstreams
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Règle LB
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Statut
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  TLS
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Actions
                </th>
              </tr>
            </thead>
            <tbody className="bg-white divide-y divide-gray-200">
              {routes.map((route) => (
                <tr key={route.id} className="hover:bg-gray-50">
                  <td className="px-6 py-4 whitespace-nowrap">
                    <div className="flex items-center">
                      <Globe className="w-4 h-4 text-gray-400 mr-2" />
                      <div>
                        <div className="text-sm font-medium text-gray-900">
                          {route.domain}
                        </div>
                        <div className="text-sm text-gray-500">
                          ID: {route.id.substring(0, 8)}...
                        </div>
                      </div>
                    </div>
                  </td>
                  
                  <td className="px-6 py-4 whitespace-nowrap">
                    <div className="text-sm text-gray-900">
                      {route.upstreams_count} upstream{route.upstreams_count > 1 ? 's' : ''}
                    </div>
                  </td>
                  
                  <td className="px-6 py-4 whitespace-nowrap">
                    <span className="px-2 py-1 text-xs font-medium bg-blue-100 text-blue-800 rounded-full">
                      {route.rule}
                    </span>
                  </td>
                  
                  <td className="px-6 py-4 whitespace-nowrap">
                    <span className={`px-2 py-1 text-xs font-medium rounded-full ${
                      route.enabled 
                        ? 'bg-green-100 text-green-800' 
                        : 'bg-gray-100 text-gray-800'
                    }`}>
                      {route.enabled ? 'Actif' : 'Inactif'}
                    </span>
                  </td>
                  
                  <td className="px-6 py-4 whitespace-nowrap">
                    {route.tls_enabled ? (
                      <Shield className="w-4 h-4 text-green-600" />
                    ) : (
                      <Shield className="w-4 h-4 text-gray-400" />
                    )}
                  </td>
                  
                  <td className="px-6 py-4 whitespace-nowrap text-sm font-medium">
                    <div className="flex items-center space-x-2">
                      <button
                        onClick={() => handleToggleRoute(route.id)}
                        className={`p-2 rounded hover:bg-gray-100 ${
                          route.enabled ? 'text-red-600' : 'text-green-600'
                        }`}
                        title={route.enabled ? 'Désactiver' : 'Activer'}
                      >
                        {route.enabled ? 
                          <PowerOff className="w-4 h-4" /> : 
                          <Power className="w-4 h-4" />
                        }
                      </button>
                      
                      <button
                        onClick={() => handleTestRoute(route.id)}
                        className="p-2 rounded hover:bg-gray-100 text-blue-600"
                        title="Tester"
                      >
                        <TestTube className="w-4 h-4" />
                      </button>
                      
                      <button
                        onClick={() => {
                          setSelectedRoute(route);
                          setShowEditModal(true);
                        }}
                        className="p-2 rounded hover:bg-gray-100 text-gray-600"
                        title="Modifier"
                      >
                        <Edit3 className="w-4 h-4" />
                      </button>
                      
                      <button
                        onClick={() => handleDeleteRoute(route.id)}
                        className="p-2 rounded hover:bg-gray-100 text-red-600"
                        title="Supprimer"
                      >
                        <Trash2 className="w-4 h-4" />
                      </button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {/* Test Results */}
      {Object.keys(testResults).length > 0 && (
        <div className="bg-white rounded-lg shadow-md p-6">
          <h3 className="text-lg font-semibold text-gray-900 mb-4">Résultats des Tests</h3>
          {Object.entries(testResults).map(([routeId, result]) => (
            <div key={routeId} className="mb-4 p-4 border rounded-lg">
              <div className="flex items-center justify-between mb-2">
                <h4 className="font-medium">{result.domain}</h4>
                <span className={`px-2 py-1 text-xs rounded-full ${
                  result.success ? 'bg-green-100 text-green-800' : 'bg-red-100 text-red-800'
                }`}>
                  {result.healthy_upstreams}/{result.total_upstreams} OK
                </span>
              </div>
              <div className="space-y-2">
                {result.results.map((upstream, index) => (
                  <div key={index} className="flex items-center justify-between text-sm">
                    <span>{upstream.upstream}</span>
                    <div className="flex items-center space-x-2">
                      <span className={upstream.success ? 'text-green-600' : 'text-red-600'}>
                        {upstream.status || 'Error'}
                      </span>
                      {upstream.success ? 
                        <CheckCircle className="w-4 h-4 text-green-600" /> :
                        <XCircle className="w-4 h-4 text-red-600" />
                      }
                    </div>
                  </div>
                ))}
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Modals */}
      {showCreateModal && (
        <RouteModal
          onClose={() => setShowCreateModal(false)}
          onSave={handleCreateRoute}
          title="Créer une Nouvelle Route"
        />
      )}

      {showEditModal && selectedRoute && (
        <RouteModal
          route={selectedRoute}
          onClose={() => {
            setShowEditModal(false);
            setSelectedRoute(null);
          }}
          onSave={(data) => handleUpdateRoute(selectedRoute.id, data)}
          title="Modifier la Route"
        />
      )}

      {showConfigModal && (
        <GlobalConfigModal
          config={globalConfig}
          onClose={() => setShowConfigModal(false)}
          onSave={handleUpdateGlobalConfig}
        />
      )}
    </div>
  );
};

// Modal pour créer/modifier une route
const RouteModal = ({ route, onClose, onSave, title }) => {
  const [formData, setFormData] = useState({
    domain: route?.domain || '',
    rule: route?.rule || 'round_robin',
    tls_enabled: route?.tls_enabled ?? true,
    enabled: route?.enabled ?? true,
    matchers: route?.matchers || [{ type: 'host', value: '', name: '' }],
    upstreams: route?.upstreams || [{ 
      address: '', 
      weight: 1, 
      health_check_uri: '/health',
      health_check_interval: '30s',
      health_check_timeout: '5s'
    }]
  });

  const handleSubmit = (e) => {
    e.preventDefault();
    onSave(formData);
  };

  const addUpstream = () => {
    setFormData(prev => ({
      ...prev,
      upstreams: [...prev.upstreams, { 
        address: '', 
        weight: 1, 
        health_check_uri: '/health',
        health_check_interval: '30s',
        health_check_timeout: '5s'
      }]
    }));
  };

  const removeUpstream = (index) => {
    setFormData(prev => ({
      ...prev,
      upstreams: prev.upstreams.filter((_, i) => i !== index)
    }));
  };

  const updateUpstream = (index, field, value) => {
    setFormData(prev => ({
      ...prev,
      upstreams: prev.upstreams.map((upstream, i) => 
        i === index ? { ...upstream, [field]: value } : upstream
      )
    }));
  };

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
      <div className="bg-white rounded-lg shadow-xl max-w-4xl w-full m-4 max-h-screen overflow-y-auto">
        <div className="flex items-center justify-between p-6 border-b">
          <h2 className="text-xl font-semibold text-gray-900">{title}</h2>
          <button onClick={onClose} className="text-gray-400 hover:text-gray-600">
            <XCircle className="w-6 h-6" />
          </button>
        </div>

        <form onSubmit={handleSubmit} className="p-6 space-y-6">
          {/* Configuration de base */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Domaine
              </label>
              <input
                type="text"
                value={formData.domain}
                onChange={(e) => setFormData(prev => ({ ...prev, domain: e.target.value }))}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                placeholder="exemple.com"
                required
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Règle de Load Balancing
              </label>
              <select
                value={formData.rule}
                onChange={(e) => setFormData(prev => ({ ...prev, rule: e.target.value }))}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
              >
                <option value="round_robin">Round Robin</option>
                <option value="least_connections">Least Connections</option>
                <option value="weighted">Weighted</option>
                <option value="ip_hash">IP Hash</option>
                <option value="health_based">Health Based</option>
              </select>
            </div>
          </div>

          {/* Options */}
          <div className="flex items-center space-x-6">
            <label className="flex items-center">
              <input
                type="checkbox"
                checked={formData.tls_enabled}
                onChange={(e) => setFormData(prev => ({ ...prev, tls_enabled: e.target.checked }))}
                className="rounded border-gray-300 text-blue-600 focus:ring-blue-500"
              />
              <span className="ml-2 text-sm text-gray-700">TLS/HTTPS activé</span>
            </label>

            <label className="flex items-center">
              <input
                type="checkbox"
                checked={formData.enabled}
                onChange={(e) => setFormData(prev => ({ ...prev, enabled: e.target.checked }))}
                className="rounded border-gray-300 text-blue-600 focus:ring-blue-500"
              />
              <span className="ml-2 text-sm text-gray-700">Route activée</span>
            </label>
          </div>

          {/* Upstreams */}
          <div>
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-lg font-medium text-gray-900">Upstreams</h3>
              <button
                type="button"
                onClick={addUpstream}
                className="bg-blue-600 text-white px-3 py-1 rounded text-sm hover:bg-blue-700"
              >
                Ajouter Upstream
              </button>
            </div>

            <div className="space-y-4">
              {formData.upstreams.map((upstream, index) => (
                <div key={index} className="border border-gray-200 rounded-lg p-4">
                  <div className="flex items-center justify-between mb-3">
                    <h4 className="font-medium text-gray-900">Upstream {index + 1}</h4>
                    {formData.upstreams.length > 1 && (
                      <button
                        type="button"
                        onClick={() => removeUpstream(index)}
                        className="text-red-600 hover:text-red-800"
                      >
                        <Trash2 className="w-4 h-4" />
                      </button>
                    )}
                  </div>

                  <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                    <div className="md:col-span-2">
                      <label className="block text-sm font-medium text-gray-700 mb-1">
                        Adresse
                      </label>
                      <input
                        type="text"
                        value={upstream.address}
                        onChange={(e) => updateUpstream(index, 'address', e.target.value)}
                        className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                        placeholder="localhost:8080"
                        required
                      />
                    </div>

                    <div>
                      <label className="block text-sm font-medium text-gray-700 mb-1">
                        Poids
                      </label>
                      <input
                        type="number"
                        value={upstream.weight}
                        onChange={(e) => updateUpstream(index, 'weight', parseInt(e.target.value))}
                        className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                        min="1"
                        max="100"
                      />
                    </div>

                    <div>
                      <label className="block text-sm font-medium text-gray-700 mb-1">
                        Health Check URI
                      </label>
                      <input
                        type="text"
                        value={upstream.health_check_uri}
                        onChange={(e) => updateUpstream(index, 'health_check_uri', e.target.value)}
                        className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                        placeholder="/health"
                      />
                    </div>

                    <div>
                      <label className="block text-sm font-medium text-gray-700 mb-1">
                        Intervalle
                      </label>
                      <input
                        type="text"
                        value={upstream.health_check_interval}
                        onChange={(e) => updateUpstream(index, 'health_check_interval', e.target.value)}
                        className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                        placeholder="30s"
                      />
                    </div>

                    <div>
                      <label className="block text-sm font-medium text-gray-700 mb-1">
                        Timeout
                      </label>
                      <input
                        type="text"
                        value={upstream.health_check_timeout}
                        onChange={(e) => updateUpstream(index, 'health_check_timeout', e.target.value)}
                        className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                        placeholder="5s"
                      />
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </div>

          {/* Actions */}
          <div className="flex items-center justify-end space-x-3 pt-6 border-t">
            <button
              type="button"
              onClick={onClose}
              className="px-4 py-2 text-gray-700 bg-gray-200 rounded-lg hover:bg-gray-300"
            >
              Annuler
            </button>
            <button
              type="submit"
              className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 flex items-center space-x-2"
            >
              <Save className="w-4 h-4" />
              <span>Sauvegarder</span>
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};

// Modal pour la configuration globale
const GlobalConfigModal = ({ config, onClose, onSave }) => {
  const [formData, setFormData] = useState({
    email: config.email || '',
    admin_port: config.admin_port || 2019,
    http_port: config.http_port || 80,
    https_port: config.https_port || 443,
    log_level: config.log_level || 'INFO'
  });

  const handleSubmit = (e) => {
    e.preventDefault();
    onSave(formData);
  };

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
      <div className="bg-white rounded-lg shadow-xl max-w-2xl w-full m-4">
        <div className="flex items-center justify-between p-6 border-b">
          <h2 className="text-xl font-semibold text-gray-900">Configuration Globale</h2>
          <button onClick={onClose} className="text-gray-400 hover:text-gray-600">
            <XCircle className="w-6 h-6" />
          </button>
        </div>

        <form onSubmit={handleSubmit} className="p-6 space-y-6">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            <div className="md:col-span-2">
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Email (Let's Encrypt)
              </label>
              <input
                type="email"
                value={formData.email}
                onChange={(e) => setFormData(prev => ({ ...prev, email: e.target.value }))}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                required
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Port Admin
              </label>
              <input
                type="number"
                value={formData.admin_port}
                onChange={(e) => setFormData(prev => ({ ...prev, admin_port: parseInt(e.target.value) }))}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                min="1"
                max="65535"
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Port HTTP
              </label>
              <input
                type="number"
                value={formData.http_port}
                onChange={(e) => setFormData(prev => ({ ...prev, http_port: parseInt(e.target.value) }))}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                min="1"
                max="65535"
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Port HTTPS
              </label>
              <input
                type="number"
                value={formData.https_port}
                onChange={(e) => setFormData(prev => ({ ...prev, https_port: parseInt(e.target.value) }))}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                min="1"
                max="65535"
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Niveau de Log
              </label>
              <select
                value={formData.log_level}
                onChange={(e) => setFormData(prev => ({ ...prev, log_level: e.target.value }))}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
              >
                <option value="DEBUG">DEBUG</option>
                <option value="INFO">INFO</option>
                <option value="WARNING">WARNING</option>
                <option value="ERROR">ERROR</option>
              </select>
            </div>
          </div>

          <div className="flex items-center justify-end space-x-3 pt-6 border-t">
            <button
              type="button"
              onClick={onClose}
              className="px-4 py-2 text-gray-700 bg-gray-200 rounded-lg hover:bg-gray-300"
            >
              Annuler
            </button>
            <button
              type="submit"
              className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 flex items-center space-x-2"
            >
              <Save className="w-4 h-4" />
              <span>Sauvegarder</span>
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};

export default CaddyManager;