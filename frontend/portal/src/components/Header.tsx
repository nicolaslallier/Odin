/**
 * Header component with user menu.
 */

import React from 'react';
import { useAuth } from '../context/AuthContext';

/**
 * Header component with branding and user controls.
 */
export const Header: React.FC = () => {
  const { user, logout } = useAuth();

  return (
    <header className="header">
      <div className="header-brand">
        <h1>Odin Portal</h1>
      </div>
      <div className="header-user">
        <span className="user-name">{user?.username || 'Guest'}</span>
        <button onClick={logout} className="btn btn-secondary btn-small">
          Logout
        </button>
      </div>
    </header>
  );
};

