interface MetricProps {
  label: string;
  value: number;
}

function Metric({ label, value }: MetricProps) {
  const percentage = value * 100;

  return (
    <div className="bg-[var(--bg-tertiary)] p-2.5 rounded-lg">
      <div className="text-[11px] text-[var(--text-muted)] uppercase mb-1">{label}</div>
      <div className="text-lg font-bold text-[var(--text-primary)]">
        {percentage.toFixed(0)}%
      </div>
      <div className="h-1 bg-[var(--bg-primary)] rounded mt-1 overflow-hidden">
        <div
          className="h-full rounded"
          style={{
            width: `${percentage}%`,
            background: 'linear-gradient(90deg, #e94560, #0f3460)',
          }}
        />
      </div>
    </div>
  );
}

interface ScoreBreakdownProps {
  aesthetic: number;
  technical: number;
}

export function ScoreBreakdown({ aesthetic, technical }: ScoreBreakdownProps) {
  return (
    <div className="grid grid-cols-2 gap-2.5 mb-3">
      <Metric label="Aesthetic" value={aesthetic} />
      <Metric label="Technical" value={technical} />
    </div>
  );
}
