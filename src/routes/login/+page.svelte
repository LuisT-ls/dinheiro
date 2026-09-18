<script lang="ts">
  import { onMount } from 'svelte';
  import { goto } from '$app/navigation';
  import { getSessionStatus, loginWithPin } from '$lib/auth';
  import Seo from '$lib/Seo.svelte';

  let pin = '';
  let error = '';
  let ready = false;
  let configured = false;
  let submitting = false;

  onMount(async () => {
    const status = await getSessionStatus();
    configured = status.configured;
    if (status.authenticated) {
      await goto('/');
      return;
    }
    ready = true;
  });

  async function submit() {
    if (!configured) {
      error = 'Configure APP_ACCESS_PIN no backend para liberar o workspace.';
      return;
    }

    submitting = true;
    error = '';
    try {
      await loginWithPin(pin);
      await goto('/');
    } catch (reason) {
      error = reason instanceof Error ? reason.message : 'Não foi possível validar o PIN.';
      pin = '';
    } finally {
      submitting = false;
    }
  }
</script>

<Seo title="Acesso ao workspace | Dinheiro" description="Acesso protegido ao workspace pessoal de orçamentos técnicos." />

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
          <button type="submit" class="flex w-full items-center justify-center rounded-xl bg-indigo-600 px-4 py-3 text-sm font-bold text-white transition hover:bg-indigo-700 disabled:cursor-not-allowed disabled:opacity-60" disabled={submitting}>{submitting ? 'Validando…' : 'Entrar no workspace'}</button>
        </form>
      {:else}
        <p class="mt-2 text-sm leading-6 text-slate-500">A proteção não está disponível porque <code class="rounded bg-slate-100 px-1.5 py-0.5 text-xs">APP_ACCESS_PIN</code> não foi configurada no backend.</p>
        {#if error}<p class="mt-4 text-sm font-semibold text-rose-600">{error}</p>{/if}
      {/if}
    </section>
  </div>
{:else}
  <div class="flex min-h-[calc(100vh-12rem)] items-center justify-center text-sm text-slate-500"><span class="animate-pulse">Verificando acesso…</span></div>
{/if}
