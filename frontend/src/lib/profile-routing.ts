import { User } from "firebase/auth";

import { fetchProfileStatus } from "@/lib/api";

export async function resolvePostLoginRoute(user: User): Promise<string> {
  const profileStatus = await fetchProfileStatus(user);
  return profileStatus.has_profile ? "/dashboard" : "/onboarding";
}
