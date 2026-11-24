import { CheckCircle, AlertTriangle, Info, XCircle, X } from 'lucide-react';

const types = {
  success: [CheckCircle, 'var(--risk-low)'],
  error: [XCircle, 'var(--risk-high)'],
  warning: [AlertTriangle, 'var(--risk-medium)'],
  info: [Info, 'var(--color-primary)'],
};

export default function Toast({ message, variant = 'info', onDismiss }) {
  const [Icon, color] = types[variant] || types.info;
  return (
    <div role="status" aria-live="assertive" className="animate-slide-up" style={{ display: 'flex', alignItems: 'center', gap: 10, minWidth: 260, maxWidth: 'min(92vw, 480px)', padding: '12px 16px', borderRadius: 14, color: 'var(--color-text)', background: 'var(--color-surface)', border: '1px solid var(--color-border)', boxShadow: 'var(--shadow-card-hover)' }}>
      <Icon color={color} size={20} aria-hidden="true" /><span style={{ flex: 1 }}>{message}</span>
      <button type="button" aria-label="Dismiss" onClick={onDismiss} style={{ border: 0, background: 'transparent', cursor: 'pointer', color: 'inherit' }}><X size={16} /></button>
    </div>
  );
}
