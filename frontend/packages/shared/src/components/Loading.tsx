/**
 * Loading spinner component.
 */

import React from 'react';

export interface LoadingProps {
  message?: string;
  size?: 'small' | 'medium' | 'large';
}

/**
 * Loading spinner with optional message.
 */
export const Loading: React.FC<LoadingProps> = ({ message, size = 'medium' }) => {
  return (
    <div className={`loading loading-${size}`}>
      <div className="spinner" />
      {message && <p className="loading-message">{message}</p>}
    </div>
  );
};

