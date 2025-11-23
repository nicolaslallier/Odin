/**
 * Health micro-frontend standalone entry point.
 * Used for development only.
 */

import React from 'react';
import { createRoot } from 'react-dom/client';
import { BrowserRouter } from 'react-router-dom';
import { HealthApp } from './HealthApp';

const container = document.getElementById('root');

if (!container) {
  throw new Error('Root element not found');
}

const root = createRoot(container);

root.render(
  <React.StrictMode>
    <BrowserRouter>
      <HealthApp />
    </BrowserRouter>
  </React.StrictMode>
);

