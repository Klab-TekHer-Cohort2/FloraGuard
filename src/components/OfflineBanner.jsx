import { WifiOff } from 'lucide-react';
import { useOffline } from '../hooks/useOffline.js';
import { useTranslation } from '../i18n/useTranslation.js';

export default function OfflineBanner() {
  const { isOffline } = useOffline();
  const { t } = useTranslation();
  if (!isOffline) return null;
  return <div role="status" aria-live="assertive" style={{ position: 'sticky', top: 0, zIndex: 30, display: 'flex', justifyContent: 'center', gap: 8, padding: '8px 12px', color: '#4A3100', background: '#FFE7A3', fontWeight: 600 }}><WifiOff size={18} />{t('offline.banner')}</div>;
}
