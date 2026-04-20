interface LineChartPoint {
  date: string;
  equity: number;
}

interface LineChartProps {
  title: string;
  points: LineChartPoint[];
}

export function LineChart({ title, points }: LineChartProps) {
  if (points.length === 0) {
    return (
      <div className="chart-card">
        <div className="chart-header">
          <h4>{title}</h4>
        </div>
        <p className="card-subtitle">No chart data available yet.</p>
      </div>
    );
  }

  const width = 640;
  const height = 220;
  const padding = 18;
  const values = points.map((point) => point.equity);
  const min = Math.min(...values);
  const max = Math.max(...values);
  const range = Math.max(max - min, 1);
  const path = points
    .map((point, index) => {
      const x = padding + (index / Math.max(points.length - 1, 1)) * (width - padding * 2);
      const y = height - padding - ((point.equity - min) / range) * (height - padding * 2);
      return `${index === 0 ? "M" : "L"} ${x.toFixed(2)} ${y.toFixed(2)}`;
    })
    .join(" ");

  return (
    <div className="chart-card">
      <div className="chart-header">
        <h4>{title}</h4>
        <p>
          {points[0].date} to {points[points.length - 1].date}
        </p>
      </div>
      <svg viewBox={`0 0 ${width} ${height}`} className="line-chart" role="img" aria-label={title}>
        <defs>
          <linearGradient id="equityFill" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stopColor="rgba(31,109,99,0.28)" />
            <stop offset="100%" stopColor="rgba(31,109,99,0.03)" />
          </linearGradient>
        </defs>
        <path d={`M ${padding} ${height - padding} ${path.slice(1)} L ${width - padding} ${height - padding} Z`} fill="url(#equityFill)" />
        <path d={path} fill="none" stroke="var(--accent)" strokeWidth="3" strokeLinejoin="round" strokeLinecap="round" />
      </svg>
      <div className="chart-scale">
        <span>${min.toFixed(0)}</span>
        <span>${max.toFixed(0)}</span>
      </div>
    </div>
  );
}

