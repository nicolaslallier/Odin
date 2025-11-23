/**
 * 404 Not Found page.
 */

import React from 'react';
import { Link } from 'react-router-dom';

/**
 * 404 error page.
 */
export const NotFoundPage: React.FC = () => {
  return (
    <div className="not-found-page">
      <h1>404 - Page Not Found</h1>
      <p>The page you are looking for does not exist.</p>
      <Link to="/">Return to Home</Link>
    </div>
  );
};

