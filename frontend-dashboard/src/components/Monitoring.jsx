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

export default Monitoring;
