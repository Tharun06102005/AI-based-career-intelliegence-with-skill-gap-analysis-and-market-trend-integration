"use client";

import React, { useEffect, useState } from "react";
import Link from "next/link";
import { isLoggedIn } from "../lib/auth";

export default function LandingPage() {
  const [authenticated, setAuthenticated] = useState(false);

  useEffect(() => {
    setAuthenticated(isLoggedIn());
  }, []);

  return (
    <div className="min-h-screen bg-[#f8f9fb] text-[#1f2328] flex flex-col selection:bg-blue-100 selection:text-blue-900">
      {/* Top Header */}
      <header className="sticky top-0 z-40 w-full bg-white/90 backdrop-blur-md border-b border-[#e2e4e8]">
        <div className="max-w-[1440px] mx-auto h-18 px-6 sm:px-10 flex items-center justify-between">
          {/* Logo & Brand */}
          <Link href="/" className="flex items-center gap-3 group">
            <div className="w-10 h-10 rounded-xl bg-gradient-to-tr from-blue-600 via-indigo-600 to-sky-500 flex items-center justify-center text-white shadow-md shadow-blue-500/20 group-hover:scale-105 transition-transform shrink-0">
              <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2.5} d="M13 10V3L4 14h7v7l9-11h-7z" />
              </svg>
            </div>
            <div className="flex flex-col">
              <span className="text-lg font-bold tracking-tight text-[#1f2328] flex items-center gap-1.5">
                CareerIntel <span className="text-xs font-bold px-1.5 py-0.5 rounded bg-blue-50 text-blue-600 border border-blue-200">AI</span>
              </span>
              <span className="text-xs text-[#656d76] font-medium leading-none hidden sm:block">
                Skill & Career Intelligence
              </span>
            </div>
          </Link>

          {/* Action Links */}
          <div className="flex items-center gap-3">
            {authenticated ? (
              <Link
                href="/dashboard"
                className="bg-blue-600 hover:bg-blue-700 text-white px-5 py-2.5 rounded-xl text-sm font-semibold transition-all shadow-sm hover:shadow-md hover:shadow-blue-500/20 flex items-center gap-1.5"
              >
                <span>Go to Dashboard</span>
                <span className="text-base">&rarr;</span>
              </Link>
            ) : (
              <>
                <Link
                  href="/login"
                  className="text-sm font-semibold text-[#4b5563] hover:text-[#111827] px-4 py-2 rounded-lg hover:bg-gray-100/80 transition-colors"
                >
                  Sign In
                </Link>
                <Link
                  href="/register"
                  className="bg-blue-600 hover:bg-blue-700 text-white px-5 py-2.5 rounded-xl text-sm font-semibold transition-all shadow-sm hover:shadow-md hover:shadow-blue-500/20"
                >
                  Get Started
                </Link>
              </>
            )}
          </div>
        </div>
      </header>

      {/* Main Content Area */}
      <main className="flex-1 w-full max-w-[1440px] mx-auto px-6 sm:px-10 py-12 lg:py-20 space-y-20">
        {/* Hero Section */}
        <section className="text-center space-y-6 max-w-4xl mx-auto pt-4">
          <div className="inline-flex items-center gap-2 px-4 py-1.5 rounded-full bg-blue-50 border border-blue-200/80 text-xs sm:text-sm font-semibold text-blue-700 shadow-2xs">
            <span className="w-2 h-2 rounded-full bg-blue-600 animate-pulse" />
            <span>AI-Driven Career Intelligence & Skill Analysis Platform</span>
          </div>

          <h1 className="text-4xl sm:text-5xl lg:text-6xl font-extrabold tracking-tight text-[#111827] leading-[1.15]">
            Supercharge Your Career with{" "}
            <span className="bg-gradient-to-r from-blue-600 via-indigo-600 to-sky-500 bg-clip-text text-transparent">
              Deterministic AI
            </span>
          </h1>

          <p className="text-base sm:text-lg lg:text-xl text-[#4b5563] leading-relaxed max-w-3xl mx-auto font-normal">
            Benchmark your resume against industry roles, verify proficiencies through adaptive code assessments, practice with an AI mock interview coach, and track tailored opportunities with absolute mathematical precision.
          </p>

          <div className="flex flex-col sm:flex-row items-center justify-center gap-4 pt-4">
            <Link
              href={authenticated ? "/dashboard" : "/register"}
              className="w-full sm:w-auto bg-blue-600 hover:bg-blue-700 text-white px-8 py-3.5 rounded-xl text-base font-semibold transition-all shadow-md hover:shadow-xl hover:shadow-blue-500/25 text-center flex items-center justify-center gap-2 hover:-translate-y-0.5"
            >
              <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12" />
              </svg>
              <span>Upload Resume & Benchmark</span>
            </Link>
            <Link
              href={authenticated ? "/dashboard" : "/login"}
              className="w-full sm:w-auto bg-white hover:bg-gray-50 text-[#1f2328] border border-[#d0d7de] hover:border-gray-400 px-8 py-3.5 rounded-xl text-base font-semibold transition-all shadow-xs text-center"
            >
              Sign In to Account
            </Link>
          </div>
        </section>

        {/* Live Metrics Showcase Banner */}
        <section className="bg-white border border-[#e2e4e8] rounded-2xl p-6 sm:p-10 shadow-sm max-w-5xl mx-auto">
          <div className="grid grid-cols-2 lg:grid-cols-4 gap-6 divide-y lg:divide-y-0 lg:divide-x divide-gray-100 text-center">
            <div className="pt-3 lg:pt-0">
              <div className="text-3xl sm:text-4xl font-extrabold text-[#111827]">120K+</div>
              <div className="text-sm font-medium text-[#656d76] mt-1">Live Job Benchmarks</div>
            </div>
            <div className="pt-3 lg:pt-0">
              <div className="text-3xl sm:text-4xl font-extrabold text-[#111827]">100+</div>
              <div className="text-sm font-medium text-[#656d76] mt-1">Verified Skill Sets</div>
            </div>
            <div className="pt-3 lg:pt-0">
              <div className="text-3xl sm:text-4xl font-extrabold text-[#111827]">10</div>
              <div className="text-sm font-medium text-[#656d76] mt-1">Target Tech Careers</div>
            </div>
            <div className="pt-3 lg:pt-0">
              <div className="text-3xl sm:text-4xl font-extrabold text-blue-600">100%</div>
              <div className="text-sm font-medium text-[#656d76] mt-1">Deterministic Scoring</div>
            </div>
          </div>
        </section>

        {/* Core Capabilities Grid (6 Features) */}
        <section className="space-y-10 max-w-6xl mx-auto">
          <div className="text-center space-y-3">
            <h2 className="text-2xl sm:text-3xl lg:text-4xl font-bold text-[#111827] tracking-tight">
              Enterprise-Grade Career Intelligence
            </h2>
            <p className="text-base sm:text-lg text-[#656d76] max-w-2xl mx-auto">
              Everything you need to benchmark, verify, simulate, and practice your technical career path.
            </p>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6 sm:gap-8">
            {/* Feature 1 */}
            <div className="bg-white border border-[#e2e4e8] rounded-2xl p-7 shadow-xs hover:shadow-lg hover:border-blue-300 transition-all group">
              <div className="w-12 h-12 rounded-xl bg-blue-50 border border-blue-100 flex items-center justify-center text-2xl mb-5 group-hover:scale-110 transition-transform">
                📄
              </div>
              <h3 className="text-lg font-bold text-[#111827] mb-2">
                Resume Intelligence & ATS
              </h3>
              <p className="text-sm text-[#4b5563] leading-relaxed">
                Automatic skill extraction, section completeness evaluation, and strict ATS parser optimization to maximize your interview callbacks.
              </p>
            </div>

            {/* Feature 2 */}
            <div className="bg-white border border-[#e2e4e8] rounded-2xl p-7 shadow-xs hover:shadow-lg hover:border-blue-300 transition-all group">
              <div className="w-12 h-12 rounded-xl bg-emerald-50 border border-emerald-100 flex items-center justify-center text-2xl mb-5 group-hover:scale-110 transition-transform">
                🎯
              </div>
              <h3 className="text-lg font-bold text-[#111827] mb-2">
                Deterministic Career-Fit
              </h3>
              <p className="text-sm text-[#4b5563] leading-relaxed">
                Versioned mathematical scoring across 10 high-growth roles combining verified skills, experience alignment, and real-time market demand.
              </p>
            </div>

            {/* Feature 3 */}
            <div className="bg-white border border-[#e2e4e8] rounded-2xl p-7 shadow-xs hover:shadow-lg hover:border-blue-300 transition-all group">
              <div className="w-12 h-12 rounded-xl bg-purple-50 border border-purple-100 flex items-center justify-center text-2xl mb-5 group-hover:scale-110 transition-transform">
                ⚡
              </div>
              <h3 className="text-lg font-bold text-[#111827] mb-2">
                Adaptive Skill Verification
              </h3>
              <p className="text-sm text-[#4b5563] leading-relaxed">
                Interactive challenges with live sandboxed Python code execution that adjusts difficulty dynamically from beginner to advanced.
              </p>
            </div>

            {/* Feature 4 */}
            <div className="bg-white border border-[#e2e4e8] rounded-2xl p-7 shadow-xs hover:shadow-lg hover:border-blue-300 transition-all group">
              <div className="w-12 h-12 rounded-xl bg-amber-50 border border-amber-100 flex items-center justify-center text-2xl mb-5 group-hover:scale-110 transition-transform">
                💼
              </div>
              <h3 className="text-lg font-bold text-[#111827] mb-2">
                Job Opportunity Matcher
              </h3>
              <p className="text-sm text-[#4b5563] leading-relaxed">
                Calculates transparent match scores with bonuses for verified skills, and lets you track your pipeline from application to offer.
              </p>
            </div>

            {/* Feature 5 */}
            <div className="bg-white border border-[#e2e4e8] rounded-2xl p-7 shadow-xs hover:shadow-lg hover:border-blue-300 transition-all group">
              <div className="w-12 h-12 rounded-xl bg-rose-50 border border-rose-100 flex items-center justify-center text-2xl mb-5 group-hover:scale-110 transition-transform">
                🎙️
              </div>
              <h3 className="text-lg font-bold text-[#111827] mb-2">
                AI Mock Interview Coach
              </h3>
              <p className="text-sm text-[#4b5563] leading-relaxed">
                Resume-grounded technical and behavioral interviews with voice dictation, rated across 5 rubric dimensions with model answers.
              </p>
            </div>

            {/* Feature 6 */}
            <div className="bg-white border border-[#e2e4e8] rounded-2xl p-7 shadow-xs hover:shadow-lg hover:border-blue-300 transition-all group">
              <div className="w-12 h-12 rounded-xl bg-sky-50 border border-sky-100 flex items-center justify-center text-2xl mb-5 group-hover:scale-110 transition-transform">
                🔮
              </div>
              <h3 className="text-lg font-bold text-[#111827] mb-2">
                What-If Career Simulator
              </h3>
              <p className="text-sm text-[#4b5563] leading-relaxed">
                Simulate acquiring new technologies or career pivots to view real-time readiness deltas before spending months studying.
              </p>
            </div>
          </div>
        </section>

        {/* Footer */}
        <footer className="border-t border-[#e2e4e8] pt-10 pb-6 text-center text-sm text-[#656d76] max-w-5xl mx-auto">
          <div className="flex flex-col sm:flex-row items-center justify-between gap-4">
            <div className="flex items-center gap-2">
              <div className="w-6 h-6 rounded-lg bg-blue-600 flex items-center justify-center text-white text-xs font-bold">
                C
              </div>
              <span className="font-semibold text-[#1f2328]">Career Intelligence Platform</span>
            </div>
            <p>&copy; {new Date().getFullYear()} Career Intelligence. Built for high-impact technical career development.</p>
          </div>
        </footer>
      </main>
    </div>
  );
}
