"use client";

import { useEffect, useState } from "react";
import { onAuthStateChanged, signOut, User } from "firebase/auth";
import { useRouter } from "next/navigation";

import { auth, isFirebaseConfigured, missingFirebaseConfigKeys } from "@/lib/firebase";
import { resolvePostLoginRoute } from "@/lib/profile-routing";

export default function DashboardPage() {
  const router = useRouter();
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(Boolean(auth));

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
        const destination = await resolvePostLoginRoute(currentUser);
        if (destination === "/onboarding") {
          router.replace(destination);
          return;
        }

        setUser(currentUser);
      } catch {
        router.replace("/login");
        return;
      }

      setLoading(false);
    });

    return unsubscribe;
  }, [router]);

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
      <main className="min-h-screen bg-slate-100 px-6 py-16 text-slate-900">
        <div className="mx-auto max-w-xl rounded-2xl border border-slate-200 bg-white p-8 shadow-sm">
          <p className="text-sm text-slate-700">Loading dashboard...</p>
        </div>
      </main>
    );
  }

  return (
    <main className="min-h-screen bg-slate-100 px-6 py-16 text-slate-900">
      <div className="mx-auto max-w-3xl rounded-3xl border border-slate-200 bg-white p-8 shadow-sm">
        <h1 className="text-3xl font-semibold tracking-tight">Dashboard</h1>
        <p className="mt-3 text-sm text-slate-600">
          You completed onboarding successfully. This page will become the chat
          dashboard in Phase 4.
        </p>
        <p className="mt-6 text-sm text-slate-800">
          Signed in as: <span className="font-semibold">{user?.email ?? user?.uid}</span>
        </p>
        <button
          type="button"
          onClick={async () => {
            if (!auth) {
              return;
            }
            await signOut(auth);
            router.replace("/login");
          }}
          className="mt-6 rounded-lg border border-slate-300 bg-white px-4 py-2 text-sm font-semibold text-slate-800 transition hover:bg-slate-50"
        >
          Sign out
        </button>
      </div>
    </main>
  );
}
