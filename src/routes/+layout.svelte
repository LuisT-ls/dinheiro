<script lang="ts">
  import { page } from '$app/stores';
  import '../app.css';

  const navigation = [
    { href: '/', label: 'Novo orçamento', shortLabel: 'Novo' },
    { href: '/historico', label: 'Histórico', shortLabel: 'Histórico' },
    { href: '/servicos', label: 'Catálogo', shortLabel: 'Catálogo' },
  ];
</script>

<svelte:head>
  <meta name="theme-color" content="#f8fafc" />
</svelte:head>

<div class="min-h-screen text-slate-900">
  <header class="border-b border-slate-200/80 bg-white/80 backdrop-blur-xl">
    <div class="mx-auto flex w-full max-w-7xl items-center justify-between gap-6 px-4 py-4 sm:px-6 lg:px-8">
      <a href="/" class="flex items-center gap-3" aria-label="Dinheiro início">
        <span class="grid h-9 w-9 place-items-center rounded-xl bg-indigo-600 text-lg font-black text-white shadow-lg shadow-indigo-200">$</span>
        <span class="text-lg font-extrabold tracking-[-0.06em] text-slate-900">dinheiro<span class="text-indigo-500">.</span></span>
      </a>

      <nav class="flex items-center gap-1 rounded-xl bg-slate-100 p-1" aria-label="Navegação principal">
        {#each navigation as item}
          <a
            href={item.href}
            class:nav-active={$page.url.pathname === item.href}
            class="rounded-lg px-3 py-2 text-xs font-semibold text-slate-500 transition hover:text-slate-900 sm:px-4"
            aria-current={$page.url.pathname === item.href ? 'page' : undefined}
          >
            <span class="hidden sm:inline">{item.label}</span>
            <span class="sm:hidden">{item.shortLabel}</span>
          </a>
        {/each}
      </nav>
    </div>
  </header>

  <main class="mx-auto w-full max-w-7xl px-4 py-8 sm:px-6 lg:px-8 lg:py-10">
    <slot />
  </main>

  <footer class="mx-auto flex w-full max-w-7xl flex-col gap-2 px-4 pb-8 text-xs text-slate-400 sm:flex-row sm:items-center sm:justify-between sm:px-6 lg:px-8">
    <span>Dinheiro · orçamentos técnicos</span>
    <span>FastAPI · SvelteKit · Firestore</span>
  </footer>
</div>

<style>
  :global(.nav-active) {
    background: white;
    color: #3730a3;
    box-shadow: 0 1px 3px rgba(15, 23, 42, 0.08);
  }
</style>
