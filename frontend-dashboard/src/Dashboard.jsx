import React, { useState } from 'react';
import { Server, Bell, Settings, LogOut } from 'lucide-react';
import Navigation from './components/Navigation';
import Overview from './components/Overview';
import Containers from './components/Containers';
import CaddyManager from './components/CaddyManager';
import Monitoring from './components/Monitoring';
import Automation from './components/Automation';
import Webhooks from './components/Webhooks';
import SettingsTab from './components/SettingsTab';
import ContainerModal from './components/ContainerModal';
import { useSimulatedData } from './hooks/useSimulatedData';

const Dashboard = () => {
  const [activeTab, setActiveTab] = useState('overview');
  const [searchTerm, setSearchTerm] = useState('');
  const [selectedContainer, setSelectedContainer] = useState(null);
  const [showContainerModal, setShowContainerModal] = useState(false);
  
  const {
    containers,
    setContainers,
    systemMetrics,
    recentEvents,
    shutdownRules,
    webhooks,
    handleContainerAction
  } = useSimulatedData();

  const filteredContainers = containers.filter(container =>
    container.name.toLowerCase().includes(searchTerm.toLowerCase())
  );

  const renderActiveTab = () => {
    switch (activeTab) {
      case 'overview':
        return <Overview 
          containers={containers}
          systemMetrics={systemMetrics}
          recentEvents={recentEvents}
          onContainerAction={handleContainerAction}
        />;
      case 'containers':
        return <Containers 
          containers={filteredContainers}
          searchTerm={searchTerm}
          setSearchTerm={setSearchTerm}
          onContainerAction={handleContainerAction}
          onSelectContainer={(container) => {
            setSelectedContainer(container);
            setShowContainerModal(true);
          }}
        />;
      case 'caddy':
        return <CaddyManager />;
      case 'monitoring':
        return <Monitoring 
          systemMetrics={systemMetrics}
          recentEvents={recentEvents}
        />;
      case 'automation':
        return <Automation rules={shutdownRules} />;
      case 'webhooks':
        return <Webhooks webhooks={webhooks} />;
      case 'settings':
        return <SettingsTab />;
      default:
        return null;
    }
  };

  return (
    <div className="min-h-screen bg-gray-100">
      {/* Header */}
      <header className="bg-white shadow-sm border-b">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex justify-between items-center h-16">
            <div className="flex items-center space-x-4">
              <div className="flex items-center space-x-2">
                <Server className="w-8 h-8 text-blue-600" />
                <h1 className="text-xl font-bold text-gray-900">SelfStart Dashboard</h1>
              </div>
            </div>
            
            <div className="flex items-center space-x-4">
              <button className="p-2 text-gray-400 hover:text-gray-600">
                <Bell className="w-5 h-5" />
              </button>
              <button className="p-2 text-gray-400 hover:text-gray-600">
                <Settings className="w-5 h-5" />
              </button>
              <button className="p-2 text-gray-400 hover:text-gray-600">
                <LogOut className="w-5 h-5" />
              </button>
            </div>
          </div>
        </div>
      </header>

      {/* Navigation */}
      <Navigation activeTab={activeTab} setActiveTab={setActiveTab} />

      {/* Contenu principal */}
      <main className="max-w-7xl mx-auto py-6 px-4 sm:px-6 lg:px-8">
        {renderActiveTab()}
      </main>

      {/* Modal */}
      {showContainerModal && (
        <ContainerModal
          container={selectedContainer}
          onClose={() => setShowContainerModal(false)}
          onAction={handleContainerAction}
        />
      )}
    </div>
  );
};

export default Dashboard;