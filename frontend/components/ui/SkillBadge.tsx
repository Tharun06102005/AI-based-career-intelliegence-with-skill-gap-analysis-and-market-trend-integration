import React from "react";

export type SkillBadgeType = "matched" | "missing" | "partial" | "default" | "gray" | "blue";

interface SkillBadgeProps {
  skill: string;
  type?: SkillBadgeType | string;
  size?: "sm" | "md" | "lg";
  onRemove?: () => void;
  className?: string;
}

export const SkillBadge: React.FC<SkillBadgeProps> = ({
  skill,
  type = "default",
  size = "md",
  onRemove,
  className = "",
}) => {
  const normType = type.toLowerCase();
  const normalizedType =
    normType.includes("match") && !normType.includes("partial")
      ? "matched"
      : normType.includes("partial")
      ? "partial"
      : normType.includes("miss")
      ? "missing"
      : normType.includes("blue")
      ? "blue"
      : normType.includes("gray")
      ? "gray"
      : "default";

  const sizeClasses = {
    sm: "text-xs px-2.5 py-1 gap-1.5 font-medium",
    md: "text-sm px-3.5 py-1.5 gap-2 font-medium",
    lg: "text-base px-4 py-2 gap-2.5 font-medium",
  }[size];

  const typeStyles = {
    matched: "bg-[#EBF5EE] text-[#1F7A4C] border-[#C6E7D2]",
    missing: "bg-[#FDE8E8] text-[#9B1C1C] border-[#F8B4B4]",
    partial: "bg-[#FEF3C7] text-[#92400E] border-[#FDE68A]",
    blue: "bg-[#EBF5FE] text-[#2383E2] border-[#CBE5FE]",
    gray: "bg-[#F1F1EF] text-[#5A5A58] border-[#E3E2DE]",
    default: "bg-[#F1F1EF] text-[#37352F] border-[#E3E2DE]",
  }[normalizedType];

  const dotColor = {
    matched: "bg-[#1F7A4C]",
    missing: "bg-[#9B1C1C]",
    partial: "bg-[#D9730D]",
    blue: "bg-[#2383E2]",
    gray: "bg-[#9B9A97]",
    default: "bg-[#9B9A97]",
  }[normalizedType];

  return (
    <span
      className={`inline-flex items-center font-medium rounded-full border transition-colors ${sizeClasses} ${typeStyles} ${className}`}
    >
      <span className={`w-1.5 h-1.5 rounded-full shrink-0 ${dotColor}`} />
      <span>{skill}</span>
      {onRemove && (
        <button
          type="button"
          onClick={(e) => {
            e.stopPropagation();
            onRemove();
          }}
          className="ml-0.5 text-[#6B6B6B] hover:text-[#37352F] rounded-full p-0.5 focus:outline-none transition-colors"
          aria-label={`Remove ${skill}`}
        >
          <svg
            className="w-3 h-3"
            fill="none"
            viewBox="0 0 24 24"
            stroke="currentColor"
            strokeWidth={2}
          >
            <path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" />
          </svg>
        </button>
      )}
    </span>
  );
};

export default SkillBadge;
