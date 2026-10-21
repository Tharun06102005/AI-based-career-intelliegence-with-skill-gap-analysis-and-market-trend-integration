"use client";

import React, { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import Navbar from "../../components/Navbar";
import LoadingSpinner from "../../components/ui/LoadingSpinner";
import { isLoggedIn, getProfileId } from "../../lib/auth";
import { careersApi, simulationsApi } from "../../lib/api";

const QUICK_SKILL_SUGGESTIONS = [
  "Docker",
  "Kubernetes",
  "AWS",
  "GraphQL",
  "TypeScript",
  "PyTorch",
  "Next.js",
  "PostgreSQL",
  "Redis",
];

export default function SimulatorPage() {
  const router = useRouter();

  const [loading, setLoading] = useState(true);
  const [profileId, setProfileId] = useState<string | null>(null);

  const [careers, setCareers] = useState<
    Array<{ id: number; name: string; description: string }>
  >([]);
  const [selectedCareerId, setSelectedCareerId] = useState<number>(1);

  // Tag inputs
  const [addInput, setAddInput] = useState("");
  const [skillsToAdd, setSkillsToAdd] = useState<string[]>(["Docker", "Kubernetes"]);
  const [removeInput, setRemoveInput] = useState("");
  const [skillsToRemove, setSkillsToRemove] = useState<string[]>([]);

  // Simulation execution state
  const [simulating, setSimulating] = useState(false);
  const [simResult, setSimResult] = useState<{
    baseline: {
      career_fit_score: number;
      readiness: number;
      missing_skills_count: number;
    };
    simulated: {
      career_fit_score: number;
      readiness: number;
      missing_skills_count: number;
    };
    delta: {
      career_fit_score: number;
      readiness: number;
      missing_skills_count: number;
    };
    added_skills?: string[];
    removed_skills?: string[];
  } | null>(null);

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
        if (data.length > 0) {
          setSelectedCareerId(data[0].id);
        }
        setLoading(false);
      })
      .catch(() => {
        setError("Failed to load careers list.");
        setLoading(false);
      });
  }, [router]);

  const handleAddSkill = (skill: string) => {
    const trimmed = skill.trim();
    if (trimmed && !skillsToAdd.includes(trimmed)) {
      setSkillsToAdd((prev) => [...prev, trimmed]);
      setAddInput("");
    }
  };

  const handleRemoveFromAdded = (skill: string) => {
    setSkillsToAdd((prev) => prev.filter((s) => s !== skill));
  };

  const handleRemoveSkill = (skill: string) => {
    const trimmed = skill.trim();
    if (trimmed && !skillsToRemove.includes(trimmed)) {
      setSkillsToRemove((prev) => [...prev, trimmed]);
      setRemoveInput("");
    }
  };

  const handleRemoveFromRemoved = (skill: string) => {
    setSkillsToRemove((prev) => prev.filter((s) => s !== skill));
  };

  const runSimulation = async () => {
    if (!profileId) {
      setError("Active profile not found. Please sign in again.");
      return;
    }

    setSimulating(true);
    setError(null);
    try {
      const res = await simulationsApi.runSimulation(
        profileId,
        selectedCareerId,
        skillsToAdd,
        skillsToRemove
      );
      setSimResult(res);
    } catch (err: any) {
      setError(err.message || "Failed to run simulation. Please try again.");
    } finally {
      setSimulating(false);
    }
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-[#F7F6F3]">
        <Navbar />
        <LoadingSpinner fullScreen text="Loading Simulator..." />
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-[#F7F6F3] text-[#37352F] flex flex-col">
      <Navbar />

      <main className="flex-1 page-wrapper py-8 sm:py-10 space-y-8">
        {/* Header */}
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-6 border-b border-[#e2e4e8]">
          <div>
            <h1 className="text-2xl sm:text-3xl lg:text-4xl font-extrabold tracking-tight text-[#111827]">
              What-If Career Simulator
            </h1>
            <p className="text-sm sm:text-base text-[#656d76] mt-1.5">
              Simulate skill acquisitions or removals to evaluate real-time career fit score deltas.
            </p>
          </div>

          {/* Career dropdown */}
          <div className="w-full sm:w-72">
            <label className="block text-xs font-semibold text-[#656d76] mb-1.5">
              Simulate Target Career:
            </label>
            <div className="relative">
              <select
                value={selectedCareerId}
                onChange={(e) => {
                  setSelectedCareerId(Number(e.target.value));
                  setSimResult(null);
                }}
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

        {/* Clean Form Layout: Tag input for adding/removing skills */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-5">
          {/* Add Skills Card */}
          <div className="bg-white border border-[#E9E9E7] rounded-lg p-5 shadow-[0_1px_3px_rgba(0,0,0,0.08)] space-y-4">
            <div className="flex items-center justify-between border-b border-[#E9E9E7] pb-2.5">
              <div className="flex items-center gap-2">
                <span className="w-5 h-5 rounded bg-[#EBF5EE] text-[#1F7A4C] border border-[#C6E7D2] flex items-center justify-center font-bold text-xs">
                  +
                </span>
                <h3 className="text-sm font-semibold text-[#37352F]">
                  Skills to Add
                </h3>
              </div>
              <span className="text-xs text-[#6B6B6B]">
                {skillsToAdd.length} added
              </span>
            </div>

            {/* Input Form */}
            <form
              onSubmit={(e) => {
                e.preventDefault();
                handleAddSkill(addInput);
              }}
              className="flex gap-2"
            >
              <input
                type="text"
                value={addInput}
                onChange={(e) => setAddInput(e.target.value)}
                placeholder="Type skill & press Enter (e.g. AWS)"
                className="flex-1 bg-white border border-[#E9E9E7] rounded-md px-3 py-1.5 text-xs text-[#37352F] placeholder-[#9B9A97] focus:outline-none focus:border-[#2383E2]"
              />
              <button
                type="button"
                onClick={() => handleAddSkill(addInput)}
                className="bg-[#2383E2] hover:bg-[#1A73E8] text-white px-3 py-1.5 rounded-md text-xs font-medium transition-colors"
              >
                Add
              </button>
            </form>

            {/* Added Tag Pills */}
            <div className="flex flex-wrap gap-1.5 min-h-[44px] p-2.5 rounded-md bg-[#F7F6F3] border border-[#E9E9E7]">
              {skillsToAdd.length === 0 ? (
                <span className="text-xs text-[#9B9A97] italic self-center">
                  No skills added yet
                </span>
              ) : (
                skillsToAdd.map((skill) => (
                  <span
                    key={skill}
                    className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full bg-[#EBF5EE] text-[#1F7A4C] border border-[#C6E7D2] text-xs font-medium"
                  >
                    <span>{skill}</span>
                    <button
                      type="button"
                      onClick={() => handleRemoveFromAdded(skill)}
                      className="text-[#1F7A4C] hover:text-[#9B1C1C] focus:outline-none"
                    >
                      &times;
                    </button>
                  </span>
                ))
              )}
            </div>

            {/* Suggestions */}
            <div>
              <span className="text-[11px] font-medium text-[#6B6B6B] block mb-1.5">
                Quick Suggestions:
              </span>
              <div className="flex flex-wrap gap-1">
                {QUICK_SKILL_SUGGESTIONS.map((skill) => (
                  <button
                    key={skill}
                    type="button"
                    onClick={() => handleAddSkill(skill)}
                    className="text-[11px] px-2 py-0.5 rounded bg-white hover:bg-[#F7F6F3] text-[#37352F] border border-[#E9E9E7] transition-colors"
                  >
                    + {skill}
                  </button>
                ))}
              </div>
            </div>
          </div>

          {/* Remove Skills Card */}
          <div className="bg-white border border-[#E9E9E7] rounded-lg p-5 shadow-[0_1px_3px_rgba(0,0,0,0.08)] space-y-4">
            <div className="flex items-center justify-between border-b border-[#E9E9E7] pb-2.5">
              <div className="flex items-center gap-2">
                <span className="w-5 h-5 rounded bg-[#FDE8E8] text-[#9B1C1C] border border-[#F8B4B4] flex items-center justify-center font-bold text-xs">
                  &minus;
                </span>
                <h3 className="text-sm font-semibold text-[#37352F]">
                  Skills to Remove
                </h3>
              </div>
              <span className="text-xs text-[#6B6B6B]">
                {skillsToRemove.length} removed
              </span>
            </div>

            {/* Input Form */}
            <form
              onSubmit={(e) => {
                e.preventDefault();
                handleRemoveSkill(removeInput);
              }}
              className="flex gap-2"
            >
              <input
                type="text"
                value={removeInput}
                onChange={(e) => setRemoveInput(e.target.value)}
                placeholder="Type skill to remove (e.g. Java)"
                className="flex-1 bg-white border border-[#E9E9E7] rounded-md px-3 py-1.5 text-xs text-[#37352F] placeholder-[#9B9A97] focus:outline-none focus:border-[#2383E2]"
              />
              <button
                type="button"
                onClick={() => handleRemoveSkill(removeInput)}
                className="bg-white hover:bg-[#FDE8E8] text-[#9B1C1C] border border-[#F8B4B4] px-3 py-1.5 rounded-md text-xs font-medium transition-colors"
              >
                Remove
              </button>
            </form>

            {/* Removed Tag Pills */}
            <div className="flex flex-wrap gap-1.5 min-h-[44px] p-2.5 rounded-md bg-[#F7F6F3] border border-[#E9E9E7]">
              {skillsToRemove.length === 0 ? (
                <span className="text-xs text-[#9B9A97] italic self-center">
                  No skills selected for removal
                </span>
              ) : (
                skillsToRemove.map((skill) => (
                  <span
                    key={skill}
                    className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full bg-[#FDE8E8] text-[#9B1C1C] border border-[#F8B4B4] text-xs font-medium"
                  >
                    <span>{skill}</span>
                    <button
                      type="button"
                      onClick={() => handleRemoveFromRemoved(skill)}
                      className="text-[#9B1C1C] hover:text-black focus:outline-none"
                    >
                      &times;
                    </button>
                  </span>
                ))
              )}
            </div>

            <p className="text-[11px] text-[#6B6B6B]">
              Simulate how resilient your match is if a legacy skill is excluded.
            </p>
          </div>
        </div>

        {/* Action Button */}
        <div className="flex justify-center pt-2">
          <button
            onClick={runSimulation}
            disabled={simulating}
            className="bg-[#2383E2] hover:bg-[#1A73E8] text-white px-6 py-2.5 rounded-md text-xs font-medium transition-colors disabled:opacity-50 flex items-center gap-2 shadow-[0_1px_2px_rgba(0,0,0,0.05)]"
          >
            {simulating ? (
              <>
                <LoadingSpinner size="sm" />
                <span>Simulating Scenario...</span>
              </>
            ) : (
              <>
                <span>🔮</span>
                <span>Calculate Simulated Impact</span>
              </>
            )}
          </button>
        </div>

        {/* Before/After comparison in clean table style */}
        {simResult && (
          <div className="bg-white border border-[#E9E9E7] rounded-lg p-6 shadow-[0_1px_3px_rgba(0,0,0,0.08)] space-y-4">
            <div className="border-b border-[#E9E9E7] pb-3">
              <h2 className="text-base font-semibold text-[#37352F]">
                Simulation Comparison
              </h2>
              <p className="text-xs text-[#6B6B6B] mt-0.5">
                Before and after metrics for the selected hypothetical scenario.
              </p>
            </div>

            <div className="overflow-x-auto">
              <table className="w-full text-left text-xs border-collapse">
                <thead>
                  <tr className="border-b border-[#E9E9E7] text-[#6B6B6B] font-medium bg-[#F7F6F3]">
                    <th className="py-2.5 px-4 font-semibold">Evaluation Metric</th>
                    <th className="py-2.5 px-4 font-semibold">Before (Baseline)</th>
                    <th className="py-2.5 px-4 font-semibold">After (Simulated)</th>
                    <th className="py-2.5 px-4 font-semibold">Impact Delta</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-[#E9E9E7]">
                  <tr>
                    <td className="py-3 px-4 font-medium text-[#37352F]">
                      Career Fit Score
                    </td>
                    <td className="py-3 px-4 text-[#6B6B6B]">
                      {Math.round(simResult.baseline.career_fit_score)}%
                    </td>
                    <td className="py-3 px-4 font-semibold text-[#37352F]">
                      {Math.round(simResult.simulated.career_fit_score)}%
                    </td>
                    <td className="py-3 px-4 font-semibold">
                      <span
                        className={`inline-block px-2 py-0.5 rounded text-xs ${
                          simResult.delta.career_fit_score >= 0
                            ? "bg-[#EBF5EE] text-[#1F7A4C]"
                            : "bg-[#FDE8E8] text-[#9B1C1C]"
                        }`}
                      >
                        {simResult.delta.career_fit_score >= 0 ? "+" : ""}
                        {simResult.delta.career_fit_score.toFixed(1)}%
                      </span>
                    </td>
                  </tr>

                  <tr>
                    <td className="py-3 px-4 font-medium text-[#37352F]">
                      Role Readiness
                    </td>
                    <td className="py-3 px-4 text-[#6B6B6B]">
                      {Math.round(simResult.baseline.readiness)}%
                    </td>
                    <td className="py-3 px-4 font-semibold text-[#37352F]">
                      {Math.round(simResult.simulated.readiness)}%
                    </td>
                    <td className="py-3 px-4 font-semibold">
                      <span
                        className={`inline-block px-2 py-0.5 rounded text-xs ${
                          simResult.delta.readiness >= 0
                            ? "bg-[#EBF5EE] text-[#1F7A4C]"
                            : "bg-[#FDE8E8] text-[#9B1C1C]"
                        }`}
                      >
                        {simResult.delta.readiness >= 0 ? "+" : ""}
                        {simResult.delta.readiness.toFixed(1)}%
                      </span>
                    </td>
                  </tr>

                  <tr>
                    <td className="py-3 px-4 font-medium text-[#37352F]">
                      Missing Skills Count
                    </td>
                    <td className="py-3 px-4 text-[#6B6B6B]">
                      {simResult.baseline.missing_skills_count}
                    </td>
                    <td className="py-3 px-4 font-semibold text-[#37352F]">
                      {simResult.simulated.missing_skills_count}
                    </td>
                    <td className="py-3 px-4 font-semibold">
                      <span
                        className={`inline-block px-2 py-0.5 rounded text-xs ${
                          simResult.delta.missing_skills_count <= 0
                            ? "bg-[#EBF5EE] text-[#1F7A4C]"
                            : "bg-[#FDE8E8] text-[#9B1C1C]"
                        }`}
                      >
                        {simResult.delta.missing_skills_count > 0 ? "+" : ""}
                        {simResult.delta.missing_skills_count}
                      </span>
                    </td>
                  </tr>
                </tbody>
              </table>
            </div>
          </div>
        )}
      </main>
    </div>
  );
}
