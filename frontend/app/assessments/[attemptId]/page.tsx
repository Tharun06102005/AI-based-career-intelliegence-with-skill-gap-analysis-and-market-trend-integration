"use client";

import React, { useState, useEffect } from "react";
import { useParams, useRouter } from "next/navigation";
import Link from "next/link";
import { Navbar } from "../../../components/Navbar";
import LoadingSpinner from "../../../components/ui/LoadingSpinner";
import { isLoggedIn } from "../../../lib/auth";
import { assessmentsApi } from "../../../lib/api";

interface QuestionData {
  question_id: number;
  skill_name: string;
  difficulty: string;
  question_type: string;
  question_text: string;
  code_snippet?: string;
  options?: string[];
  has_test_cases: boolean;
  total_answered: number;
}

export default function AssessmentAttemptRunnerPage() {
  const params = useParams();
  const router = useRouter();
  const attemptId = parseInt(params.attemptId as string, 10);

  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [currentQuestion, setCurrentQuestion] = useState<QuestionData | null>(null);
  const [userAnswer, setUserAnswer] = useState("");
  const [submissionResult, setSubmissionResult] = useState<any | null>(null);
  const [isCompleted, setIsCompleted] = useState(false);
  const [finalScorecard, setFinalScorecard] = useState<any | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!isLoggedIn()) {
      router.push("/login");
      return;
    }

    if (!attemptId) {
      setError("Invalid attempt ID.");
      setLoading(false);
      return;
    }

    loadNextQuestion();
  }, [attemptId, router]);

  const loadNextQuestion = async () => {
    setLoading(true);
    setSubmissionResult(null);
    setUserAnswer("");
    setError(null);

    try {
      const res = await assessmentsApi.getNextQuestion(attemptId);
      if (res.has_more && res.question) {
        setCurrentQuestion(res.question);
        if (res.question.code_snippet && res.question.question_type === "coding") {
          setUserAnswer(res.question.code_snippet);
        }
      } else {
        // No further questions, complete the attempt
        handleCompleteAttempt();
      }
    } catch (err: any) {
      setError(err.message || "Failed to load question.");
    } finally {
      setLoading(false);
    }
  };

  const handleSubmitAnswer = async () => {
    if (!currentQuestion || !userAnswer.trim()) {
      setError("Please select or enter an answer before submitting.");
      return;
    }

    setSubmitting(true);
    setError(null);

    try {
      const res = await assessmentsApi.submitAnswer(
        attemptId,
        currentQuestion.question_id,
        userAnswer
      );
      setSubmissionResult(res);
    } catch (err: any) {
      setError(err.message || "Failed to submit answer.");
    } finally {
      setSubmitting(false);
    }
  };

  const handleCompleteAttempt = async () => {
    setLoading(true);
    setError(null);

    try {
      const summary = await assessmentsApi.completeAssessment(attemptId);
      setFinalScorecard(summary);
      setIsCompleted(true);
    } catch (err: any) {
      setError(err.message || "Failed to finalize assessment attempt.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-[#F7F6F3] text-[#37352F]">
      <Navbar />

      <main className="page-wrapper py-8">
        {/* Top Header Bar */}
        <div className="flex items-center justify-between pb-6 mb-6 border-b border-[#E9E9E7]">
          <div>
            <Link
              href="/assessments"
              className="text-xs text-[#6B6B6B] hover:text-[#37352F] flex items-center gap-1 mb-1"
            >
              &larr; Back to Assessments
            </Link>
            <h1 className="text-xl font-bold text-[#37352F]">
              {currentQuestion ? `${currentQuestion.skill_name} Verification` : "Assessment Session"}
            </h1>
          </div>

          {!isCompleted && currentQuestion && (
            <div className="flex items-center gap-2">
              <span className="text-xs px-2.5 py-1 rounded bg-[#EBF5FB] text-[#2383E2] font-semibold">
                Adaptive Level: {currentQuestion.difficulty}
              </span>
              <button
                onClick={handleCompleteAttempt}
                className="text-xs px-3 py-1 rounded border border-[#E9E9E7] bg-white hover:bg-[#F1F1EF] text-[#6B6B6B] font-medium"
              >
                Finish Early
              </button>
            </div>
          )}
        </div>

        {error && (
          <div className="mb-6 p-4 rounded-lg bg-[#FDE8E8] border border-[#F8B4B4] text-[#9B1C1C] text-xs">
            {error}
          </div>
        )}

        {loading ? (
          <div className="flex justify-center py-20">
            <LoadingSpinner size="lg" text="Loading adaptive question..." />
          </div>
        ) : isCompleted && finalScorecard ? (
          /* Final Scorecard */
          <div className="bg-white rounded-xl border border-[#E9E9E7] p-8 shadow-xs max-w-2xl mx-auto space-y-6">
            <div className="text-center space-y-2">
              <div
                className={`w-16 h-16 rounded-full mx-auto flex items-center justify-center text-2xl font-bold ${
                  finalScorecard.passed ? "bg-[#DEF7EC] text-[#03543F]" : "bg-[#FDE8E8] text-[#9B1C1C]"
                }`}
              >
                {finalScorecard.passed ? "✓" : "!"}
              </div>
              <h2 className="text-2xl font-bold text-[#37352F]">
                {finalScorecard.passed ? "Skill Verified Successfully!" : "Assessment Completed"}
              </h2>
              <p className="text-xs text-[#6B6B6B]">
                {finalScorecard.passed
                  ? `Congratulations! You have verified ${finalScorecard.skill_name}. Your CareerFit evidence rating has been elevated.`
                  : `You scored ${finalScorecard.score}%. A minimum of 70% is required to verify this competency.`}
              </p>
            </div>

            {/* Score Grid */}
            <div className="grid grid-cols-3 gap-3 p-4 bg-[#F7F6F3] rounded-lg text-center">
              <div>
                <span className="text-xs text-[#8A8985]">Score</span>
                <p className="text-xl font-bold text-[#37352F]">{finalScorecard.score}%</p>
              </div>
              <div>
                <span className="text-xs text-[#8A8985]">Accuracy</span>
                <p className="text-xl font-bold text-[#37352F]">{finalScorecard.accuracy}%</p>
              </div>
              <div>
                <span className="text-xs text-[#8A8985]">Status</span>
                <p
                  className={`text-sm font-semibold mt-1 ${
                    finalScorecard.passed ? "text-[#03543F]" : "text-[#9B1C1C]"
                  }`}
                >
                  {finalScorecard.passed ? "PASSED" : "NOT PASSED"}
                </p>
              </div>
            </div>

            {/* Strengths & Weaknesses */}
            {finalScorecard.summary && (
              <div className="space-y-4 pt-2">
                {finalScorecard.summary.strengths?.length > 0 && (
                  <div>
                    <h4 className="text-xs font-semibold text-[#03543F] mb-1.5 uppercase tracking-wide">
                      Strengths Identified
                    </h4>
                    <ul className="list-disc pl-5 text-xs text-[#37352F] space-y-1">
                      {finalScorecard.summary.strengths.map((s: string, idx: number) => (
                        <li key={idx}>{s}</li>
                      ))}
                    </ul>
                  </div>
                )}

                {finalScorecard.summary.weaknesses?.length > 0 && (
                  <div>
                    <h4 className="text-xs font-semibold text-[#9B1C1C] mb-1.5 uppercase tracking-wide">
                      Areas to Improve
                    </h4>
                    <ul className="list-disc pl-5 text-xs text-[#6B6B6B] space-y-1">
                      {finalScorecard.summary.weaknesses.map((w: string, idx: number) => (
                        <li key={idx}>{w}</li>
                      ))}
                    </ul>
                  </div>
                )}

                {finalScorecard.summary.next_steps?.length > 0 && (
                  <div>
                    <h4 className="text-xs font-semibold text-[#2383E2] mb-1.5 uppercase tracking-wide">
                      Recommended Next Steps
                    </h4>
                    <ul className="list-disc pl-5 text-xs text-[#37352F] space-y-1">
                      {finalScorecard.summary.next_steps.map((n: string, idx: number) => (
                        <li key={idx}>{n}</li>
                      ))}
                    </ul>
                  </div>
                )}
              </div>
            )}

            <div className="flex gap-3 pt-4 border-t border-[#E9E9E7]">
              <Link
                href="/assessments"
                className="flex-1 py-2.5 text-center rounded-lg bg-white border border-[#E9E9E7] text-xs font-semibold text-[#37352F] hover:bg-[#F7F6F3]"
              >
                Assessments Catalog
              </Link>
              <Link
                href="/dashboard"
                className="flex-1 py-2.5 text-center rounded-lg bg-[#2383E2] text-white text-xs font-semibold hover:bg-[#1A73E8]"
              >
                View Dashboard &rarr;
              </Link>
            </div>
          </div>
        ) : currentQuestion ? (
          /* Active Question Card */
          <div className="bg-white rounded-xl border border-[#E9E9E7] p-6 shadow-xs space-y-5">
            {/* Meta header */}
            <div className="flex items-center justify-between text-xs text-[#8A8985]">
              <span className="font-medium text-[#2383E2] uppercase tracking-wide">
                Question Type: {currentQuestion.question_type}
              </span>
              <span>Question #{currentQuestion.total_answered + 1}</span>
            </div>

            {/* Question Text */}
            <h3 className="text-base font-semibold text-[#37352F] leading-snug">
              {currentQuestion.question_text}
            </h3>

            {/* Code snippet if present */}
            {currentQuestion.code_snippet && (
              <div className="bg-[#1E1E1E] text-[#D4D4D4] p-4 rounded-lg font-mono text-xs overflow-x-auto">
                <pre>{currentQuestion.code_snippet}</pre>
              </div>
            )}

            {/* Answer Input Section */}
            {!submissionResult ? (
              <div className="space-y-4 pt-2">
                {currentQuestion.question_type === "coding" ? (
                  /* Coding Textarea */
                  <div>
                    <label className="block text-xs font-medium text-[#6B6B6B] mb-1.5">
                      Your Code Solution (Python Sandbox):
                    </label>
                    <textarea
                      rows={10}
                      value={userAnswer}
                      onChange={(e) => setUserAnswer(e.target.value)}
                      placeholder="# Write your function solution here"
                      className="w-full font-mono text-xs p-3 rounded-lg border border-[#E9E9E7] bg-[#FAFAFA] text-[#37352F] focus:outline-none focus:border-[#2383E2]"
                    />
                  </div>
                ) : currentQuestion.options && currentQuestion.options.length > 0 ? (
                  /* MCQ Options */
                  <div className="space-y-2">
                    {currentQuestion.options.map((opt, idx) => (
                      <label
                        key={idx}
                        className={`flex items-center gap-3 p-3 rounded-lg border cursor-pointer text-xs transition-all ${
                          userAnswer === opt
                            ? "border-[#2383E2] bg-[#EBF5FB] font-semibold text-[#2383E2]"
                            : "border-[#E9E9E7] hover:bg-[#F7F6F3] text-[#37352F]"
                        }`}
                      >
                        <input
                          type="radio"
                          name="question_opt"
                          value={opt}
                          checked={userAnswer === opt}
                          onChange={() => setUserAnswer(opt)}
                          className="text-[#2383E2] focus:ring-[#2383E2]"
                        />
                        <span>{opt}</span>
                      </label>
                    ))}
                  </div>
                ) : (
                  /* General text input */
                  <div>
                    <input
                      type="text"
                      value={userAnswer}
                      onChange={(e) => setUserAnswer(e.target.value)}
                      placeholder="Type your answer here"
                      className="w-full text-xs p-2.5 rounded-lg border border-[#E9E9E7] text-[#37352F] focus:outline-none focus:border-[#2383E2]"
                    />
                  </div>
                )}

                <button
                  onClick={handleSubmitAnswer}
                  disabled={submitting || !userAnswer.trim()}
                  className="w-full py-2.5 rounded-lg bg-[#2383E2] hover:bg-[#1A73E8] text-white text-xs font-semibold transition-colors flex items-center justify-center gap-2 disabled:opacity-50"
                >
                  {submitting ? (
                    <>
                      <div className="w-3.5 h-3.5 border-2 border-white border-t-transparent rounded-full animate-spin" />
                      Evaluating Answer...
                    </>
                  ) : (
                    "Submit Answer & Evaluate"
                  )}
                </button>
              </div>
            ) : (
              /* Post-Submission Result Feedback */
              <div className="space-y-4 pt-3 border-t border-[#E9E9E7]">
                <div
                  className={`p-4 rounded-lg text-xs ${
                    submissionResult.is_correct
                      ? "bg-[#DEF7EC] border border-[#BCF0DA] text-[#03543F]"
                      : "bg-[#FDE8E8] border border-[#F8B4B4] text-[#9B1C1C]"
                  }`}
                >
                  <div className="font-semibold text-sm mb-1">
                    {submissionResult.is_correct ? "✓ Correct!" : "✗ Needs Review"}
                  </div>
                  <p>{submissionResult.feedback}</p>
                </div>

                {/* Execution output for test cases */}
                {submissionResult.execution_output && (
                  <div className="bg-[#F7F6F3] p-3 rounded-lg border border-[#E9E9E7] text-xs">
                    <span className="font-semibold text-[#37352F] block mb-2">Test Case Results:</span>
                    <div className="space-y-1.5">
                      {submissionResult.execution_output.results?.map((tc: any, i: number) => (
                        <div key={i} className="flex items-center justify-between text-[11px] p-1.5 bg-white rounded border border-[#E9E9E7]">
                          <span className="text-[#6B6B6B]">Case #{tc.test_case_index} ({tc.execution_time_ms}ms)</span>
                          <span className={tc.passed ? "text-[#03543F] font-bold" : "text-[#9B1C1C] font-bold"}>
                            {tc.passed ? "PASSED" : "FAILED"}
                          </span>
                        </div>
                      ))}
                    </div>
                  </div>
                )}

                <div className="flex items-center justify-between pt-2">
                  <span className="text-xs text-[#6B6B6B]">
                    Next Adaptive Level: <strong className="text-[#2383E2]">{submissionResult.next_difficulty}</strong>
                  </span>
                  <button
                    onClick={loadNextQuestion}
                    className="py-2 px-4 rounded-lg bg-[#2383E2] hover:bg-[#1A73E8] text-white text-xs font-semibold transition-colors"
                  >
                    Next Adaptive Question &rarr;
                  </button>
                </div>
              </div>
            )}
          </div>
        ) : (
          <div className="text-center py-12">
            <p className="text-sm text-[#6B6B6B] mb-4">No active question found.</p>
            <button
              onClick={handleCompleteAttempt}
              className="py-2 px-4 rounded-lg bg-[#2383E2] text-white text-xs font-semibold"
            >
              Finish Assessment
            </button>
          </div>
        )}
      </main>
    </div>
  );
}
