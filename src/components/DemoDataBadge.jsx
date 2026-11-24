import { useState } from 'react';
import { X } from 'lucide-react';
import { useTranslation } from '../i18n/useTranslation.js';

export default function DemoDataBadge() {
  const [visible, setVisible] = useState(true);
  const { t } = useTranslation();
  if (!visible) return null;
  return <div className="fg-demo-badge" style={{ position: 'fixed', zIndex: 25, right: 12, bottom: 12, display: 'flex', alignItems: 'center', gap: 4, padding: '5px 8px', border: '1px solid var(--color-border)', borderRadius: 999, background: 'var(--color-surface)', color: 'var(--color-text-muted)', fontSize: 11, boxShadow: 'var(--shadow-card)' }}>
    {t('app.demoData')}<button type="button" aria-label={t('app.demoDataDismiss')} onClick={() => setVisible(false)} style={{ border: 0, background: 'transparent', color: 'inherit', padding: 2, cursor: 'pointer' }}><X size={13} /></button>
  </div>;
}
