/**
 * Main layout component with navigation.
 */

import React from 'react';
import { Navigation } from './Navigation';
import { Header } from './Header';

interface LayoutProps {
  children: React.ReactNode;
}

/**
 * Layout component providing consistent structure across the portal.
 */
export const Layout: React.FC<LayoutProps> = ({ children }) => {
  return (
    <div className="layout">
      <Header />
      <div className="layout-content">
        <Navigation />
        <main className="main-content">{children}</main>
      </div>
    </div>
  );
};

