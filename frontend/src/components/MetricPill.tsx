interface MetricPillProps {
  label: string;
  value: string;
}

export function MetricPill({ label, value }: MetricPillProps) {
  return (
    <div className="metric-pill">
      <span>{label}</span>
      <strong>{value}</strong>
    </div>
  );
}

