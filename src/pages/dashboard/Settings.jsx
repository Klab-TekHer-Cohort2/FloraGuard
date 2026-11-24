import { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { useRole } from '../../context/RoleContext.jsx';
import { useTheme } from '../../context/ThemeContext.jsx';
import { useTranslation } from '../../i18n/useTranslation.js';
import Button from '../../components/Button.jsx';
import Card from '../../components/Card.jsx';
import Modal from '../../components/Modal.jsx';

export default function Settings() {
  const { t, lang, setLang } = useTranslation();
  const { theme, toggleTheme } = useTheme();
  const { role, setRole } = useRole();
  const navigate = useNavigate();
  const [confirm, setConfirm] = useState(false);
  const switchTheme = (next) => { if (next !== theme) toggleTheme(); };
  const toggle = (label, options, value, onChange) => <div style={{ display: 'flex', flexWrap: 'wrap', gap: 8 }} role="group" aria-label={label}>{options.map(([code, title]) => <Button key={code} variant={value === code ? 'primary' : 'secondary'} aria-pressed={value === code} onClick={() => onChange(code)}>{title}</Button>)}</div>;
  return <main className="fg-page fg-dashboard-content">
    <h1>{t('dashboard.settings.title')}</h1>
    <div className="fg-grid" style={{ marginTop: 20 }}>
      <Card><h2>{t('dashboard.settings.language')}</h2>{toggle(t('dashboard.settings.language'), [['en', t('dashboard.settings.languageEN')], ['rw', t('dashboard.settings.languageRW')]], lang, setLang)}</Card>
      <Card><h2>{t('dashboard.settings.theme')}</h2>{toggle(t('dashboard.settings.theme'), [['light', t('dashboard.settings.themeLight')], ['dark', t('dashboard.settings.themeDark')]], theme, switchTheme)}</Card>
      <Card><h2>{t('dashboard.settings.role')}</h2><p>{role === 'grower' ? t('dashboard.settings.roleGrowerLabel') : t('dashboard.settings.roleManagerLabel')}</p><Button variant="secondary" onClick={() => setConfirm(true)}>{t('dashboard.settings.switchRole')}</Button></Card>
      <Card><h2>{t('dashboard.settings.about')}</h2><p>{t('app.tagline')}</p><Link to="/about">{t('dashboard.settings.aboutLink')}</Link></Card>
    </div>
    <Modal isOpen={confirm} onClose={() => setConfirm(false)} title={t('dashboard.settings.switchRole')}><p>{t('dashboard.settings.switchRoleConfirm')}</p><div style={{ display: 'flex', justifyContent: 'flex-end', gap: 8 }}><Button variant="ghost" onClick={() => setConfirm(false)}>{t('common.cancel')}</Button><Button onClick={() => { setRole(null); navigate('/'); }}>{t('common.confirm')}</Button></div></Modal>
  </main>;
}
