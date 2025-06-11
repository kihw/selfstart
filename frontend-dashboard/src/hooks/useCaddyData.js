import { useState, useEffect, useCallback } from 'react';
import axios from 'axios';

export const useCaddyData = () => {
  const [routes, setRoutes] = useState([]);
  const [status, setStatus] = useState({});
  const [globalConfig, setGlobalConfig] = useState({});
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

  const fetchData = useCallback(async () => {
    try {
      setLoading(true);
      
      const [routesRes, statusRes, configRes] = await Promise.all([
        axios.get(`${API_BASE_URL}/api/caddy/routes`),
        axios.get(`${API_BASE_URL}/api/caddy/status`),
        axios.get(`${API_BASE_URL}/api/caddy/global-config`)
      ]);

      setRoutes(routesRes.data.routes || []);
      setStatus(statusRes.data);
      setGlobalConfig(configRes.data);
      setError(null);
    } catch (err) {
      console.error('Erreur chargement données Caddy:', err);
      setError('Erreur lors du chargement des données Caddy');
    } finally {
      setLoading(false);
    }
  }, [API_BASE_URL]);

  useEffect(() => {
    fetchData();
    
    // Polling toutes les 30 secondes
    const interval = setInterval(fetchData, 30000);
    return () => clearInterval(interval);
  }, [fetchData]);

  const createRoute = useCallback(async (routeData) => {
    try {
      const response = await axios.post(`${API_BASE_URL}/api/caddy/routes`, routeData);
      await fetchData();
      return { success: true, data: response.data };
    } catch (err) {
      console.error('Erreur création route:', err);
      return { 
        success: false, 
        error: err.response?.data?.detail || 'Erreur lors de la création de la route' 
      };
    }
  }, [API_BASE_URL, fetchData]);

  const updateRoute = useCallback(async (routeId, routeData) => {
    try {
      const response = await axios.put(`${API_BASE_URL}/api/caddy/routes/${routeId}`, routeData);
      await fetchData();
      return { success: true, data: response.data };
    } catch (err) {
      console.error('Erreur mise à jour route:', err);
      return { 
        success: false, 
        error: err.response?.data?.detail || 'Erreur lors de la mise à jour de la route' 
      };
    }
  }, [API_BASE_URL, fetchData]);

  const deleteRoute = useCallback(async (routeId) => {
    try {
      const response = await axios.delete(`${API_BASE_URL}/api/caddy/routes/${routeId}`);
      await fetchData();
      return { success: true, data: response.data };
    } catch (err) {
      console.error('Erreur suppression route:', err);
      return { 
        success: false, 
        error: err.response?.data?.detail || 'Erreur lors de la suppression de la route' 
      };
    }
  }, [API_BASE_URL, fetchData]);

  const toggleRoute = useCallback(async (routeId) => {
    try {
      const response = await axios.post(`${API_BASE_URL}/api/caddy/routes/${routeId}/toggle`);
      await fetchData();
      return { success: true, data: response.data };
    } catch (err) {
      console.error('Erreur toggle route:', err);
      return { 
        success: false, 
        error: err.response?.data?.detail || 'Erreur lors du changement de statut de la route' 
      };
    }
  }, [API_BASE_URL, fetchData]);

  const testRoute = useCallback(async (routeId) => {
    try {
      const response = await axios.post(`${API_BASE_URL}/api/caddy/routes/${routeId}/test`);
      return { success: true, data: response.data };
    } catch (err) {
      console.error('Erreur test route:', err);
      return { 
        success: false, 
        error: err.response?.data?.detail || 'Erreur lors du test de la route' 
      };
    }
  }, [API_BASE_URL]);

  const updateGlobalConfig = useCallback(async (configData) => {
    try {
      const response = await axios.put(`${API_BASE_URL}/api/caddy/global-config`, configData);
      await fetchData();
      return { success: true, data: response.data };
    } catch (err) {
      console.error('Erreur mise à jour config globale:', err);
      return { 
        success: false, 
        error: err.response?.data?.detail || 'Erreur lors de la mise à jour de la configuration' 
      };
    }
  }, [API_BASE_URL, fetchData]);

  const backupConfig = useCallback(async () => {
    try {
      const response = await axios.post(`${API_BASE_URL}/api/caddy/backup`);
      return { success: true, data: response.data };
    } catch (err) {
      console.error('Erreur sauvegarde config:', err);
      return { 
        success: false, 
        error: err.response?.data?.detail || 'Erreur lors de la sauvegarde de la configuration' 
      };
    }
  }, [API_BASE_URL]);

  const restoreConfig = useCallback(async (backupPath) => {
    try {
      const response = await axios.post(`${API_BASE_URL}/api/caddy/restore`, { backup_path: backupPath });
      await fetchData();
      return { success: true, data: response.data };
    } catch (err) {
      console.error('Erreur restauration config:', err);
      return { 
        success: false, 
        error: err.response?.data?.detail || 'Erreur lors de la restauration de la configuration' 
      };
    }
  }, [API_BASE_URL, fetchData]);

  const reloadConfig = useCallback(async () => {
    try {
      const response = await axios.post(`${API_BASE_URL}/api/caddy/reload`);
      await fetchData();
      return { success: true, data: response.data };
    } catch (err) {
      console.error('Erreur rechargement config:', err);
      return { 
        success: false, 
        error: err.response?.data?.detail || 'Erreur lors du rechargement de la configuration' 
      };
    }
  }, [API_BASE_URL, fetchData]);

  return {
    routes,
    status,
    globalConfig,
    loading,
    error,
    fetchData,
    createRoute,
    updateRoute,
    deleteRoute,
    toggleRoute,
    testRoute,
    updateGlobalConfig,
    backupConfig,
    restoreConfig,
    reloadConfig
  };
};