import React from 'react';

export default function SystemRingChart({ value, label, color = 'rgb(0, 240, 255)', icon }) {
  const roundedValue = Math.round(value);
  const radius = 35;
  const strokeWidth = 4;
  const circumference = 2 * Math.PI * radius;
  const strokeDashoffset = circumference - (roundedValue / 100) * circumference;

  return (
    <div className="flex flex-col items-center justify-center p-3 bg-cyber-darker/35 border border-cyber-blue/10 rounded-xl relative group hover:border-cyber-blue/30 transition-all">
      {/* SVG Circular Ring */}
      <div className="relative w-20 h-20 flex items-center justify-center">
        <svg className="w-full h-full transform -rotate-90" viewBox="0 0 80 80">
          {/* Background circle */}
          <circle
            cx="40"
            cy="40"
            r={radius}
            stroke="rgba(15, 23, 42, 0.6)"
            strokeWidth={strokeWidth}
            fill="transparent"
          />
          {/* Accent border circle track */}
          <circle
            cx="40"
            cy="40"
            r={radius}
            stroke="rgba(0, 240, 255, 0.06)"
            strokeWidth={strokeWidth + 2}
            fill="transparent"
          />
          {/* Foreground progress circle */}
          <circle
            cx="40"
            cy="40"
            r={radius}
            stroke={color}
            strokeWidth={strokeWidth}
            fill="transparent"
            strokeDasharray={circumference}
            strokeDashoffset={strokeDashoffset}
            strokeLinecap="round"
            style={{
              transition: 'stroke-dashoffset 0.8s ease-in-out',
              filter: `drop-shadow(0 0 6px ${color})`,
            }}
          />
        </svg>

        {/* Center content */}
        <div className="absolute inset-0 flex flex-col items-center justify-center text-center">
          {icon && <span className="text-[10px] opacity-70 group-hover:scale-110 transition-transform">{icon}</span>}
          <span className="font-orbitron font-bold text-xs text-glow tracking-tighter" style={{ color }}>
            {roundedValue}%
          </span>
        </div>
      </div>

      {/* Label */}
      <span className="mt-2 font-mono text-[8px] tracking-widest text-slate-400 uppercase select-none group-hover:text-white transition-colors">
        {label}
      </span>
    </div>
  );
}
