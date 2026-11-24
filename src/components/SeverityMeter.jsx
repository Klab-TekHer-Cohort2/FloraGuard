import { useTranslation } from '../i18n/useTranslation.js';

export default function SeverityMeter({ value = 0, label, ariaLabel, compact = false }) {
  const { t } = useTranslation();
  const safeValue = Math.min(100, Math.max(0, Number(value) || 0));
  const color = safeValue < 40 ? 'var(--risk-low)' : safeValue <= 70 ? 'var(--risk-medium)' : 'var(--risk-high)';
  return (
    <div style={{ minWidth: compact ? 72 : 140 }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', gap: 8, fontSize: 12, marginBottom: 5 }}>
        <span>{label || t('common.severity')}</span><span>{safeValue}%</span>
      </div>
      <div
        role="progressbar"
        aria-label={ariaLabel || t('aria.severityMeter', { value: safeValue })}
        aria-valuemin={0}
        aria-valuemax={100}
        aria-valuenow={safeValue}
        style={{ height: compact ? 6 : 9, background: 'var(--color-border)', borderRadius: 99, overflow: 'hidden' }}
      >
        <div style={{ width: `${safeValue}%`, height: '100%', background: color, borderRadius: 99 }} />
      </div>
    </div>
  );
}
