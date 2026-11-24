export default function Skeleton({ variant = 'line', count = 1, style }) {
  const shape = variant === 'circle'
    ? { width: 44, height: 44, borderRadius: '50%' }
    : variant === 'block'
      ? { width: '100%', height: 120, borderRadius: 12 }
      : { width: '100%', height: 14, borderRadius: 8 };
  return (
    <div aria-busy="true" aria-label="Loading" style={{ display: 'grid', gap: 10 }}>
      {Array.from({ length: Math.max(1, count) }, (_, index) => (
        <div key={index} className="skeleton-shimmer" style={{ ...shape, ...style }} />
      ))}
    </div>
  );
}
