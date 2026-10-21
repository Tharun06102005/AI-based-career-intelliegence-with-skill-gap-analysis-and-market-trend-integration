"use client";

import React, { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { Navbar } from "../../components/Navbar";
import LoadingSpinner from "../../components/ui/LoadingSpinner";
import ScoreBar from "../../components/ui/ScoreBar";
import { isLoggedIn, getProfileId } from "../../lib/auth";
import { careersApi, interviewsApi } from "../../lib/api";

const CATEGORIES = [
  { id: "technical", label: "Technical Depth", icon: "💻", desc: "Core algorithms, data structures, and architecture concepts." },
  { id: "project_defense", label: "Project Defense", icon: "🛡️", desc: "Deep architectural defense of actual projects from your resume." },
  { id: "coding", label: "System & Coding", icon: "⚙️", desc: "Implementation logic, complexity tradeoffs, and edge cases." },
  { id: "hr", label: "Behavioral & HR", icon: "🤝", desc: "Leadership, conflict resolution, and teamwork using STAR format." },
];

export default function MockInterviewPage() {
  const router = useRouter();
  const [profileId, setProfileId] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  // Setup state
  const [careers, setCareers] = useState<Array<{ id: number; name: string }>>([]);
  const [selectedRole, setSelectedRole] = useState<string>("Software Engineer");
  const [selectedCategory, setSelectedCategory] = useState<string>("technical");
  const [selectedDifficulty, setSelectedDifficulty] = useState<string>("Intermediate");
  const [selectedDuration, setSelectedDuration] = useState<number>(30);

  // Active interview session state
  const [activeSession, setActiveSession] = useState<{
    session_id: number;
    role_name: string;
    category: string;
  } | null>(null);

  const [currentQuestion, setCurrentQuestion] = useState<{
    turn_id: number;
    turn_number: number;
    question: string;
    category: string;
    context_snippet?: string;
  } | null>(null);

  const [userAnswer, setUserAnswer] = useState("");
  const [evaluating, setEvaluating] = useState(false);
  const [turnResult, setTurnResult] = useState<any | null>(null);
  const [isRecording, setIsRecording] = useState(false);

  // Completed session report
  const [finalReport, setFinalReport] = useState<any | null>(null);
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
          setSelectedRole(data[0].name);
        }
      })
      .catch(() => {})
      .finally(() => {
        setLoading(false);
      });
  }, [router]);

  const handleStartInterview = async () => {
    if (!profileId) return;
    setLoading(true);
    setError(null);
    setFinalReport(null);

    try {
      const res = await interviewsApi.startInterview({
        profileId,
        roleName: selectedRole,
        category: selectedCategory,
        difficulty: selectedDifficulty,
        durationMinutes: selectedDuration,
      });

      setActiveSession({
        session_id: res.session_id,
        role_name: res.role_name,
        category: res.category,
      });

      setCurrentQuestion(res.current_question);
      setUserAnswer("");
      setTurnResult(null);
    } catch (err: any) {
      setError(err.message || "Failed to start interview session.");
    } finally {
      setLoading(false);
    }
  };

  const handleSubmitAnswer = async () => {
    if (!activeSession || !currentQuestion || !userAnswer.trim()) {
      setError("Please provide an answer before submitting.");
      return;
    }

    setEvaluating(true);
    setError(null);

    try {
      const evalRes = await interviewsApi.submitAnswer(
        activeSession.session_id,
        currentQuestion.turn_id,
        userAnswer
      );
      setTurnResult(evalRes);
    } catch (err: any) {
      setError(err.message || "Evaluation failed. Please try again.");
    } finally {
      setEvaluating(false);
    }
  };

  const handleNextQuestion = async () => {
    if (!activeSession) return;
    setLoading(true);
    setTurnResult(null);
    setUserAnswer("");
    setError(null);

    try {
      const qRes = await interviewsApi.getQuestion(activeSession.session_id);
      setCurrentQuestion(qRes);
    } catch (err: any) {
      setError(err.message || "Failed to generate next question.");
    } finally {
      setLoading(false);
    }
  };

  const handleFinishInterview = async () => {
    if (!activeSession) return;
    setLoading(true);
    setError(null);

    try {
      const report = await interviewsApi.finishInterview(activeSession.session_id);
      setFinalReport(report);
      setActiveSession(null);
      setCurrentQuestion(null);
      setTurnResult(null);
    } catch (err: any) {
      setError(err.message || "Failed to finalize interview report.");
    } finally {
      setLoading(false);
    }
  };

  // Optional Web Speech API Dictation
  const toggleSpeechRecognition = () => {
    if (typeof window === "undefined") return;
    const SpeechRecognition =
      (window as any).SpeechRecognition || (window as any).webkitSpeechRecognition;

    if (!SpeechRecognition) {
      alert("Speech-to-text is not supported in this browser. Please type your response.");
      return;
    }

    if (isRecording) {
      setIsRecording(false);
      return;
    }

    try {
      const recognition = new SpeechRecognition();
      recognition.continuous = true;
      recognition.interimResults = true;
      recognition.lang = "en-US";

      recognition.onstart = () => setIsRecording(true);
      recognition.onend = () => setIsRecording(false);
      recognition.onerror = () => setIsRecording(false);

      recognition.onresult = (event: any) => {
        let transcript = "";
        for (let i = 0; i < event.results.length; i++) {
          transcript += event.results[i][0].transcript;
        }
        setUserAnswer((prev) => (prev ? `${prev} ${transcript}` : transcript));
      };

      recognition.start();
    } catch {
      setIsRecording(false);
    }
  };

  return (
    <div className="min-h-screen bg-[#F7F6F3] text-[#37352F]">
      <Navbar />

      <main className="page-wrapper py-8 sm:py-10 space-y-8">
        {/* Header */}
        <div className="pb-6 border-b border-[#e2e4e8]">
          <div className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full bg-blue-50 text-blue-700 text-xs font-semibold mb-2 border border-blue-200">
            <span className="w-1.5 h-1.5 rounded-full bg-blue-600" />
            <span>AI Mock Interview Simulator</span>
          </div>
          <h1 className="text-2xl sm:text-3xl lg:text-4xl font-extrabold tracking-tight text-[#111827]">
            Interactive Technical Mock Interview
          </h1>
          <p className="text-sm sm:text-base text-[#656d76] mt-1.5 max-w-3xl">
            Practice role-specific interview rounds with instant 5-dimension rubric critiques, project defense questions based on your resume, and gold-standard model answers.
          </p>
        </div>

        {error && (
          <div className="mb-6 p-4 rounded-lg bg-[#FDE8E8] border border-[#F8B4B4] text-[#9B1C1C] text-xs">
            {error}
          </div>
        )}

        {loading ? (
          <div className="flex justify-center py-20">
            <LoadingSpinner size="lg" text="Preparing interview coach..." />
          </div>
        ) : finalReport ? (
          /* Final Performance Scorecard */
          <div className="bg-white rounded-xl border border-[#E9E9E7] p-8 shadow-xs space-y-6">
            <div className="text-center space-y-2">
              <span className="text-3xl">🏆</span>
              <h2 className="text-2xl font-bold text-[#37352F]">
                Mock Interview Performance Report
              </h2>
              <span className="text-xs text-[#8A8985] block">
                Target Role: {finalReport.role_name} • Category: {finalReport.category}
              </span>
            </div>

            <div className="p-6 bg-[#F7F6F3] rounded-xl text-center space-y-2">
              <span className="text-xs text-[#8A8985] font-semibold uppercase tracking-wider">
                Overall Interview Score
              </span>
              <div className="text-4xl font-extrabold text-[#2383E2]">
                {finalReport.overall_score}%
              </div>
              <p className="text-xs text-[#37352F] max-w-xl mx-auto pt-2 font-medium">
                {finalReport.final_feedback}
              </p>
            </div>

            {/* Strengths & Improvements */}
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6 pt-2">
              <div className="p-4 bg-[#DEF7EC] rounded-lg border border-[#BCF0DA]">
                <h4 className="text-xs font-bold text-[#03543F] uppercase tracking-wider mb-2">
                  Demonstrated Strengths
                </h4>
                <ul className="list-disc pl-4 text-xs text-[#03543F] space-y-1.5">
                  {finalReport.strengths?.map((s: string, idx: number) => (
                    <li key={idx}>{s}</li>
                  ))}
                </ul>
              </div>

              <div className="p-4 bg-[#FDE8E8] rounded-lg border border-[#F8B4B4]">
                <h4 className="text-xs font-bold text-[#9B1C1C] uppercase tracking-wider mb-2">
                  Priority Action Areas
                </h4>
                <ul className="list-disc pl-4 text-xs text-[#9B1C1C] space-y-1.5">
                  {finalReport.improvements?.map((imp: string, idx: number) => (
                    <li key={idx}>{imp}</li>
                  ))}
                </ul>
              </div>
            </div>

            <div className="text-[11px] text-[#8A8985] italic text-center pt-2">
              {finalReport.disclaimer}
            </div>

            <div className="flex gap-3 pt-4 border-t border-[#E9E9E7]">
              <button
                onClick={() => setFinalReport(null)}
                className="flex-1 py-2.5 rounded-lg bg-white border border-[#E9E9E7] text-xs font-semibold text-[#37352F] hover:bg-[#F7F6F3]"
              >
                Start New Practice Session
              </button>
              <Link
                href="/roadmap"
                className="flex-1 py-2.5 text-center rounded-lg bg-[#2383E2] text-white text-xs font-semibold hover:bg-[#1A73E8]"
              >
                Review Learning Roadmap &rarr;
              </Link>
            </div>
          </div>
        ) : activeSession && currentQuestion ? (
          /* Live Interview Q&A Room */
          <div className="bg-white rounded-xl border border-[#E9E9E7] p-6 shadow-xs space-y-6">
            <div className="flex items-center justify-between pb-4 border-b border-[#E9E9E7]">
              <div>
                <span className="text-[11px] font-semibold text-[#2383E2] uppercase tracking-wider">
                  Question #{currentQuestion.turn_number} • {activeSession.category.toUpperCase()}
                </span>
                <h3 className="text-lg font-bold text-[#37352F] mt-1">
                  {currentQuestion.question}
                </h3>
              </div>

              <button
                onClick={handleFinishInterview}
                className="text-xs px-3 py-1 rounded border border-[#E9E9E7] bg-white hover:bg-[#FDE8E8] hover:text-[#E03E3E] text-[#6B6B6B] font-medium"
              >
                End Session
              </button>
            </div>

            {currentQuestion.context_snippet && (
              <div className="p-3 bg-[#F7F6F3] rounded-lg border border-[#E9E9E7] text-xs text-[#6B6B6B]">
                <span className="font-semibold text-[#37352F]">Context: </span>
                {currentQuestion.context_snippet}
              </div>
            )}

            {!turnResult ? (
              /* Answer Textarea */
              <div className="space-y-4">
                <div>
                  <div className="flex items-center justify-between mb-1.5">
                    <label className="text-xs font-medium text-[#6B6B6B]">Your Answer:</label>
                    <button
                      onClick={toggleSpeechRecognition}
                      className={`text-xs px-2.5 py-0.5 rounded-md flex items-center gap-1.5 transition-colors ${
                        isRecording ? "bg-[#FDE8E8] text-[#E03E3E] animate-pulse" : "bg-[#F7F6F3] text-[#6B6B6B]"
                      }`}
                    >
                      <span>🎙️</span>
                      {isRecording ? "Listening..." : "Dictate with Mic"}
                    </button>
                  </div>

                  <textarea
                    rows={8}
                    value={userAnswer}
                    onChange={(e) => setUserAnswer(e.target.value)}
                    placeholder="Structure your answer with context, approach, technical implementation, and metrics..."
                    className="w-full text-xs p-3.5 rounded-lg border border-[#E9E9E7] text-[#37352F] focus:outline-none focus:border-[#2383E2] bg-[#FAFAFA]"
                  />
                </div>

                <button
                  onClick={handleSubmitAnswer}
                  disabled={evaluating || !userAnswer.trim()}
                  className="w-full py-2.5 rounded-lg bg-[#2383E2] hover:bg-[#1A73E8] text-white text-xs font-semibold transition-colors flex items-center justify-center gap-2 disabled:opacity-50"
                >
                  {evaluating ? (
                    <>
                      <div className="w-3.5 h-3.5 border-2 border-white border-t-transparent rounded-full animate-spin" />
                      Evaluating against 5-Dimension Rubric...
                    </>
                  ) : (
                    "Submit Answer for Evaluation"
                  )}
                </button>
              </div>
            ) : (
              /* Turn Rubric Evaluation Feedback */
              <div className="space-y-5 pt-2">
                <div className="p-4 bg-[#F7F6F3] rounded-xl border border-[#E9E9E7] space-y-3">
                  <div className="flex items-center justify-between">
                    <span className="text-xs font-semibold text-[#37352F]">Question Score:</span>
                    <span className="text-xl font-bold text-[#2383E2]">{turnResult.score}%</span>
                  </div>

                  {/* Rubric metrics breakdown */}
                  {turnResult.rubric && (
                    <div className="grid grid-cols-5 gap-2 pt-1 text-center">
                      {Object.entries(turnResult.rubric).map(([k, v]) => (
                        <div key={k} className="p-2 bg-white rounded border border-[#E9E9E7]">
                          <span className="text-[10px] text-[#8A8985] uppercase block truncate">{k}</span>
                          <span className="text-xs font-bold text-[#37352F]">{String(v)}%</span>
                        </div>
                      ))}
                    </div>
                  )}

                  <p className="text-xs text-[#37352F] leading-relaxed pt-1">
                    {turnResult.feedback}
                  </p>
                </div>

                {/* Missing concepts */}
                {turnResult.missing_concepts?.length > 0 && (
                  <div>
                    <span className="text-xs font-semibold text-[#9B1C1C] block mb-1.5">
                      Key Concepts You Missed:
                    </span>
                    <div className="flex flex-wrap gap-1.5">
                      {turnResult.missing_concepts.map((c: string, idx: number) => (
                        <span key={idx} className="text-[11px] px-2 py-0.5 rounded bg-[#FDE8E8] text-[#9B1C1C]">
                          {c}
                        </span>
                      ))}
                    </div>
                  </div>
                )}

                {/* Example Strong Response */}
                {turnResult.example_answer && (
                  <div className="p-4 rounded-lg bg-[#EBF5FB] border border-[#BCF0DA]/30 text-xs text-[#37352F] space-y-1.5">
                    <span className="font-semibold text-[#2383E2] block">Gold-Standard Model Answer:</span>
                    <p className="text-xs leading-relaxed text-[#37352F] whitespace-pre-wrap">
                      {turnResult.example_answer}
                    </p>
                  </div>
                )}

                <div className="flex items-center justify-between pt-3 border-t border-[#E9E9E7]">
                  <button
                    onClick={handleFinishInterview}
                    className="py-2 px-4 rounded-lg border border-[#E9E9E7] bg-white hover:bg-[#F1F1EF] text-xs font-semibold text-[#6B6B6B]"
                  >
                    Finish & View Scorecard
                  </button>

                  <button
                    onClick={handleNextQuestion}
                    className="py-2 px-4 rounded-lg bg-[#2383E2] hover:bg-[#1A73E8] text-white text-xs font-semibold transition-colors"
                  >
                    Next Question &rarr;
                  </button>
                </div>
              </div>
            )}
          </div>
        ) : (
          /* Interview Setup Card */
          <div className="bg-white rounded-xl border border-[#E9E9E7] p-8 shadow-xs space-y-6">
            <h2 className="text-base font-semibold text-[#37352F]">Configure Your Practice Session</h2>

            {/* Target Role Selector */}
            <div>
              <label className="block text-xs font-medium text-[#6B6B6B] mb-1.5">Target Career Role:</label>
              <select
                value={selectedRole}
                onChange={(e) => setSelectedRole(e.target.value)}
                className="w-full p-2.5 rounded-lg border border-[#E9E9E7] bg-white text-xs text-[#37352F] font-medium focus:outline-none focus:border-[#2383E2]"
              >
                {careers.map((c) => (
                  <option key={c.id} value={c.name}>
                    {c.name}
                  </option>
                ))}
              </select>
            </div>

            {/* Category Cards */}
            <div>
              <label className="block text-xs font-medium text-[#6B6B6B] mb-2">Practice Round Category:</label>
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                {CATEGORIES.map((cat) => (
                  <div
                    key={cat.id}
                    onClick={() => setSelectedCategory(cat.id)}
                    className={`p-4 rounded-xl border cursor-pointer transition-all ${
                      selectedCategory === cat.id
                        ? "border-[#2383E2] bg-[#EBF5FB] shadow-xs"
                        : "border-[#E9E9E7] hover:bg-[#F7F6F3]"
                    }`}
                  >
                    <div className="flex items-center gap-2 mb-1">
                      <span className="text-lg">{cat.icon}</span>
                      <span className="text-xs font-bold text-[#37352F]">{cat.label}</span>
                    </div>
                    <p className="text-[11px] text-[#6B6B6B] leading-relaxed">{cat.desc}</p>
                  </div>
                ))}
              </div>
            </div>

            {/* Difficulty & Duration */}
            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="block text-xs font-medium text-[#6B6B6B] mb-1.5">Difficulty Tier:</label>
                <select
                  value={selectedDifficulty}
                  onChange={(e) => setSelectedDifficulty(e.target.value)}
                  className="w-full p-2.5 rounded-lg border border-[#E9E9E7] bg-white text-xs text-[#37352F] font-medium focus:outline-none"
                >
                  <option value="Beginner">Beginner (Foundations & Syntax)</option>
                  <option value="Intermediate">Intermediate (Core Architecture)</option>
                  <option value="Advanced">Advanced (Scale & Complex Tradeoffs)</option>
                </select>
              </div>

              <div>
                <label className="block text-xs font-medium text-[#6B6B6B] mb-1.5">Session Length:</label>
                <select
                  value={selectedDuration}
                  onChange={(e) => setSelectedDuration(parseInt(e.target.value, 10))}
                  className="w-full p-2.5 rounded-lg border border-[#E9E9E7] bg-white text-xs text-[#37352F] font-medium focus:outline-none"
                >
                  <option value={15}>15 Minutes (Sprint Practice)</option>
                  <option value={30}>30 Minutes (Standard Round)</option>
                  <option value={45}>45 Minutes (Full Simulation)</option>
                </select>
              </div>
            </div>

            <button
              onClick={handleStartInterview}
              className="w-full py-3 rounded-lg bg-[#2383E2] hover:bg-[#1A73E8] text-white text-xs font-semibold transition-colors shadow-xs"
            >
              Start Mock Interview Room &rarr;
            </button>
          </div>
        )}
      </main>
    </div>
  );
}
