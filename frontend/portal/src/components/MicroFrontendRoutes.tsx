/**
 * Dynamic routes for micro-frontends.
 */

import React, { lazy, Suspense } from 'react';
import { Route, Routes } from 'react-router-dom';
import { Loading, ErrorBoundary } from '@odin/shared';
import { useMicroFrontends } from '../context/MicroFrontendContext';

/**
 * Dynamically load micro-frontend components.
 */
const loadMicroFrontend = (remoteName: string, moduleName: string) => {
  return lazy(async () => {
    try {
      // @ts-ignore - Dynamic import from Module Federation
      const module = await import(`${remoteName}/${moduleName}`);
      return module;
    } catch (error) {
      console.error(`Failed to load ${remoteName}/${moduleName}:`, error);
      // Return fallback component
      return {
        default: () => (
          <div className="error-message">
            <h2>Service Unavailable</h2>
            <p>The {remoteName} service is currently unavailable.</p>
          </div>
        ),
      };
    }
  });
};

/**
 * Routes that dynamically load micro-frontends.
 */
export const MicroFrontendRoutes: React.FC = () => {
  const { manifests } = useMicroFrontends();

  return (
    <Routes>
      {Object.entries(manifests).map(([name, manifest]) => {
        if (!manifest.routes) return null;
        
        return manifest.routes.map(route => {
          const Component = loadMicroFrontend(name, manifest.exposedModules[0].replace('./', ''));
          
          return (
            <Route
              key={route.path}
              path={`${route.path}/*`}
              element={
                <ErrorBoundary>
                  <Suspense fallback={<Loading message={`Loading ${route.title}...`} />}>
                    <Component />
                  </Suspense>
                </ErrorBoundary>
              }
            />
          );
        });
      })}
    </Routes>
  );
};

