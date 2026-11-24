import { Link, useNavigate } from 'react-router-dom';
import { Moon, Sun, Leaf } from 'lucide-react';
import { useTheme } from '../context/ThemeContext.jsx';
import { useRole } from '../context/RoleContext.jsx';
import { useTranslation } from '../i18n/useTranslation.js';

export function Brand({ light = false }) {
  return <Link to="/" aria-label="FloraGuard home" style={{ display: 'inline-flex', alignItems: 'center', gap: 8, textDecoration: 'none', color: light ? '#fff' : 'var(--color-primary)', fontWeight: 800, fontSize: 20 }}>
    <span aria-hidden="true" style={{ width: 34, height: 34, borderRadius: 10, display: 'grid', placeItems: 'center', color: '#fff', background: 'var(--color-primary)' }}><Leaf size={21} /></span>
    FloraGuard
  </Link>;
}

export default function Header() {
  const { theme, toggleTheme } = useTheme();
  const { role, setRole } = useRole();
  const { t, lang, setLang } = useTranslation();
  const navigate = useNavigate();
  return (
    <header style={{ minHeight: 64, display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: 12, padding: '10px max(16px, calc((100% - 1200px)/2))', background: 'var(--color-surface)', borderBottom: '1px solid var(--color-border)' }}>
      <Brand />
      <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
        <div role="group" aria-label={t('header.languageSwitcher')} style={{ display: 'flex', gap: 2 }}>
          {['en', 'rw'].map((code) => <button key={code} type="button" onClick={() => setLang(code)} aria-pressed={lang === code} style={{ padding: '7px 8px', border: 0, borderRadius: 8, background: lang === code ? 'var(--color-primary-tint)' : 'transparent', color: 'var(--color-text)', cursor: 'pointer', fontWeight: 700 }}>{code.toUpperCase()}</button>)}
        </div>
        <button type="button" onClick={toggleTheme} aria-label={t('header.themeSwitcher')} style={{ width: 40, height: 40, border: 0, borderRadius: 10, background: 'var(--color-bg)', color: 'var(--color-text)', cursor: 'pointer' }}>{theme === 'dark' ? <Sun size={19} /> : <Moon size={19} />}</button>
        {role && <button type="button" onClick={() => { setRole(null); navigate('/'); }} style={{ padding: '8px 10px', border: '1px solid var(--color-border)', borderRadius: 10, background: 'transparent', color: 'var(--color-text)', cursor: 'pointer' }}>{t('nav.switchRole')}</button>}
      </div>
    </header>
  );
}
