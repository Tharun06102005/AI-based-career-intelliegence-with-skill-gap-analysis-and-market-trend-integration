import React from "react";
import Link from "next/link";

export default function NotFound() {
  return (
    <div className="min-h-screen bg-[#F7F6F3] text-[#37352F] flex items-center justify-center p-6">
      <div className="max-w-sm w-full text-center">
        <div className="bg-white border border-[#E9E9E7] rounded-lg p-8 shadow-[0_1px_3px_rgba(0,0,0,0.08)]">
          <div className="text-3xl mb-3">🔍</div>
          <h1 className="text-xl font-bold text-[#37352F] mb-1.5">Page Not Found</h1>
          <p className="text-xs text-[#6B6B6B] mb-5">
            The page you are looking for does not exist or has been moved.
          </p>
          <Link
            href="/dashboard"
            className="inline-flex items-center gap-1.5 px-4 py-2 rounded-md font-medium text-xs bg-[#2383E2] hover:bg-[#1A73E8] text-white transition-colors"
          >
            Return to Dashboard &rarr;
          </Link>
        </div>
      </div>
    </div>
  );
}
