<script lang="ts">
  import { onMount } from 'svelte';
  import { goto } from '$app/navigation';
  import { grantAccess, hasAccess, isAccessPinConfigured, verifyAccessPin } from '$lib/auth';

  let pin = '';
  let error = '';
  let ready = false;
  const configured = isAccessPinConfigured();

  onMount(() => {
    if (hasAccess()) {
      goto('/');
      return;
    }
    ready = true;
  });

  function submit() {
    if (!configured) {
      goto('/');
      return;
    }
    if (!verifyAccessPin(pin)) {
      error = 'PIN incorreto. Tente novamente.';
      pin = '';
      return;
    }
    grantAccess();
    goto('/');
  }
</script>

<svelte:head>
  <title>Acesso — Dinheiro</title>
  <meta name="description" content="Acesso protegido ao workspace de orçamentos." />
</svelte:head>

{#if ready}
  <div class="mx-auto flex min-h-[calc(100vh-12rem)] max-w-md items-center justify-center py-10">
    <section class="surface w-full p-6 text-center sm:p-8">
      <span class="mx-auto grid h-14 w-14 place-items-center rounded-2xl bg-indigo-600 text-2xl font-black text-white shadow-lg shadow-indigo-200">$</span>
      <p class="eyebrow mt-6">Workspace privado</p>
      <h1 class="mt-2 text-2xl font-extrabold tracking-[-0.04em] text-slate-950">Acesso ao Dinheiro</h1>
      {#if configured}
        <p class="mt-2 text-sm leading-6 text-slate-500">Digite seu PIN para abrir o painel de orçamentos.</p>
        <form class="mt-6 space-y-3 text-left" on:submit|preventDefault={submit}>
          <label><span class="field-label">PIN de acesso</span><input class="field text-center text-lg tracking-[0.3em]" type="password" inputmode="numeric" autocomplete="current-password" bind:value={pin} placeholder="••••" /></label>
          {#if error}<p class="text-center text-sm font-semibold text-rose-600">{error}</p>{/if}
          <button type="submit" class="flex w-full items-center justify-center rounded-xl bg-indigo-600 px-4 py-3 text-sm font-bold text-white transition hover:bg-indigo-700">Entrar no workspace</button>
        </form>
      {:else}
        <p class="mt-2 text-sm leading-6 text-slate-500">A proteção está desativada porque <code class="rounded bg-slate-100 px-1.5 py-0.5 text-xs">APP_ACCESS_PIN</code> ainda não foi configurada.</p>
        <button type="button" class="mt-6 w-full rounded-xl bg-indigo-600 px-4 py-3 text-sm font-bold text-white transition hover:bg-indigo-700" on:click={submit}>Continuar</button>
      {/if}
    </section>
  </div>
{:else}
  <div class="flex min-h-[calc(100vh-12rem)] items-center justify-center text-sm text-slate-500"><span class="animate-pulse">Verificando acesso…</span></div>
{/if}
