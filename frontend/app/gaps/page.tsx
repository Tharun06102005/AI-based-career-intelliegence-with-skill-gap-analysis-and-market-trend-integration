"use client";

import React, { useState, useEffect, Suspense } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import Link from "next/link";
import Navbar from "../../components/Navbar";
import SkillBadge from "../../components/ui/SkillBadge";
import ScoreBar from "../../components/ui/ScoreBar";
import LoadingSpinner from "../../components/ui/LoadingSpinner";
import { isLoggedIn, getProfileId } from "../../lib/auth";
import { careersApi, gapsApi } from "../../lib/api";

function SkillGapsContent() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const initialCareerParam = searchParams.get("career");

  const [loading, setLoading] = useState(true);
  const [reportLoading, setReportLoading] = useState(false);
  const [profileId, setProfileId] = useState<string | null>(null);

  const [careers, setCareers] = useState<
    Array<{ id: number; name: string; description: string }>
  >([]);
  const [selectedCareerId, setSelectedCareerId] = useState<number>(1);

  const [gapReport, setGapReport] = useState<{
    career_name: string;
    readiness: number;
    matched_skills: string[];
    missing_skills: string[];
    partial_skills: string[];
    skill_gaps: Array<{
      skill_name: string;
      status: "Missing" | "Partially Matched";
      importance: number;
      required: boolean;
    }>;
  } | null>(null);

  const [filterTab, setFilterTab] = useState<"all" | "matched" | "partial" | "missing">("all");
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!isLoggedIn()) {
      router.push("/login");
      return;
    }

    const pid = getProfileId();
    setProfileId(pid);

    careersApi
      .getCareers()
      .then((data) => {
        setCareers(data);
        const targetId = initialCareerParam
          ? parseInt(initialCareerParam, 10)
          : data.length > 0
          ? data[0].id
          : 1;
        setSelectedCareerId(targetId);

        if (pid) {
          fetchReport(pid, targetId);
        } else {
          setLoading(false);
        }
      })
      .catch(() => {
        setError("Failed to load careers list.");
        setLoading(false);
      });
  }, [router, initialCareerParam]);

  const fetchReport = async (pid: string, careerId: number) => {
    setReportLoading(true);
    setError(null);
    try {
      const report = await gapsApi.getGapReport(pid, careerId);
      setGapReport(report);
    } catch (err: any) {
      setError(err.message || "Failed to fetch skill gap analysis.");
    } finally {
      setReportLoading(false);
      setLoading(false);
    }
  };

  const handleCareerChange = (newCareerId: number) => {
    setSelectedCareerId(newCareerId);
    if (profileId) {
      fetchReport(profileId, newCareerId);
    }
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-[#F7F6F3]">
        <Navbar />
        <LoadingSpinner fullScreen text="Loading Skill Gaps..." />
      </div>
    );
  }

  const readinessScore = gapReport ? Math.round(gapReport.readiness) : 0;

  return (
    <div className="min-h-screen bg-[#F7F6F3] text-[#37352F] flex flex-col">
      <Navbar />

      <main className="flex-1 page-wrapper py-8 sm:py-10 space-y-8">
        {/* Clean Page Header with Career Selector */}
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-6 border-b border-[#e2e4e8]">
          <div>
            <h1 className="text-2xl sm:text-3xl lg:text-4xl font-extrabold tracking-tight text-[#111827]">
              Skill Gap & Readiness Analysis
            </h1>
            <p className="text-sm sm:text-base text-[#656d76] mt-1.5">
              Review your matched competencies and address identified gap areas with mathematical precision.
            </p>
          </div>

          {/* Career Selector Dropdown */}
          <div className="w-full sm:w-72">
            <label className="block text-xs font-semibold text-[#656d76] mb-1.5">
              Target Career Role:
            </label>
            <div className="relative">
              <select
                value={selectedCareerId}
                onChange={(e) => handleCareerChange(Number(e.target.value))}
                className="w-full bg-white border border-[#d0d7de] rounded-xl px-4 py-2.5 text-sm text-[#1f2328] font-semibold focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-600 transition-all cursor-pointer appearance-none shadow-xs"
              >
                {careers.map((career) => (
                  <option key={career.id} value={career.id}>
                    {career.name}
                  </option>
                ))}
              </select>
              <div className="absolute inset-y-0 right-0 flex items-center px-2.5 pointer-events-none text-[#6B6B6B]">
                <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
                </svg>
              </div>
            </div>
          </div>
        </div>

        {error && (
          <div className="p-3 rounded-md bg-[#FDE8E8] border border-[#F8B4B4] text-[#9B1C1C] text-xs">
            {error}
          </div>
        )}

        {reportLoading ? (
          <div className="py-16">
            <LoadingSpinner size="lg" text="Analyzing skill gaps..." />
          </div>
        ) : !gapReport ? (
          <div className="bg-white border border-[#E9E9E7] rounded-lg p-10 text-center space-y-2 shadow-[0_1px_3px_rgba(0,0,0,0.08)]">
            <div className="text-2xl">⚠️</div>
            <h3 className="text-sm font-semibold text-[#37352F]">
              No Gap Report Available
            </h3>
            <p className="text-xs text-[#6B6B6B]">
              Please upload a resume on the Dashboard to calculate skill readiness.
            </p>
          </div>
        ) : (
          /* Simple Two Column Layout */
          <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 items-start">
            {/* Left Column: Skill badges (green / red / yellow pills) */}
            <div className="lg:col-span-7 bg-white border border-[#E9E9E7] rounded-lg p-6 shadow-[0_1px_3px_rgba(0,0,0,0.08)] space-y-5">
              <div className="flex items-center justify-between border-b border-[#E9E9E7] pb-3">
                <div>
                  <h2 className="text-sm font-semibold text-[#37352F]">
                    Skill Breakdown
                  </h2>
                  <span className="text-[11px] text-[#6B6B6B]">
                    For {gapReport.career_name}
                  </span>
                </div>

                {/* Filter Tabs */}
                <div className="flex gap-1 text-xs">
                  <button
                    onClick={() => setFilterTab("all")}
                    className={`px-2 py-1 rounded text-xs transition-colors ${
                      filterTab === "all"
                        ? "bg-[#F7F6F3] text-[#37352F] font-semibold"
                        : "text-[#6B6B6B] hover:text-[#37352F]"
                    }`}
                  >
                    All ({gapReport.matched_skills.length + gapReport.partial_skills.length + gapReport.missing_skills.length})
                  </button>
                  <button
                    onClick={() => setFilterTab("matched")}
                    className={`px-2 py-1 rounded text-xs transition-colors ${
                      filterTab === "matched"
                        ? "bg-[#EBF5EE] text-[#1F7A4C] font-semibold"
                        : "text-[#6B6B6B] hover:text-[#1F7A4C]"
                    }`}
                  >
                    Matched ({gapReport.matched_skills.length})
                  </button>
                  <button
                    onClick={() => setFilterTab("partial")}
                    className={`px-2 py-1 rounded text-xs transition-colors ${
                      filterTab === "partial"
                        ? "bg-[#FEF3C7] text-[#92400E] font-semibold"
                        : "text-[#6B6B6B] hover:text-[#92400E]"
                    }`}
                  >
                    Partial ({gapReport.partial_skills.length})
                  </button>
                  <button
                    onClick={() => setFilterTab("missing")}
                    className={`px-2 py-1 rounded text-xs transition-colors ${
                      filterTab === "missing"
                        ? "bg-[#FDE8E8] text-[#9B1C1C] font-semibold"
                        : "text-[#6B6B6B] hover:text-[#9B1C1C]"
                    }`}
                  >
                    Missing ({gapReport.missing_skills.length})
                  </button>
                </div>
              </div>

              {/* Badges Display */}
              <div className="space-y-4">
                {/* Matched (Green pills) */}
                {(filterTab === "all" || filterTab === "matched") &&
                  gapReport.matched_skills.length > 0 && (
                    <div>
                      <span className="text-xs font-semibold text-[#1F7A4C] block mb-2">
                        Matched Skills ({gapReport.matched_skills.length})
                      </span>
                      <div className="flex flex-wrap gap-1.5">
                        {gapReport.matched_skills.map((skill) => (
                          <SkillBadge
                            key={skill}
                            skill={skill}
                            type="matched"
                            size="md"
                          />
                        ))}
                      </div>
                    </div>
                  )}

                {/* Partial (Yellow pills) */}
                {(filterTab === "all" || filterTab === "partial") &&
                  gapReport.partial_skills.length > 0 && (
                    <div>
                      <span className="text-xs font-semibold text-[#92400E] block mb-2">
                        Partially Matched Skills ({gapReport.partial_skills.length})
                      </span>
                      <div className="flex flex-wrap gap-1.5">
                        {gapReport.partial_skills.map((skill) => (
                          <SkillBadge
                            key={skill}
                            skill={skill}
                            type="partial"
                            size="md"
                          />
                        ))}
                      </div>
                    </div>
                  )}

                {/* Missing (Red pills) */}
                {(filterTab === "all" || filterTab === "missing") &&
                  gapReport.missing_skills.length > 0 && (
                    <div>
                      <span className="text-xs font-semibold text-[#9B1C1C] block mb-2">
                        Missing Skills ({gapReport.missing_skills.length})
                      </span>
                      <div className="flex flex-wrap gap-1.5">
                        {gapReport.missing_skills.map((skill) => (
                          <SkillBadge
                            key={skill}
                            skill={skill}
                            type="missing"
                            size="md"
                          />
                        ))}
                      </div>
                    </div>
                  )}
              </div>
            </div>

            {/* Right Column: Readiness percentage with clean progress bar */}
            <div className="lg:col-span-5 space-y-4">
              {/* Readiness Card */}
              <div className="bg-white border border-[#E9E9E7] rounded-lg p-6 shadow-[0_1px_3px_rgba(0,0,0,0.08)] space-y-4">
                <span className="text-xs font-semibold uppercase tracking-wider text-[#6B6B6B] block">
                  Readiness Percentage
                </span>

                <div>
                  <div className="text-4xl font-bold text-[#37352F]">
                    {readinessScore}%
                  </div>
                  <p className="text-xs text-[#6B6B6B] mt-1">
                    Based on required skill coverage and evidence confidence.
                  </p>
                </div>

                {/* Clean Progress Bar */}
                <div className="pt-2">
                  <ScoreBar
                    label="Career Fit"
                    value={readinessScore}
                    size="lg"
                    color={
                      readinessScore >= 75
                        ? "emerald"
                        : readinessScore >= 50
                        ? "amber"
                        : "rose"
                    }
                  />
                </div>

                {/* Gaps Summary Stats */}
                <div className="pt-4 border-t border-[#E9E9E7] grid grid-cols-2 gap-3 text-center">
                  <div className="p-3 bg-[#F7F6F3] rounded-md">
                    <span className="text-[11px] text-[#6B6B6B] block">Matched</span>
                    <span className="text-lg font-bold text-[#1F7A4C]">
                      {gapReport.matched_skills.length}
                    </span>
                  </div>
                  <div className="p-3 bg-[#F7F6F3] rounded-md">
                    <span className="text-[11px] text-[#6B6B6B] block">Gaps to Close</span>
                    <span className="text-lg font-bold text-[#9B1C1C]">
                      {gapReport.missing_skills.length + gapReport.partial_skills.length}
                    </span>
                  </div>
                </div>

                <div className="pt-2">
                  <Link
                    href={`/roadmap?career=${selectedCareerId}`}
                    className="w-full inline-flex items-center justify-center bg-[#2383E2] hover:bg-[#1A73E8] text-white px-4 py-2 rounded-md text-xs font-medium transition-colors"
                  >
                    View Learning Roadmap &rarr;
                  </Link>
                </div>
              </div>

              {/* Priority Gaps List */}
              {gapReport.skill_gaps.length > 0 && (
                <div className="bg-white border border-[#E9E9E7] rounded-lg p-5 shadow-[0_1px_3px_rgba(0,0,0,0.08)] space-y-3">
                  <div className="flex items-center justify-between border-b border-[#E9E9E7] pb-2">
                    <h3 className="text-xs font-semibold text-[#37352F]">
                      Priority Missing Skills
                    </h3>
                    <span className="text-[11px] text-[#6B6B6B]">Importance</span>
                  </div>

                  <div className="space-y-2.5">
                    {gapReport.skill_gaps.slice(0, 5).map((gap) => (
                      <div key={gap.skill_name} className="space-y-1">
                        <div className="flex justify-between items-center text-xs">
                          <span className="font-medium text-[#37352F]">
                            {gap.skill_name}
                          </span>
                          <span
                            className={`text-[11px] font-medium ${
                              gap.status === "Missing"
                                ? "text-[#9B1C1C]"
                                : "text-[#92400E]"
                            }`}
                          >
                            {gap.status} {gap.required && "(Required)"}
                          </span>
                        </div>
                        <ScoreBar
                          label=""
                          value={gap.importance * 100}
                          size="sm"
                          showValue={false}
                          color={gap.status === "Missing" ? "rose" : "amber"}
                        />
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          </div>
        )}
      </main>
    </div>
  );
}

export default function SkillGapsPage() {
  return (
    <Suspense fallback={<LoadingSpinner fullScreen text="Loading Skill Gaps..." />}>
      <SkillGapsContent />
    </Suspense>
  );
}
