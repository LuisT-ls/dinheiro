import { browser } from '$app/environment';

const ACCESS_SESSION_KEY = 'dinheiro.access.granted';
const configuredPin = typeof __APP_ACCESS_PIN__ === 'string' ? __APP_ACCESS_PIN__.trim() : '';

export function isAccessPinConfigured() {
  return configuredPin.length > 0;
}

export function hasAccess() {
  if (!browser || !isAccessPinConfigured()) return true;
  return localStorage.getItem(ACCESS_SESSION_KEY) === 'granted';
}

export function verifyAccessPin(pin: string) {
  return !isAccessPinConfigured() || pin.trim() === configuredPin;
}

export function grantAccess() {
  if (browser && isAccessPinConfigured()) {
    localStorage.setItem(ACCESS_SESSION_KEY, 'granted');
  }
}

export function revokeAccess() {
  if (browser) localStorage.removeItem(ACCESS_SESSION_KEY);
}
