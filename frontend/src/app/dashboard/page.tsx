"use client";

import { FormEvent, useEffect, useRef, useState } from "react";
import { onAuthStateChanged, signOut, User } from "firebase/auth";
import { useRouter } from "next/navigation";

import {
  fetchProfileStatus,
  saveProfile,
  sendChatMessage,
  UserProfile,
} from "@/lib/api";
import { auth, isFirebaseConfigured, missingFirebaseConfigKeys } from "@/lib/firebase";
import ReactMarkdown from "react-markdown";

type ChatMessage = {
  id: string;
  role: "user" | "assistant";
  text: string;
};

const starterMessage: ChatMessage = {
  id: "starter",
  role: "assistant",
  text:
    "Welcome back. I can analyze EGX ticker momentum, daily market pulse, and tailor guidance based on your profile.",
};

function formatCurrency(value: number): string {
  return new Intl.NumberFormat("en-EG", {
    style: "currency",
    currency: "EGP",
    maximumFractionDigits: 0,
  }).format(value);
}

export default function DashboardPage() {
  const router = useRouter();
  const [user, setUser] = useState<User | null>(null);
  const [profile, setProfile] = useState<UserProfile | null>(null);
  const [loading, setLoading] = useState(Boolean(auth));
  const [sending, setSending] = useState(false);
  const [draft, setDraft] = useState("");
  const [messages, setMessages] = useState<ChatMessage[]>([starterMessage]);
  const [error, setError] = useState("");
  const [editingProfile, setEditingProfile] = useState(false);
  const [profileDraft, setProfileDraft] = useState<UserProfile | null>(null);
  const [profileSaving, setProfileSaving] = useState(false);
  const [profileError, setProfileError] = useState("");
  const [profileSuccess, setProfileSuccess] = useState("");
  const messagesEndRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  useEffect(() => {
    if (!auth) {
      return;
    }

    const unsubscribe = onAuthStateChanged(auth, async (currentUser) => {
      if (!currentUser) {
        router.replace("/login");
        return;
      }

      try {
        const profileStatus = await fetchProfileStatus(currentUser);
        if (!profileStatus.has_profile || !profileStatus.profile) {
          router.replace("/onboarding");
          return;
        }

        setUser(currentUser);
        setProfile(profileStatus.profile);
        setProfileDraft(profileStatus.profile);
        setError("");
      } catch (profileError) {
        const details =
          profileError instanceof Error
            ? profileError.message
            : "Unable to load profile data";
        setError(details);
        router.replace("/login");
        return;
      }

      setLoading(false);
    });

    return unsubscribe;
  }, [router]);

  const handleProfileSave = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (!user || !profileDraft || profileSaving) {
      return;
    }

    const normalizedProfile: UserProfile = {
      monthly_income: Number(profileDraft.monthly_income),
      savings: Number(profileDraft.savings),
      risk_tolerance: Number(profileDraft.risk_tolerance),
      investment_goal: profileDraft.investment_goal.trim(),
    };

    if (!Number.isFinite(normalizedProfile.monthly_income) || normalizedProfile.monthly_income < 0) {
      setProfileError("Monthly income must be a valid non-negative number.");
      return;
    }
    if (!Number.isFinite(normalizedProfile.savings) || normalizedProfile.savings < 0) {
      setProfileError("Savings must be a valid non-negative number.");
      return;
    }
    if (
      !Number.isFinite(normalizedProfile.risk_tolerance) ||
      normalizedProfile.risk_tolerance < 1 ||
      normalizedProfile.risk_tolerance > 10
    ) {
      setProfileError("Risk tolerance must be between 1 and 10.");
      return;
    }
    if (!normalizedProfile.investment_goal) {
      setProfileError("Investment goal cannot be empty.");
      return;
    }

    try {
      setProfileSaving(true);
      setProfileError("");
      setProfileSuccess("");
      await saveProfile(user, normalizedProfile);
      setProfile(normalizedProfile);
      setProfileDraft(normalizedProfile);
      setEditingProfile(false);
      setProfileSuccess("Profile updated successfully.");
    } catch (saveError) {
      const details =
        saveError instanceof Error ? saveError.message : "Unable to save profile changes";
      setProfileError(details);
    } finally {
      setProfileSaving(false);
    }
  };

  const handleSendMessage = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    const trimmed = draft.trim();
    if (!trimmed || !user || sending) {
      return;
    }

    const userMessage: ChatMessage = {
      id: `user-${Date.now()}`,
      role: "user",
      text: trimmed,
    };

    setMessages((prev) => [...prev, userMessage]);
    setDraft("");
    setSending(true);
    setError("");

    try {
      const responseText = await sendChatMessage(user, trimmed);
      const assistantMessage: ChatMessage = {
        id: `assistant-${Date.now()}`,
        role: "assistant",
        text: responseText,
      };
      setMessages((prev) => [...prev, assistantMessage]);
    } catch (chatError) {
      const details =
        chatError instanceof Error
          ? chatError.message
          : "Unable to get assistant response";
      setError(details);
      setMessages((prev) => [
        ...prev,
        {
          id: `assistant-error-${Date.now()}`,
          role: "assistant",
          text: "The advisory engine is temporarily unavailable. Please try again.",
        },
      ]);
    } finally {
      setSending(false);
    }
  };

  if (!isFirebaseConfigured) {
    return (
      <main className="min-h-screen bg-amber-50 px-6 py-20 text-slate-900">
        <div className="mx-auto max-w-2xl rounded-2xl border border-amber-300 bg-white p-8 shadow-sm">
          <h1 className="text-2xl font-semibold">Firebase config missing</h1>
          <ul className="mt-4 list-disc pl-6 text-sm text-slate-800">
            {missingFirebaseConfigKeys.map((key) => (
              <li key={key}>{key}</li>
            ))}
          </ul>
        </div>
      </main>
    );
  }

  if (loading) {
    return (
      <main className="min-h-screen bg-[#06070b] px-6 py-16 text-slate-100">
        <div className="mx-auto max-w-xl rounded-2xl border border-slate-700/50 bg-slate-900/60 p-8 shadow-2xl">
          <p className="text-sm text-slate-300">Loading dashboard...</p>
        </div>
      </main>
    );
  }

  return (
    <main className="relative min-h-screen overflow-hidden bg-[#06070b] text-slate-100">
      <div className="pointer-events-none absolute inset-0 bg-[radial-gradient(circle_at_20%_10%,rgba(34,197,94,0.22),transparent_45%),radial-gradient(circle_at_80%_80%,rgba(14,165,233,0.2),transparent_42%)]" />

      <div className="relative mx-auto grid min-h-screen w-full max-w-[1300px] grid-cols-1 gap-4 px-4 py-4 lg:grid-cols-[320px_1fr] lg:p-6">
        <aside className="rounded-2xl border border-slate-700/70 bg-slate-900/70 p-5 backdrop-blur">
          <p className="text-xs uppercase tracking-[0.2em] text-emerald-300">Current User Profile</p>
        

          {editingProfile && profileDraft ? (
            <form onSubmit={handleProfileSave} className="mt-6 space-y-3">
              <div>
                <label className="block text-xs font-semibold uppercase tracking-[0.12em] text-slate-400">
                  Monthly Income (EGP)
                </label>
                <input
                  type="number"
                  min={0}
                  step="1"
                  value={profileDraft.monthly_income}
                  onChange={(event) => {
                    const nextValue = Number(event.target.value);
                    setProfileDraft((prev) =>
                      prev && Number.isFinite(nextValue)
                        ? { ...prev, monthly_income: nextValue }
                        : prev
                    );
                  }}
                  className="mt-1 w-full rounded-lg border border-slate-600 bg-slate-950 px-3 py-2 text-sm text-slate-100 outline-none focus:border-emerald-400"
                />
              </div>

              <div>
                <label className="block text-xs font-semibold uppercase tracking-[0.12em] text-slate-400">
                  Savings (EGP)
                </label>
                <input
                  type="number"
                  min={0}
                  step="1"
                  value={profileDraft.savings}
                  onChange={(event) => {
                    const nextValue = Number(event.target.value);
                    setProfileDraft((prev) =>
                      prev && Number.isFinite(nextValue)
                        ? { ...prev, savings: nextValue }
                        : prev
                    );
                  }}
                  className="mt-1 w-full rounded-lg border border-slate-600 bg-slate-950 px-3 py-2 text-sm text-slate-100 outline-none focus:border-emerald-400"
                />
              </div>

              <div>
                <label className="block text-xs font-semibold uppercase tracking-[0.12em] text-slate-400">
                  Risk Tolerance (1-10)
                </label>
                <input
                  type="number"
                  min={1}
                  max={10}
                  step="1"
                  value={profileDraft.risk_tolerance}
                  onChange={(event) => {
                    const nextValue = Number(event.target.value);
                    setProfileDraft((prev) =>
                      prev && Number.isFinite(nextValue)
                        ? { ...prev, risk_tolerance: nextValue }
                        : prev
                    );
                  }}
                  className="mt-1 w-full rounded-lg border border-slate-600 bg-slate-950 px-3 py-2 text-sm text-slate-100 outline-none focus:border-emerald-400"
                />
              </div>

              <div>
                <label className="block text-xs font-semibold uppercase tracking-[0.12em] text-slate-400">
                  Investment Goal
                </label>
                <textarea
                  value={profileDraft.investment_goal}
                  onChange={(event) =>
                    setProfileDraft((prev) =>
                      prev ? { ...prev, investment_goal: event.target.value } : prev
                    )
                  }
                  rows={3}
                  className="mt-1 w-full rounded-lg border border-slate-600 bg-slate-950 px-3 py-2 text-sm text-slate-100 outline-none focus:border-emerald-400"
                  placeholder="e.g. Build emergency fund and long-term growth portfolio"
                />
              </div>

              <div className="grid grid-cols-2 gap-2 pt-1">
                <button
                  type="button"
                  onClick={() => {
                    setProfileDraft(profile);
                    setEditingProfile(false);
                    setProfileError("");
                  }}
                  className="rounded-lg border border-slate-600 bg-slate-900 px-3 py-2 text-sm font-semibold text-slate-200 transition hover:bg-slate-800"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={profileSaving}
                  className="rounded-lg bg-emerald-500 px-3 py-2 text-sm font-semibold text-slate-950 transition hover:bg-emerald-400 disabled:cursor-not-allowed disabled:bg-slate-600 disabled:text-slate-300"
                >
                  {profileSaving ? "Saving..." : "Save"}
                </button>
              </div>
              {profileError && <p className="text-xs text-rose-300">{profileError}</p>}
            </form>
          ) : (
            <div className="mt-6 space-y-4">
              <div className="rounded-xl border border-slate-700 bg-slate-950/70 p-4">
                <p className="text-xs text-slate-400">Monthly Income</p>
                <p className="mt-1 text-lg font-semibold text-emerald-300">
                  {profile ? formatCurrency(profile.monthly_income) : "-"}
                </p>
              </div>
              <div className="rounded-xl border border-slate-700 bg-slate-950/70 p-4">
                <p className="text-xs text-slate-400">Savings</p>
                <p className="mt-1 text-lg font-semibold text-sky-300">
                  {profile ? formatCurrency(profile.savings) : "-"}
                </p>
              </div>
              <div className="rounded-xl border border-slate-700 bg-slate-950/70 p-4">
                <p className="text-xs text-slate-400">Risk Tolerance</p>
                <p className="mt-1 text-lg font-semibold text-amber-300">
                  {profile ? `${profile.risk_tolerance}/10` : "-"}
                </p>
              </div>
              <div className="rounded-xl border border-slate-700 bg-slate-950/70 p-4">
                <p className="text-xs text-slate-400">Investment Goal</p>
                <p className="mt-1 text-sm text-slate-200">
                  {profile ? profile.investment_goal : "-"}
                </p>
              </div>
              <button
                type="button"
                onClick={() => {
                  setEditingProfile(true);
                  setProfileDraft(profile);
                  setProfileError("");
                  setProfileSuccess("");
                }}
                className="w-full rounded-lg border border-slate-600 bg-slate-900 px-3 py-2 text-sm font-semibold text-slate-200 transition hover:bg-slate-800"
              >
                Edit profile
              </button>
              {profileSuccess && <p className="text-xs text-emerald-300">{profileSuccess}</p>}
            </div>
          )}

          <div className="mt-8 border-t border-slate-700 pt-5 text-xs text-slate-300">
            <p className="truncate">{user?.email ?? user?.uid}</p>
            <button
              type="button"
              onClick={async () => {
                if (!auth) {
                  return;
                }
                await signOut(auth);
                router.replace("/login");
              }}
              className="mt-3 rounded-lg border border-slate-600 bg-slate-900 px-3 py-2 font-semibold text-slate-200 transition hover:border-slate-500 hover:bg-slate-800"
            >
              Sign out
            </button>
          </div>
        </aside>

        <section className="flex min-h-[70vh] flex-col rounded-2xl border border-slate-700/70 bg-slate-900/70 backdrop-blur">
          <header className="border-b border-slate-700/70 px-5 py-4 sm:px-6">
            <h1 className="text-xl font-semibold tracking-tight sm:text-2xl">Conversation Dashboard</h1>
            <p className="mt-1 text-xs text-slate-300 sm:text-sm">
              Ask about market pulse, ticker momentum, and portfolio actions aligned to your profile.
            </p>
          </header>

          <div className="flex-1 space-y-4 overflow-y-auto px-5 py-5 sm:px-6">
            {messages.map((message) => (
              <article
                key={message.id}
                className={`max-w-3xl rounded-2xl border px-4 py-3 text-sm leading-6 sm:text-[15px] ${
                  message.role === "user"
                    ? "ml-auto border-emerald-500/50 bg-emerald-500/15 text-emerald-50"
                    : "border-slate-700 bg-slate-950/80 text-slate-100"
                }`}
              >
                <p className="mb-1 text-[11px] font-semibold uppercase tracking-[0.14em] text-slate-400">
                  {message.role === "user" ? "You" : "Advisor"}
                </p>
                <div className="whitespace-pre-wrap">
                 <ReactMarkdown>{message.text}</ReactMarkdown>
                </div>
                
              </article>
            ))}
            <div ref={messagesEndRef} />
          </div>

          <div className="border-t border-slate-700/70 p-4 sm:p-5">
            <form onSubmit={handleSendMessage} className="flex flex-col gap-3 sm:flex-row">
              <input
                type="text"
                value={draft}
                onChange={(event) => setDraft(event.target.value)}
                placeholder="Ask: How is COMI performing this month, and does it fit my risk level?"
                className="w-full rounded-xl border border-slate-600 bg-slate-950 px-4 py-3 text-sm text-slate-100 outline-none placeholder:text-slate-500 focus:border-emerald-400"
              />
              <button
                type="submit"
                disabled={sending || !draft.trim()}
                className="rounded-xl bg-emerald-500 px-5 py-3 text-sm font-semibold text-slate-950 transition hover:bg-emerald-400 disabled:cursor-not-allowed disabled:bg-slate-600 disabled:text-slate-300"
              >
                {sending ? "Thinking..." : "Send"}
              </button>
            </form>
            {error && <p className="mt-2 text-xs text-rose-300">{error}</p>}
          </div>
        </section>
      </div>
    </main>
  );
}
