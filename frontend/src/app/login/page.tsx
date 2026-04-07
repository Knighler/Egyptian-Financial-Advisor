"use client";

import { FormEvent, useCallback, useEffect, useState } from "react";
import {
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
      <main className="min-h-screen bg-amber-50 px-6 py-20 text-slate-900">
        <div className="mx-auto max-w-2xl rounded-2xl border border-amber-300 bg-white p-8 shadow-sm">
          <h1 className="text-2xl font-semibold">Firebase config missing</h1>
          <p className="mt-3 text-sm text-slate-700">
            Copy frontend/.env.local.example to .env.local, then fill the values
            below.
          </p>
          <ul className="mt-4 list-disc pl-6 text-sm text-slate-800">
            {missingFirebaseConfigKeys.map((key) => (
              <li key={key}>{key}</li>
            ))}
          </ul>
        </div>
      </main>
    );
  }

  const handleEmailPasswordLogin = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (!auth) {
      return;
    }

    try {
      setLoading(true);
      await signInWithEmailAndPassword(auth, email, password);
      setError("");
    } catch (loginError) {
      const details =
        loginError instanceof Error ? loginError.message : "Login failed";
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
      <main className="min-h-screen bg-slate-100 px-6 py-16 text-slate-900">
        <div className="mx-auto max-w-md rounded-2xl border border-slate-200 bg-white p-8 shadow-sm">
          <p className="text-sm text-slate-700">Checking your account...</p>
        </div>
      </main>
    );
  }

  return (
    <main className="min-h-screen bg-slate-100 px-6 py-16 text-slate-900">
      <div className="mx-auto max-w-md rounded-2xl border border-slate-200 bg-white p-8 shadow-sm">
        <h1 className="text-3xl font-bold tracking-tight">Login</h1>
        <p className="mt-2 text-sm text-slate-600">
          Sign in with email/password or continue with Google.
        </p>

        <form onSubmit={handleEmailPasswordLogin} className="mt-6 space-y-4">
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
              className="mt-1 w-full rounded-lg border border-slate-300 px-3 py-2 text-sm outline-none focus:border-slate-500"
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
              className="mt-1 w-full rounded-lg border border-slate-300 px-3 py-2 text-sm outline-none focus:border-slate-500"
              placeholder="Your password"
            />
          </div>
          <button
            type="submit"
            disabled={loading}
            className="w-full rounded-lg bg-slate-900 px-4 py-2 text-sm font-semibold text-white transition hover:bg-slate-700 disabled:cursor-not-allowed disabled:bg-slate-400"
          >
            {loading ? "Signing in..." : "Sign in"}
          </button>
        </form>

        <button
          type="button"
          onClick={handleGoogleLogin}
          disabled={loading}
          className="mt-3 w-full rounded-lg border border-slate-300 bg-white px-4 py-2 text-sm font-semibold text-slate-800 transition hover:bg-slate-50 disabled:cursor-not-allowed"
        >
          Continue with Google
        </button>
        {error && <p className="mt-4 text-sm text-red-700">{error}</p>}
      </div>
    </main>
  );
}
