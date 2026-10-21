"use client";

import React, { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import Navbar from "../../components/Navbar";
import ScoreBar from "../../components/ui/ScoreBar";
import LoadingSpinner from "../../components/ui/LoadingSpinner";
import { isLoggedIn, getProfileId } from "../../lib/auth";
import { progressApi } from "../../lib/api";

interface TrackedResource {
  id: number;
  profile_id: string;
  resource_id: number;
  status: string;
  progress: number;
  updated_at: string;
  resource?: {
    id: number;
    skill_name: string;
    title: string;
    url?: string;
    provider?: string;
    resource_type?: string;
  };
}

interface AvailableResource {
  id: number;
  skill_name: string;
  title: string;
  url?: string;
  provider?: string;
  resource_type?: string;
}

export default function ProgressTrackerPage() {
  const router = useRouter();

  const [loading, setLoading] = useState(true);
  const [profileId, setProfileId] = useState<string | null>(null);

  const [progressSummary, setProgressSummary] = useState<{
    total_tracked: number;
    completed_count: number;
    in_progress_count: number;
    average_progress: number;
    entries: TrackedResource[];
  }>({
    total_tracked: 0,
    completed_count: 0,
    in_progress_count: 0,
    average_progress: 0,
    entries: [],
  });

  const [libraryResources, setLibraryResources] = useState<AvailableResource[]>([]);
  const [updatingId, setUpdatingId] = useState<number | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!isLoggedIn()) {
      router.push("/login");
      return;
    }

    const pid = getProfileId();
    setProfileId(pid);

    if (pid) {
      loadData(pid);
    } else {
      setLoading(false);
    }
  }, [router]);

  const loadData = async (pid: string) => {
    setLoading(true);
    setError(null);
    try {
      const [progRes, libRes] = await Promise.all([
        progressApi.getProgress(pid).catch(() => ({
          profile_id: pid,
          total_tracked: 0,
          completed_count: 0,
          in_progress_count: 0,
          average_progress: 0,
          entries: [],
        })),
        progressApi.getResources().catch(() => []),
      ]);

      setProgressSummary(progRes);
      setLibraryResources(libRes as AvailableResource[]);
    } catch (err: any) {
      setError(err.message || "Failed to load progress records.");
    } finally {
      setLoading(false);
    }
  };

  const handleUpdateProgress = async (resourceId: number, newProgress: number) => {
    if (!profileId) return;

    const clamped = Math.min(100, Math.max(0, newProgress));
    const newStatus: "not_started" | "in_progress" | "completed" =
      clamped === 100
        ? "completed"
        : clamped > 0
        ? "in_progress"
        : "not_started";

    setUpdatingId(resourceId);
    try {
      await progressApi.updateProgress(profileId, resourceId, newStatus, clamped);
      const updated = await progressApi.getProgress(profileId);
      setProgressSummary(updated);
    } catch (err: any) {
      setError(err.message || "Failed to update resource progress.");
    } finally {
      setUpdatingId(null);
    }
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-[#F7F6F3]">
        <Navbar />
        <LoadingSpinner fullScreen text="Loading Progress..." />
      </div>
    );
  }

  const avgProgress = Math.round(progressSummary.average_progress || 0);
  const trackedMap = new Map(progressSummary.entries.map((e) => [e.resource_id, e]));

  return (
    <div className="min-h-screen bg-[#F7F6F3] text-[#37352F] flex flex-col">
      <Navbar />

      <main className="flex-1 page-wrapper py-8 space-y-6">
        {/* Header */}
        <div className="pb-4 border-b border-[#E9E9E7]">
          <h1 className="text-2xl font-bold tracking-tight text-[#37352F]">
            Learning Progress Tracker
          </h1>
          <p className="text-xs text-[#6B6B6B] mt-0.5">
            Log progress across courses, certifications, and documentation to build verifiable career competence.
          </p>
        </div>

        {error && (
          <div className="p-3 rounded-md bg-[#FDE8E8] border border-[#F8B4B4] text-[#9B1C1C] text-xs">
            {error}
          </div>
        )}

        {/* Overview Stats */}
        <div className="grid grid-cols-1 sm:grid-cols-4 gap-4">
          <div className="bg-white border border-[#E9E9E7] rounded-lg p-5 shadow-[0_1px_3px_rgba(0,0,0,0.08)]">
            <span className="text-xs font-medium text-[#6B6B6B] block">
              Average Completion
            </span>
            <div className="text-3xl font-bold text-[#37352F] mt-2">
              {avgProgress}%
            </div>
            <span className="text-[11px] text-[#9B9A97] mt-1 block">
              Across tracked items
            </span>
          </div>

          <div className="bg-white border border-[#E9E9E7] rounded-lg p-5 shadow-[0_1px_3px_rgba(0,0,0,0.08)]">
            <span className="text-xs font-medium text-[#6B6B6B] block">
              Total Modules
            </span>
            <div className="text-3xl font-bold text-[#37352F] mt-2">
              {progressSummary.total_tracked}
            </div>
            <span className="text-[11px] text-[#9B9A97] mt-1 block">
              Enrolled courses
            </span>
          </div>

          <div className="bg-white border border-[#E9E9E7] rounded-lg p-5 shadow-[0_1px_3px_rgba(0,0,0,0.08)]">
            <span className="text-xs font-medium text-[#D9730D] block">
              In Progress
            </span>
            <div className="text-3xl font-bold text-[#D9730D] mt-2">
              {progressSummary.in_progress_count}
            </div>
            <span className="text-[11px] text-[#9B9A97] mt-1 block">
              Active learning
            </span>
          </div>

          <div className="bg-white border border-[#E9E9E7] rounded-lg p-5 shadow-[0_1px_3px_rgba(0,0,0,0.08)]">
            <span className="text-xs font-medium text-[#0F7B6C] block">
              Completed
            </span>
            <div className="text-3xl font-bold text-[#0F7B6C] mt-2">
              {progressSummary.completed_count}
            </div>
            <span className="text-[11px] text-[#0F7B6C] mt-1 block font-medium">
              Verified skills
            </span>
          </div>
        </div>

        {/* Section: Tracked Resources Grid */}
        <section className="space-y-4">
          <div className="flex items-center justify-between">
            <h2 className="text-base font-semibold text-[#37352F]">
              Active Learning Modules
            </h2>
            <span className="text-xs text-[#6B6B6B]">
              {progressSummary.entries.length} Enrolled Resources
            </span>
          </div>

          {progressSummary.entries.length === 0 ? (
            <div className="bg-white border border-[#E9E9E7] rounded-lg p-8 text-center text-xs text-[#6B6B6B] shadow-[0_1px_3px_rgba(0,0,0,0.08)]">
              You haven&apos;t enrolled in any learning modules yet. Start tracking from the library below!
            </div>
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
              {progressSummary.entries.map((entry) => {
                const res = entry.resource;
                const title = res?.title || `Resource #${entry.resource_id}`;
                const skill = res?.skill_name || "General";
                const provider = res?.provider || "Official";
                const isBusy = updatingId === entry.resource_id;

                return (
                  <div
                    key={entry.id}
                    className="bg-white border border-[#E9E9E7] rounded-lg p-5 shadow-[0_1px_3px_rgba(0,0,0,0.08)] flex flex-col justify-between"
                  >
                    <div>
                      <div className="flex items-center justify-between gap-2 mb-2">
                        <span className="text-xs font-semibold px-2 py-0.5 rounded bg-[#EBF5FE] text-[#2383E2] border border-[#CBE5FE]">
                          {skill}
                        </span>
                        <span
                          className={`text-[10px] font-medium px-2 py-0.5 rounded-full capitalize ${
                            entry.status === "completed"
                              ? "bg-[#EBF5EE] text-[#1F7A4C]"
                              : "bg-[#FEF3C7] text-[#92400E]"
                          }`}
                        >
                          {entry.status.replace("_", " ")}
                        </span>
                      </div>

                      <h3 className="text-sm font-semibold text-[#37352F] line-clamp-2 mt-1">
                        {title}
                      </h3>
                      <p className="text-xs text-[#6B6B6B] mt-1">Provider: {provider}</p>

                      <div className="mt-4">
                        <ScoreBar
                          label="Completion"
                          value={entry.progress}
                          color={entry.progress === 100 ? "emerald" : "blue"}
                          size="sm"
                        />
                      </div>
                    </div>

                    <div className="mt-5 pt-3 border-t border-[#E9E9E7] flex items-center justify-between">
                      {res?.url ? (
                        <a
                          href={res.url}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="text-xs text-[#2383E2] hover:underline font-medium"
                        >
                          Open &rarr;
                        </a>
                      ) : (
                        <span className="text-xs text-[#9B9A97]">Resource</span>
                      )}

                      <div className="flex items-center gap-1">
                        <button
                          disabled={isBusy || entry.progress <= 0}
                          onClick={() =>
                            handleUpdateProgress(entry.resource_id, entry.progress - 25)
                          }
                          className="px-2 py-1 rounded bg-[#F7F6F3] hover:bg-[#EAE8E3] text-xs font-medium text-[#37352F] disabled:opacity-40"
                        >
                          &minus;25%
                        </button>
                        <button
                          disabled={isBusy || entry.progress >= 100}
                          onClick={() =>
                            handleUpdateProgress(entry.resource_id, entry.progress + 25)
                          }
                          className="px-2 py-1 rounded bg-[#F7F6F3] hover:bg-[#EAE8E3] text-xs font-medium text-[#37352F] disabled:opacity-40"
                        >
                          +25%
                        </button>
                        <button
                          disabled={isBusy || entry.progress === 100}
                          onClick={() => handleUpdateProgress(entry.resource_id, 100)}
                          className="px-2 py-1 rounded bg-[#EBF5EE] hover:bg-[#D4EBDC] text-xs font-medium text-[#1F7A4C] disabled:opacity-40"
                        >
                          Done
                        </button>
                      </div>
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </section>

        {/* Section: Curated Resource Library */}
        <section className="space-y-4 pt-2">
          <div className="flex items-center justify-between">
            <h2 className="text-base font-semibold text-[#37352F]">
              Curated Learning Library
            </h2>
            <span className="text-xs text-[#6B6B6B]">
              {libraryResources.length} Resources Available
            </span>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {libraryResources.slice(0, 9).map((lib) => {
              const isAlreadyTracked = trackedMap.has(lib.id);

              return (
                <div
                  key={lib.id}
                  className="bg-white border border-[#E9E9E7] rounded-lg p-5 shadow-[0_1px_3px_rgba(0,0,0,0.08)] flex flex-col justify-between"
                >
                  <div>
                    <div className="flex items-center justify-between gap-2 mb-1.5">
                      <span className="text-xs font-medium text-[#2383E2] bg-[#EBF5FE] px-2 py-0.5 rounded border border-[#CBE5FE]">
                        {lib.skill_name}
                      </span>
                      <span className="text-[11px] text-[#6B6B6B] capitalize">
                        {lib.resource_type || "course"}
                      </span>
                    </div>

                    <h3 className="text-sm font-semibold text-[#37352F] mt-1 line-clamp-2">
                      {lib.title}
                    </h3>
                    <p className="text-xs text-[#6B6B6B] mt-0.5">
                      Provider: {lib.provider || "Official Docs"}
                    </p>
                  </div>

                  <div className="mt-4 pt-3 border-t border-[#E9E9E7] flex items-center justify-between">
                    {lib.url ? (
                      <a
                        href={lib.url}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="text-xs text-[#6B6B6B] hover:text-[#37352F] underline"
                      >
                        Visit Resource &rarr;
                      </a>
                    ) : (
                      <span className="text-xs text-[#9B9A97]">Resource</span>
                    )}

                    {isAlreadyTracked ? (
                      <span className="text-xs text-[#1F7A4C] font-medium">
                        ✓ Enrolled
                      </span>
                    ) : (
                      <button
                        onClick={() => handleUpdateProgress(lib.id, 0)}
                        className="px-2.5 py-1 rounded-md text-xs font-medium bg-[#2383E2] hover:bg-[#1A73E8] text-white transition-colors"
                      >
                        + Start Tracking
                      </button>
                    )}
                  </div>
                </div>
              );
            })}
          </div>
        </section>
      </main>
    </div>
  );
}
