import { browser } from '$app/environment';
import { getAccessStatus, loginWithPin, logoutFromApi, type AccessStatus } from '$lib/api';

export type { AccessStatus };

export async function getSessionStatus(): Promise<AccessStatus> {
  if (!browser) {
    return { configured: false, authenticated: false };
  }

  try {
    return await getAccessStatus();
  } catch {
    // Fail closed if the API is unavailable or the deployment is misconfigured.
    return { configured: true, authenticated: false };
  }
}

export { loginWithPin };

export async function revokeAccess(): Promise<void> {
  await logoutFromApi().catch(() => undefined);
}
