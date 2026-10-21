"use client";

import React, { useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { authApi } from "../../lib/api";
import { saveToken, saveProfileId, saveUserEmail } from "../../lib/auth";
import LoadingSpinner from "../../components/ui/LoadingSpinner";

export default function LoginPage() {
  const router = useRouter();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);

    if (!email || !password) {
      setError("Please enter your email and password.");
      return;
    }

    setLoading(true);
    try {
      const res = await authApi.login({ email, password });
      const token = res.access_token || res.token;
      if (token) {
        saveToken(token);
      }
      if (res.profile_id) {
        saveProfileId(res.profile_id);
      }
      saveUserEmail(email);

      router.push("/dashboard");
    } catch (err: any) {
      setError(
        err.message || "Invalid email or password. Please verify your credentials."
      );
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center p-6 bg-[#f8f9fb]">
      <div className="w-full max-w-md">
        {/* Brand Icon & Heading */}
        <div className="text-center mb-6">
          <Link href="/" className="inline-flex items-center gap-2 mb-4">
            <div className="w-10 h-10 rounded-xl bg-gradient-to-tr from-blue-600 via-indigo-600 to-sky-500 flex items-center justify-center text-white shadow-md shadow-blue-500/20">
              <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2.5} d="M13 10V3L4 14h7v7l9-11h-7z" />
              </svg>
            </div>
            <span className="text-xl font-bold tracking-tight text-[#111827]">
              CareerIntel <span className="text-xs font-bold px-1.5 py-0.5 rounded bg-blue-50 text-blue-600 border border-blue-200">AI</span>
            </span>
          </Link>
          <h1 className="text-2xl font-bold text-[#111827] tracking-tight">
            Sign In to Your Account
          </h1>
          <p className="text-sm text-[#656d76] mt-1.5">
            Enter your credentials to access your intelligence dashboard
          </p>
        </div>

        <div className="bg-white border border-[#e2e4e8] rounded-2xl p-8 sm:p-9 shadow-sm">
          {/* Error banner */}
          {error && (
            <div className="mb-5 p-3 rounded-xl bg-red-50 border border-red-200 text-red-700 text-sm flex items-center gap-2">
              <svg className="w-4 h-4 shrink-0 text-red-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
              </svg>
              <span>{error}</span>
            </div>
          )}

          {/* Form */}
          <form onSubmit={handleSubmit} className="space-y-5">
            <div>
              <label className="block text-sm font-medium text-[#1f2328] mb-1.5">
                Email Address
              </label>
              <input
                type="email"
                required
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder="name@example.com"
                className="w-full px-4 py-3 bg-white border border-[#d0d7de] rounded-xl text-sm text-[#1f2328] placeholder-[#9ca3af] focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-600 transition-all"
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-[#1f2328] mb-1.5">
                Password
              </label>
              <input
                type="password"
                required
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder="••••••••"
                className="w-full px-4 py-3 bg-white border border-[#d0d7de] rounded-xl text-sm text-[#1f2328] placeholder-[#9ca3af] focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-600 transition-all"
              />
            </div>

            <button
              type="submit"
              disabled={loading}
              className="w-full mt-2 py-3.5 rounded-xl font-semibold text-base bg-blue-600 hover:bg-blue-700 text-white transition-all shadow-sm hover:shadow-md hover:shadow-blue-500/20 disabled:opacity-50 flex items-center justify-center gap-2"
            >
              {loading ? (
                <>
                  <LoadingSpinner size="sm" />
                  <span>Signing in...</span>
                </>
              ) : (
                <span>Sign In</span>
              )}
            </button>
          </form>

          {/* Footer link */}
          <div className="mt-6 pt-5 border-t border-[#e2e4e8] text-center text-sm text-[#656d76]">
            Don&apos;t have an account?{" "}
            <Link
              href="/register"
              className="text-blue-600 hover:text-blue-700 font-semibold"
            >
              Create one now &rarr;
            </Link>
          </div>
        </div>
      </div>
    </div>
  );
}
