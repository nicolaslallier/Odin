/**
 * Home page / dashboard.
 */

import React from 'react';
import { Card } from '@odin/shared';
import { useMicroFrontends } from '../context/MicroFrontendContext';

/**
 * Home page showing available services.
 */
export const HomePage: React.FC = () => {
  const { manifests } = useMicroFrontends();

  return (
    <div className="home-page">
      <h1>Welcome to Odin Portal</h1>
      <p>Manage your data platform services from one unified interface.</p>

      <div className="services-grid">
        {Object.values(manifests).map(manifest => (
          <Card key={manifest.name} title={manifest.name}>
            <p>Version: {manifest.version}</p>
            {manifest.routes && (
              <ul>
                {manifest.routes.map(route => (
                  <li key={route.path}>
                    <a href={route.path}>{route.title}</a>
                  </li>
                ))}
              </ul>
            )}
          </Card>
        ))}
      </div>
    </div>
  );
};

