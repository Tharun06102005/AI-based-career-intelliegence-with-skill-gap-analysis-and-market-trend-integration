import React from "react";

export interface GlassCardProps extends React.HTMLAttributes<HTMLDivElement> {
  children: React.ReactNode;
  className?: string;
  gradient?: boolean;
  hover?: boolean;
}

export const GlassCard: React.FC<GlassCardProps> = ({
  children,
  className = "",
  gradient = false,
  hover = false,
  onClick,
  style,
  ...rest
}) => {
  return (
    <div
      onClick={onClick}
      style={{
        width: "100%",
        padding: "1.5rem",
        borderRadius: "8px",
        ...style,
      }}
      className={`bg-white border border-[#E9E9E7] shadow-[0_1px_3px_rgba(0,0,0,0.08)] transition-all duration-150 ${
        hover ? "hover:bg-[#F7F6F3] hover:border-[#D3D1CB]" : ""
      } ${onClick ? "cursor-pointer" : ""} ${className}`}
      {...rest}
    >
      {children}
    </div>
  );
};

export default GlassCard;
