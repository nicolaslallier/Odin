/**
 * Main Portal Application Component.
 */

import React from 'react';
import { Routes, Route } from 'react-router-dom';
import { AuthProvider } from './context/AuthContext';
import { MicroFrontendProvider } from './context/MicroFrontendContext';
import { Layout } from './components/Layout';
import { HomePage } from './pages/HomePage';
import { LoginPage } from './pages/LoginPage';
import { NotFoundPage } from './pages/NotFoundPage';
import { ProtectedRoute } from './components/ProtectedRoute';
import { MicroFrontendRoutes } from './components/MicroFrontendRoutes';
import { ErrorBoundary } from '@odin/shared';

/**
 * Root application component with routing and context providers.
 */
export const App: React.FC = () => {
  return (
    <ErrorBoundary>
      <AuthProvider>
        <MicroFrontendProvider>
          <Routes>
            <Route path="/login" element={<LoginPage />} />
            <Route
              path="/*"
              element={
                <ProtectedRoute>
                  <Layout>
                    <Routes>
                      <Route path="/" element={<HomePage />} />
                      <Route path="/*" element={<MicroFrontendRoutes />} />
                      <Route path="*" element={<NotFoundPage />} />
                    </Routes>
                  </Layout>
                </ProtectedRoute>
              }
            />
          </Routes>
        </MicroFrontendProvider>
      </AuthProvider>
    </ErrorBoundary>
  );
};

