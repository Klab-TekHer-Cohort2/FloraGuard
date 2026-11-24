import { NavLink, Outlet } from 'react-router-dom';
import { Bell, FileText, LayoutDashboard, Map, Settings } from 'lucide-react';
import Header from '../../components/Header.jsx';
import { Brand } from '../../components/Header.jsx';
import { useAlerts } from '../../context/AlertContext.jsx';
import { useTranslation } from '../../i18n/useTranslation.js';

const links = [
  ['/dashboard', 'nav.overview', LayoutDashboard, true],
  ['/dashboard/map', 'nav.map', Map],
  ['/dashboard/reports', 'nav.reports', FileText],
  ['/dashboard/alerts', 'nav.alerts', Bell],
  ['/dashboard/settings', 'nav.settings', Settings],
];

export default function DashboardLayout() {
  const { t } = useTranslation();
  const { unreadCount } = useAlerts();
  const renderLinks = (className) => <nav className={className} aria-label={t('aria.mainNav')}>
    {links.map(([href, key, Icon, end]) => <NavLink key={href} to={href} end={end} className={({ isActive }) => isActive ? 'active' : ''}>
      <Icon aria-hidden="true" size={19} /><span>{t(key)}</span>
      {key === 'nav.alerts' && unreadCount > 0 && <span style={{ marginLeft: 'auto', minWidth: 20, padding: '2px 6px', borderRadius: 99, textAlign: 'center', color: '#fff', background: 'var(--color-accent)', fontSize: 11 }}>{unreadCount}</span>}
    </NavLink>)}
  </nav>;
  return <div className="fg-dashboard-shell">
    <aside className="fg-sidebar"><Brand /><div className="fg-sidebar-links">{renderLinks('fg-sidebar-links')}</div><small className="text-muted" style={{ marginTop: 'auto', padding: 8 }}>{t('header.roleManagerShort')}</small></aside>
    <div className="fg-dashboard-main"><Header /><Outlet /></div>
    {renderLinks('fg-mobile-dash-nav')}
  </div>;
}
