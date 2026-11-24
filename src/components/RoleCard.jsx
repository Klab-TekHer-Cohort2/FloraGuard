import { ArrowRight } from 'lucide-react';

/** Large keyboard-accessible role selector. */
export default function RoleCard({ icon: Icon, title, description, onClick, selected = false }) {
  return (
    <button type="button" onClick={onClick} aria-pressed={selected} className={`fg-role-card${selected ? ' is-selected' : ''}`}>
      {Icon && <span className="fg-role-icon"><Icon size={23} aria-hidden="true" /></span>}
      <span className="fg-role-copy"><strong>{title}</strong><span>{description}</span></span>
      <ArrowRight className="fg-role-arrow" size={20} aria-hidden="true" />
    </button>
  );
}
