import { Loader2 } from 'lucide-react';

const variants = {
  primary: { background: 'var(--color-primary)', color: 'var(--on-primary)', border: '1px solid var(--color-primary)' },
  secondary: { background: 'var(--color-primary-tint)', color: 'var(--color-primary)', border: '1px solid var(--color-border)' },
  ghost: { background: 'transparent', color: 'var(--color-text)', border: '1px solid transparent' },
  danger: { background: 'var(--risk-high)', color: 'var(--on-danger)', border: '1px solid var(--risk-high)' },
};

/** Accessible action button with variants, sizing, and loading state. */
export default function Button({
  variant = 'primary',
  size = 'md',
  loading = false,
  disabled = false,
  fullWidth = false,
  className = '',
  style,
  children,
  ...props
}) {
  const heights = { sm: 38, md: 48, lg: 56 };
  return (
    <button
      className={`fg-button ${className}`}
      disabled={disabled || loading}
      aria-busy={loading || undefined}
      style={{
        ...variants[variant],
        minHeight: heights[size] || heights.md,
        width: fullWidth ? '100%' : undefined,
        padding: size === 'sm' ? '8px 12px' : '12px 18px',
        borderRadius: 12,
        fontFamily: 'inherit',
        fontSize: '0.95rem',
        fontWeight: 600,
        display: 'inline-flex',
        alignItems: 'center',
        justifyContent: 'center',
        gap: 8,
        cursor: disabled || loading ? 'not-allowed' : 'pointer',
        opacity: disabled ? 0.6 : 1,
        ...style,
      }}
      {...props}
    >
      {loading && <Loader2 aria-hidden="true" size={18} className="fg-spin" />}
      {children}
    </button>
  );
}
