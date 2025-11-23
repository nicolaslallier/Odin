/**
 * Micro-frontend context for managing available services.
 */

import React, { createContext, useContext, useState, useEffect } from 'react';
import { apiClient, MicroFrontendManifest } from '@odin/shared';

interface MicroFrontendContextValue {
  manifests: Record<string, MicroFrontendManifest>;
  loading: boolean;
  error: string | null;
  reloadManifests: () => Promise<void>;
}

const MicroFrontendContext = createContext<MicroFrontendContextValue | undefined>(undefined);

/**
 * Provider for micro-frontend discovery and management.
 */
export const MicroFrontendProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [manifests, setManifests] = useState<Record<string, MicroFrontendManifest>>({});
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const loadManifests = async () => {
    setLoading(true);
    setError(null);
    try {
      // Load service discovery endpoint
      const response = await apiClient.get<{ services: MicroFrontendManifest[] }>(
        '/api/portal/services'
      );
      
      const manifestMap = response.services.reduce((acc, manifest) => {
        acc[manifest.name] = manifest;
        return acc;
      }, {} as Record<string, MicroFrontendManifest>);
      
      setManifests(manifestMap);
    } catch (err: any) {
      console.error('Failed to load micro-frontend manifests:', err);
      setError(err.message || 'Failed to load services');
      // Set default manifests for development
      setManifests(getDefaultManifests());
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadManifests();
  }, []);

  const value: MicroFrontendContextValue = {
    manifests,
    loading,
    error,
    reloadManifests: loadManifests,
  };

  return <MicroFrontendContext.Provider value={value}>{children}</MicroFrontendContext.Provider>;
};

/**
 * Hook to access micro-frontend context.
 */
export const useMicroFrontends = (): MicroFrontendContextValue => {
  const context = useContext(MicroFrontendContext);
  if (!context) {
    throw new Error('useMicroFrontends must be used within MicroFrontendProvider');
  }
  return context;
};

/**
 * Default manifests for development/fallback.
 */
function getDefaultManifests(): Record<string, MicroFrontendManifest> {
  return {
    health: {
      name: 'health',
      version: '2.0.0',
      remoteEntry: '/mfe/health/remoteEntry.js',
      exposedModules: ['./HealthApp', './routes'],
      routes: [{ path: '/health', title: 'Health Monitoring', icon: 'health' }],
    },
    data: {
      name: 'data',
      version: '2.0.0',
      remoteEntry: '/mfe/data/remoteEntry.js',
      exposedModules: ['./DataApp', './routes'],
      routes: [{ path: '/data', title: 'Data Management', icon: 'database' }],
    },
  };
}

