<script lang="ts">
  import { page } from '$app/stores';
  import { browser } from '$app/environment';
  import { afterNavigate, goto } from '$app/navigation';
  import { onMount } from 'svelte';
  import { getSessionStatus, revokeAccess } from '$lib/auth';
  import '../app.css';

  const navigation = [
    { href: '/', label: 'Novo orçamento', shortLabel: 'Novo' },
    { href: '/historico', label: 'Histórico', shortLabel: 'Histórico' },
    { href: '/dashboard', label: 'Painel', shortLabel: 'Painel' },
    { href: '/servicos', label: 'Catálogo', shortLabel: 'Catálogo' },
  ];

  let accessReady = false;
  let accessConfigured = false;
  let theme: 'light' | 'dark' = 'light';
  let isOnline = true;
  let authCheckInFlight = false;

  function applyTheme(nextTheme: 'light' | 'dark') {
    theme = nextTheme;
    document.documentElement.classList.toggle('dark', nextTheme === 'dark');
    localStorage.setItem('dinheiro-theme', nextTheme);
  }

  function initializeTheme() {
    const storedTheme = localStorage.getItem('dinheiro-theme');
    applyTheme(storedTheme === 'dark' ? 'dark' : 'light');
  }

  function toggleTheme() {
    applyTheme(theme === 'dark' ? 'light' : 'dark');
  }

  async function enforceAccess() {
    if (!browser) return;
    if (authCheckInFlight) return;

    const isLoginPage = $page.url.pathname === '/login';
    const isPublicSharePage = $page.url.pathname.startsWith('/compartilhar/');
    if (isPublicSharePage) {
      accessReady = true;
      return;
    }

    authCheckInFlight = true;
    try {
      const status = await getSessionStatus();
      accessConfigured = status.configured;
      if (status.configured && !status.authenticated && !isLoginPage) {
        accessReady = false;
        await goto('/login');
        return;
      }
      if (isLoginPage && status.authenticated) {
        accessReady = false;
        await goto('/');
        return;
      }
      accessReady = true;
    } finally {
      authCheckInFlight = false;
    }
  }

  if (browser) afterNavigate(enforceAccess);
  onMount(() => {
    initializeTheme();
    isOnline = navigator.onLine;
    const handleOnline = () => (isOnline = true);
    const handleOffline = () => (isOnline = false);
    window.addEventListener('online', handleOnline);
    window.addEventListener('offline', handleOffline);
    void enforceAccess();
    return () => {
      window.removeEventListener('online', handleOnline);
      window.removeEventListener('offline', handleOffline);
    };
  });

  async function logout() {
    await revokeAccess();
    await goto('/login');
  }
</script>

<svelte:head>
  <meta name="theme-color" content={theme === 'dark' ? '#0b1120' : '#f8fafc'} />
</svelte:head>

{#if accessReady}
  <div class="min-h-screen text-slate-900">
    {#if $page.url.pathname !== '/login' && !$page.url.pathname.startsWith('/compartilhar/')}
      <header class="border-b border-slate-200/80 bg-white/80 backdrop-blur-xl">
        <div class="mx-auto flex w-full max-w-7xl items-center justify-between gap-6 px-4 py-4 sm:px-6 lg:px-8">
          <a href="/" class="flex items-center gap-3" aria-label="Dinheiro início">
            <span class="grid h-9 w-9 place-items-center rounded-xl bg-indigo-600 text-lg font-black text-white shadow-lg shadow-indigo-200">$</span>
            <span class="text-lg font-extrabold tracking-[-0.06em] text-slate-900">dinheiro<span class="text-indigo-500">.</span></span>
          </a>

          <div class="flex items-center gap-2">
            <nav class="flex items-center gap-1 rounded-xl bg-slate-100 p-1" aria-label="Navegação principal">
              {#each navigation as item}
                <a href={item.href} class:nav-active={$page.url.pathname === item.href} class="rounded-lg px-3 py-2 text-xs font-semibold text-slate-500 transition hover:text-slate-900 sm:px-4" aria-current={$page.url.pathname === item.href ? 'page' : undefined}>
                  <span class="hidden sm:inline">{item.label}</span><span class="sm:hidden">{item.shortLabel}</span>
                </a>
              {/each}
            </nav>
            <a href="/configuracoes" class="settings-link" class:nav-active={$page.url.pathname === '/configuracoes'} aria-label="Configurações" title="Configurações">⚙</a>
            <button type="button" class="theme-toggle" on:click={toggleTheme} aria-label={theme === 'dark' ? 'Ativar modo claro' : 'Ativar modo escuro'} title={theme === 'dark' ? 'Modo claro' : 'Modo escuro'}><span aria-hidden="true">{theme === 'dark' ? '☀' : '☾'}</span><span class="hidden sm:inline">{theme === 'dark' ? 'Claro' : 'Escuro'}</span></button>
            {#if accessConfigured}<button type="button" class="rounded-lg px-2.5 py-2 text-xs font-bold text-slate-400 transition hover:bg-rose-50 hover:text-rose-600" on:click={logout} title="Sair">Sair</button>{/if}
          </div>
        </div>
      </header>
    {/if}

    {#if !isOnline && !$page.url.pathname.startsWith('/compartilhar/')}
      <div class="border-b border-amber-200 bg-amber-50 px-4 py-2.5 text-center text-xs font-semibold text-amber-800">
        Você está offline. Rascunhos e templates continuam disponíveis neste dispositivo; sincronização com o Firestore volta quando a conexão retornar.
      </div>
    {/if}

    <main class="mx-auto w-full max-w-7xl px-4 py-8 sm:px-6 lg:px-8 lg:py-10"><slot /></main>

    {#if $page.url.pathname !== '/login' && !$page.url.pathname.startsWith('/compartilhar/')}
      <footer class="mx-auto flex w-full max-w-7xl flex-col gap-2 px-4 pb-8 text-xs text-slate-400 sm:flex-row sm:items-center sm:justify-between sm:px-6 lg:px-8"><span>Dinheiro · orçamentos técnicos</span><span>FastAPI · SvelteKit · Firestore</span></footer>
    {/if}
  </div>
{:else}
  <div class="flex min-h-screen items-center justify-center bg-slate-50 text-sm text-slate-500"><span class="animate-pulse">Carregando workspace…</span></div>
{/if}

<style>
  :global(.nav-active) {
    background: white;
    color: #3730a3;
    box-shadow: 0 1px 3px rgba(15, 23, 42, 0.08);
  }

  .theme-toggle {
    @apply inline-flex items-center gap-1.5 rounded-xl border border-slate-200 bg-white px-2.5 py-2 text-xs font-bold text-slate-500 transition hover:border-indigo-200 hover:bg-indigo-50 hover:text-indigo-700;
  }

  .settings-link {
    @apply grid h-9 w-9 place-items-center rounded-xl border border-slate-200 bg-white text-sm font-bold text-slate-500 transition hover:border-indigo-200 hover:bg-indigo-50 hover:text-indigo-700;
  }
</style>
