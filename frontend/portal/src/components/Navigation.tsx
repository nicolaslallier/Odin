/**
 * Navigation sidebar component.
 */

import React from 'react';
import { NavLink } from 'react-router-dom';
import { useMicroFrontends } from '../context/MicroFrontendContext';

/**
 * Navigation sidebar with links to all micro-frontends.
 */
export const Navigation: React.FC = () => {
  const { manifests, loading } = useMicroFrontends();

  if (loading) {
    return (
      <nav className="navigation">
        <div className="nav-loading">Loading services...</div>
      </nav>
    );
  }

  return (
    <nav className="navigation">
      <ul className="nav-list">
        <li>
          <NavLink to="/" className="nav-link">
            Home
          </NavLink>
        </li>
        {Object.values(manifests).map(manifest =>
          manifest.routes?.map(route => (
            <li key={route.path}>
              <NavLink to={route.path} className="nav-link">
                {route.icon && <span className={`icon icon-${route.icon}`} />}
                {route.title}
              </NavLink>
            </li>
          ))
        )}
      </ul>
    </nav>
  );
};

