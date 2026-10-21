"use client";

import React, { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { Navbar } from "../../components/Navbar";
import LoadingSpinner from "../../components/ui/LoadingSpinner";
import ScoreBar from "../../components/ui/ScoreBar";
import { isLoggedIn, getProfileId } from "../../lib/auth";
import { jobsApi } from "../../lib/api";

const APPLICATION_STATUSES = [
  "Saved",
  "Applied",
  "Assessment",
  "Interview",
  "Offer",
  "Rejected",
];

export default function JobsPage() {
  const router = useRouter();
  const [profileId, setProfileId] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [activeTab, setActiveTab] = useState<"matches" | "tracker">("matches");

  // Filters
  const [opportunityType, setOpportunityType] = useState<string>("All");
  const [workMode, setWorkMode] = useState<string>("All");
  const [search, setSearch] = useState<string>("");

  // Data
  const [opportunities, setOpportunities] = useState<any[]>([]);
  const [trackedApplications, setTrackedApplications] = useState<any[]>([]);
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
      const [oppsRes, trackedRes] = await Promise.all([
        jobsApi.getOpportunities({
          profileId: pid,
          opportunityType: opportunityType !== "All" ? opportunityType : undefined,
          workMode: workMode !== "All" ? workMode : undefined,
          search: search || undefined,
        }).catch(() => ({ opportunities: [] })),
        jobsApi.getTracked(pid).catch(() => []),
      ]);

      setOpportunities(oppsRes.opportunities || []);
      setTrackedApplications(trackedRes || []);
    } catch (err: any) {
      setError(err.message || "Failed to load opportunities.");
    } finally {
      setLoading(false);
    }
  };

  const handleApplyFilter = () => {
    if (profileId) {
      loadData(profileId);
    }
  };

  const handleUpdateStatus = async (opportunityId: number, newStatus: string) => {
    if (!profileId) return;
    setUpdatingId(opportunityId);

    try {
      await jobsApi.trackOpportunity(profileId, opportunityId, newStatus);
      // Reload tracked list
      const trackedRes = await jobsApi.getTracked(profileId);
      setTrackedApplications(trackedRes || []);
      // Update local opportunity list status
      setOpportunities((prev) =>
        prev.map((opp) => (opp.id === opportunityId ? { ...opp, application_status: newStatus } : opp))
      );
    } catch (err: any) {
      setError(err.message || "Failed to update application status.");
    } finally {
      setUpdatingId(null);
    }
  };

  return (
    <div className="min-h-screen bg-[#F7F6F3] text-[#37352F]">
      <Navbar />

      <main className="page-wrapper py-8 sm:py-10 space-y-8">
        {/* Header & Tabs */}
        <div className="flex flex-col lg:flex-row lg:items-center lg:justify-between gap-6 pb-6 border-b border-[#e2e4e8]">
          <div>
            <div className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full bg-blue-50 text-blue-700 text-xs font-semibold mb-2 border border-blue-200">
              <span className="w-1.5 h-1.5 rounded-full bg-blue-600" />
              <span>Personalized Opportunity Matching</span>
            </div>
            <h1 className="text-2xl sm:text-3xl lg:text-4xl font-extrabold tracking-tight text-[#111827]">
              Job & Internship Opportunities
            </h1>
            <p className="text-sm sm:text-base text-[#656d76] mt-1.5 max-w-3xl">
              Real-world roles scored transparently against your candidate profile. Roles matching your assessment-verified skills receive an empirical confidence bonus.
            </p>
          </div>

          {/* Tab Switcher */}
          <div className="flex bg-white p-1.5 rounded-xl border border-[#e2e4e8] shadow-xs shrink-0">
            <button
              onClick={() => setActiveTab("matches")}
              className={`px-5 py-2 text-sm font-semibold rounded-lg transition-all ${
                activeTab === "matches"
                  ? "bg-blue-600 text-white shadow-xs"
                  : "text-[#656d76] hover:text-[#111827]"
              }`}
            >
              Opportunity Matches ({opportunities.length})
            </button>
            <button
              onClick={() => setActiveTab("tracker")}
              className={`px-5 py-2 text-sm font-semibold rounded-lg transition-all ${
                activeTab === "tracker"
                  ? "bg-blue-600 text-white shadow-xs"
                  : "text-[#656d76] hover:text-[#111827]"
              }`}
            >
              Application Tracker ({trackedApplications.length})
            </button>
          </div>
        </div>

        {error && (
          <div className="mb-6 p-4 rounded-lg bg-[#FDE8E8] border border-[#F8B4B4] text-[#9B1C1C] text-xs">
            {error}
          </div>
        )}

        {/* Filter Controls Bar (Matches View) */}
        {activeTab === "matches" && (
          <div className="bg-white p-4 rounded-xl border border-[#E9E9E7] mb-6 flex flex-wrap items-center gap-3 text-xs shadow-xs">
            <div className="flex-1 min-w-[200px]">
              <input
                type="text"
                placeholder="Search by title, company, or keyword..."
                value={search}
                onChange={(e) => setSearch(e.target.value)}
                onKeyDown={(e) => e.key === "Enter" && handleApplyFilter()}
                className="w-full p-2 rounded-lg border border-[#E9E9E7] text-xs text-[#37352F] focus:outline-none focus:border-[#2383E2]"
              />
            </div>

            <div>
              <select
                value={opportunityType}
                onChange={(e) => setOpportunityType(e.target.value)}
                className="p-2 rounded-lg border border-[#E9E9E7] bg-white text-xs text-[#37352F] focus:outline-none"
              >
                <option value="All">All Types</option>
                <option value="Internship">Internship</option>
                <option value="Full-time">Full-time</option>
              </select>
            </div>

            <div>
              <select
                value={workMode}
                onChange={(e) => setWorkMode(e.target.value)}
                className="p-2 rounded-lg border border-[#E9E9E7] bg-white text-xs text-[#37352F] focus:outline-none"
              >
                <option value="All">All Work Modes</option>
                <option value="Remote">Remote</option>
                <option value="Hybrid">Hybrid</option>
                <option value="On-site">On-site</option>
              </select>
            </div>

            <button
              onClick={handleApplyFilter}
              className="py-2 px-4 rounded-lg bg-[#2383E2] hover:bg-[#1A73E8] text-white font-semibold transition-colors"
            >
              Filter
            </button>
          </div>
        )}

        {loading ? (
          <div className="flex justify-center py-20">
            <LoadingSpinner size="lg" text="Matching opportunities with your profile..." />
          </div>
        ) : activeTab === "matches" ? (
          /* Opportunities Matches List */
          <div className="space-y-4">
            {opportunities.length === 0 ? (
              <div className="bg-white p-12 rounded-xl border border-[#E9E9E7] text-center space-y-3">
                <p className="text-sm font-semibold text-[#37352F]">No opportunities found matching your filters.</p>
                <p className="text-xs text-[#6B6B6B]">Try adjusting your search criteria or work mode settings.</p>
              </div>
            ) : (
              opportunities.map((opp) => (
                <div
                  key={opp.id}
                  className="bg-white rounded-xl border border-[#E9E9E7] p-6 shadow-xs hover:border-[#D0CFCB] transition-all flex flex-col md:flex-row md:items-start justify-between gap-6"
                >
                  {/* Left Column: Role Details */}
                  <div className="flex-1 space-y-3">
                    <div className="flex flex-wrap items-center gap-2">
                      <h3 className="text-base font-bold text-[#37352F]">{opp.title}</h3>
                      <span className="text-xs text-[#6B6B6B] font-medium">• {opp.company_name}</span>

                      {opp.is_verified && (
                        <span className="text-[10px] font-semibold px-2 py-0.5 rounded-full bg-[#DEF7EC] text-[#03543F]">
                          ✓ Verified Partner
                        </span>
                      )}

                      <span className="text-[10px] font-medium px-2 py-0.5 rounded bg-[#F7F6F3] text-[#6B6B6B] border border-[#E9E9E7]">
                        {opp.opportunity_type}
                      </span>
                      <span className="text-[10px] font-medium px-2 py-0.5 rounded bg-[#F7F6F3] text-[#6B6B6B] border border-[#E9E9E7]">
                        {opp.work_mode}
                      </span>
                    </div>

                    <p className="text-xs text-[#6B6B6B] line-clamp-2">{opp.description}</p>

                    {/* Compensation & Location */}
                    <div className="flex flex-wrap items-center gap-4 text-xs text-[#8A8985]">
                      {opp.min_salary && (
                        <span>
                          💰 {opp.currency} {opp.min_salary.toLocaleString()}
                          {opp.max_salary ? ` - ${opp.max_salary.toLocaleString()}` : ""}
                        </span>
                      )}
                      {opp.location && <span>📍 {opp.location}</span>}
                    </div>

                    {/* Skill Breakdown */}
                    <div className="pt-2 space-y-2">
                      <div className="flex flex-wrap items-center gap-1.5">
                        <span className="text-xs text-[#8A8985] font-medium mr-1">Matched Skills:</span>
                        {opp.matched_skills?.map((s: string) => {
                          const isVerified = opp.verified_matched_skills?.includes(s);
                          return (
                            <span
                              key={s}
                              className={`text-[11px] font-medium px-2 py-0.5 rounded-md ${
                                isVerified
                                  ? "bg-[#DEF7EC] text-[#03543F] font-semibold border border-[#BCF0DA]"
                                  : "bg-[#EBF5FB] text-[#2383E2]"
                              }`}
                            >
                              {s} {isVerified && "✓"}
                            </span>
                          );
                        })}
                      </div>

                      {opp.missing_skills?.length > 0 && (
                        <div className="flex flex-wrap items-center gap-1.5">
                          <span className="text-xs text-[#8A8985] font-medium mr-1">Gaps:</span>
                          {opp.missing_skills.map((s: string) => (
                            <span
                              key={s}
                              className="text-[11px] font-medium px-2 py-0.5 rounded-md bg-[#FDE8E8] text-[#9B1C1C]"
                            >
                              {s}
                            </span>
                          ))}
                        </div>
                      )}
                    </div>

                    {/* Match Reasons */}
                    {opp.match_reasons?.length > 0 && (
                      <div className="pt-1">
                        <span className="text-[11px] text-[#03543F] font-medium">
                          ✦ {opp.match_reasons[0]}
                        </span>
                      </div>
                    )}
                  </div>

                  {/* Right Column: Match Score & Action Buttons */}
                  <div className="w-full md:w-56 flex flex-col justify-between items-end border-t md:border-t-0 md:border-l border-[#E9E9E7] pt-4 md:pt-0 md:pl-6 space-y-4">
                    <div className="w-full text-right">
                      <div className="text-2xl font-bold text-[#2383E2]">{opp.match_score}%</div>
                      <span className="text-xs text-[#8A8985] block">Profile Match Score</span>
                      <div className="mt-2">
                        <ScoreBar label="Match" value={opp.match_score} size="sm" showValue={false} />
                      </div>
                    </div>

                    <div className="w-full space-y-2">
                      {opp.application_url && (
                        <a
                          href={opp.application_url}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="w-full py-2 px-3 text-center rounded-lg bg-[#2383E2] hover:bg-[#1A73E8] text-white text-xs font-semibold block transition-colors"
                        >
                          Apply Directly &rarr;
                        </a>
                      )}

                      {/* Tracker Status Selector */}
                      <div className="flex items-center gap-1.5">
                        <span className="text-[11px] text-[#8A8985]">Status:</span>
                        <select
                          value={opp.application_status || "Saved"}
                          onChange={(e) => handleUpdateStatus(opp.id, e.target.value)}
                          disabled={updatingId === opp.id}
                          className="flex-1 p-1.5 rounded-md border border-[#E9E9E7] text-xs bg-white text-[#37352F] font-medium focus:outline-none"
                        >
                          {APPLICATION_STATUSES.map((st) => (
                            <option key={st} value={st}>
                              {st}
                            </option>
                          ))}
                        </select>
                      </div>
                    </div>
                  </div>
                </div>
              ))
            )}
          </div>
        ) : (
          /* Tracked Applications Table */
          <div className="bg-white rounded-xl border border-[#E9E9E7] p-6 shadow-xs">
            <h2 className="text-base font-semibold text-[#37352F] mb-4">
              Your Application Pipeline ({trackedApplications.length})
            </h2>

            {trackedApplications.length === 0 ? (
              <div className="py-12 text-center text-xs text-[#6B6B6B]">
                No applications tracked yet. Click &quot;Save&quot; or update status on any opportunity match to track it here.
              </div>
            ) : (
              <div className="overflow-x-auto">
                <table className="w-full text-left text-xs">
                  <thead>
                    <tr className="border-b border-[#E9E9E7] text-[#8A8985]">
                      <th className="pb-3 font-medium">Position</th>
                      <th className="pb-3 font-medium">Company</th>
                      <th className="pb-3 font-medium">Type</th>
                      <th className="pb-3 font-medium">Work Mode</th>
                      <th className="pb-3 font-medium">Status</th>
                      <th className="pb-3 font-medium">Last Updated</th>
                      <th className="pb-3 font-medium">Link</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-[#F1F1EF]">
                    {trackedApplications.map((app) => (
                      <tr key={app.id} className="hover:bg-[#FDFDFD]">
                        <td className="py-3 font-semibold text-[#37352F]">{app.title}</td>
                        <td className="py-3 text-[#6B6B6B]">{app.company_name}</td>
                        <td className="py-3 text-[#6B6B6B]">{app.opportunity_type}</td>
                        <td className="py-3 text-[#6B6B6B]">{app.work_mode}</td>
                        <td className="py-3">
                          <select
                            value={app.status}
                            onChange={(e) => handleUpdateStatus(app.opportunity_id, e.target.value)}
                            className="p-1 rounded border border-[#E9E9E7] bg-white text-xs text-[#37352F] font-semibold focus:outline-none"
                          >
                            {APPLICATION_STATUSES.map((st) => (
                              <option key={st} value={st}>
                                {st}
                              </option>
                            ))}
                          </select>
                        </td>
                        <td className="py-3 text-[#8A8985]">
                          {new Date(app.updated_at).toLocaleDateString()}
                        </td>
                        <td className="py-3">
                          {app.application_url && (
                            <a
                              href={app.application_url}
                              target="_blank"
                              rel="noopener noreferrer"
                              className="text-[#2383E2] hover:underline font-semibold"
                            >
                              Apply &rarr;
                            </a>
                          )}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        )}
      </main>
    </div>
  );
}
