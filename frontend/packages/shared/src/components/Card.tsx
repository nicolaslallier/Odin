/**
 * Reusable Card component.
 */

import React from 'react';

export interface CardProps {
  title?: string;
  children: React.ReactNode;
  className?: string;
  footer?: React.ReactNode;
}

/**
 * Card component for displaying content in a container.
 */
export const Card: React.FC<CardProps> = ({ title, children, className = '', footer }) => {
  return (
    <div className={`card ${className}`.trim()}>
      {title && <div className="card-header">{title}</div>}
      <div className="card-body">{children}</div>
      {footer && <div className="card-footer">{footer}</div>}
    </div>
  );
};

