import { NavLink } from 'react-router-dom';
import { Home, Camera, Map, Bell } from 'lucide-react';
import { useAlerts } from '../context/AlertContext.jsx';
import { useTranslation } from '../i18n/useTranslation.js';

const tabs = [
  { path: '/grower', key: 'nav.home', Icon: Home, end: true },
  { path: '/grower/check', key: 'nav.check', Icon: Camera },
  { path: '/grower/map', key: 'nav.map', Icon: Map },
  { path: '/grower/alerts', key: 'nav.alerts', Icon: Bell },
];

export default function BottomNav() {
  const { unreadCount } = useAlerts();
  const { t } = useTranslation();
  return <nav aria-label={t('aria.bottomNav')} className="fg-bottom-nav" style={{ position: 'fixed', bottom: 0, left: 0, right: 0, zIndex: 20, display: 'grid', gridTemplateColumns: `repeat(${tabs.length},1fr)`, background: 'var(--color-surface)', borderTop: '1px solid var(--color-border)', paddingBottom: 'env(safe-area-inset-bottom)' }}>
    {tabs.map(({ path, key, Icon, end }) => <NavLink key={path} to={path} end={end} style={({ isActive }) => ({ minHeight: 60, display: 'grid', placeContent: 'center', justifyItems: 'center', gap: 3, textDecoration: 'none', color: isActive ? 'var(--color-primary)' : 'var(--color-text-muted)', fontSize: 12, fontWeight: 600, position: 'relative' })}>
      <Icon size={21} aria-hidden="true" />{t(key)}
      {key === 'nav.alerts' && unreadCount > 0 && <span aria-label={t('aria.unreadBadge', { n: unreadCount })} style={{ position: 'absolute', top: 4, left: '58%', minWidth: 17, height: 17, borderRadius: 20, background: 'var(--color-accent)', color: '#fff', fontSize: 10, display: 'grid', placeItems: 'center' }}>{unreadCount}</span>}
    </NavLink>)}
  </nav>;
}
