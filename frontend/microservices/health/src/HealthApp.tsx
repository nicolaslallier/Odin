/**
 * Health monitoring micro-frontend main component.
 */

import React from 'react';
import { Routes, Route } from 'react-router-dom';
import { ErrorBoundary } from '@odin/shared';
import { HealthDashboard } from './components/HealthDashboard';
import { HealthHistory } from './components/HealthHistory';
import { HealthDetails } from './components/HealthDetails';

/**
 * Main Health application component.
 * Exported for Module Federation.
 */
export const HealthApp: React.FC = () => {
  return (
    <ErrorBoundary>
      <div className="health-app">
        <Routes>
          <Route path="/" element={<HealthDashboard />} />
          <Route path="/history" element={<HealthHistory />} />
          <Route path="/details/:serviceName" element={<HealthDetails />} />
        </Routes>
      </div>
    </ErrorBoundary>
  );
};

