<script lang="ts">
  import { onMount } from 'svelte';
  import { deleteQuote, getQuotes, updateQuoteStatus, type QuoteResponse, type QuoteStatus } from '$lib/api';
  import { gerarOrcamentoPDF } from '$lib/pdfGenerator';

  type FilterStatus = QuoteStatus | 'todos';

  const statuses: { value: QuoteStatus; label: string }[] = [
    { value: 'rascunho', label: 'Rascunho' },
    { value: 'enviado', label: 'Enviado' },
    { value: 'negociacao', label: 'Negociação' },
    { value: 'aprovado', label: 'Aprovado' },
    { value: 'recusado', label: 'Recusado' },
    { value: 'concluido', label: 'Concluído' },
  ];

  let quotes: QuoteResponse[] = [];
  let loading = true;
  let error = '';
  let query = '';
  let filterStatus: FilterStatus = 'todos';
  let updatingId = '';
  let deletingId = '';
  let toast = '';
  let lastUpdated = '';

  $: normalizedQuery = query.trim().toLocaleLowerCase('pt-BR');
  $: filteredQuotes = quotes.filter((quote) => {
    const matchesStatus = filterStatus === 'todos' || quote.status === filterStatus;
    if (!matchesStatus) return false;
    if (!normalizedQuery) return true;
    const searchable = [
      quote.id,
      quote.cliente.nome,
      quote.cliente.telefone,
      quote.cliente.identificador_aparelho,
      ...quote.itens.map((item) => item.nome),
    ]
      .filter(Boolean)
      .join(' ')
      .toLocaleLowerCase('pt-BR');
    return searchable.includes(normalizedQuery);
  });
  $: totalValue = quotes.reduce((sum, quote) => sum + quote.valor_total, 0);
  $: approvedValue = quotes
    .filter((quote) => quote.status === 'aprovado' || quote.status === 'concluido')
    .reduce((sum, quote) => sum + quote.valor_total, 0);
  $: attentionCount = quotes.filter((quote) => quote.status === 'rascunho' || quote.status === 'enviado' || quote.status === 'negociacao').length;
  $: hasFilters = Boolean(normalizedQuery) || filterStatus !== 'todos';

  onMount(() => {
    const requestedStatus = new URLSearchParams(window.location.search).get('status') as QuoteStatus | null;
    if (requestedStatus && statuses.some((status) => status.value === requestedStatus)) {
      filterStatus = requestedStatus;
    }
    loadQuotes();
  });

  async function loadQuotes() {
    loading = true;
    error = '';
    try {
      quotes = await getQuotes();
      lastUpdated = new Intl.DateTimeFormat('pt-BR', { hour: '2-digit', minute: '2-digit' }).format(new Date());
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
      rascunho: 'bg-slate-100 text-slate-600 ring-slate-200',
      enviado: 'bg-sky-50 text-sky-700 ring-sky-200',
      negociacao: 'bg-amber-50 text-amber-700 ring-amber-200',
      aprovado: 'bg-emerald-50 text-emerald-700 ring-emerald-200',
      recusado: 'bg-rose-50 text-rose-700 ring-rose-200',
      concluido: 'bg-indigo-50 text-indigo-700 ring-indigo-200',
    }[status];
  }

  function statusDotClass(status: QuoteStatus) {
    return {
      rascunho: 'bg-slate-400',
      enviado: 'bg-sky-500',
      negociacao: 'bg-amber-500',
      aprovado: 'bg-emerald-500',
      recusado: 'bg-rose-500',
      concluido: 'bg-indigo-500',
    }[status];
  }

  function countFor(status: FilterStatus) {
    return status === 'todos' ? quotes.length : quotes.filter((quote) => quote.status === status).length;
  }

  function initials(name: string) {
    const parts = name.trim().split(/\s+/).filter(Boolean);
    return (parts[0]?.[0] ?? '?') + (parts.length > 1 ? parts[parts.length - 1][0] : '');
  }

  function shortId(id: string) {
    return `#${id.slice(0, 8).toUpperCase()}`;
  }

  function clearFilters() {
    query = '';
    filterStatus = 'todos';
  }

  async function changeStatus(quote: QuoteResponse, status: QuoteStatus) {
    if (quote.status === status) return;
    updatingId = quote.id;
    error = '';
    try {
      const updated = await updateQuoteStatus(quote.id, status);
      quotes = quotes.map((item) => (item.id === updated.id ? updated : item));
      toast = 'Status atualizado.';
      window.setTimeout(() => (toast = ''), 2500);
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

  async function copyShareLink(quote: QuoteResponse) {
    const link = `${window.location.origin}/compartilhar/${encodeURIComponent(quote.id)}`;
    try {
      await navigator.clipboard.writeText(link);
      toast = 'Link público copiado.';
    } catch {
      toast = 'Não foi possível copiar o link automaticamente.';
    }
    window.setTimeout(() => (toast = ''), 3000);
  }
</script>

<svelte:head>
  <title>Histórico — Dinheiro</title>
  <meta name="description" content="Acompanhe seus orçamentos e atualize o status de cada negociação." />
</svelte:head>

<div class="space-y-7 pb-4">
  <section class="flex flex-col justify-between gap-5 lg:flex-row lg:items-end">
    <div>
      <div class="flex items-center gap-2">
        <p class="eyebrow">Central de acompanhamento</p>
        {#if lastUpdated}<span class="hidden text-[11px] text-slate-400 sm:inline">Atualizado às {lastUpdated}</span>{/if}
      </div>
      <h1 class="mt-2 text-3xl font-extrabold tracking-[-0.055em] text-slate-950 sm:text-4xl">Histórico de orçamentos</h1>
      <p class="mt-2 max-w-2xl text-sm leading-6 text-slate-500">Encontre rapidamente uma proposta, acompanhe a negociação e retome o próximo passo.</p>
    </div>
    <a href="/" class="inline-flex items-center justify-center gap-2 rounded-xl bg-indigo-600 px-4 py-3 text-xs font-bold text-white transition hover:-translate-y-0.5 hover:bg-indigo-700"> <span class="text-base leading-none">+</span> Novo orçamento</a>
  </section>

  {#if error}<div class="flex items-start gap-3 rounded-2xl border border-rose-200 bg-rose-50 px-4 py-3 text-sm font-medium text-rose-700"><span class="mt-0.5">!</span><span>{error}</span></div>{/if}
  {#if toast}<div class="fixed bottom-5 left-1/2 z-50 flex -translate-x-1/2 items-center gap-2 rounded-xl bg-slate-950 px-4 py-3 text-sm font-semibold text-white shadow-xl"><span class="grid h-5 w-5 place-items-center rounded-full bg-emerald-400 text-[11px] text-slate-950">✓</span>{toast}</div>{/if}

  <section class="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
    <div class="surface flex items-start justify-between p-4 sm:p-5">
      <div><p class="text-[10px] font-bold uppercase tracking-[0.14em] text-slate-400">Propostas</p><p class="mt-2 text-2xl font-black tracking-tight text-slate-950">{quotes.length}</p><p class="mt-1 text-xs text-slate-500">no histórico</p></div>
      <span class="grid h-10 w-10 place-items-center rounded-xl bg-indigo-50 text-lg text-indigo-600">▤</span>
    </div>
    <div class="surface flex items-start justify-between p-4 sm:p-5">
      <div><p class="text-[10px] font-bold uppercase tracking-[0.14em] text-slate-400">Valor em carteira</p><p class="mt-2 text-xl font-black tracking-tight text-slate-950">{money(totalValue)}</p><p class="mt-1 text-xs text-slate-500">soma das propostas</p></div>
      <span class="grid h-10 w-10 place-items-center rounded-xl bg-sky-50 text-lg text-sky-600">↗</span>
    </div>
    <div class="surface flex items-start justify-between p-4 sm:p-5">
      <div><p class="text-[10px] font-bold uppercase tracking-[0.14em] text-slate-400">Aguardando ação</p><p class="mt-2 text-2xl font-black tracking-tight text-slate-950">{attentionCount}</p><p class="mt-1 text-xs text-slate-500">em aberto ou negociação</p></div>
      <span class="grid h-10 w-10 place-items-center rounded-xl bg-amber-50 text-lg text-amber-600">◷</span>
    </div>
    <div class="surface flex items-start justify-between p-4 sm:p-5">
      <div><p class="text-[10px] font-bold uppercase tracking-[0.14em] text-slate-400">Aprovado / concluído</p><p class="mt-2 text-xl font-black tracking-tight text-slate-950">{money(approvedValue)}</p><p class="mt-1 text-xs text-slate-500">valor convertido</p></div>
      <span class="grid h-10 w-10 place-items-center rounded-xl bg-emerald-50 text-lg text-emerald-600">✓</span>
    </div>
  </section>

  <section class="surface p-4 sm:p-5">
    <div class="flex flex-col justify-between gap-2 sm:flex-row sm:items-center">
      <div><p class="eyebrow">Pipeline comercial</p><h2 class="mt-1 text-base font-bold text-slate-900">Veja onde cada proposta está</h2></div>
      <span class="text-xs font-semibold text-slate-400">{attentionCount} em andamento</span>
    </div>
    <div class="mt-4 grid grid-cols-2 gap-2 sm:grid-cols-3 lg:grid-cols-5">
      {#each statuses.filter((status) => status.value !== 'recusado') as status}
        <button type="button" class:filter-active={filterStatus === status.value} class="pipeline-stage" on:click={() => (filterStatus = status.value)} aria-pressed={filterStatus === status.value}>
          <span class={`h-2 w-2 rounded-full ${statusDotClass(status.value)}`}></span>
          <span class="min-w-0 flex-1 truncate text-left">{status.label}</span>
          <strong>{countFor(status.value)}</strong>
        </button>
      {/each}
    </div>
  </section>

  <section class="surface overflow-hidden">
    <div class="border-b border-slate-100 px-4 py-4 sm:px-5">
      <div class="flex flex-col gap-3 lg:flex-row lg:items-center lg:justify-between">
        <label class="relative block min-w-0 flex-1 lg:max-w-md">
          <span class="sr-only">Buscar orçamento</span>
          <span class="pointer-events-none absolute inset-y-0 left-3.5 flex items-center text-slate-400">⌕</span>
          <input class="field pl-10 pr-10" type="search" bind:value={query} placeholder="Buscar por cliente, projeto ou serviço..." />
          {#if query}<button type="button" class="absolute inset-y-0 right-3 flex items-center text-sm font-bold text-slate-400 hover:text-slate-700" on:click={() => (query = '')} aria-label="Limpar busca">×</button>{/if}
        </label>
        <div class="flex items-center gap-2">
          <span class="hidden text-xs font-semibold text-slate-400 sm:inline">{filteredQuotes.length} resultado{filteredQuotes.length === 1 ? '' : 's'}</span>
          <button type="button" class="inline-flex items-center gap-2 rounded-xl border border-slate-200 px-3 py-2.5 text-xs font-bold text-slate-600 transition hover:border-indigo-200 hover:bg-indigo-50 hover:text-indigo-700" on:click={loadQuotes} disabled={loading}><span class:animate-spin={loading}>↻</span> Atualizar</button>
        </div>
      </div>
      <div class="mt-4 -mx-1 flex gap-1 overflow-x-auto pb-1" role="tablist" aria-label="Filtrar por status">
        <button type="button" role="tab" class:filter-active={filterStatus === 'todos'} class="filter-pill" on:click={() => (filterStatus = 'todos')} aria-selected={filterStatus === 'todos'}>Todos <span>{countFor('todos')}</span></button>
        {#each statuses as status}
          <button type="button" role="tab" class:filter-active={filterStatus === status.value} class="filter-pill" on:click={() => (filterStatus = status.value)} aria-selected={filterStatus === status.value}><span class={`h-1.5 w-1.5 rounded-full ${statusDotClass(status.value)}`}></span>{status.label} <span>{countFor(status.value)}</span></button>
        {/each}
      </div>
    </div>

    {#if loading}
      <div class="divide-y divide-slate-100">
        {#each [1, 2, 3] as item}
          <div class="animate-pulse px-4 py-5 sm:px-5"><div class="flex gap-3"><div class="h-10 w-10 rounded-xl bg-slate-100"></div><div class="flex-1 space-y-2"><div class="h-4 w-48 rounded bg-slate-100"></div><div class="h-3 w-72 max-w-full rounded bg-slate-100"></div></div><div class="hidden h-10 w-28 rounded bg-slate-100 sm:block"></div></div></div>
        {/each}
      </div>
    {:else if quotes.length === 0}
      <div class="flex min-h-72 flex-col items-center justify-center px-6 py-12 text-center"><span class="grid h-14 w-14 place-items-center rounded-2xl bg-indigo-50 text-2xl text-indigo-500">▤</span><p class="mt-4 font-bold text-slate-800">Seu histórico está pronto para começar</p><p class="mt-1 max-w-sm text-sm leading-6 text-slate-500">Crie o primeiro orçamento e acompanhe tudo por aqui.</p><a href="/" class="mt-5 inline-flex items-center rounded-xl bg-indigo-600 px-4 py-2.5 text-xs font-bold text-white hover:bg-indigo-700">Criar primeiro orçamento</a></div>
    {:else if filteredQuotes.length === 0}
      <div class="flex min-h-60 flex-col items-center justify-center px-6 py-12 text-center"><span class="grid h-12 w-12 place-items-center rounded-2xl bg-slate-100 text-xl text-slate-400">⌕</span><p class="mt-4 font-bold text-slate-800">Nenhum orçamento encontrado</p><p class="mt-1 max-w-sm text-sm leading-6 text-slate-500">Tente outro termo de busca ou remova o filtro de status.</p><button type="button" class="mt-4 text-xs font-bold text-indigo-600 hover:text-indigo-800" on:click={clearFilters}>Limpar filtros</button></div>
    {:else}
      <div class="divide-y divide-slate-100">
        {#each filteredQuotes as quote}
          <article class="group px-4 py-4 transition hover:bg-slate-50/70 sm:px-5 sm:py-5">
            <div class="grid gap-4 lg:grid-cols-[minmax(0,1fr)_auto] lg:items-center">
              <div class="flex min-w-0 items-start gap-3">
                <span class="grid h-11 w-11 shrink-0 place-items-center rounded-xl bg-slate-900 text-xs font-black tracking-wide text-white shadow-sm">{initials(quote.cliente.nome)}</span>
                <div class="min-w-0 flex-1">
                  <div class="flex flex-wrap items-center gap-2">
                    <h2 class="truncate font-bold text-slate-900">{quote.cliente.nome}</h2>
                    <span class={`inline-flex items-center gap-1.5 rounded-full px-2.5 py-1 text-[10px] font-extrabold uppercase tracking-wider ring-1 ring-inset ${statusClass(quote.status)}`}><span class={`h-1.5 w-1.5 rounded-full ${statusDotClass(quote.status)}`}></span>{statusLabel(quote.status)}</span>
                    <span class="text-[11px] font-semibold text-slate-400">{shortId(quote.id)}</span>
                  </div>
                  <div class="mt-1 flex flex-wrap items-center gap-x-2 gap-y-1 text-xs text-slate-500">
                    <span class="truncate">{quote.cliente.identificador_aparelho || 'Projeto não informado'}</span><span class="text-slate-300">·</span><span>{formatDate(quote.criado_em)}</span>
                  </div>
                  <div class="mt-2 flex flex-wrap items-center gap-2 text-[11px] font-medium text-slate-400">
                    <span class="rounded-md bg-slate-100 px-2 py-1 text-slate-500">{quote.itens.length} serviço{quote.itens.length === 1 ? '' : 's'}</span>
                    {#if quote.cliente.telefone}<span>{quote.cliente.telefone}</span>{:else}<span>Sem telefone</span>{/if}
                    {#if quote.observacoes}<span class="max-w-xs truncate text-indigo-500" title={quote.observacoes}>Com observações</span>{/if}
                    {#if quote.margem_percentual != null}<span class="text-emerald-600">Margem {quote.margem_percentual.toFixed(0)}%</span>{/if}
                  </div>
                </div>
              </div>

              <div class="flex items-center justify-between gap-4 border-t border-slate-100 pt-3 lg:border-0 lg:pt-0">
                <div class="lg:text-right"><p class="text-[10px] font-bold uppercase tracking-[0.14em] text-slate-400">Valor total</p><p class="mt-0.5 text-xl font-black tracking-tight text-slate-950">{money(quote.valor_total)}</p></div>
                <label class="min-w-36"><span class="sr-only">Status de {quote.cliente.nome}</span><select class="field py-2 text-xs font-bold" value={quote.status} on:change={(event) => changeStatus(quote, event.currentTarget.value as QuoteStatus)} disabled={updatingId === quote.id}><option disabled>{updatingId === quote.id ? 'Salvando...' : 'Alterar status'}</option>{#each statuses as status}<option value={status.value}>{status.label}</option>{/each}</select></label>
              </div>
            </div>

            <div class="mt-4 flex flex-col gap-3 border-t border-slate-100 pt-3 sm:flex-row sm:items-center sm:justify-between">
              <p class="hidden text-xs text-slate-400 sm:block">Última referência: {quote.observacoes ? 'há observações salvas' : 'sem observações adicionais'}</p>
              <div class="flex flex-wrap gap-2 sm:justify-end">
                <a href={`/?edit=${encodeURIComponent(quote.id)}`} class="action-button action-primary" title="Editar orçamento">✎ <span>Editar</span></a>
                <a href={`/?clone=${encodeURIComponent(quote.id)}`} class="action-button" title="Duplicar orçamento">⧉ <span>Duplicar</span></a>
                <button type="button" class="action-button action-pdf" on:click={() => gerarOrcamentoPDF(quote)} title="Baixar PDF">↓ <span>PDF</span></button>
                <button type="button" class="action-button" on:click={() => copyShareLink(quote)} title="Copiar link público">⌁ <span>Link</span></button>
                <button type="button" class="action-button action-whatsapp disabled:cursor-not-allowed disabled:opacity-40" on:click={() => resendWhatsApp(quote)} disabled={!quote.cliente.telefone} title={quote.cliente.telefone ? 'Reenviar pelo WhatsApp' : 'Telefone não informado'}>↗ <span>WhatsApp</span></button>
                <button type="button" class="action-button action-delete disabled:cursor-not-allowed disabled:opacity-50" on:click={() => removeQuote(quote)} disabled={deletingId === quote.id} title="Excluir orçamento">⌫ <span>{deletingId === quote.id ? 'Excluindo...' : 'Excluir'}</span></button>
              </div>
            </div>
          </article>
        {/each}
      </div>
    {/if}
  </section>
</div>

<style>
  .filter-pill {
    @apply inline-flex shrink-0 items-center gap-2 rounded-lg px-3 py-2 text-xs font-bold text-slate-500 transition hover:bg-slate-100 hover:text-slate-800;
  }

  .filter-pill span:last-child {
    @apply rounded-md bg-slate-100 px-1.5 py-0.5 text-[10px] text-slate-400;
  }

  .filter-active {
    @apply bg-slate-900 text-white hover:bg-slate-900 hover:text-white;
  }

  .filter-active span:last-child {
    @apply bg-white/15 text-white;
  }

  .action-button {
    @apply inline-flex items-center justify-center gap-1.5 rounded-lg border border-slate-200 bg-white px-3 py-2 text-[11px] font-bold text-slate-600 transition hover:-translate-y-px hover:border-indigo-200 hover:bg-indigo-50 hover:text-indigo-700;
  }

  .action-primary {
    @apply border-indigo-600 bg-indigo-600 text-white hover:border-indigo-700 hover:bg-indigo-700 hover:text-white;
  }

  .action-pdf {
    @apply border-indigo-200 bg-indigo-50 text-indigo-700 hover:bg-indigo-100;
  }

  .action-whatsapp {
    @apply border-emerald-200 bg-emerald-50 text-emerald-700 hover:bg-emerald-100;
  }

  .action-delete {
    @apply border-rose-200 bg-rose-50 text-rose-600 hover:bg-rose-100;
  }

  .pipeline-stage {
    @apply inline-flex min-w-0 items-center gap-2 rounded-xl border border-slate-200 bg-white px-3 py-3 text-xs font-bold text-slate-600 transition hover:border-indigo-200 hover:bg-indigo-50 hover:text-indigo-700;
  }

  .pipeline-stage strong {
    @apply ml-auto rounded-md bg-slate-100 px-1.5 py-0.5 text-[10px] text-slate-500;
  }

  .pipeline-stage.filter-active {
    @apply border-slate-900 bg-slate-900 text-white hover:bg-slate-900;
  }

  .pipeline-stage.filter-active strong {
    @apply bg-white/15 text-white;
  }
</style>
