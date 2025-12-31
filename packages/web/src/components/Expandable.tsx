import { useState, type ReactNode } from 'react';

interface ExpandableProps {
  title: string;
  icon: string;
  children: ReactNode;
}

export function Expandable({ title, icon, children }: ExpandableProps) {
  const [isOpen, setIsOpen] = useState(false);

  return (
    <div className="bg-[var(--bg-tertiary)] rounded-lg mb-4 overflow-hidden">
      <div
        className="flex justify-between items-center p-3 cursor-pointer select-none hover:opacity-80 transition-opacity"
        onClick={() => setIsOpen(!isOpen)}
      >
        <span className="text-[11px] text-[var(--text-muted)] uppercase font-semibold">
          {icon} {title}
        </span>
        <span
          className={`text-xs text-[#e94560] transition-transform duration-200 ${
            isOpen ? 'rotate-180' : ''
          }`}
        >
          ▼
        </span>
      </div>
      <div
        className={`overflow-hidden transition-all duration-300 ${
          isOpen ? 'max-h-[2000px]' : 'max-h-0'
        }`}
      >
        {children}
      </div>
    </div>
  );
}
