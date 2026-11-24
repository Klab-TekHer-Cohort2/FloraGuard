/** Surface card; clickable cards receive keyboard semantics automatically. */
export default function Card({ className = '', onClick, padding = 16, as = 'div', children, style, ...props }) {
  const Tag = as;
  return (
    <Tag
      className={`fg-card ${className}`}
      onClick={onClick}
      onKeyDown={onClick ? (event) => {
        if (event.key === 'Enter' || event.key === ' ') {
          event.preventDefault();
          onClick(event);
        }
      } : undefined}
      role={onClick ? 'button' : props.role}
      tabIndex={onClick ? 0 : props.tabIndex}
      style={{
        padding,
        borderRadius: 16,
        border: '1px solid var(--color-border)',
        background: 'var(--color-surface)',
        color: 'var(--color-text)',
        boxShadow: 'var(--shadow-card)',
        cursor: onClick ? 'pointer' : undefined,
        ...style,
      }}
      {...props}
    >
      {children}
    </Tag>
  );
}
