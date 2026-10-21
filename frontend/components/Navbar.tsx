"use client";

import React, { useState, useEffect } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { getUserEmail, logout } from "../lib/auth";

export const Navbar: React.FC = () => {
  const pathname = usePathname();
  const [email, setEmail] = useState<string | null>(null);
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);

  useEffect(() => {
    setEmail(getUserEmail());
  }, []);

  const navLinks = [
    { label: "Dashboard", href: "/dashboard" },
    { label: "Assessments", href: "/assessments" },
    { label: "Job Matches", href: "/jobs" },
    { label: "Mock Interview", href: "/interview" },
    { label: "Skill Gaps", href: "/gaps" },
    { label: "Simulator", href: "/simulate" },
    { label: "Roadmap", href: "/roadmap" },
    { label: "ATS Check", href: "/ats" },
    { label: "Progress", href: "/progress" },
  ];

  return (
    <header className="sticky top-0 z-40 w-full bg-white/95 backdrop-blur-md border-b border-[#e2e4e8] shadow-xs">
      <div className="w-full max-w-[1440px] mx-auto flex items-center justify-between h-16 px-6 sm:px-10">
        {/* Left side: Brand Logo & Title */}
        <Link href="/" className="flex items-center gap-3 group">
          <div className="w-9 h-9 rounded-xl bg-gradient-to-tr from-blue-600 via-indigo-600 to-sky-500 flex items-center justify-center text-white shadow-md shadow-blue-500/20 group-hover:scale-105 transition-transform shrink-0">
            <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2.5} d="M13 10V3L4 14h7v7l9-11h-7z" />
            </svg>
          </div>
          <div className="flex flex-col">
            <span className="text-base font-bold tracking-tight text-[#1f2328] flex items-center gap-1.5">
              CareerIntel <span className="text-[11px] font-bold px-1.5 py-0.5 rounded bg-blue-50 text-blue-600 border border-blue-200">AI</span>
            </span>
            <span className="text-xs text-[#656d76] font-medium leading-none hidden sm:block">
              Skill & Career Intelligence
            </span>
          </div>
        </Link>

        {/* Right side: Navigation Links & User Menu */}
        <div className="hidden xl:flex items-center gap-2">
          <nav className="flex items-center gap-1">
            {navLinks.map((link) => {
              const isActive = pathname === link.href;
              return (
                <Link
                  key={link.href}
                  href={link.href}
                  className={`px-3 py-2 rounded-lg text-sm font-medium transition-all ${
                    isActive
                      ? "bg-blue-50 text-blue-600 font-semibold shadow-xs"
                      : "text-[#4b5563] hover:text-[#111827] hover:bg-gray-100/80"
                  }`}
                >
                  {link.label}
                </Link>
              );
            })}
          </nav>

          {/* User Email & Sign Out */}
          <div className="flex items-center gap-3 pl-3 ml-2 border-l border-[#e2e4e8]">
            {email && (
              <div className="flex items-center gap-2 px-2.5 py-1 rounded-full bg-gray-50 border border-gray-200/80 text-xs font-medium text-[#4b5563] max-w-[170px]" title={email}>
                <span className="w-2 h-2 rounded-full bg-emerald-500 shrink-0" />
                <span className="truncate">{email}</span>
              </div>
            )}
            <button
              onClick={() => logout()}
              className="px-3 py-1.5 rounded-lg text-sm font-medium text-gray-600 hover:text-red-600 hover:bg-red-50 border border-transparent hover:border-red-200 transition-all"
            >
              Sign Out
            </button>
          </div>
        </div>

        {/* Tablet / Mobile Menu Button */}
        <div className="flex xl:hidden items-center gap-3 ml-auto">
          {email && (
            <span className="text-xs font-medium text-gray-500 max-w-[120px] truncate hidden sm:block">
              {email}
            </span>
          )}
          <button
            onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
            className="p-2 rounded-lg text-gray-600 hover:text-gray-900 hover:bg-gray-100 focus:outline-none transition-colors border border-gray-200"
            aria-label="Toggle navigation menu"
          >
            <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              {mobileMenuOpen ? (
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
              ) : (
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 6h16M4 12h16M4 18h16" />
              )}
            </svg>
          </button>
        </div>
      </div>

      {/* Mobile Drawer */}
      {mobileMenuOpen && (
        <div className="xl:hidden border-t border-[#e2e4e8] bg-white px-6 py-4 space-y-1 shadow-lg">
          <div className="grid grid-cols-2 sm:grid-cols-3 gap-1 pb-3 mb-3 border-b border-gray-100">
            {navLinks.map((link) => {
              const isActive = pathname === link.href;
              return (
                <Link
                  key={link.href}
                  href={link.href}
                  onClick={() => setMobileMenuOpen(false)}
                  className={`block px-3 py-2 rounded-lg text-sm font-medium transition-colors ${
                    isActive
                      ? "bg-blue-50 text-blue-600 font-semibold"
                      : "text-gray-600 hover:bg-gray-50 hover:text-gray-900"
                  }`}
                >
                  {link.label}
                </Link>
              );
            })}
          </div>
          <div className="flex items-center justify-between pt-1">
            {email && <span className="text-xs text-gray-500 truncate">{email}</span>}
            <button
              onClick={() => logout()}
              className="px-3 py-1.5 text-sm text-red-600 hover:bg-red-50 rounded-lg font-medium transition-colors"
            >
              Sign Out
            </button>
          </div>
        </div>
      )}
    </header>
  );
};

export default Navbar;
