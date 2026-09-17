<script lang="ts">
  import { onMount } from 'svelte';
  import { deleteQuote, getQuotes, updateQuoteStatus, type QuoteResponse, type QuoteStatus } from '$lib/api';
  import { gerarOrcamentoPDF } from '$lib/pdfGenerator';

  const statuses: { value: QuoteStatus; label: string }[] = [
    { value: 'rascunho', label: 'Rascunho' },
    { value: 'enviado', label: 'Enviado' },
    { value: 'aprovado', label: 'Aprovado' },
    { value: 'recusado', label: 'Recusado' },
    { value: 'concluido', label: 'Concluído' },
  ];

  let quotes: QuoteResponse[] = [];
  let loading = true;
  let error = '';
  let updatingId = '';
  let deletingId = '';
  let toast = '';

  onMount(loadQuotes);

  async function loadQuotes() {
    loading = true;
    error = '';
    try {
      quotes = await getQuotes();
    } catch (reason) {
      error = reason instanceof Error ? reason.message : 'Não foi possível carregar o histórico.';
    } finally {
      loading = false;
    }
  }

  function formatDate(value: string) {
    return new Intl.DateTimeFormat('pt-BR', {
      day: '2-digit',
      month: 'short',
      year: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    }).format(new Date(value));
  }

  function money(value: number) {
    return new Intl.NumberFormat('pt-BR', { style: 'currency', currency: 'BRL' }).format(value || 0);
  }

  function statusLabel(status: QuoteStatus) {
    return statuses.find((item) => item.value === status)?.label ?? status;
  }

  function statusClass(status: QuoteStatus) {
    return {
      rascunho: 'bg-slate-100 text-slate-600',
      enviado: 'bg-sky-100 text-sky-700',
      aprovado: 'bg-emerald-100 text-emerald-700',
      recusado: 'bg-rose-100 text-rose-700',
      concluido: 'bg-indigo-100 text-indigo-700',
    }[status];
  }

  async function changeStatus(quote: QuoteResponse, status: QuoteStatus) {
    if (quote.status === status) return;
    updatingId = quote.id;
    error = '';
    try {
      const updated = await updateQuoteStatus(quote.id, status);
      quotes = quotes.map((item) => (item.id === updated.id ? updated : item));
    } catch (reason) {
      error = reason instanceof Error ? reason.message : 'Não foi possível atualizar o status.';
    } finally {
      updatingId = '';
    }
  }

  async function removeQuote(quote: QuoteResponse) {
    if (!window.confirm(`Deseja realmente excluir o orçamento de ${quote.cliente.nome}?`)) return;

    deletingId = quote.id;
    error = '';
    try {
      await deleteQuote(quote.id);
      quotes = quotes.filter((item) => item.id !== quote.id);
      toast = 'Orçamento removido com sucesso.';
      window.setTimeout(() => (toast = ''), 3500);
    } catch (reason) {
      error = reason instanceof Error ? reason.message : 'Não foi possível excluir o orçamento.';
    } finally {
      deletingId = '';
    }
  }

  function whatsappUrl(quote: QuoteResponse) {
    const digits = (quote.cliente.telefone || '').replace(/\D/g, '');
    const phone = digits ? (digits.startsWith('55') ? digits : `55${digits}`) : '';
    return `https://wa.me/${phone}?text=${encodeURIComponent(quote.mensagem_whatsapp)}`;
  }

  function resendWhatsApp(quote: QuoteResponse) {
    if (quote.cliente.telefone) {
      window.open(whatsappUrl(quote), '_blank', 'noopener,noreferrer');
    }
  }
</script>

<svelte:head>
  <title>Histórico — Dinheiro</title>
  <meta name="description" content="Acompanhe seus orçamentos e atualize o status de cada negociação." />
</svelte:head>

<div class="space-y-8">
  <section class="flex flex-col justify-between gap-5 sm:flex-row sm:items-end">
    <div>
      <p class="eyebrow">Acompanhamento</p>
      <h1 class="mt-2 text-3xl font-extrabold tracking-[-0.055em] text-slate-950 sm:text-4xl">Histórico de orçamentos</h1>
      <p class="mt-2 max-w-2xl text-sm leading-6 text-slate-500">Veja o que já foi enviado, aprovado ou ainda precisa de atenção.</p>
    </div>
    <a href="/" class="inline-flex items-center justify-center gap-2 rounded-xl bg-indigo-600 px-4 py-2.5 text-xs font-bold text-white shadow-lg shadow-indigo-200 transition hover:bg-indigo-700">+ Novo orçamento</a>
  </section>

  {#if error}<div class="rounded-xl border border-rose-200 bg-rose-50 px-4 py-3 text-sm font-medium text-rose-700">{error}</div>{/if}
  {#if toast}<div class="fixed bottom-5 left-1/2 z-50 -translate-x-1/2 rounded-xl bg-slate-950 px-4 py-3 text-sm font-semibold text-white shadow-xl">{toast}</div>{/if}

  <section class="surface overflow-hidden">
    <div class="flex items-center justify-between border-b border-slate-100 px-5 py-4 sm:px-6">
      <div><p class="text-sm font-bold text-slate-900">Todos os orçamentos</p><p class="mt-0.5 text-xs text-slate-500">{quotes.length} registro{quotes.length === 1 ? '' : 's'}</p></div>
      <button type="button" class="rounded-lg px-3 py-2 text-xs font-bold text-slate-500 transition hover:bg-slate-100 hover:text-indigo-700" on:click={loadQuotes} disabled={loading}>Atualizar</button>
    </div>

    {#if loading}
      <div class="flex min-h-56 items-center justify-center text-sm text-slate-500"><span class="animate-pulse">Carregando histórico…</span></div>
    {:else if quotes.length === 0}
      <div class="flex min-h-64 flex-col items-center justify-center px-6 text-center"><span class="grid h-12 w-12 place-items-center rounded-2xl bg-indigo-50 text-xl text-indigo-500">▤</span><p class="mt-4 font-bold text-slate-700">Ainda não há orçamentos salvos</p><p class="mt-1 max-w-sm text-sm leading-6 text-slate-500">Quando você salvar o primeiro orçamento, ele aparecerá aqui para acompanhamento.</p><a href="/" class="mt-5 text-sm font-bold text-indigo-600 hover:text-indigo-800">Criar primeiro orçamento →</a></div>
    {:else}
      <div class="divide-y divide-slate-100">
        {#each quotes as quote}
          <article class="flex flex-col gap-4 px-5 py-5 transition hover:bg-slate-50/70 sm:px-6 lg:flex-row lg:items-center lg:justify-between">
            <div class="min-w-0">
              <div class="flex flex-wrap items-center gap-2">
                <h2 class="truncate font-bold text-slate-900">{quote.cliente.nome}</h2>
                <span class={`rounded-full px-2.5 py-1 text-[10px] font-extrabold uppercase tracking-wider ${statusClass(quote.status)}`}>{statusLabel(quote.status)}</span>
              </div>
              <p class="mt-1 text-xs text-slate-500">{quote.cliente.identificador_aparelho || 'Projeto não informado'} · {formatDate(quote.criado_em)}</p>
              <p class="mt-2 text-xs text-slate-400">{quote.itens.length} serviço{quote.itens.length === 1 ? '' : 's'} · {quote.cliente.telefone || 'sem telefone'}</p>
            </div>
            <div class="flex flex-col gap-3 sm:flex-row sm:items-center">
              <div class="text-left sm:text-right"><p class="text-[10px] font-bold uppercase tracking-wider text-slate-400">Valor total</p><p class="text-xl font-black tracking-tight text-slate-900">{money(quote.valor_total)}</p></div>
              <select class="field min-w-36 py-2 text-xs font-bold" value={quote.status} aria-label={`Status de ${quote.cliente.nome}`} on:change={(event) => changeStatus(quote, event.currentTarget.value as QuoteStatus)} disabled={updatingId === quote.id}>
                {#each statuses as status}<option value={status.value}>{status.label}</option>{/each}
              </select>
              <div class="flex flex-wrap gap-2">
                <a href={`/?edit=${encodeURIComponent(quote.id)}`} class="inline-flex items-center justify-center rounded-xl border border-slate-200 bg-white px-3 py-2.5 text-xs font-bold text-slate-600 transition hover:border-indigo-200 hover:bg-indigo-50 hover:text-indigo-700" title="Editar orçamento">✎ Editar</a>
                <a href={`/?clone=${encodeURIComponent(quote.id)}`} class="inline-flex items-center justify-center rounded-xl border border-slate-200 bg-white px-3 py-2.5 text-xs font-bold text-slate-600 transition hover:border-indigo-200 hover:bg-indigo-50 hover:text-indigo-700" title="Duplicar orçamento">⧉ Duplicar</a>
                <button type="button" class="inline-flex items-center justify-center rounded-xl border border-indigo-200 bg-indigo-50 px-3 py-2.5 text-xs font-bold text-indigo-700 transition hover:bg-indigo-100" on:click={() => gerarOrcamentoPDF(quote)} title="Baixar PDF">PDF</button>
                <button type="button" class="inline-flex items-center justify-center rounded-xl border border-slate-200 px-3 py-2.5 text-xs font-bold text-slate-600 transition hover:border-emerald-200 hover:bg-emerald-50 hover:text-emerald-700 disabled:cursor-not-allowed disabled:opacity-40" on:click={() => resendWhatsApp(quote)} disabled={!quote.cliente.telefone} title={quote.cliente.telefone ? 'Reenviar pelo WhatsApp' : 'Telefone não informado'}>↗ WhatsApp</button>
                <button type="button" class="inline-flex items-center justify-center rounded-xl border border-rose-200 bg-rose-50 px-3 py-2.5 text-xs font-bold text-rose-600 transition hover:bg-rose-100 disabled:cursor-not-allowed disabled:opacity-50" on:click={() => removeQuote(quote)} disabled={deletingId === quote.id} title="Excluir orçamento">{deletingId === quote.id ? 'Excluindo…' : '⌫ Excluir'}</button>
              </div>
            </div>
          </article>
        {/each}
      </div>
    {/if}
  </section>
</div>
