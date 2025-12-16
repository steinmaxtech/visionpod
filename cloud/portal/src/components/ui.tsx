'use client';

import { forwardRef, useState } from 'react';
import { X, AlertCircle, CheckCircle2, Loader2 } from 'lucide-react';
import { cn } from '@/lib/utils';

// =============================================================================
// STATUS BADGE
// =============================================================================

interface StatusBadgeProps {
  status: 'granted' | 'denied' | 'unknown' | 'online' | 'offline' | 'allow' | 'deny' | 'visitor' | 'vendor';
  className?: string;
}

const statusStyles: Record<string, string> = {
  granted: 'badge-granted',
  denied: 'badge-denied',
  unknown: 'badge-unknown',
  online: 'badge-online',
  offline: 'badge-offline',
  allow: 'badge-granted',
  deny: 'badge-denied',
  visitor: 'bg-blue-500/20 text-blue-400',
  vendor: 'bg-purple-500/20 text-purple-400',
};

export function StatusBadge({ status, className }: StatusBadgeProps) {
  return (
    <span className={cn('badge', statusStyles[status] || 'badge-unknown', className)}>
      {status.charAt(0).toUpperCase() + status.slice(1)}
    </span>
  );
}

// =============================================================================
// DEVICE STATUS INDICATOR
// =============================================================================

interface DeviceStatusProps {
  status: 'online' | 'offline' | 'error';
  lastSeen?: string | null;
}

export function DeviceStatus({ status, lastSeen }: DeviceStatusProps) {
  return (
    <div className="flex items-center gap-2">
      <span
        className={cn(
          'w-2 h-2 rounded-full',
          status === 'online' && 'bg-status-online animate-pulse-slow',
          status === 'offline' && 'bg-status-offline',
          status === 'error' && 'bg-status-denied'
        )}
      />
      <span className="text-sm text-text-secondary capitalize">{status}</span>
    </div>
  );
}

// =============================================================================
// MODAL
// =============================================================================

interface ModalProps {
  isOpen: boolean;
  onClose: () => void;
  title: string;
  children: React.ReactNode;
  size?: 'sm' | 'md' | 'lg';
}

export function Modal({ isOpen, onClose, title, children, size = 'md' }: ModalProps) {
  if (!isOpen) return null;

  const sizeClasses = {
    sm: 'max-w-md',
    md: 'max-w-lg',
    lg: 'max-w-2xl',
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center">
      {/* Backdrop */}
      <div 
        className="absolute inset-0 bg-black/60 backdrop-blur-sm animate-fade-in"
        onClick={onClose}
      />
      
      {/* Modal */}
      <div className={cn(
        'relative w-full mx-4 bg-surface border border-border rounded-lg shadow-2xl animate-slide-up',
        sizeClasses[size]
      )}>
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-border">
          <h2 className="text-lg font-semibold text-text-primary">{title}</h2>
          <button
            onClick={onClose}
            className="p-1 text-text-muted hover:text-text-primary transition-colors"
          >
            <X className="w-5 h-5" />
          </button>
        </div>
        
        {/* Content */}
        <div className="p-6">
          {children}
        </div>
      </div>
    </div>
  );
}

// =============================================================================
// EMPTY STATE
// =============================================================================

interface EmptyStateProps {
  icon?: React.ComponentType<{ className?: string }>;
  title: string;
  description?: string;
  action?: React.ReactNode;
}

export function EmptyState({ icon: Icon, title, description, action }: EmptyStateProps) {
  return (
    <div className="flex flex-col items-center justify-center py-12 text-center">
      {Icon && (
        <div className="w-12 h-12 rounded-full bg-surface-raised flex items-center justify-center mb-4">
          <Icon className="w-6 h-6 text-text-muted" />
        </div>
      )}
      <h3 className="text-lg font-medium text-text-primary mb-1">{title}</h3>
      {description && (
        <p className="text-sm text-text-secondary max-w-sm mb-4">{description}</p>
      )}
      {action}
    </div>
  );
}

// =============================================================================
// LOADING SPINNER
// =============================================================================

export function LoadingSpinner({ className }: { className?: string }) {
  return <Loader2 className={cn('w-6 h-6 animate-spin text-accent', className)} />;
}

// =============================================================================
// STAT CARD
// =============================================================================

interface StatCardProps {
  label: string;
  value: string | number;
  change?: string;
  changeType?: 'positive' | 'negative' | 'neutral';
  icon?: React.ComponentType<{ className?: string }>;
}

export function StatCard({ label, value, change, changeType = 'neutral', icon: Icon }: StatCardProps) {
  const changeColors = {
    positive: 'text-status-granted',
    negative: 'text-status-denied',
    neutral: 'text-text-muted',
  };

  return (
    <div className="card p-6">
      <div className="flex items-start justify-between">
        <div>
          <p className="text-sm text-text-secondary mb-1">{label}</p>
          <p className="text-2xl font-semibold text-text-primary">{value}</p>
          {change && (
            <p className={cn('text-sm mt-1', changeColors[changeType])}>
              {change}
            </p>
          )}
        </div>
        {Icon && (
          <div className="w-10 h-10 rounded-lg bg-accent/10 flex items-center justify-center">
            <Icon className="w-5 h-5 text-accent" />
          </div>
        )}
      </div>
    </div>
  );
}

// =============================================================================
// TABLE
// =============================================================================

interface Column<T> {
  key: string;
  header: string;
  render?: (item: T) => React.ReactNode;
  className?: string;
}

interface TableProps<T> {
  columns: Column<T>[];
  data: T[];
  keyExtractor: (item: T) => string;
  onRowClick?: (item: T) => void;
  emptyMessage?: string;
  loading?: boolean;
}

export function Table<T>({
  columns,
  data,
  keyExtractor,
  onRowClick,
  emptyMessage = 'No data',
  loading,
}: TableProps<T>) {
  if (loading) {
    return (
      <div className="flex items-center justify-center py-12">
        <LoadingSpinner />
      </div>
    );
  }

  if (data.length === 0) {
    return (
      <div className="text-center py-12 text-text-muted">
        {emptyMessage}
      </div>
    );
  }

  return (
    <div className="overflow-x-auto">
      <table className="w-full">
        <thead>
          <tr className="border-b border-border">
            {columns.map((col) => (
              <th
                key={col.key}
                className={cn(
                  'px-4 py-3 text-left text-xs font-medium text-text-muted uppercase tracking-wider',
                  col.className
                )}
              >
                {col.header}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {data.map((item) => (
            <tr
              key={keyExtractor(item)}
              onClick={() => onRowClick?.(item)}
              className={cn(
                'border-b border-border/50 table-row-hover',
                onRowClick && 'cursor-pointer'
              )}
            >
              {columns.map((col) => (
                <td
                  key={col.key}
                  className={cn('px-4 py-3 text-sm', col.className)}
                >
                  {col.render
                    ? col.render(item)
                    : (item as Record<string, unknown>)[col.key]?.toString()}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

// =============================================================================
// FORM INPUT
// =============================================================================

interface InputProps extends React.InputHTMLAttributes<HTMLInputElement> {
  label?: string;
  error?: string;
}

export const Input = forwardRef<HTMLInputElement, InputProps>(
  ({ label, error, className, ...props }, ref) => {
    return (
      <div className="space-y-1">
        {label && (
          <label className="block text-sm font-medium text-text-secondary">
            {label}
          </label>
        )}
        <input
          ref={ref}
          className={cn('input', error && 'border-status-denied', className)}
          {...props}
        />
        {error && (
          <p className="text-sm text-status-denied flex items-center gap-1">
            <AlertCircle className="w-4 h-4" />
            {error}
          </p>
        )}
      </div>
    );
  }
);
Input.displayName = 'Input';

// =============================================================================
// SELECT
// =============================================================================

interface SelectProps extends React.SelectHTMLAttributes<HTMLSelectElement> {
  label?: string;
  options: { value: string; label: string }[];
}

export const Select = forwardRef<HTMLSelectElement, SelectProps>(
  ({ label, options, className, ...props }, ref) => {
    return (
      <div className="space-y-1">
        {label && (
          <label className="block text-sm font-medium text-text-secondary">
            {label}
          </label>
        )}
        <select
          ref={ref}
          className={cn('input', className)}
          {...props}
        >
          {options.map((opt) => (
            <option key={opt.value} value={opt.value}>
              {opt.label}
            </option>
          ))}
        </select>
      </div>
    );
  }
);
Select.displayName = 'Select';

// =============================================================================
// TOAST NOTIFICATION
// =============================================================================

interface ToastProps {
  message: string;
  type?: 'success' | 'error' | 'info';
  onClose: () => void;
}

export function Toast({ message, type = 'info', onClose }: ToastProps) {
  const icons = {
    success: CheckCircle2,
    error: AlertCircle,
    info: AlertCircle,
  };
  const colors = {
    success: 'border-status-granted/50 bg-status-granted/10',
    error: 'border-status-denied/50 bg-status-denied/10',
    info: 'border-border bg-surface-raised',
  };
  const Icon = icons[type];

  return (
    <div className={cn(
      'fixed bottom-4 right-4 flex items-center gap-3 px-4 py-3 rounded-lg border shadow-lg animate-slide-up',
      colors[type]
    )}>
      <Icon className={cn(
        'w-5 h-5',
        type === 'success' && 'text-status-granted',
        type === 'error' && 'text-status-denied',
        type === 'info' && 'text-text-muted'
      )} />
      <span className="text-sm text-text-primary">{message}</span>
      <button onClick={onClose} className="text-text-muted hover:text-text-primary">
        <X className="w-4 h-4" />
      </button>
    </div>
  );
}
