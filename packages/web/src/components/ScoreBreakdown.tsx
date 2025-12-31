interface MetricProps {
  label: string;
  value: number;
}

function Metric({ label, value }: MetricProps) {
  const percentage = value * 100;

  return (
    <div className="bg-ps-accent p-2.5 rounded-lg">
      <div className="text-[11px] text-gray-500 uppercase mb-1">{label}</div>
      <div className="text-lg font-bold text-gray-200">
        {percentage.toFixed(0)}%
      </div>
      <div className="h-1 bg-ps-bg rounded mt-1 overflow-hidden">
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
    <div className="grid grid-cols-2 gap-2.5 mb-4">
      <Metric label="Aesthetic" value={aesthetic} />
      <Metric label="Technical" value={technical} />
    </div>
  );
}
