import { User } from "firebase/auth";

const API_BASE_URL =
  process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";

export type UserProfile = {
  monthly_income: number;
  savings: number;
  investment_goal: string;
  risk_tolerance: number;
};

export type ProfileStatusResponse = {
  has_profile: boolean;
  profile: UserProfile | null;
};

type ChatResponse = {
  response: string;
};

async function withAuthHeaders(user: User): Promise<Record<string, string>> {
  const token = await user.getIdToken();
  return {
    Authorization: `Bearer ${token}`,
    "Content-Type": "application/json",
  };
}

export async function fetchProfileStatus(user: User): Promise<ProfileStatusResponse> {
  const headers = await withAuthHeaders(user);
  const response = await fetch(`${API_BASE_URL}/profile/me`, {
    method: "GET",
    headers,
  });

  if (!response.ok) {
    throw new Error("Unable to load profile status");
  }

  return (await response.json()) as ProfileStatusResponse;
}

export async function saveProfile(user: User, profile: UserProfile): Promise<void> {
  const headers = await withAuthHeaders(user);
  const response = await fetch(`${API_BASE_URL}/profile`, {
    method: "POST",
    headers,
    body: JSON.stringify(profile),
  });

  if (!response.ok) {
    const details = await response.text();
    throw new Error(details || "Unable to save profile");
  }
}

export async function fetchCurrentProfile(user: User): Promise<UserProfile> {
  const profileStatus = await fetchProfileStatus(user);
  if (!profileStatus.has_profile || !profileStatus.profile) {
    throw new Error("Profile is missing");
  }

  return profileStatus.profile;
}

export async function sendChatMessage(user: User, message: string): Promise<string> {
  const headers = await withAuthHeaders(user);
  const response = await fetch(`${API_BASE_URL}/chat`, {
    method: "POST",
    headers,
    body: JSON.stringify({ message }),
  });

  if (!response.ok) {
    let details = "Unable to get advisor response";
    try {
      const payload = (await response.json()) as { detail?: string };
      if (payload?.detail) {
        details = payload.detail;
      }
    } catch {
      const text = await response.text();
      if (text) {
        details = text;
      }
    }
    throw new Error(details);
  }

  const payload = (await response.json()) as ChatResponse;
  return payload.response;
}
