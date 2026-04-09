"use client";

import { FormEvent, useEffect, useState } from "react";
import { onAuthStateChanged, User } from "firebase/auth";
import { useRouter } from "next/navigation";

import { saveProfile, UserProfile } from "@/lib/api";
import { auth, isFirebaseConfigured, missingFirebaseConfigKeys } from "@/lib/firebase";
import { resolvePostLoginRoute } from "@/lib/profile-routing";

const initialState: UserProfile = {
  monthly_income: 0,
  savings: 0,
  investment_goal: "",
  risk_tolerance: 5,
};

export default function OnboardingPage() {
  const router = useRouter();
  const [user, setUser] = useState<User | null>(null);
  const [formData, setFormData] = useState<UserProfile>(initialState);
  const [booting, setBooting] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    if (!auth) {
      setBooting(false);
      return;
    }

    const unsubscribe = onAuthStateChanged(auth, async (currentUser) => {
      if (!currentUser) {
        router.replace("/login");
        return;
      }

      try {
        const destination = await resolvePostLoginRoute(currentUser);
        if (destination === "/dashboard") {
          router.replace(destination);
          return;
        }

        setUser(currentUser);
      } catch (routeError) {
        const details =
          routeError instanceof Error
            ? routeError.message
            : "Unable to check profile status";
        setError(details);
      } finally {
        setBooting(false);
      }
    });

    return unsubscribe;
  }, [router]);

  const handleSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (!user) {
      setError("Please log in again.");
      return;
    }

    try {
      setSubmitting(true);
      setError("");
      await saveProfile(user, formData);
      router.replace("/dashboard");
    } catch (submitError) {
      const details =
        submitError instanceof Error ? submitError.message : "Unable to save profile";
      setError(details);
    } finally {
      setSubmitting(false);
    }
  };

  if (!isFirebaseConfigured) {
    return (
      <main className="relative min-h-screen overflow-hidden bg-[#06070b] px-6 py-20 text-slate-100">
        <div className="pointer-events-none absolute inset-0 bg-[radial-gradient(circle_at_20%_10%,rgba(34,197,94,0.22),transparent_45%),radial-gradient(circle_at_80%_80%,rgba(14,165,233,0.2),transparent_42%)]" />
        <div className="relative mx-auto max-w-2xl rounded-2xl border border-slate-700/70 bg-slate-900/70 p-8 shadow-2xl backdrop-blur">
          <h1 className="text-2xl font-semibold">Firebase config missing</h1>
          <ul className="mt-4 list-disc pl-6 text-sm text-slate-200">
            {missingFirebaseConfigKeys.map((key) => (
              <li key={key}>{key}</li>
            ))}
          </ul>
        </div>
      </main>
    );
  }

  if (booting) {
    return (
      <main className="relative min-h-screen overflow-hidden bg-[#06070b] px-6 py-20 text-slate-100">
        <div className="pointer-events-none absolute inset-0 bg-[radial-gradient(circle_at_20%_10%,rgba(34,197,94,0.22),transparent_45%),radial-gradient(circle_at_80%_80%,rgba(14,165,233,0.2),transparent_42%)]" />
        <div className="relative mx-auto max-w-3xl rounded-3xl border border-slate-700/70 bg-slate-900/70 p-8 shadow-2xl backdrop-blur">
          <p className="text-sm text-slate-300">Preparing your onboarding profile...</p>
        </div>
      </main>
    );
  }

  return (
    <main className="relative min-h-screen overflow-hidden bg-[#06070b] px-6 py-14 text-slate-100">
      <div className="pointer-events-none absolute inset-0 bg-[radial-gradient(circle_at_20%_10%,rgba(34,197,94,0.22),transparent_45%),radial-gradient(circle_at_80%_80%,rgba(14,165,233,0.2),transparent_42%)]" />

      <div className="relative mx-auto max-w-3xl rounded-3xl border border-slate-700/70 bg-slate-900/70 p-8 shadow-2xl backdrop-blur sm:p-10">
        <p className="text-xs font-semibold uppercase tracking-[0.2em] text-emerald-300">
          Egyptian Financial Advisor
        </p>
        <h1 className="mt-3 text-3xl font-semibold tracking-tight text-slate-100 sm:text-4xl">
          Build your investment profile
        </h1>
        <p className="mt-3 max-w-2xl text-sm leading-6 text-slate-300">
          We use this profile to personalize market insights and recommendations
          around EGX stocks, FX, and gold.
        </p>

        <form onSubmit={handleSubmit} className="mt-8 grid gap-6">
          <div className="grid gap-6 sm:grid-cols-2">
            <label className="space-y-2">
              <span className="text-sm font-medium text-slate-200">Monthly Income (EGP)</span>
              <input
                type="number"
                min={0}
                step="0.01"
                value={formData.monthly_income || ""}
                onChange={(event) =>
                  setFormData((prev) => ({
                    ...prev,
                    monthly_income: Number(event.target.value),
                  }))
                }
                required
                className="w-full rounded-xl border border-slate-600 bg-slate-950 px-4 py-3 text-sm text-slate-100 outline-none transition focus:border-emerald-400"
                placeholder="35000"
              />
            </label>

            <label className="space-y-2">
              <span className="text-sm font-medium text-slate-200">Current Savings (EGP)</span>
              <input
                type="number"
                min={0}
                step="0.01"
                value={formData.savings || ""}
                onChange={(event) =>
                  setFormData((prev) => ({ ...prev, savings: Number(event.target.value) }))
                }
                required
                className="w-full rounded-xl border border-slate-600 bg-slate-950 px-4 py-3 text-sm text-slate-100 outline-none transition focus:border-emerald-400"
                placeholder="120000"
              />
            </label>
          </div>

          <label className="space-y-2">
            <span className="text-sm font-medium text-slate-200">Investment Goal</span>
            <input
              type="text"
              value={formData.investment_goal}
              onChange={(event) =>
                setFormData((prev) => ({ ...prev, investment_goal: event.target.value }))
              }
              required
              minLength={2}
              maxLength={200}
              className="w-full rounded-xl border border-slate-600 bg-slate-950 px-4 py-3 text-sm text-slate-100 outline-none transition focus:border-emerald-400"
              placeholder="Buy a home in 5 years"
            />
          </label>

          <label className="space-y-3">
            <div className="flex items-center justify-between">
              <span className="text-sm font-medium text-slate-200">Risk Tolerance</span>
              <span className="rounded-full bg-emerald-500 px-3 py-1 text-xs font-semibold text-slate-950">
                {formData.risk_tolerance}/10
              </span>
            </div>
            <input
              type="range"
              min={1}
              max={10}
              step={1}
              value={formData.risk_tolerance}
              onChange={(event) =>
                setFormData((prev) => ({
                  ...prev,
                  risk_tolerance: Number(event.target.value),
                }))
              }
              className="w-full accent-emerald-500"
            />
            <div className="flex justify-between text-xs text-slate-400">
              <span>Conservative</span>
              <span>Aggressive</span>
            </div>
          </label>

          <button
            type="submit"
            disabled={submitting}
            className="mt-2 rounded-xl bg-emerald-500 px-5 py-3 text-sm font-semibold text-slate-950 transition hover:bg-emerald-400 disabled:cursor-not-allowed disabled:bg-slate-600 disabled:text-slate-300"
          >
            {submitting ? "Saving profile..." : "Save and continue"}
          </button>

          {error && <p className="text-sm text-rose-300">{error}</p>}
        </form>
      </div>
    </main>
  );
}
