import React, { useState, useEffect, useCallback } from 'react';
import axios from 'axios';
import { 
  Play, 
  AlertCircle, 
  CheckCircle, 
  Loader, 
  RefreshCw, 
  Server,
  Clock,
  Zap,
  Activity
} from 'lucide-react';

// Configuration
const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';
const POLLING_INTERVAL = parseInt(import.meta.env.VITE_POLLING_INTERVAL) || 2000;

function App() {
  const [containerName, setContainerName] = useState('');
  const [status, setStatus] = useState('loading');
  const [message, setMessage] = useState('Initialisation...');
  const [progress, setProgress] = useState(0);
  const [error, setError] = useState(null);
  const [startTime, setStartTime] = useState(Date.now());
  const [elapsed, setElapsed] = useState(0);
  const [logs, setLogs] = useState([]);

  // Extraire le nom du container depuis l'URL ou les headers
  useEffect(() => {
    const extractContainerName = () => {
      // Essayer d'abord les headers (envoyés par Caddy)
      const headerName = window.location.hostname.split('.')[0];
      
      // Si on est en localhost, utiliser un paramètre d'URL ou une valeur par défaut
      if (headerName === 'localhost' || headerName === '127') {
        const urlParams = new URLSearchParams(window.location.search);
        return urlParams.get('container') || 'sonarr';
      }
      
      return headerName;
    };

    const name = extractContainerName();
    setContainerName(name);
    addLog(`Détection du container: ${name}`);
  }, []);

  // Ajouter un log avec timestamp
  const addLog = useCallback((message) => {
    setLogs(prev => [
      ...prev.slice(-9), // Garder seulement les 10 derniers logs
      {
        timestamp: new Date().toLocaleTimeString(),
        message
      }
    ]);
  }, []);

  // Fonction pour vérifier le statut du container
  const checkStatus = useCallback(async () => {
    if (!containerName) return;

    try {
      const response = await axios.get(`${API_BASE_URL}/api/status`, {
        params: { name: containerName },
        timeout: 5000
      });

      const data = response.data;
      
      if (data.status === 'running') {
        setStatus('ready');
        setMessage('Container prêt ! Redirection...');
        setProgress(100);
        addLog('Container opérationnel, redirection en cours...');
        
        // Attendre un peu puis recharger la page
        setTimeout(() => {
          window.location.reload();
        }, 2000);
      } else if (data.status === 'not_found') {
        setStatus('error');
        setError(`Container '${containerName}' introuvable`);
        addLog(`Erreur: Container '${containerName}' introuvable`);
      } else {
        // Container existe mais n'est pas en cours d'exécution
        if (status === 'loading') {
          startContainer();
        }
      }
    } catch (err) {
      console.error('Erreur lors de la vérification du statut:', err);
      if (err.code === 'ECONNABORTED') {
        addLog('Timeout lors de la vérification du statut');
      } else {
        addLog(`Erreur de connexion: ${err.message}`);
      }
    }
  }, [containerName, status]);

  // Fonction pour démarrer le container
  const startContainer = useCallback(async () => {
    if (!containerName || status === 'starting') return;

    try {
      setStatus('starting');
      setMessage('Démarrage du container en cours...');
      setProgress(10);
      addLog(`Démarrage du container ${containerName}...`);

      const response = await axios.post(`${API_BASE_URL}/api/start`, null, {
        params: { name: containerName },
        timeout: 10000
      });

      if (response.data.success) {
        setMessage('Container en cours de démarrage...');
        setProgress(30);
        addLog('Commande de démarrage envoyée avec succès');
      } else {
        throw new Error(response.data.message);
      }
    } catch (err) {
      console.error('Erreur lors du démarrage:', err);
      setStatus('error');
      setError(`Erreur lors du démarrage: ${err.response?.data?.detail || err.message}`);
      addLog(`Erreur de démarrage: ${err.response?.data?.detail || err.message}`);
    }
  }, [containerName, status]);

  // Polling pour vérifier le statut
  useEffect(() => {
    if (!containerName) return;

    // Vérification initiale
    checkStatus();

    // Polling régulier
    const interval = setInterval(() => {
      if (status !== 'ready' && status !== 'error') {
        checkStatus();
      }
    }, POLLING_INTERVAL);

    return () => clearInterval(interval);
  }, [containerName, checkStatus, status]);

  // Mise à jour du temps écoulé et de la barre de progression
  useEffect(() => {
    const interval = setInterval(() => {
      const newElapsed = Math.floor((Date.now() - startTime) / 1000);
      setElapsed(newElapsed);

      // Mise à jour de la progression basée sur le temps (simulation)
      if (status === 'starting' && progress < 90) {
        setProgress(prev => Math.min(prev + 1, 90));
      }
    }, 1000);

    return () => clearInterval(interval);
  }, [startTime, status, progress]);

  // Fonction pour formater le temps
  const formatTime = (seconds) => {
    const mins = Math.floor(seconds / 60);
    const secs = seconds % 60;
    return `${mins}:${secs.toString().padStart(2, '0')}`;
  };

  // Fonction pour réessayer en cas d'erreur
  const retry = () => {
    setStatus('loading');
    setError(null);
    setProgress(0);
    setStartTime(Date.now());
    setLogs([]);
    addLog('Nouvelle tentative de démarrage...');
  };

  return (
    <div className="min-h-screen gradient-bg flex items-center justify-center p-4">
      <div className="max-w-md w-full">
        {/* Carte principale */}
        <div className="glass-effect rounded-2xl p-8 shadow-2xl">
          {/* En-tête avec icône */}
          <div className="text-center mb-8">
            <div className="mx-auto w-16 h-16 mb-4 relative">
              {status === 'ready' ? (
                <CheckCircle className="w-16 h-16 text-success-400 glow-animation" />
              ) : status === 'error' ? (
                <AlertCircle className="w-16 h-16 text-error-400" />
              ) : (
                <div className="relative">
                  <Server className="w-16 h-16 text-primary-400 float-animation" />
                  <Loader className="w-6 h-6 text-primary-300 absolute -top-1 -right-1 animate-spin" />
                </div>
              )}
            </div>
            
            <h1 className="text-2xl font-bold text-white mb-2">
              {containerName ? containerName.charAt(0).toUpperCase() + containerName.slice(1) : 'SelfStart'}
            </h1>
            
            <p className="text-gray-300 text-sm">
              {status === 'ready' ? 'Prêt à utiliser' : 
               status === 'error' ? 'Erreur détectée' :
               'Démarrage en cours...'}
            </p>
          </div>

          {/* Barre de progression */}
          {status !== 'error' && (
            <div className="mb-6">
              <div className="flex justify-between items-center mb-2">
                <span className="text-sm text-gray-300">Progression</span>
                <span className="text-sm text-primary-300">{progress}%</span>
              </div>
              <div className="progress-bar">
                <div 
                  className="progress-fill" 
                  style={{ width: `${progress}%` }}
                />
              </div>
            </div>
          )}

          {/* Message de statut */}
          <div className="text-center mb-6">
            <p className="text-white font-medium mb-2">{message}</p>
            
            {/* Informations de temps */}
            <div className="flex items-center justify-center space-x-4 text-sm text-gray-300">
              <div className="flex items-center space-x-1">
                <Clock className="w-4 h-4" />
                <span>{formatTime(elapsed)}</span>
              </div>
              
              {status === 'starting' && (
                <div className="flex items-center space-x-1">
                  <Activity className="w-4 h-4 animate-pulse" />
                  <span>Démarrage...</span>
                </div>
              )}
            </div>
          </div>

          {/* Points de chargement animés */}
          {status === 'starting' && (
            <div className="flex justify-center mb-6">
              <div className="loading-dots">
                <div className="loading-dot"></div>
                <div className="loading-dot"></div>
                <div className="loading-dot"></div>
              </div>
            </div>
          )}

          {/* Gestion des erreurs */}
          {status === 'error' && (
            <div className="mb-6">
              <div className="bg-error-500/20 border border-error-500/50 rounded-lg p-4 mb-4">
                <p className="text-error-300 text-sm">{error}</p>
              </div>
              
              <button
                onClick={retry}
                className="w-full bg-primary-600 hover:bg-primary-700 text-white py-3 px-4 rounded-lg transition-colors duration-200 flex items-center justify-center space-x-2"
              >
                <RefreshCw className="w-4 h-4" />
                <span>Réessayer</span>
              </button>
            </div>
          )}

          {/* Logs en temps réel */}
          {logs.length > 0 && (
            <div className="mt-6">
              <h3 className="text-sm font-medium text-gray-300 mb-3 flex items-center space-x-2">
                <Zap className="w-4 h-4" />
                <span>Activité récente</span>
              </h3>
              
              <div className="bg-gray-800/50 rounded-lg p-3 max-h-32 overflow-y-auto">
                {logs.map((log, index) => (
                  <div key={index} className="text-xs text-gray-400 mb-1 last:mb-0">
                    <span className="text-gray-500">{log.timestamp}</span>
                    <span className="ml-2">{log.message}</span>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="text-center mt-6">
          <p className="text-gray-400 text-xs">
            SelfStart - Démarrage automatique de containers
          </p>
        </div>
      </div>
    </div>
  );
}

export default App;