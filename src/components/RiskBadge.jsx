import { CircleHelp, ShieldCheck, ShieldAlert, ShieldX } from 'lucide-react';
import { useTranslation } from '../i18n/useTranslation.js';

const riskStyles = {
  Low: ['var(--risk-low)', 'var(--risk-low-tint)', ShieldCheck, 'common.riskLevel.low'],
  Medium: ['var(--risk-medium)', 'var(--risk-medium-tint)', ShieldAlert, 'common.riskLevel.medium'],
  High: ['var(--risk-high)', 'var(--risk-high-tint)', ShieldX, 'common.riskLevel.high'],
  Unknown: ['var(--color-text-muted)', 'var(--color-bg)', CircleHelp, 'common.riskLevel.unknown'],
};

/** Risk is always communicated with icon, colour, and visible text. */
export default function RiskBadge({ level = 'Low' }) {
  const { t } = useTranslation();
  const [riskColor, background, Icon, key] = riskStyles[level] || riskStyles.Low;
  const color = level === 'Medium' ? 'var(--risk-medium-text)' : riskColor;
  return (
    <span
      aria-label={t('common.riskLevel.ariaLabel', { level: t(key) })}
      style={{ display: 'inline-flex', alignItems: 'center', gap: 6, color, background, borderRadius: 999, padding: '5px 10px', fontWeight: 700, fontSize: 13 }}
    >
      <Icon aria-hidden="true" size={16} />
      {t(key)}
    </span>
  );
}
