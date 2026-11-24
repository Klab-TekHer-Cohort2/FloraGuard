import Button from './Button.jsx';

export default function EmptyState({ icon: Icon, title, message, action }) {
  return (
    <div style={{ display: 'grid', justifyItems: 'center', gap: 10, padding: '36px 20px', textAlign: 'center', color: 'var(--color-text-muted)' }}>
      <svg aria-hidden="true" viewBox="0 0 64 64" width="56" height="56" fill="none" stroke="var(--color-primary)" strokeWidth="2">
        <path d="M32 30c-9-8-3-18 2-17 7 1 6 9-2 17Zm0 0c-1-12 10-16 13-11 4 6-4 12-13 11Zm0 0c10-7 19 0 16 6-3 6-12 3-16-6Zm0 0c8 9 2 18-4 16-6-2-4-12 4-16Zm0 0c-11 4-17-5-13-10 4-5 12 0 13 10Z" />
        <path d="M32 30v24m0-10c-7-8-13-5-14-2 5 5 10 5 14 2Zm0 3c6-8 12-7 15-3-4 5-10 6-15 3Z" />
      </svg>
      {Icon && <Icon size={22} aria-hidden="true" />}
      <strong style={{ color: 'var(--color-text)' }}>{title}</strong>
      {message && <p style={{ margin: 0, maxWidth: 420 }}>{message}</p>}
      {action && <Button onClick={action.onClick}>{action.label}</Button>}
    </div>
  );
}
