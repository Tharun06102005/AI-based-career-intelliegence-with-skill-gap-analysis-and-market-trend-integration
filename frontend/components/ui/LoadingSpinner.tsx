import React from "react";

interface LoadingSpinnerProps {
  size?: "sm" | "md" | "lg" | "xl";
  text?: string;
  fullScreen?: boolean;
}

export const LoadingSpinner: React.FC<LoadingSpinnerProps> = ({
  size = "md",
  text,
  fullScreen = false,
}) => {
  const sizeClass = {
    sm: "w-4 h-4 border-2",
    md: "w-6 h-6 border-2",
    lg: "w-8 h-8 border-[3px]",
    xl: "w-10 h-10 border-4",
  }[size];

  const content = (
    <div className="flex flex-col items-center justify-center gap-2">
      <div
        className={`${sizeClass} rounded-full border-[#E9E9E7] border-t-[#2383E2] animate-spin`}
      />
      {text && (
        <p className="text-xs font-medium text-[#6B6B6B] tracking-normal">
          {text}
        </p>
      )}
    </div>
  );

  if (fullScreen) {
    return (
      <div className="fixed inset-0 z-50 flex items-center justify-center bg-[#FFFFFF]/80 backdrop-blur-sm">
        {content}
      </div>
    );
  }

  return <div className="py-6 flex justify-center items-center">{content}</div>;
};

export default LoadingSpinner;
