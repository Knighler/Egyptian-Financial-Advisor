"use client";

import { FormEvent, useCallback, useEffect, useState } from "react";
import {
  createUserWithEmailAndPassword,
  onAuthStateChanged,
  signInWithEmailAndPassword,
  signInWithPopup,
  User,
} from "firebase/auth";
import { useRouter } from "next/navigation";
import {
  auth,
  googleProvider,
  isFirebaseConfigured,
  missingFirebaseConfigKeys,
} from "@/lib/firebase";
import { resolvePostLoginRoute } from "@/lib/profile-routing";

export default function LoginPage() {
  const router = useRouter();
  const [mode, setMode] = useState<"signin" | "signup">("signin");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [loading, setLoading] = useState(false);
  const [checkingSession, setCheckingSession] = useState(true);
  const [error, setError] = useState("");

  const routeUser = useCallback(async (user: User) => {
    const targetRoute = await resolvePostLoginRoute(user);
    router.replace(targetRoute);
  }, [router]);

  useEffect(() => {
    if (!auth) {
      setCheckingSession(false);
      return;
    }

    const unsubscribe = onAuthStateChanged(auth, async (user) => {
      if (!user) {
        setCheckingSession(false);
        return;
      }

      try {
        await routeUser(user);
      } catch (routeError) {
        const details =
          routeError instanceof Error
            ? routeError.message
            : "Unable to load profile status";
        setError(details);
        setCheckingSession(false);
      }
    });

    return unsubscribe;
  }, [routeUser]);

  if (!isFirebaseConfigured) {
    return (
      <main className="relative min-h-screen overflow-hidden bg-[#06070b] px-6 py-20 text-slate-100">
        <div className="pointer-events-none absolute inset-0 bg-[radial-gradient(circle_at_20%_10%,rgba(34,197,94,0.22),transparent_45%),radial-gradient(circle_at_80%_80%,rgba(14,165,233,0.2),transparent_42%)]" />
        <div className="relative mx-auto max-w-2xl rounded-2xl border border-slate-700/70 bg-slate-900/70 p-8 shadow-2xl backdrop-blur">
          <h1 className="text-2xl font-semibold">Firebase config missing</h1>
          <p className="mt-3 text-sm text-slate-300">
            Copy frontend/.env.local.example to .env.local, then fill the values
            below.
          </p>
          <ul className="mt-4 list-disc pl-6 text-sm text-slate-200">
            {missingFirebaseConfigKeys.map((key) => (
              <li key={key}>{key}</li>
            ))}
          </ul>
        </div>
      </main>
    );
  }

  const handleEmailPasswordAuth = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (!auth) {
      return;
    }

    try {
      setLoading(true);
      if (mode === "signup") {
        await createUserWithEmailAndPassword(auth, email, password);
      } else {
        await signInWithEmailAndPassword(auth, email, password);
      }
      setError("");
    } catch (loginError) {
      const details =
        loginError instanceof Error
          ? loginError.message
          : mode === "signup"
            ? "Sign up failed"
            : "Login failed";
      setError(details);
    } finally {
      setLoading(false);
    }
  };

  const handleGoogleLogin = async () => {
    if (!auth || !googleProvider) {
      return;
    }

    try {
      setLoading(true);
      await signInWithPopup(auth, googleProvider);
      setError("");
    } catch (loginError) {
      const details =
        loginError instanceof Error ? loginError.message : "Google login failed";
      setError(details);
    } finally {
      setLoading(false);
    }
  };

  if (checkingSession) {
    return (
      <main className="relative min-h-screen overflow-hidden bg-[#06070b] px-6 py-16 text-slate-100">
        <div className="pointer-events-none absolute inset-0 bg-[radial-gradient(circle_at_20%_10%,rgba(34,197,94,0.22),transparent_45%),radial-gradient(circle_at_80%_80%,rgba(14,165,233,0.2),transparent_42%)]" />
        <div className="relative mx-auto max-w-md rounded-2xl border border-slate-700/70 bg-slate-900/70 p-8 shadow-2xl backdrop-blur">
          <p className="text-sm text-slate-300">Checking your account...</p>
        </div>
      </main>
    );
  }

  return (
    <main className="relative min-h-screen overflow-hidden bg-[#06070b] px-6 py-16 text-slate-100">
      <div className="pointer-events-none absolute inset-0 bg-[radial-gradient(circle_at_20%_10%,rgba(34,197,94,0.22),transparent_45%),radial-gradient(circle_at_80%_80%,rgba(14,165,233,0.2),transparent_42%)]" />

      <div className="relative mx-auto max-w-md rounded-2xl border border-slate-700/70 bg-slate-900/70 p-8 shadow-2xl backdrop-blur">
        <p className="text-xs uppercase tracking-[0.2em] text-emerald-300">Egyptian Financial Advisor</p>
        <h1 className="text-3xl font-bold tracking-tight">
          {mode === "signup" ? "Create Account" : "Login"}
        </h1>
        <p className="mt-2 text-sm text-slate-300">
          {mode === "signup"
            ? "Sign up with email/password, or continue with Google."
            : "Sign in with email/password or continue with Google."}
        </p>

        <div className="mt-5 grid grid-cols-2 gap-2 rounded-lg border border-slate-700 bg-slate-950/80 p-1">
          <button
            type="button"
            onClick={() => {
              setMode("signin");
              setError("");
            }}
            className={`rounded-md px-3 py-2 text-sm font-semibold transition ${
              mode === "signin"
                ? "bg-slate-800 text-slate-100 shadow-sm"
                : "text-slate-400 hover:text-slate-100"
            }`}
          >
            Sign in
          </button>
          <button
            type="button"
            onClick={() => {
              setMode("signup");
              setError("");
            }}
            className={`rounded-md px-3 py-2 text-sm font-semibold transition ${
              mode === "signup"
                ? "bg-slate-800 text-slate-100 shadow-sm"
                : "text-slate-400 hover:text-slate-100"
            }`}
          >
            Sign up
          </button>
        </div>

        <form onSubmit={handleEmailPasswordAuth} className="mt-6 space-y-4">
          <div>
            <label htmlFor="email" className="block text-sm font-medium">
              Email
            </label>
            <input
              id="email"
              type="email"
              value={email}
              onChange={(event) => setEmail(event.target.value)}
              required
              className="mt-1 w-full rounded-lg border border-slate-600 bg-slate-950 px-3 py-2 text-sm text-slate-100 outline-none focus:border-emerald-400"
              placeholder="you@example.com"
            />
          </div>
          <div>
            <label htmlFor="password" className="block text-sm font-medium">
              Password
            </label>
            <input
              id="password"
              type="password"
              value={password}
              onChange={(event) => setPassword(event.target.value)}
              required
              className="mt-1 w-full rounded-lg border border-slate-600 bg-slate-950 px-3 py-2 text-sm text-slate-100 outline-none focus:border-emerald-400"
              placeholder="Your password"
            />
          </div>
          <button
            type="submit"
            disabled={loading}
            className="w-full rounded-lg bg-emerald-500 px-4 py-2 text-sm font-semibold text-slate-950 transition hover:bg-emerald-400 disabled:cursor-not-allowed disabled:bg-slate-600 disabled:text-slate-300"
          >
            {loading
              ? mode === "signup"
                ? "Creating account..."
                : "Signing in..."
              : mode === "signup"
                ? "Create account"
                : "Sign in"}
          </button>
        </form>

        <button
          type="button"
          onClick={handleGoogleLogin}
          disabled={loading}
          className="mt-3 w-full rounded-lg border border-slate-600 bg-slate-900 px-4 py-2 text-sm font-semibold text-slate-100 transition hover:bg-slate-800 disabled:cursor-not-allowed"
        >
          Continue with Google
        </button>
        {error && <p className="mt-4 text-sm text-rose-300">{error}</p>}
      </div>
    </main>
  );
}
