"use client";

import React, { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import Navbar from "../../components/Navbar";
import LoadingSpinner from "../../components/ui/LoadingSpinner";
import SkillBadge from "../../components/ui/SkillBadge";
import ScoreBar from "../../components/ui/ScoreBar";
import { isLoggedIn, getResumeId, getToken } from "../../lib/auth";
import { resumesApi, atsCheck } from "../../lib/api";

const SAMPLE_JOB_DESCRIPTION = `Senior Full Stack Software Engineer

About the Role:
We are seeking an experienced Full Stack Engineer to lead the architecture and development of scalable cloud applications. You will collaborate across cross-functional teams to design RESTful APIs, deploy microservices, and build intuitive user interfaces.

Requirements & Qualifications:
• 4+ years of professional software engineering experience.
• Strong proficiency in Python, TypeScript, and React.
• Hands-on experience with Docker, Kubernetes, and AWS cloud infrastructure.
• Deep understanding of SQL, PostgreSQL, database modeling, and Redis caching.
• Experience architecting CI/CD pipelines, Git workflows, and automated testing suites.
• Solid background in Microservices architecture, REST APIs, and system scalability.
• Excellent communication and Agile collaboration skills.`;

export default function ATSCheckerPage() {
  const router = useRouter();

  const [loading, setLoading] = useState(true);
  const [calculating, setCalculating] = useState(false);
  const [resumeId, setResumeId] = useState<string | null>(null);

  // Resume content
  const [resumeFilename, setResumeFilename] = useState<string | null>(null);
  const [resumeText, setResumeText] = useState("");
  const [resumeSkills, setResumeSkills] = useState<string[]>([]);

  // Job Description content
  const [jobDescription, setJobDescription] = useState("");

  // Results
  const [atsResult, setAtsResult] = useState<{
    ats_score: number;
    match_percentage: number;
    matched_keywords: string[];
    missing_keywords: string[];
    recommendations: string[];
  } | null>(null);

  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!isLoggedIn()) {
      router.push("/login");
      return;
    }

    const savedResumeId = getResumeId();
    setResumeId(savedResumeId);

    if (savedResumeId) {
      resumesApi
        .getResume(savedResumeId)
        .then((res) => {
          setResumeFilename(res.filename);
          setResumeSkills(res.skills.map((s) => s.skill_name));

          // Combine sections into plain text for display
          const sectionsText = Object.entries(res.sections || {})
            .map(([title, body]) => `--- ${title.toUpperCase()} ---\n${body}`)
            .join("\n\n");

          setResumeText(sectionsText);
        })
        .catch((err) => {
          console.warn("Could not load resume text:", err);
        })
        .finally(() => {
          setLoading(false);
        });
    } else {
      setLoading(false);
    }
  }, [router]);

  const handleCalculateScore = async () => {
    if (!jobDescription.trim()) {
      setError("Please paste a job description to calculate the ATS score.");
      return;
    }

    if (!resumeText.trim() && !resumeId) {
      setError("Please upload a resume on the Dashboard or paste your resume text on the left.");
      return;
    }

    setCalculating(true);
    setError(null);

    try {
      const token = getToken() || undefined;
      const result = await atsCheck(
        resumeId || null,
        jobDescription,
        token,
        resumeText
      );
      setAtsResult(result);
    } catch (err: any) {
      setError(err.message || "Failed to calculate ATS score. Please try again.");
    } finally {
      setCalculating(false);
    }
  };

  const loadSampleJD = () => {
    setJobDescription(SAMPLE_JOB_DESCRIPTION);
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-[#F7F6F3]">
        <Navbar />
        <LoadingSpinner fullScreen text="Loading ATS Score Checker..." />
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-[#f8f9fb] text-[#1f2328] flex flex-col">
      <Navbar />

      <main className="flex-1 page-wrapper py-8 sm:py-10 space-y-8">
        {/* Page Header */}
        <div className="pb-4 border-b border-[#e2e4e8]">
          <h1 className="text-2xl sm:text-3xl lg:text-4xl font-extrabold tracking-tight text-[#111827]">
            ATS Score Checker
          </h1>
          <p className="text-sm sm:text-base text-[#656d76] mt-1.5">
            Evaluate your resume against real job descriptions to measure keyword alignment and ATS compatibility.
          </p>
        </div>

        {error && (
          <div className="p-3.5 rounded-xl bg-red-50 border border-red-200 text-red-700 text-sm">
            {error}
          </div>
        )}

        {/* Two Column Layout: Left Resume Display | Right Job Description */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6 items-start">
          {/* Left Column: Resume Text Display */}
          <div className="bg-white border border-[#e2e4e8] rounded-2xl p-6 shadow-xs space-y-4">
            <div className="flex items-center justify-between border-b border-[#e2e4e8] pb-3">
              <div>
                <h2 className="text-base font-bold text-[#111827]">
                  Resume Content
                </h2>
                <span className="text-xs text-[#656d76]">
                  {resumeFilename ? `File: ${resumeFilename}` : "Editable text box"}
                </span>
              </div>

              {resumeId ? (
                <span className="text-[11px] text-[#1F7A4C] bg-[#EBF5EE] border border-[#C6E7D2] px-2 py-0.5 rounded-full font-medium">
                  {resumeSkills.length} skills parsed
                </span>
              ) : (
                <Link
                  href="/dashboard"
                  className="text-xs text-[#2383E2] hover:underline font-medium"
                >
                  Upload file &rarr;
                </Link>
              )}
            </div>

            <div>
              <label className="block text-[11px] font-medium text-[#6B6B6B] mb-1.5">
                Resume Text (from parsed upload or paste custom):
              </label>
              <textarea
                value={resumeText}
                onChange={(e) => setResumeText(e.target.value)}
                placeholder="Paste your resume plain text here or upload a resume from the Dashboard..."
                rows={14}
                className="w-full bg-[#F7F6F3] border border-[#E9E9E7] rounded-md p-3 text-xs text-[#37352F] placeholder-[#9B9A97] focus:outline-none focus:border-[#2383E2] font-mono leading-relaxed resize-y"
              />
            </div>

            {resumeSkills.length > 0 && (
              <div>
                <span className="text-[11px] font-medium text-[#6B6B6B] block mb-1">
                  Extracted Skills from Resume:
                </span>
                <div className="flex flex-wrap gap-1 max-h-24 overflow-y-auto pr-1">
                  {resumeSkills.slice(0, 15).map((skill, idx) => (
                    <span
                      key={idx}
                      className="px-2 py-0.5 rounded bg-[#F1F1EF] text-[#37352F] border border-[#E3E2DE] text-[11px] font-medium"
                    >
                      {skill}
                    </span>
                  ))}
                  {resumeSkills.length > 15 && (
                    <span className="text-[11px] text-[#6B6B6B] self-center pl-1">
                      +{resumeSkills.length - 15} more
                    </span>
                  )}
                </div>
              </div>
            )}
          </div>

          {/* Right Column: Job Description Textarea */}
          <div className="bg-white border border-[#E9E9E7] rounded-lg p-5 shadow-[0_1px_3px_rgba(0,0,0,0.08)] space-y-3">
            <div className="flex items-center justify-between border-b border-[#E9E9E7] pb-2.5">
              <div>
                <h2 className="text-sm font-semibold text-[#37352F]">
                  Target Job Description
                </h2>
                <span className="text-[11px] text-[#6B6B6B]">
                  Paste the requirements & responsibilities
                </span>
              </div>

              <button
                type="button"
                onClick={loadSampleJD}
                className="text-xs text-[#2383E2] hover:underline font-medium"
              >
                Insert Sample JD
              </button>
            </div>

            <div>
              <label className="block text-[11px] font-medium text-[#6B6B6B] mb-1.5">
                Paste Job Description:
              </label>
              <textarea
                value={jobDescription}
                onChange={(e) => setJobDescription(e.target.value)}
                placeholder="Paste the target job description here (responsibilities, required tech stack, qualifications)..."
                rows={14}
                className="w-full bg-[#FFFFFF] border border-[#E9E9E7] rounded-md p-3 text-xs text-[#37352F] placeholder-[#9B9A97] focus:outline-none focus:border-[#2383E2] leading-relaxed resize-y"
              />
            </div>

            <div className="flex items-center justify-between text-[11px] text-[#6B6B6B]">
              <span>{jobDescription.length} characters</span>
              <span>Extracts required keywords automatically</span>
            </div>
          </div>
        </div>

        {/* Calculate ATS Score Button */}
        <div className="flex justify-center pt-1">
          <button
            onClick={handleCalculateScore}
            disabled={calculating}
            className="bg-[#2383E2] hover:bg-[#1A73E8] text-white px-8 py-2.5 rounded-md text-xs font-medium transition-colors disabled:opacity-50 flex items-center gap-2 shadow-[0_1px_2px_rgba(0,0,0,0.05)]"
          >
            {calculating ? (
              <>
                <LoadingSpinner size="sm" />
                <span>Analyzing ATS Keywords...</span>
              </>
            ) : (
              <>
                <span>📄</span>
                <span>Calculate ATS Score</span>
              </>
            )}
          </button>
        </div>

        {/* Results Section */}
        {atsResult && (
          <div className="bg-white border border-[#E9E9E7] rounded-lg p-6 shadow-[0_1px_3px_rgba(0,0,0,0.08)] space-y-6">
            <div className="border-b border-[#E9E9E7] pb-3">
              <h2 className="text-base font-semibold text-[#37352F]">
                ATS Compatibility Report
              </h2>
              <p className="text-xs text-[#6B6B6B] mt-0.5">
                Detailed keyword match and optimization recommendations for this job description.
              </p>
            </div>

            {/* Score Overview Cards */}
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              {/* Overall ATS Score as large number */}
              <div className="bg-[#F7F6F3] border border-[#E9E9E7] rounded-lg p-5 text-center">
                <span className="text-xs font-medium text-[#6B6B6B] uppercase tracking-wider block">
                  Overall ATS Score
                </span>
                <div className="text-5xl font-bold text-[#37352F] mt-2">
                  {atsResult.ats_score}
                  <span className="text-xl font-normal text-[#6B6B6B]">/100</span>
                </div>
                <div className="mt-3 max-w-xs mx-auto">
                  <ScoreBar
                    label=""
                    value={atsResult.ats_score}
                    size="sm"
                    showValue={false}
                    color={
                      atsResult.ats_score >= 80
                        ? "emerald"
                        : atsResult.ats_score >= 60
                        ? "blue"
                        : "amber"
                    }
                  />
                </div>
              </div>

              {/* Keyword Match Percentage */}
              <div className="bg-[#F7F6F3] border border-[#E9E9E7] rounded-lg p-5 text-center">
                <span className="text-xs font-medium text-[#6B6B6B] uppercase tracking-wider block">
                  Keyword Match Rate
                </span>
                <div className="text-5xl font-bold text-[#2383E2] mt-2">
                  {atsResult.match_percentage}%
                </div>
                <span className="text-xs text-[#6B6B6B] mt-2 block">
                  {atsResult.matched_keywords.length} of{" "}
                  {atsResult.matched_keywords.length + atsResult.missing_keywords.length} JD
                  keywords matched
                </span>
              </div>
            </div>

            {/* Skills Found (Green badges) & Missing (Red badges) */}
            <div className="grid grid-cols-1 md:grid-cols-2 gap-5 pt-2">
              {/* Skills found in JD: green badges */}
              <div className="space-y-2.5">
                <div className="flex items-center justify-between">
                  <span className="text-xs font-semibold text-[#1F7A4C] flex items-center gap-1.5">
                    <span className="w-2 h-2 rounded-full bg-[#1F7A4C]" />
                    Skills Found in JD ({atsResult.matched_keywords.length})
                  </span>
                  <span className="text-[11px] text-[#6B6B6B]">Included in resume</span>
                </div>

                <div className="p-3 bg-[#F7F6F3] border border-[#E9E9E7] rounded-md min-h-[60px] flex flex-wrap gap-1.5">
                  {atsResult.matched_keywords.length === 0 ? (
                    <span className="text-xs text-[#9B9A97] italic self-center">
                      No matching keywords found.
                    </span>
                  ) : (
                    atsResult.matched_keywords.map((skill) => (
                      <SkillBadge
                        key={skill}
                        skill={skill}
                        type="matched"
                        size="sm"
                      />
                    ))
                  )}
                </div>
              </div>

              {/* Skills missing from JD: red badges */}
              <div className="space-y-2.5">
                <div className="flex items-center justify-between">
                  <span className="text-xs font-semibold text-[#9B1C1C] flex items-center gap-1.5">
                    <span className="w-2 h-2 rounded-full bg-[#9B1C1C]" />
                    Skills Missing from JD ({atsResult.missing_keywords.length})
                  </span>
                  <span className="text-[11px] text-[#6B6B6B]">Required by job</span>
                </div>

                <div className="p-3 bg-[#F7F6F3] border border-[#E9E9E7] rounded-md min-h-[60px] flex flex-wrap gap-1.5">
                  {atsResult.missing_keywords.length === 0 ? (
                    <span className="text-xs text-[#1F7A4C] font-medium self-center">
                      ✓ Excellent! No missing keywords detected.
                    </span>
                  ) : (
                    atsResult.missing_keywords.map((skill) => (
                      <SkillBadge
                        key={skill}
                        skill={skill}
                        type="missing"
                        size="sm"
                      />
                    ))
                  )}
                </div>
              </div>
            </div>

            {/* Recommendations: bullet list */}
            {atsResult.recommendations && atsResult.recommendations.length > 0 && (
              <div className="pt-3 border-t border-[#E9E9E7] space-y-2">
                <span className="text-xs font-semibold text-[#37352F] uppercase tracking-wider block">
                  Optimization Recommendations:
                </span>
                <ul className="space-y-1.5 text-xs text-[#37352F] pl-4 list-disc leading-relaxed">
                  {atsResult.recommendations.map((rec, idx) => (
                    <li key={idx} className="text-[#37352F]">
                      {rec}
                    </li>
                  ))}
                </ul>
              </div>
            )}
          </div>
        )}
      </main>
    </div>
  );
}
