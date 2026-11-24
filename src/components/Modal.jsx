import { useEffect, useRef } from 'react';
import { createPortal } from 'react-dom';
import { X } from 'lucide-react';
import { useTranslation } from '../i18n/useTranslation.js';

export default function Modal({ isOpen, onClose, title, children }) {
  const dialogRef = useRef(null);
  const { t } = useTranslation();
  useEffect(() => {
    if (!isOpen) return undefined;
    const previous = document.activeElement;
    const dialog = dialogRef.current;
    const focusable = () => [...dialog.querySelectorAll('button:not([disabled]), [href], input:not([disabled]), select:not([disabled]), textarea:not([disabled]), [tabindex]:not([tabindex="-1"])')];
    focusable()[0]?.focus();
    const handleKey = (event) => {
      if (event.key === 'Escape') onClose();
      if (event.key === 'Tab') {
        const items = focusable();
        if (!items.length) { event.preventDefault(); return; }
        if (event.shiftKey && document.activeElement === items[0]) {
          event.preventDefault(); items[items.length - 1].focus();
        } else if (!event.shiftKey && document.activeElement === items[items.length - 1]) {
          event.preventDefault(); items[0].focus();
        }
      }
    };
    document.addEventListener('keydown', handleKey);
    return () => {
      document.removeEventListener('keydown', handleKey);
      previous?.focus?.();
    };
  }, [isOpen, onClose]);
  if (!isOpen) return null;
  return createPortal(
    <div onMouseDown={(event) => { if (event.target === event.currentTarget) onClose(); }} style={{ position: 'fixed', inset: 0, zIndex: 1000, background: 'rgba(0,0,0,.52)', display: 'grid', placeItems: 'center', padding: 16 }}>
      <section ref={dialogRef} role="dialog" aria-modal="true" aria-labelledby="fg-modal-title" tabIndex={-1} className="fg-modal" style={{ width: 'min(100%, 480px)', maxHeight: '90vh', overflow: 'auto', borderRadius: 18, padding: 24, background: 'var(--color-surface)', color: 'var(--color-text)', boxShadow: 'var(--shadow-card-hover)' }}>
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: 12 }}>
          <h2 id="fg-modal-title" style={{ margin: 0 }}>{title}</h2>
          <button type="button" aria-label={t('aria.closeModal')} onClick={onClose} style={{ border: 0, background: 'transparent', color: 'inherit', cursor: 'pointer' }}><X /></button>
        </div>
        <div style={{ marginTop: 16 }}>{children}</div>
      </section>
    </div>,
    document.body
  );
}
