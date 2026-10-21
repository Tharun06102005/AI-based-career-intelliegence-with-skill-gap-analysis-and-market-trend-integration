"use client";

import React, { useState, useEffect, useRef } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import Navbar from "../../components/Navbar";
import ScoreBar from "../../components/ui/ScoreBar";
import LoadingSpinner from "../../components/ui/LoadingSpinner";
import {
  isLoggedIn,
  getProfileId,
  getUserEmail,
  saveResumeId,
  getResumeId,
  getToken,
} from "../../lib/auth";
import { resumesApi, careersApi, gapsApi } from "../../lib/api";

const CAREER_EMOJIS: Record<string, string> = {
  "Software Engineer": "💻",
  "Backend Developer": "⚙️",
  "Frontend Developer": "🎨",
  "Full Stack Developer": "🚀",
  "Data Scientist": "📊",
  "Machine Learning Engineer": "🤖",
  "DevOps Engineer": "♾️",
  "Cloud Engineer": "☁️",
  "Data Engineer": "🗄️",
  "Product Manager": "🎯",
};

export default function DashboardPage() {
  const router = useRouter();
  const fileInputRef = useRef<HTMLInputElement>(null);

  const [loading, setLoading] = useState(true);
  const [profileId, setProfileId] = useState<string | null>(null);
  const [userName, setUserName] = useState("Candidate");

  // Resume state
  const [isDragging, setIsDragging] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [uploadedResume, setUploadedResume] = useState<{
    resume_id: string;
    skills_count: number;
    skills: Array<{ skill_name: string; confidence?: string }>;
  } | null>(null);
  const [resumeError, setResumeError] = useState<string | null>(null);

  // Careers state
  const [rankingLoading, setRankingLoading] = useState(false);
  const [careerRankings, setCareerRankings] = useState<
    Array<{
      career_id: number;
      career_name: string;
      total_score: number;
      components: {
        skill_match: number;
        evidence_strength: number;
        experience_alignment: number;
        education_alignment: number;
        market_demand: number;
      };
      demand_score: number;
    }>
  >([]);
  const [rankingError, setRankingError] = useState<string | null>(null);

  // Stats state
  const [stats, setStats] = useState({
    skillsDetected: 0,
    topCareer: "None",
    readiness: 0,
    skillsToLearn: 0,
  });

  useEffect(() => {
    if (!isLoggedIn()) {
      router.push("/login");
      return;
    }

    const pid = getProfileId();
    const email = getUserEmail();
    setProfileId(pid);
    if (email) {
      const rawName = email.split("@")[0];
      setUserName(rawName.charAt(0).toUpperCase() + rawName.slice(1));
    }

    const existingResumeId = getResumeId();
    if (existingResumeId) {
      resumesApi
        .getResume(existingResumeId)
        .then((res) => {
          setUploadedResume({
            resume_id: res.resume_id,
            skills_count: res.skills.length,
            skills: res.skills,
          });
          setStats((prev) => ({ ...prev, skillsDetected: res.skills.length }));
        })
        .catch(() => {});
    }

    if (pid) {
      loadCareerRankings(pid);
    } else {
      setLoading(false);
    }
  }, [router]);

  const loadCareerRankings = async (pid: string) => {
    setRankingLoading(true);
    setRankingError(null);
    try {
      const rankings = await careersApi.rankCareers(pid);
      setCareerRankings(rankings);

      if (rankings.length > 0) {
        const top = rankings[0];
        try {
          const gapReport = await gapsApi.getGapReport(pid, top.career_id);
          setStats((prev) => ({
            ...prev,
            topCareer: top.career_name,
            readiness: Math.round(gapReport.readiness),
            skillsToLearn: gapReport.missing_skills.length + gapReport.partial_skills.length,
          }));
        } catch {
          setStats((prev) => ({
            ...prev,
            topCareer: top.career_name,
            readiness: Math.round(top.total_score),
            skillsToLearn: 3,
          }));
        }
      }
    } catch (err: any) {
      console.warn("Could not load initial rankings:", err);
    } finally {
      setRankingLoading(false);
      setLoading(false);
    }
  };

  const handleFileUpload = async (file: File) => {
    if (!file) return;

    const validTypes = [
      "application/pdf",
      "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
      "application/msword",
    ];
    if (!validTypes.includes(file.type) && !file.name.match(/\.(pdf|docx|doc)$/i)) {
      setResumeError("Please upload a PDF or DOCX file.");
      return;
    }

    const token = getToken();
    if (!token) {
      setResumeError("Session expired. Please sign in again.");
      router.push("/login");
      return;
    }

    setResumeError(null);
    setUploading(true);

    try {
      const formData = new FormData();
      formData.append("file", file);

      const res = await resumesApi.uploadResume(formData, token);
      setUploadedResume(res);
      saveResumeId(res.resume_id);
      setStats((prev) => ({
        ...prev,
        skillsDetected: res.skills_count || res.skills?.length || 0,
      }));

      const pid = getProfileId();
      if (pid) {
        await loadCareerRankings(pid);
      }
    } catch (err: any) {
      setResumeError(err.message || "Failed to parse resume. Please try again.");
    } finally {
      setUploading(false);
    }
  };

  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(true);
  };

  const handleDragLeave = () => {
    setIsDragging(false);
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);
    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      handleFileUpload(e.dataTransfer.files[0]);
    }
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-[#F7F6F3]">
        <Navbar />
        <LoadingSpinner fullScreen text="Loading dashboard..." />
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-[#f8f9fb] text-[#1f2328] flex flex-col">
      <Navbar />

      <main className="flex-1 page-wrapper py-8 sm:py-10 space-y-8">
        {/* Welcome Text */}
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
          <div>
            <h1 className="text-2xl sm:text-3xl lg:text-4xl font-extrabold tracking-tight text-[#111827]">
              Good morning, {userName}
            </h1>
            <p className="text-sm sm:text-base text-[#656d76] mt-1.5">
              Your real-time career intelligence and role alignment metrics.
            </p>
          </div>

          <div className="flex items-center gap-2">
            <button
              onClick={() => {
                const pid = getProfileId();
                if (pid) loadCareerRankings(pid);
              }}
              disabled={rankingLoading}
              className="bg-white hover:bg-gray-50 text-[#1f2328] border border-[#d0d7de] px-4 py-2 rounded-xl text-sm font-semibold transition-all shadow-xs flex items-center gap-2"
            >
              <svg
                className={`w-4 h-4 text-[#656d76] ${rankingLoading ? "animate-spin" : ""}`}
                fill="none"
                viewBox="0 0 24 24"
                stroke="currentColor"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15"
                />
              </svg>
              <span>Refresh Scores</span>
            </button>
          </div>
        </div>

        {/* 4 Metric Cards with colored left border accent: minmax(220px, 1fr) */}
        <div
          style={{
            display: "grid",
            gridTemplateColumns: "repeat(auto-fit, minmax(240px, 1fr))",
            gap: "1.25rem",
          }}
        >
          {/* Card 1: Skills Detected (blue) */}
          <div className="bg-white border border-[#e2e4e8] border-l-4 border-l-blue-600 rounded-2xl p-6 shadow-xs">
            <span className="text-sm font-semibold text-[#656d76] block">
              Skills Detected
            </span>
            <div className="text-3xl sm:text-4xl font-extrabold text-[#111827] mt-2">
              {uploadedResume?.skills_count ?? stats.skillsDetected}
            </div>
            <span className="text-xs text-[#8c959f] mt-1.5 block">
              From parsed resume
            </span>
          </div>

          {/* Card 2: Top Career (green) */}
          <div className="bg-white border border-[#e2e4e8] border-l-4 border-l-emerald-600 rounded-2xl p-6 shadow-xs">
            <span className="text-sm font-semibold text-[#656d76] block">
              Top Career
            </span>
            <div className="text-2xl sm:text-3xl font-extrabold text-[#111827] mt-2 truncate" title={stats.topCareer}>
              {stats.topCareer}
            </div>
            <span className="text-xs text-emerald-700 font-semibold mt-1.5 block">
              Highest fit match
            </span>
          </div>

          {/* Card 3: Readiness (orange) */}
          <div className="bg-white border border-[#e2e4e8] border-l-4 border-l-amber-500 rounded-2xl p-6 shadow-xs">
            <span className="text-sm font-semibold text-[#656d76] block">
              Readiness
            </span>
            <div className="text-3xl sm:text-4xl font-extrabold text-amber-600 mt-2">
              {stats.readiness}%
            </div>
            <span className="text-xs text-[#8c959f] mt-1.5 block">
              Role readiness score
            </span>
          </div>

          {/* Card 4: Skills to Learn (purple) */}
          <div className="bg-white border border-[#e2e4e8] border-l-4 border-l-purple-600 rounded-2xl p-6 shadow-xs">
            <span className="text-sm font-semibold text-[#656d76] block">
              Skills to Learn
            </span>
            <div className="text-3xl sm:text-4xl font-extrabold text-purple-600 mt-2">
              {stats.skillsToLearn}
            </div>
            <span className="text-xs text-[#8c959f] mt-1.5 block">
              Identified gap areas
            </span>
          </div>
        </div>

        {/* Resume Upload Zone */}
        <section className="space-y-4">
          <div className="flex items-center justify-between">
            <h2 className="text-lg sm:text-xl font-bold text-[#111827]">
              Resume Upload & Extraction
            </h2>
            {uploadedResume && (
              <span className="text-xs sm:text-sm text-emerald-700 bg-emerald-50 border border-emerald-200 px-3 py-1 rounded-full font-semibold">
                Active Resume ({uploadedResume.skills_count} skills)
              </span>
            )}
          </div>

          <div
            onDragOver={handleDragOver}
            onDragLeave={handleDragLeave}
            onDrop={handleDrop}
            className={`bg-white border-2 border-dashed rounded-2xl p-8 sm:p-12 text-center transition-all shadow-xs ${
              isDragging
                ? "border-blue-600 bg-blue-50/50"
                : "border-[#d0d7de] hover:border-gray-400"
            }`}
          >
            <input
              type="file"
              ref={fileInputRef}
              accept=".pdf,.docx,.doc"
              onChange={(e) => {
                if (e.target.files && e.target.files[0]) {
                  handleFileUpload(e.target.files[0]);
                }
              }}
              className="hidden"
            />

            {uploading ? (
              <div className="py-6 space-y-3">
                <LoadingSpinner size="md" />
                <p className="text-sm font-semibold text-[#656d76]">
                  Analyzing resume and extracting skills with NLP...
                </p>
              </div>
            ) : (
              <div className="py-2 space-y-2">
                <div className="text-3xl mb-2">📄</div>
                <p className="text-base font-semibold text-[#111827]">
                  Drag and drop your resume here, or{" "}
                  <button
                    type="button"
                    onClick={() => fileInputRef.current?.click()}
                    className="text-blue-600 hover:text-blue-700 underline font-bold focus:outline-none"
                  >
                    browse files
                  </button>
                </p>
                <p className="text-sm text-[#656d76]">
                  PDF and DOCX formats supported (up to 10MB)
                </p>
                {resumeError && (
                  <p className="text-sm text-red-600 font-semibold pt-1">
                    {resumeError}
                  </p>
                )}
              </div>
            )}

            {/* After upload: show skills as simple gray tags */}
            {uploadedResume && uploadedResume.skills && uploadedResume.skills.length > 0 && (
              <div className="mt-8 pt-6 border-t border-[#e2e4e8] text-left">
                <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 mb-3">
                  <span className="text-sm font-bold text-[#1f2328]">
                    Detected Skills ({uploadedResume.skills.length})
                  </span>
                  <div className="flex items-center gap-4">
                    <Link
                      href="/assessments"
                      className="text-sm text-emerald-700 hover:underline font-bold"
                    >
                      Verify Skills &rarr;
                    </Link>
                    <Link
                      href="/ats"
                      className="text-sm text-blue-600 hover:underline font-semibold"
                    >
                      Check ATS &rarr;
                    </Link>
                  </div>
                </div>
                <div className="flex flex-wrap gap-2 max-h-40 overflow-y-auto pr-1">
                  {uploadedResume.skills.map((s: any, idx: number) => (
                    <span
                      key={idx}
                      className={`px-3 py-1 rounded-lg text-xs sm:text-sm font-medium flex items-center gap-1.5 ${
                        s.is_verified
                          ? "bg-emerald-50 text-emerald-700 border border-emerald-200 font-bold"
                          : "bg-gray-100 text-[#1f2328] border border-gray-200"
                      }`}
                    >
                      <span>{s.skill_name}</span>
                      {s.is_verified && <span title="Assessment Verified" className="text-emerald-600 font-bold">✓</span>}
                    </span>
                  ))}
                </div>
              </div>
            )}
          </div>
        </section>

        {/* 3 Upgraded Features Quick Launch Action Hub */}
        <section
          style={{
            display: "grid",
            gridTemplateColumns: "repeat(auto-fit, minmax(280px, 1fr))",
            gap: "1.25rem",
          }}
        >
          <Link
            href="/assessments"
            className="bg-white border border-[#e2e4e8] hover:border-blue-500 rounded-2xl p-6 shadow-xs hover:shadow-md transition-all group flex flex-col justify-between"
          >
            <div>
              <div className="flex items-center gap-2.5 mb-3">
                <span className="text-2xl">✅</span>
                <h3 className="text-base font-bold text-[#111827] group-hover:text-blue-600 transition-colors">
                  Skill Verification
                </h3>
              </div>
              <p className="text-sm text-[#4b5563] leading-relaxed">
                Take adaptive coding and conceptual assessments to upgrade your skills from resume-claimed to verified.
              </p>
            </div>
            <div className="pt-4 mt-2 text-sm font-bold text-blue-600 flex items-center gap-1">
              Start Assessment &rarr;
            </div>
          </Link>

          <Link
            href="/jobs"
            className="bg-white border border-[#e2e4e8] hover:border-blue-500 rounded-2xl p-6 shadow-xs hover:shadow-md transition-all group flex flex-col justify-between"
          >
            <div>
              <div className="flex items-center gap-2.5 mb-3">
                <span className="text-2xl">💼</span>
                <h3 className="text-base font-bold text-[#111827] group-hover:text-blue-600 transition-colors">
                  Opportunity Matching
                </h3>
              </div>
              <p className="text-sm text-[#4b5563] leading-relaxed">
                Explore real jobs and internships scored against your profile with verified competency bonuses.
              </p>
            </div>
            <div className="pt-4 mt-2 text-sm font-bold text-blue-600 flex items-center gap-1">
              Find Job Matches &rarr;
            </div>
          </Link>

          <Link
            href="/interview"
            className="bg-white border border-[#e2e4e8] hover:border-blue-500 rounded-2xl p-6 shadow-xs hover:shadow-md transition-all group flex flex-col justify-between"
          >
            <div>
              <div className="flex items-center gap-2.5 mb-3">
                <span className="text-2xl">🎙️</span>
                <h3 className="text-base font-bold text-[#111827] group-hover:text-blue-600 transition-colors">
                  AI Mock Interview
                </h3>
              </div>
              <p className="text-sm text-[#4b5563] leading-relaxed">
                Practice role-specific technical rounds and resume project defense with 5-dimension rubric critiques.
              </p>
            </div>
            <div className="pt-4 mt-2 text-sm font-bold text-blue-600 flex items-center gap-1">
              Practice Interview &rarr;
            </div>
          </Link>
        </section>

        {/* Career Cards Section */}
        <section className="space-y-4">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2">
            <div>
              <h2 className="text-lg sm:text-xl font-bold text-[#111827]">
                Target Career Alignments
              </h2>
              <p className="text-sm text-[#656d76]">
                Deterministic mathematical scoring based on skill coverage, evidence depth, and market demand.
              </p>
            </div>

            <Link
              href="/ats"
              className="text-sm font-semibold text-blue-600 hover:text-blue-700"
            >
              Test with Job Description &rarr;
            </Link>
          </div>

          {rankingError && (
            <div className="p-3.5 rounded-xl bg-red-50 border border-red-200 text-red-700 text-sm">
              {rankingError}
            </div>
          )}

          {rankingLoading ? (
            <div className="py-14">
              <LoadingSpinner size="lg" text="Computing deterministic career rankings..." />
            </div>
          ) : careerRankings.length === 0 ? (
            <div className="bg-white border border-[#e2e4e8] rounded-2xl p-12 text-center space-y-3 shadow-xs">
              <div className="text-3xl">🔍</div>
              <h3 className="text-base font-bold text-[#111827]">
                No Career Matches Computed Yet
              </h3>
              <p className="text-sm text-[#656d76] max-w-md mx-auto">
                Upload your resume above to calculate role alignments, evidence strengths, and skill gaps across tech careers.
              </p>
            </div>
          ) : (
            <div
              style={{
                display: "grid",
                gridTemplateColumns: "repeat(auto-fit, minmax(310px, 1fr))",
                gap: "1.25rem",
              }}
            >
              {careerRankings.map((c) => {
                const emoji = CAREER_EMOJIS[c.career_name] || "💼";
                const fitScore = Math.round(c.total_score);

                return (
                  <div
                    key={c.career_id}
                    className="bg-white border border-[#e2e4e8] rounded-2xl p-6 shadow-xs hover:border-blue-400 hover:shadow-md transition-all flex flex-col justify-between"
                  >
                    <div>
                      {/* Top Header: Simple score badge | Career name */}
                      <div className="flex items-start justify-between gap-3">
                        <div className="flex items-center gap-3">
                          <span className="text-2xl">{emoji}</span>
                          <div>
                            <h3 className="text-base font-bold text-[#111827] leading-snug">
                              {c.career_name}
                            </h3>
                            <span className="text-xs text-[#656d76] font-medium">
                              Market Demand: {(c.demand_score * 100).toFixed(0)}%
                            </span>
                          </div>
                        </div>

                        {/* Simple Score Badge */}
                        <span className="px-3 py-1 rounded-lg bg-blue-50 text-blue-700 border border-blue-200 text-sm font-bold shrink-0">
                          {fitScore}%
                        </span>
                      </div>

                      {/* Score Bars */}
                      <div className="mt-5 pt-4 border-t border-[#e2e4e8] space-y-3">
                        <ScoreBar
                          label="Skill Match"
                          value={c.components.skill_match * 100}
                          size="md"
                          color="blue"
                        />
                        <ScoreBar
                          label="Evidence Strength"
                          value={c.components.evidence_strength * 100}
                          size="md"
                          color="purple"
                        />
                        <ScoreBar
                          label="Experience"
                          value={c.components.experience_alignment * 100}
                          size="md"
                          color="emerald"
                        />
                      </div>
                    </div>

                    {/* "View Gaps" and "Roadmap" text links */}
                    <div className="mt-6 pt-4 border-t border-[#e2e4e8] flex items-center justify-between">
                      <Link
                        href={`/gaps?career=${c.career_id}`}
                        className="text-sm font-bold text-blue-600 hover:text-blue-700"
                      >
                        View Gaps &rarr;
                      </Link>
                      <Link
                        href={`/roadmap?career=${c.career_id}`}
                        className="text-sm font-bold text-blue-600 hover:text-blue-700"
                      >
                        Learning Roadmap &rarr;
                      </Link>
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </section>
      </main>
    </div>
  );
}
