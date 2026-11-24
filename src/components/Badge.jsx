export default function Badge({ label, children, icon: Icon, color = 'var(--color-text-muted)', bgColor = 'var(--color-bg)', style }) {
  return (
    <span style={{
      display: 'inline-flex', alignItems: 'center', gap: 5, padding: '4px 9px',
      borderRadius: 999, color, background: bgColor, fontSize: 12, fontWeight: 600,
      ...style,
    }}>
      {Icon && <Icon aria-hidden="true" size={14} />}
      {label ?? children}
    </span>
  );
}
