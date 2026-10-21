import React, { useEffect, useState } from "react";

interface ScoreBarProps {
  label: string;
  value: number; // 0 to 100
  color?: "blue" | "purple" | "emerald" | "amber" | "rose" | "gradient";
  size?: "sm" | "md" | "lg";
  showValue?: boolean;
  className?: string;
}

export const ScoreBar: React.FC<ScoreBarProps> = ({
  label,
  value,
  color = "blue",
  size = "md",
  showValue = true,
  className = "",
}) => {
  const [width, setWidth] = useState(0);
  const normalizedValue = Math.min(100, Math.max(0, Math.round(value)));

  useEffect(() => {
    const timer = setTimeout(() => {
      setWidth(normalizedValue);
    }, 50);
    return () => clearTimeout(timer);
  }, [normalizedValue]);

  const heightClass = {
    sm: "h-2",
    md: "h-2.5",
    lg: "h-3.5",
  }[size];

  const barColor = {
    gradient: "bg-[#2563eb]",
    blue: "bg-[#2563eb]",
    purple: "bg-[#7c3aed]",
    emerald: "bg-[#059669]",
    amber: "bg-[#d97706]",
    rose: "bg-[#e11d48]",
  }[color];

  return (
    <div className={`w-full ${className}`}>
      {(label || showValue) && (
        <div className="flex justify-between items-center mb-1.5 text-sm">
          <span className="text-[#656d76] truncate pr-2 font-medium">{label}</span>
          {showValue && (
            <span className="font-semibold text-[#1f2328]">{normalizedValue}%</span>
          )}
        </div>
      )}
      <div className={`w-full bg-[#E9E9E7] rounded-full overflow-hidden ${heightClass}`}>
        <div
          className={`${heightClass} rounded-full transition-all duration-500 ease-out ${barColor}`}
          style={{ width: `${width}%` }}
        />
      </div>
    </div>
  );
};

export default ScoreBar;
