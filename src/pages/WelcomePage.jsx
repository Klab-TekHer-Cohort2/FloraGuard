import { useRef } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { BarChart3, Bell, Camera, Cpu, Leaf, Map, ShieldCheck } from 'lucide-react';
import { useRole } from '../context/RoleContext.jsx';
import { useTranslation } from '../i18n/useTranslation.js';
import Button from '../components/Button.jsx';
import Card from '../components/Card.jsx';
import RoleCard from '../components/RoleCard.jsx';
import { Brand } from '../components/Header.jsx';

const steps = [
  ['step1', Camera], ['step2', Cpu], ['step3', Map], ['step4', Bell],
];

export default function WelcomePage() {
  const { t, lang, setLang } = useTranslation();
  const { setRole } = useRole();
  const navigate = useNavigate();
  const roleRef = useRef(null);
  const howRef = useRef(null);
  const chooseRole = (role) => {
    setRole(role);
    navigate(role === 'grower' ? '/grower' : '/dashboard');
  };
  return (
    <div>
      <header className="fg-welcome-header"><Brand /><div style={{ display: 'flex', gap: 6 }}>
        {['en', 'rw'].map((code) => <button key={code} type="button" aria-pressed={lang === code} onClick={() => setLang(code)} style={{ border: 0, borderRadius: 8, padding: 8, background: lang === code ? 'var(--color-primary-tint)' : 'transparent', color: 'var(--color-text)', cursor: 'pointer' }}>{code.toUpperCase()}</button>)}
      </div></header>
      <section className="fg-hero">
        <div className="fg-hero-copy">
          <span className="fg-eyebrow"><Leaf size={17} /> {t('app.tagline')}</span>
          <h1>{t('welcome.hero.headline')}</h1>
          <p>{t('welcome.hero.subheadline')}</p>
          <div className="fg-hero-actions">
            <Button size="lg" onClick={() => roleRef.current?.scrollIntoView({ behavior: 'smooth' })}>{t('welcome.hero.getStarted')}</Button>
            <Button variant="ghost" onClick={() => howRef.current?.scrollIntoView({ behavior: 'smooth' })}>{t('welcome.hero.howItWorks')}</Button>
          </div>
          <p className="fg-hero-note"><ShieldCheck size={17} /> {t('welcome.trust.title')}</p>
        </div>
        <div className="fg-hero-art">
          <img className="fg-hero-image" src="/images/rose-hero.jpg" alt="" />
          <div className="fg-hero-image-overlay">
            <span className="fg-photo-tag"><Leaf size={16} /> {t('app.tagline')}</span>
            <div className="fg-photo-caption">
              <ShieldCheck size={22} />
              <span><strong>{t('welcome.builtForRwanda.title')}</strong><small>{t('welcome.builtForRwanda.subtitle')}</small></span>
            </div>
          </div>
        </div>
      </section>
      <main>
        <section id="role-chooser" ref={roleRef} className="fg-section fg-role-section">
          <h2>{t('welcome.chooseRole.title')}</h2><p>{t('welcome.chooseRole.subtitle')}</p>
          <div className="fg-grid fg-two-col" style={{ maxWidth: 880, margin: '22px auto 0' }}>
            <RoleCard icon={Leaf} title={t('welcome.chooseRole.grower.title')} description={t('welcome.chooseRole.grower.description')} onClick={() => chooseRole('grower')} />
            <RoleCard icon={BarChart3} title={t('welcome.chooseRole.manager.title')} description={t('welcome.chooseRole.manager.description')} onClick={() => chooseRole('manager')} />
          </div>
        </section>
        <section id="how-it-works" ref={howRef} className="fg-section">
          <h2>{t('welcome.howItWorks.title')}</h2>
          <div className="fg-grid fg-four-col" style={{ marginTop: 24 }}>{steps.map(([key, Icon], i) => <Card key={key} style={{ textAlign: 'left' }}><span className="fg-step-icon"><Icon size={22} /></span><small className="text-muted">0{i + 1}</small><h3>{t(`welcome.howItWorks.${key}.title`)}</h3><p className="text-muted">{t(`welcome.howItWorks.${key}.description`)}</p></Card>)}</div>
        </section>
        <section className="fg-section fg-tint-section">
          <h2>{t('welcome.whyItMatters.title')}</h2>
          <div className="fg-grid fg-three-col" style={{ marginTop: 24 }}>{[1, 2, 3].map((n) => <Card key={n}><h3>{t(`welcome.whyItMatters.card${n}.title`)}</h3><p className="text-muted">{t(`welcome.whyItMatters.card${n}.description`)}</p></Card>)}</div>
        </section>
        <section className="fg-section">
          <h2>{t('welcome.whoItIsFor.title')}</h2>
          <div className="fg-grid fg-three-col" style={{ marginTop: 24 }}>{['grower', 'manager', 'officer'].map((key) => <Card key={key}><h3>{t(`welcome.whoItIsFor.${key}.title`)}</h3><p className="text-muted">{t(`welcome.whoItIsFor.${key}.description`)}</p></Card>)}</div>
        </section>
        <section className="fg-rwanda-strip"><div className="fg-rwanda-shape" aria-label={t('welcome.builtForRwanda.mapAlt')} role="img">RW</div><div><h2>{t('welcome.builtForRwanda.title')}</h2><p>{t('welcome.builtForRwanda.subtitle')}</p></div></section>
        <section className="fg-trust-section"><ShieldCheck size={28} /><div><strong>{t('welcome.trust.title')}</strong><p>{t('welcome.trust.disclaimer')}</p><small>{t('welcome.trust.privacy')}</small></div></section>
      </main>
      <footer className="fg-footer"><Brand /><small>© {new Date().getFullYear()} FloraGuard</small><Link to="/about">{t('about.title')}</Link></footer>
    </div>
  );
}
