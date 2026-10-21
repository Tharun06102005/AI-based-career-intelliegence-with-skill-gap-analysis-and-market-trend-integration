"use client";

import React, { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { Navbar } from "../../components/Navbar";
import LoadingSpinner from "../../components/ui/LoadingSpinner";
import { isLoggedIn, getProfileId } from "../../lib/auth";
import { assessmentsApi } from "../../lib/api";

const SKILL_ICONS: Record<string, string> = {
  Python: "🐍",
  SQL: "🗄️",
  JavaScript: "⚡",
  React: "⚛️",
  OOP: "🧩",
  Docker: "🐳",
  Git: "🌱",
  Java: "☕",
  TypeScript: "🔷",
};

export default function AssessmentsPage() {
  const router = useRouter();
  const [profileId, setProfileId] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [skills, setSkills] = useState<
    Array<{
      skill_name: string;
      total_questions: number;
      difficulties: string[];
      question_types: string[];
    }>
  >([]);
  const [history, setHistory] = useState<any[]>([]);
  const [selectedDifficulty, setSelectedDifficulty] = useState<string>("Intermediate");
  const [startingSkill, setStartingSkill] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!isLoggedIn()) {
      router.push("/login");
      return;
    }

    const pid = getProfileId();
    setProfileId(pid);

    Promise.all([
      assessmentsApi.getSkills().catch(() => []),
      pid ? assessmentsApi.getHistory(pid).catch(() => ({ attempts: [] })) : Promise.resolve({ attempts: [] }),
    ])
      .then(([skillsRes, historyRes]) => {
        setSkills(skillsRes);
        setHistory(historyRes.attempts || []);
      })
      .catch((err) => {
        setError(err.message || "Failed to load assessments.");
      })
      .finally(() => {
        setLoading(false);
      });
  }, [router]);

  const handleStartAssessment = async (skillName: string) => {
    if (!profileId) return;
    setStartingSkill(skillName);
    setError(null);

    try {
      const res = await assessmentsApi.startAssessment(profileId, skillName, selectedDifficulty);
      router.push(`/assessments/${res.attempt_id}`);
    } catch (err: any) {
      setError(err.message || `Failed to start ${skillName} assessment.`);
      setStartingSkill(null);
    }
  };

  return (
    <div className="min-h-screen bg-[#F7F6F3] text-[#37352F]">
      <Navbar />

      <main className="page-wrapper py-8 sm:py-10 space-y-8">
        {/* Header */}
        <div className="pb-6 border-b border-[#e2e4e8]">
          <div className="flex flex-col lg:flex-row lg:items-center lg:justify-between gap-6">
            <div>
              <div className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full bg-blue-50 text-blue-700 text-xs font-semibold mb-2 border border-blue-200">
                <span className="w-1.5 h-1.5 rounded-full bg-blue-600" />
                <span>Adaptive Verification Engine</span>
              </div>
              <h1 className="text-2xl sm:text-3xl lg:text-4xl font-extrabold tracking-tight text-[#111827]">
                Skill Verification Assessments
              </h1>
              <p className="text-sm sm:text-base text-[#656d76] mt-1.5 max-w-3xl">
                Verify your claimed technical competencies through adaptive multiple-choice, output prediction, and sandboxed coding exercises. Verified skills directly boost your CareerFit evidence score.
              </p>
            </div>

            {/* Difficulty Selector */}
            <div className="bg-white p-1.5 rounded-xl border border-[#e2e4e8] flex items-center shadow-xs shrink-0">
              <span className="text-xs text-[#656d76] px-3 font-semibold">Difficulty:</span>
              {["Beginner", "Intermediate", "Advanced"].map((level) => (
                <button
                  key={level}
                  onClick={() => setSelectedDifficulty(level)}
                  className={`px-4 py-1.5 text-xs sm:text-sm font-semibold rounded-lg transition-all ${
                    selectedDifficulty === level
                      ? "bg-blue-600 text-white shadow-xs"
                      : "text-[#656d76] hover:text-[#111827]"
                  }`}
                >
                  {level}
                </button>
              ))}
            </div>
          </div>
        </div>

        {error && (
          <div className="mb-6 p-4 rounded-lg bg-[#FDE8E8] border border-[#F8B4B4] text-[#9B1C1C] text-sm">
            {error}
          </div>
        )}

        {loading ? (
          <div className="flex justify-center py-24">
            <LoadingSpinner size="lg" text="Loading assessable skills..." />
          </div>
        ) : (
          <div className="space-y-10">
            {/* Skills Catalog */}
            <section>
              <h2 className="text-lg font-semibold text-[#37352F] mb-4 flex items-center gap-2">
                <span>Available Skill Assessments</span>
                <span className="text-xs font-normal text-[#8A8985]">({skills.length} skills ready)</span>
              </h2>

              <div
                style={{
                  display: "grid",
                  gridTemplateColumns: "repeat(auto-fit, minmax(280px, 1fr))",
                  gap: "1rem",
                }}
              >
                {skills.map((item) => {
                  const icon = SKILL_ICONS[item.skill_name] || "⚡";
                  const isStarting = startingSkill === item.skill_name;

                  // Find if already passed
                  const pastPassed = history.some(
                    (h) => h.skill_name.toLowerCase() === item.skill_name.toLowerCase() && h.passed
                  );

                  return (
                    <div
                      key={item.skill_name}
                      className="bg-white rounded-xl border border-[#E9E9E7] p-5 shadow-xs hover:border-[#D0CFCB] transition-all flex flex-col justify-between"
                    >
                      <div>
                        <div className="flex items-start justify-between mb-3">
                          <div className="flex items-center gap-3">
                            <span className="text-2xl p-2 bg-[#F7F6F3] rounded-lg">{icon}</span>
                            <div>
                              <h3 className="font-semibold text-base text-[#37352F]">{item.skill_name}</h3>
                              <span className="text-xs text-[#8A8985]">
                                {item.total_questions} questions available
                              </span>
                            </div>
                          </div>

                          {pastPassed && (
                            <span className="inline-flex items-center gap-1 text-[11px] font-semibold px-2 py-0.5 rounded-full bg-[#DEF7EC] text-[#03543F]">
                              ✓ Verified
                            </span>
                          )}
                        </div>

                        <div className="flex flex-wrap gap-1.5 my-3">
                          {item.question_types.map((type) => (
                            <span
                              key={type}
                              className="text-[10px] font-medium px-2 py-0.5 rounded bg-[#F7F6F3] text-[#6B6B6B] border border-[#E9E9E7]"
                            >
                              {type.toUpperCase()}
                            </span>
                          ))}
                        </div>
                      </div>

                      <div className="pt-3 border-t border-[#F1F1EF] mt-2">
                        <button
                          onClick={() => handleStartAssessment(item.skill_name)}
                          disabled={isStarting}
                          className="w-full py-2 px-3 rounded-lg bg-[#2383E2] hover:bg-[#1A73E8] text-white text-xs font-semibold transition-colors flex items-center justify-center gap-2 disabled:opacity-50"
                        >
                          {isStarting ? (
                            <>
                              <div className="w-3.5 h-3.5 border-2 border-white border-t-transparent rounded-full animate-spin" />
                              Starting...
                            </>
                          ) : (
                            <>
                              Start {selectedDifficulty} Assessment &rarr;
                            </>
                          )}
                        </button>
                      </div>
                    </div>
                  );
                })}
              </div>
            </section>

            {/* Assessment History */}
            {history.length > 0 && (
              <section className="bg-white rounded-xl border border-[#E9E9E7] p-6 shadow-xs">
                <div className="flex items-center justify-between mb-4">
                  <h2 className="text-base font-semibold text-[#37352F]">
                    Your Assessment Attempts History
                  </h2>
                  <span className="text-xs text-[#8A8985]">{history.length} recorded attempts</span>
                </div>

                <div className="overflow-x-auto">
                  <table className="w-full text-left text-xs">
                    <thead>
                      <tr className="border-b border-[#E9E9E7] text-[#8A8985]">
                        <th className="pb-3 font-medium">Skill</th>
                        <th className="pb-3 font-medium">Difficulty</th>
                        <th className="pb-3 font-medium">Status</th>
                        <th className="pb-3 font-medium">Score</th>
                        <th className="pb-3 font-medium">Accuracy</th>
                        <th className="pb-3 font-medium">Date</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-[#F1F1EF]">
                      {history.map((att) => (
                        <tr key={att.id} className="hover:bg-[#FDFDFD]">
                          <td className="py-3 font-medium text-[#37352F]">{att.skill_name}</td>
                          <td className="py-3 text-[#6B6B6B]">{att.difficulty}</td>
                          <td className="py-3">
                            <span
                              className={`px-2 py-0.5 rounded text-[10px] font-semibold ${
                                att.passed
                                  ? "bg-[#DEF7EC] text-[#03543F]"
                                  : att.status === "completed"
                                  ? "bg-[#FDE8E8] text-[#9B1C1C]"
                                  : "bg-[#FEF08A] text-[#854D0E]"
                              }`}
                            >
                              {att.passed ? "Verified Passed" : att.status === "completed" ? "Not Passed" : "In Progress"}
                            </span>
                          </td>
                          <td className="py-3 font-semibold text-[#37352F]">{att.score}%</td>
                          <td className="py-3 text-[#6B6B6B]">{att.accuracy}%</td>
                          <td className="py-3 text-[#8A8985]">
                            {new Date(att.started_at).toLocaleDateString()}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </section>
            )}
          </div>
        )}
      </main>
    </div>
  );
}
