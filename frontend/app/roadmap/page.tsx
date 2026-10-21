"use client";

import React, { useState, useEffect, Suspense } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import Navbar from "../../components/Navbar";
import LoadingSpinner from "../../components/ui/LoadingSpinner";
import ScoreBar from "../../components/ui/ScoreBar";
import { isLoggedIn, getProfileId } from "../../lib/auth";
import { careersApi, roadmapsApi } from "../../lib/api";

const SKILL_YOUTUBE_LINKS: Record<string, string> = {
  python: "https://youtube.com/watch?v=_uQrJ0TkZlc",
  javascript: "https://youtube.com/watch?v=W6NZfCO5SIk",
  react: "https://youtube.com/watch?v=bMknfKXIFA8",
  docker: "https://youtube.com/watch?v=3c-iBn73dDE",
  sql: "https://youtube.com/watch?v=HXV3zeQKqGY",
  "machine learning": "https://youtube.com/watch?v=NWONeJKn9Kc",
  aws: "https://youtube.com/watch?v=3hLmDS179YE",
  git: "https://youtube.com/watch?v=RGOj5yH7evk",
  typescript: "https://youtube.com/watch?v=30LWjhZzg50",
  "node.js": "https://youtube.com/watch?v=Oe421EPjeBE",
  nodejs: "https://youtube.com/watch?v=Oe421EPjeBE",
  kubernetes: "https://youtube.com/watch?v=X48VuDVv0do",
  tensorflow: "https://youtube.com/watch?v=tPYj3fFJGjk",
  "rest apis": "https://youtube.com/watch?v=GZvSYJDk-us",
  rest: "https://youtube.com/watch?v=GZvSYJDk-us",
  api: "https://youtube.com/watch?v=GZvSYJDk-us",
  golang: "https://youtube.com/watch?v=un6ZyFkqFKo",
  go: "https://youtube.com/watch?v=un6ZyFkqFKo",
  java: "https://youtube.com/watch?v=eIrMbAQSU34",
  "c++": "https://youtube.com/watch?v=vLnPwxZdW4Y",
  cpp: "https://youtube.com/watch?v=vLnPwxZdW4Y",
  linux: "https://youtube.com/watch?v=wBp0Rb-ZJak",
  graphql: "https://youtube.com/watch?v=eIQh02xuVw4",
  postgresql: "https://youtube.com/watch?v=qw--VYLpxG4",
  postgres: "https://youtube.com/watch?v=qw--VYLpxG4",
  redis: "https://youtube.com/watch?v=jgpVdJB2sKQ",
  "system design": "https://youtube.com/watch?v=m8Icp_Cid5o",
  "ci/cd": "https://youtube.com/watch?v=scEDHsr3APg",
  cicd: "https://youtube.com/watch?v=scEDHsr3APg",
  "next.js": "https://youtube.com/watch?v=843nec-IvW0",
  nextjs: "https://youtube.com/watch?v=843nec-IvW0",
};

function getSkillVideoUrl(skillName: string): string {
  const normalized = skillName.toLowerCase().trim();
  if (SKILL_YOUTUBE_LINKS[normalized]) {
    return SKILL_YOUTUBE_LINKS[normalized];
  }
  for (const [key, url] of Object.entries(SKILL_YOUTUBE_LINKS)) {
    if (normalized.includes(key) || key.includes(normalized)) {
      return url;
    }
  }
  return `https://youtube.com/results?search_query=${encodeURIComponent(
    skillName + " full course tutorial"
  )}`;
}

const TIMELINE_OPTIONS = [
  { days: 7, label: "7 Days", tag: "Sprint 🔥" },
  { days: 15, label: "15 Days", tag: "Fast Track ⚡" },
  { days: 30, label: "30 Days", tag: "Standard 📅" },
  { days: 60, label: "60 Days", tag: "Deep Learning 🎓" },
  { days: 90, label: "90 Days", tag: "Mastery 🏆" },
];

interface RoadmapItem {
  skill: string;
  days_allocated?: string;
  daily_tasks?: string[];
  steps: string[];
  youtube_link?: string;
  resources: string[];
}

interface RoadmapData {
  career_name: string;
  fit_score: number;
  readiness: number;
  days_available?: number;
  explanation: {
    summary: string;
    strengths: string[];
    gaps: Array<{ skill: string; reason: string } | string>;
    roadmap: Array<{ skill: string; steps: string[] }>;
    caveats: string[];
  };
  roadmap: RoadmapItem[];
}

function RoadmapContent() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const initialCareerParam = searchParams.get("career");

  const [loading, setLoading] = useState(true);
  const [roadmapLoading, setRoadmapLoading] = useState(false);
  const [profileId, setProfileId] = useState<string | null>(null);

  const [careers, setCareers] = useState<
    Array<{ id: number; name: string; description: string }>
  >([]);
  const [selectedCareerId, setSelectedCareerId] = useState<number>(1);
  const [selectedDays, setSelectedDays] = useState<number>(30);
  const [customDays, setCustomDays] = useState<string>("");

  const [roadmapData, setRoadmapData] = useState<RoadmapData | null>(null);
  const [taskCheckedState, setTaskCheckedState] = useState<Record<string, boolean>>({});
  const [error, setError] = useState<string | null>(null);

  // Load task checked state from localStorage
  useEffect(() => {
    if (typeof window !== "undefined" && profileId) {
      try {
        const stored = localStorage.getItem(`roadmap_tasks_${profileId}_${selectedCareerId}`);
        if (stored) {
          setTaskCheckedState(JSON.parse(stored));
        } else {
          setTaskCheckedState({});
        }
      } catch (e) {
        console.warn(e);
      }
    }
  }, [profileId, selectedCareerId]);

  // Save task checked state to localStorage
  const saveTaskState = (newState: Record<string, boolean>) => {
    setTaskCheckedState(newState);
    if (typeof window !== "undefined" && profileId) {
      try {
        localStorage.setItem(
          `roadmap_tasks_${profileId}_${selectedCareerId}`,
          JSON.stringify(newState)
        );
      } catch (e) {
        console.warn(e);
      }
    }
  };

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
          fetchRoadmap(pid, targetId, 30);
        } else {
          setLoading(false);
        }
      })
      .catch(() => {
        setError("Failed to load careers list.");
        setLoading(false);
      });
  }, [router, initialCareerParam]);

  const fetchRoadmap = async (pid: string, careerId: number, days: number) => {
    setError(null);
    setRoadmapLoading(true);

    const cacheKey = `roadmap_${pid}_${careerId}_${days}`;
    if (typeof window !== "undefined") {
      try {
        const cached = localStorage.getItem(cacheKey);
        if (cached) {
          const parsed = JSON.parse(cached);
          if (parsed && (parsed.career_name || parsed.roadmap)) {
            setRoadmapData(parsed);
            setRoadmapLoading(false);
          }
        }
      } catch (e) {
        console.warn(e);
      }
    }

    try {
      const data = await roadmapsApi.getRoadmap(pid, careerId, days);
      setRoadmapData(data);
      if (typeof window !== "undefined") {
        try {
          localStorage.setItem(cacheKey, JSON.stringify(data));
        } catch (e) {}
      }
    } catch (err: any) {
      if (!roadmapData) {
        setError(err.message || "Failed to load learning roadmap.");
      }
    } finally {
      setRoadmapLoading(false);
      setLoading(false);
    }
  };

  const handleCareerChange = (careerId: number) => {
    setSelectedCareerId(careerId);
    if (profileId) {
      fetchRoadmap(profileId, careerId, selectedDays);
    }
  };

  const handleDaysChange = (days: number) => {
    setSelectedDays(days);
    setCustomDays("");
    if (profileId) {
      fetchRoadmap(profileId, selectedCareerId, days);
    }
  };

  const handleCustomDaysSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    const parsed = parseInt(customDays, 10);
    if (!isNaN(parsed) && parsed > 0 && parsed <= 365) {
      setSelectedDays(parsed);
      if (profileId) {
        fetchRoadmap(profileId, selectedCareerId, parsed);
      }
    }
  };

  const toggleTaskCheck = (taskKey: string) => {
    const nextState = {
      ...taskCheckedState,
      [taskKey]: !taskCheckedState[taskKey],
    };
    saveTaskState(nextState);
  };

  const markTodayCompleteForSkill = (skill: string, tasks: string[]) => {
    // Find the first uncompleted task for this skill
    const uncompletedIdx = tasks.findIndex((_, idx) => !taskCheckedState[`${skill}_${idx}`]);
    if (uncompletedIdx !== -1) {
      const nextState = {
        ...taskCheckedState,
        [`${skill}_${uncompletedIdx}`]: true,
      };
      saveTaskState(nextState);
    }
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-[#F7F6F3]">
        <Navbar />
        <LoadingSpinner fullScreen text="Loading Personalized Roadmap..." />
      </div>
    );
  }

  const roadmapSteps = roadmapData?.roadmap || [];

  // Calculate target completion date
  const startDate = new Date();
  const targetDate = new Date();
  targetDate.setDate(targetDate.getDate() + selectedDays);
  const formattedTargetDate = targetDate.toLocaleDateString("en-US", {
    month: "short",
    day: "numeric",
    year: "numeric",
  });

  return (
    <div className="min-h-screen bg-[#F7F6F3] text-[#37352F] flex flex-col">
      <Navbar />

      <main className="flex-1 page-wrapper py-8 space-y-6">
        {/* Header with Career Selector */}
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-4 border-b border-[#E9E9E7]">
          <div>
            <h1 className="text-2xl font-bold tracking-tight text-[#37352F]">
              Personalized Learning Roadmap
            </h1>
            <p className="text-xs text-[#6B6B6B] mt-0.5">
              Targeted day-by-day roadmap tailored to your available timeline.
            </p>
          </div>

          <div className="w-full sm:w-64">
            <label className="block text-[11px] font-medium text-[#6B6B6B] mb-1">
              Select Career Roadmap:
            </label>
            <div className="relative">
              <select
                value={selectedCareerId}
                onChange={(e) => handleCareerChange(Number(e.target.value))}
                className="w-full bg-white border border-[#E9E9E7] rounded-md px-3 py-1.5 text-xs text-[#37352F] font-medium focus:outline-none focus:border-[#2383E2] transition-colors cursor-pointer appearance-none shadow-[0_1px_2px_rgba(0,0,0,0.05)]"
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

        {/* 1. Timeline Selector at top before generating roadmap */}
        <div className="bg-white border border-[#E9E9E7] rounded-lg p-5 shadow-[0_1px_3px_rgba(0,0,0,0.08)] space-y-3">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 border-b border-[#E9E9E7] pb-2.5">
            <div>
              <h2 className="text-xs font-semibold uppercase tracking-wider text-[#37352F]">
                Target Study Timeline
              </h2>
              <p className="text-[11px] text-[#6B6B6B]">
                Choose how many days you want to distribute your missing skills across.
              </p>
            </div>
            <span className="text-xs font-semibold text-[#2383E2] bg-[#EBF5FE] border border-[#CBE5FE] px-2.5 py-0.5 rounded-full self-start sm:self-auto">
              Current Plan: {selectedDays} Days
            </span>
          </div>

          <div className="flex flex-wrap items-center gap-2 pt-1">
            {TIMELINE_OPTIONS.map((opt) => {
              const isSelected = selectedDays === opt.days;
              return (
                <button
                  key={opt.days}
                  type="button"
                  onClick={() => handleDaysChange(opt.days)}
                  className={`px-3.5 py-2 rounded-md text-xs font-medium transition-colors flex items-center gap-1.5 border ${
                    isSelected
                      ? "bg-[#2383E2] text-white border-[#2383E2] shadow-sm font-semibold"
                      : "bg-white text-[#37352F] border-[#E9E9E7] hover:bg-[#F7F6F3]"
                  }`}
                >
                  <span>{opt.label}</span>
                  <span className={`text-[10px] ${isSelected ? "text-white/80" : "text-[#6B6B6B]"}`}>
                    ({opt.tag})
                  </span>
                </button>
              );
            })}

            {/* Custom Days Input */}
            <form onSubmit={handleCustomDaysSubmit} className="flex items-center gap-1.5 ml-auto">
              <input
                type="number"
                min="1"
                max="365"
                value={customDays}
                onChange={(e) => setCustomDays(e.target.value)}
                placeholder="Custom days"
                className="w-24 px-2.5 py-1.5 bg-white border border-[#E9E9E7] rounded-md text-xs text-[#37352F] placeholder-[#9B9A97] focus:outline-none focus:border-[#2383E2]"
              />
              <button
                type="submit"
                className="bg-white hover:bg-[#F7F6F3] text-[#37352F] border border-[#E9E9E7] px-3 py-1.5 rounded-md text-xs font-medium transition-colors"
              >
                Set
              </button>
            </form>
          </div>
        </div>

        {error && (
          <div className="p-3 rounded-md bg-[#FDE8E8] border border-[#F8B4B4] text-[#9B1C1C] text-xs">
            {error}
          </div>
        )}

        {roadmapLoading ? (
          <div className="py-16">
            <LoadingSpinner size="lg" text={`Generating ${selectedDays}-day learning schedule...`} />
          </div>
        ) : !roadmapData ? (
          <div className="bg-white border border-[#E9E9E7] rounded-lg p-10 text-center space-y-2 shadow-[0_1px_3px_rgba(0,0,0,0.08)]">
            <div className="text-2xl">⚠️</div>
            <h3 className="text-sm font-semibold text-[#37352F]">
              No Roadmap Available
            </h3>
            <p className="text-xs text-[#6B6B6B]">
              Please upload a resume on the Dashboard to generate tailored roadmaps.
            </p>
          </div>
        ) : (
          <div className="space-y-6">
            {/* 6. Timeline Overview at Top of Roadmap */}
            <div className="bg-white border border-[#E9E9E7] rounded-lg p-5 shadow-[0_1px_3px_rgba(0,0,0,0.08)] space-y-4">
              <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 border-b border-[#E9E9E7] pb-3">
                <div className="flex items-center gap-2">
                  <span className="text-base">📅</span>
                  <div>
                    <h3 className="text-sm font-semibold text-[#37352F]">
                      Timeline Schedule Overview
                    </h3>
                    <p className="text-[11px] text-[#6B6B6B]">
                      Day 1 of {selectedDays} &bull; Target Completion:{" "}
                      <strong className="text-[#37352F]">{formattedTargetDate}</strong>
                    </p>
                  </div>
                </div>

                <div className="flex items-center gap-3 text-xs text-[#6B6B6B]">
                  <div className="flex items-center gap-1">
                    <span className="w-2.5 h-2.5 rounded bg-[#EBF5EE] border border-[#C6E7D2]" />
                    <span>Complete</span>
                  </div>
                  <div className="flex items-center gap-1">
                    <span className="w-2.5 h-2.5 rounded bg-[#EBF5FE] border border-[#CBE5FE]" />
                    <span>In Progress</span>
                  </div>
                  <div className="flex items-center gap-1">
                    <span className="w-2.5 h-2.5 rounded bg-[#F1F1EF] border border-[#E3E2DE]" />
                    <span>Not Started</span>
                  </div>
                </div>
              </div>

              {/* Horizontal Timeline Bar showing all skills */}
              {roadmapSteps.length > 0 && (
                <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-2 pt-1">
                  {roadmapSteps.map((step) => {
                    const tasks = step.daily_tasks || step.steps || [];
                    const completedTasks = tasks.filter(
                      (_, idx) => !!taskCheckedState[`${step.skill}_${idx}`]
                    ).length;
                    const isAllComplete = tasks.length > 0 && completedTasks === tasks.length;
                    const isInProgress = completedTasks > 0 && !isAllComplete;

                    const blockStyle = isAllComplete
                      ? "bg-[#EBF5EE] border-[#C6E7D2] text-[#1F7A4C]"
                      : isInProgress
                      ? "bg-[#EBF5FE] border-[#CBE5FE] text-[#2383E2]"
                      : "bg-[#F1F1EF] border-[#E3E2DE] text-[#6B6B6B]";

                    return (
                      <div
                        key={step.skill}
                        className={`p-3 rounded-md border transition-colors flex flex-col justify-between ${blockStyle}`}
                      >
                        <div className="flex items-center justify-between gap-1 mb-1">
                          <span className="font-semibold text-xs truncate" title={step.skill}>
                            {step.skill}
                          </span>
                          <span className="text-[10px] opacity-80 whitespace-nowrap">
                            {step.days_allocated || "Milestone"}
                          </span>
                        </div>
                        <div className="text-[11px] opacity-90">
                          {isAllComplete
                            ? "✓ Completed"
                            : isInProgress
                            ? `${completedTasks}/${tasks.length} tasks`
                            : "Not started"}
                        </div>
                      </div>
                    );
                  })}
                </div>
              )}
            </div>

            {/* AI Summary Card */}
            <div className="bg-white border border-[#E9E9E7] rounded-lg p-5 shadow-[0_1px_3px_rgba(0,0,0,0.08)] space-y-3">
              <div className="flex items-center justify-between border-b border-[#E9E9E7] pb-3">
                <div>
                  <h2 className="text-sm font-semibold text-[#37352F]">
                    Career Advisory Brief &bull; {roadmapData.career_name}
                  </h2>
                  <div className="flex items-center gap-3 text-xs text-[#6B6B6B] mt-0.5">
                    <span>
                      Fit Score:{" "}
                      <strong className="text-[#2383E2]">
                        {Math.round(roadmapData.fit_score)}%
                      </strong>
                    </span>
                    <span>&bull;</span>
                    <span>
                      Readiness:{" "}
                      <strong className="text-[#0F7B6C]">
                        {Math.round(roadmapData.readiness)}%
                      </strong>
                    </span>
                  </div>
                </div>
              </div>

              <blockquote className="text-xs text-[#37352F] italic border-l-2 border-[#2383E2] pl-3 py-1 font-normal leading-relaxed">
                &ldquo;{roadmapData.explanation.summary}&rdquo;
              </blockquote>
            </div>

            {/* 5. Detailed Skill Cards */}
            <div className="space-y-4">
              <div className="flex items-center justify-between">
                <h3 className="text-base font-semibold text-[#37352F]">
                  Day-by-Day Skill Milestones
                </h3>
                <span className="text-xs text-[#6B6B6B]">
                  {roadmapSteps.length} Core Competencies
                </span>
              </div>

              {roadmapSteps.length === 0 ? (
                <div className="bg-white border border-[#E9E9E7] rounded-lg p-8 text-center text-xs text-[#6B6B6B] shadow-[0_1px_3px_rgba(0,0,0,0.08)]">
                  All competencies fulfilled! You currently have no critical skill gaps for this role.
                </div>
              ) : (
                <div className="space-y-5">
                  {roadmapSteps.map((step, index) => {
                    const videoUrl = step.youtube_link || getSkillVideoUrl(step.skill);
                    const docsUrl = `https://www.google.com/search?q=${encodeURIComponent(
                      step.skill + " official documentation"
                    )}`;
                    const courseUrl = `https://www.google.com/search?q=${encodeURIComponent(
                      step.skill + " freecodecamp coursera full course"
                    )}`;

                    const tasks =
                      step.daily_tasks && step.daily_tasks.length > 0
                        ? step.daily_tasks
                        : step.steps && step.steps.length > 0
                        ? step.steps.map((st, i) => `Day ${i + 1}: ${st}`)
                        : [
                            `Day 1: Study ${step.skill} fundamentals`,
                            `Day 2: Build a practical module with ${step.skill}`,
                          ];

                    const completedTasks = tasks.filter(
                      (_, idx) => !!taskCheckedState[`${step.skill}_${idx}`]
                    ).length;
                    const totalTasks = tasks.length;
                    const completionPct = totalTasks > 0 ? Math.round((completedTasks / totalTasks) * 100) : 0;
                    const isFullyComplete = totalTasks > 0 && completedTasks === totalTasks;

                    return (
                      <div
                        key={step.skill}
                        className={`bg-white border rounded-lg p-6 shadow-[0_1px_3px_rgba(0,0,0,0.08)] transition-all space-y-4 ${
                          isFullyComplete ? "border-[#C6E7D2] bg-[#EBF5EE]/10" : "border-[#E9E9E7]"
                        }`}
                      >
                        {/* Card Header: Skill Name + Day Range Badge "Day 1-5" */}
                        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 border-b border-[#E9E9E7] pb-3">
                          <div className="flex items-center gap-2.5">
                            <span className="w-6 h-6 rounded-full bg-[#F7F6F3] border border-[#E9E9E7] flex items-center justify-center text-xs font-bold text-[#37352F]">
                              {index + 1}
                            </span>
                            <h4 className="text-base font-semibold text-[#37352F]">
                              {step.skill}
                            </h4>
                            <span className="text-xs font-semibold px-2.5 py-0.5 rounded-full bg-[#EBF5FE] text-[#2383E2] border border-[#CBE5FE]">
                              {step.days_allocated || `Milestone ${index + 1}`}
                            </span>
                          </div>

                          {/* "Mark Today Complete" Button */}
                          <div className="flex items-center gap-2">
                            <button
                              type="button"
                              onClick={() => markTodayCompleteForSkill(step.skill, tasks)}
                              disabled={isFullyComplete}
                              className={`px-3 py-1 rounded-md text-xs font-medium transition-colors ${
                                isFullyComplete
                                  ? "bg-[#EBF5EE] text-[#1F7A4C] cursor-default"
                                  : "bg-[#2383E2] hover:bg-[#1A73E8] text-white"
                              }`}
                            >
                              {isFullyComplete ? "✓ All Days Complete" : "Mark Today Complete"}
                            </button>
                          </div>
                        </div>

                        {/* Progress Bar showing completed days / total days */}
                        <div className="space-y-1">
                          <div className="flex justify-between items-center text-xs">
                            <span className="text-[#6B6B6B] font-medium">
                              Progress: {completedTasks} of {totalTasks} days completed
                            </span>
                            <span className="font-semibold text-[#37352F]">
                              {completionPct}%
                            </span>
                          </div>
                          <ScoreBar
                            label=""
                            value={completionPct}
                            size="sm"
                            showValue={false}
                            color={isFullyComplete ? "emerald" : "blue"}
                          />
                        </div>

                        {/* Daily tasks as numbered checklist */}
                        <div className="space-y-2 pt-2">
                          <span className="text-xs font-semibold text-[#37352F] uppercase tracking-wider block">
                            Daily Learning Checklist:
                          </span>
                          <div className="space-y-2">
                            {tasks.map((taskText, tIdx) => {
                              const taskKey = `${step.skill}_${tIdx}`;
                              const isChecked = !!taskCheckedState[taskKey];

                              return (
                                <label
                                  key={tIdx}
                                  className={`flex items-start gap-2.5 p-2.5 rounded-md border text-xs cursor-pointer transition-colors select-none ${
                                    isChecked
                                      ? "bg-[#EBF5EE]/50 border-[#C6E7D2] text-[#1F7A4C]"
                                      : "bg-[#F7F6F3] border-[#E9E9E7] text-[#37352F] hover:bg-white"
                                  }`}
                                >
                                  <input
                                    type="checkbox"
                                    checked={isChecked}
                                    onChange={() => toggleTaskCheck(taskKey)}
                                    className="mt-0.5 w-4 h-4 rounded text-[#2383E2] border-[#D3D1CB] focus:ring-0 cursor-pointer"
                                  />
                                  <span className={isChecked ? "line-through opacity-80" : ""}>
                                    {taskText}
                                  </span>
                                </label>
                              );
                            })}
                          </div>
                        </div>

                        {/* Resource Chips: YouTube | Docs | Course */}
                        <div className="pt-3 border-t border-[#E9E9E7]">
                          <span className="text-[11px] font-semibold text-[#6B6B6B] uppercase tracking-wider block mb-2">
                            Curated Learning Resources:
                          </span>
                          <div className="flex flex-wrap gap-2">
                            {/* YouTube link chip */}
                            <a
                              href={videoUrl}
                              target="_blank"
                              rel="noopener noreferrer"
                              className="inline-flex items-center gap-1.5 px-3 py-1 rounded-md text-xs font-medium bg-[#FDE8E8] text-[#9B1C1C] border border-[#F8B4B4] hover:bg-[#FCD2D2] transition-colors"
                            >
                              <span>📺</span>
                              <span>YouTube Tutorial</span>
                              <span className="text-[10px] opacity-70">&rarr;</span>
                            </a>

                            {/* Docs chip */}
                            <a
                              href={docsUrl}
                              target="_blank"
                              rel="noopener noreferrer"
                              className="inline-flex items-center gap-1.5 px-3 py-1 rounded-md text-xs font-medium bg-[#F7F6F3] text-[#37352F] border border-[#E9E9E7] hover:bg-[#EAE8E3] transition-colors"
                            >
                              <span>📖</span>
                              <span>Official Docs</span>
                              <span className="text-[10px] opacity-70">&rarr;</span>
                            </a>

                            {/* Course chip */}
                            <a
                              href={courseUrl}
                              target="_blank"
                              rel="noopener noreferrer"
                              className="inline-flex items-center gap-1.5 px-3 py-1 rounded-md text-xs font-medium bg-[#EBF5FE] text-[#2383E2] border border-[#CBE5FE] hover:bg-[#D9EDFE] transition-colors"
                            >
                              <span>🎓</span>
                              <span>Full Course</span>
                              <span className="text-[10px] opacity-70">&rarr;</span>
                            </a>
                          </div>
                        </div>
                      </div>
                    );
                  })}
                </div>
              )}
            </div>
          </div>
        )}
      </main>
    </div>
  );
}

export default function RoadmapPage() {
  return (
    <Suspense fallback={<LoadingSpinner fullScreen text="Loading Roadmap..." />}>
      <RoadmapContent />
    </Suspense>
  );
}
