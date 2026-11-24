import { AlertTriangle, CheckCircle, Info, XCircle, X } from 'lucide-react';

const styles = {
  info: [Info, 'var(--color-primary)', 'var(--color-primary-tint)'],
  success: [CheckCircle, 'var(--risk-low)', 'var(--risk-low-tint)'],
  warning: [AlertTriangle, 'var(--risk-medium-text)', 'var(--risk-medium-tint)'],
  error: [XCircle, 'var(--risk-high)', 'var(--risk-high-tint)'],
};

export default function Alert({ variant = 'info', title, message, children, onDismiss }) {
  const [Icon, color, background] = styles[variant] || styles.info;
  return (
    <div role="alert" aria-live="polite" style={{ display: 'flex', alignItems: 'flex-start', gap: 12, padding: 16, borderRadius: 14, color: 'var(--color-text)', background, border: `1px solid ${color}` }}>
      <Icon aria-hidden="true" color={color} size={20} />
      <div style={{ flex: 1 }}>
        {title && <strong style={{ display: 'block', marginBottom: 4 }}>{title}</strong>}
        {message && <div>{message}</div>}
        {children}
      </div>
      {onDismiss && <button type="button" aria-label="Dismiss" onClick={onDismiss} style={{ border: 0, background: 'transparent', color, cursor: 'pointer' }}><X size={18} /></button>}
    </div>
  );
}
