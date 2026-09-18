<script lang="ts">
  import { onMount } from 'svelte';
  import { getQuotes, type QuoteResponse, type QuoteStatus } from '$lib/api';

  const pipelineStatuses: { value: QuoteStatus; label: string; dot: string }[] = [
    { value: 'rascunho', label: 'Rascunhos', dot: 'bg-slate-400' },
    { value: 'enviado', label: 'Enviados', dot: 'bg-sky-500' },
    { value: 'negociacao', label: 'Negociação', dot: 'bg-amber-500' },
    { value: 'aprovado', label: 'Aprovados', dot: 'bg-emerald-500' },
    { value: 'concluido', label: 'Concluídos', dot: 'bg-indigo-500' },
  ];

  let quotes: QuoteResponse[] = [];
  let loading = true;
  let error = '';

  $: totalValue = quotes.reduce((sum, quote) => sum + quote.valor_total, 0);
  $: approvedValue = quotes
    .filter((quote) => quote.status === 'aprovado' || quote.status === 'concluido')
    .reduce((sum, quote) => sum + quote.valor_total, 0);
  $: totalMargin = quotes.reduce((sum, quote) => sum + (quote.margem_bruta ?? 0), 0);
  $: averageTicket = quotes.length > 0 ? totalValue / quotes.length : 0;
  $: conversionRate = quotes.length > 0
    ? Math.round((quotes.filter((quote) => quote.status === 'aprovado' || quote.status === 'concluido').length / quotes.length) * 100)
    : 0;
  $: maxMonthlyValue = Math.max(...monthlyData.map((month) => month.value), 1);
  $: topServices = serviceRanking(quotes);
  $: monthlyData = buildMonthlyData(quotes);

  onMount(loadQuotes);

  async function loadQuotes() {
    loading = true;
    error = '';
    try {
      quotes = await getQuotes();
    } catch (reason) {
      error = reason instanceof Error ? reason.message : 'Não foi possível carregar os indicadores.';
    } finally {
      loading = false;
    }
  }

  function money(value: number) {
    return new Intl.NumberFormat('pt-BR', { style: 'currency', currency: 'BRL' }).format(value || 0);
  }

  function compactMoney(value: number) {
    return new Intl.NumberFormat('pt-BR', { notation: 'compact', maximumFractionDigits: 1 }).format(value || 0);
  }

  function countFor(status: QuoteStatus) {
    return quotes.filter((quote) => quote.status === status).length;
  }

  function buildMonthlyData(items: QuoteResponse[]) {
    const now = new Date();
    const months = Array.from({ length: 6 }, (_, index) => {
      const date = new Date(now.getFullYear(), now.getMonth() - (5 - index), 1);
      const key = `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, '0')}`;
      return {
        key,
        label: new Intl.DateTimeFormat('pt-BR', { month: 'short' }).format(date).replace('.', ''),
        value: 0,
        count: 0,
      };
    });

    for (const quote of items) {
      const date = new Date(quote.criado_em);
      const key = `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, '0')}`;
      const month = months.find((item) => item.key === key);
      if (month) {
        month.value += quote.valor_total;
        month.count += 1;
      }
    }

    return months;
  }

  function serviceRanking(items: QuoteResponse[]) {
    const totals = new Map<string, { nome: string; total: number; count: number }>();
    for (const quote of items) {
      for (const item of quote.itens) {
        const current = totals.get(item.nome) ?? { nome: item.nome, total: 0, count: 0 };
        current.total += item.subtotal;
        current.count += 1;
        totals.set(item.nome, current);
      }
    }
    return [...totals.values()].sort((a, b) => b.total - a.total).slice(0, 5);
  }
</script>

<svelte:head>
  <title>Painel financeiro — Dinheiro</title>
  <meta name="description" content="Acompanhe valor vendido, conversão, margem e evolução das suas propostas." />
</svelte:head>

<div class="space-y-7 pb-4">
  <section class="flex flex-col justify-between gap-5 lg:flex-row lg:items-end">
    <div>
      <p class="eyebrow">Visão do negócio</p>
      <h1 class="mt-2 text-3xl font-extrabold tracking-[-0.055em] text-slate-950 sm:text-4xl">Painel financeiro</h1>
      <p class="mt-2 max-w-2xl text-sm leading-6 text-slate-500">Uma leitura rápida do seu pipeline, faturamento potencial e margem estimada.</p>
    </div>
    <div class="flex flex-wrap gap-2">
      <button type="button" class="rounded-xl border border-slate-200 bg-white px-4 py-2.5 text-xs font-bold text-slate-600 transition hover:border-indigo-200 hover:bg-indigo-50 hover:text-indigo-700" on:click={loadQuotes} disabled={loading}>↻ Atualizar</button>
      <a href="/" class="inline-flex items-center gap-2 rounded-xl bg-indigo-600 px-4 py-2.5 text-xs font-bold text-white transition hover:bg-indigo-700"><span class="text-base leading-none">+</span> Novo orçamento</a>
    </div>
  </section>

  {#if error}<div class="rounded-2xl border border-rose-200 bg-rose-50 px-4 py-3 text-sm font-semibold text-rose-700">{error}</div>{/if}

  {#if loading}
    <div class="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
      {#each [1, 2, 3, 4] as item}<div class="surface h-32 animate-pulse bg-slate-50"></div>{/each}
    </div>
  {:else}
    <section class="grid gap-3 sm:grid-cols-2 xl:grid-cols-4" aria-label="Indicadores financeiros">
      <div class="metric-card"><span class="metric-icon bg-indigo-50 text-indigo-600">R$</span><div><p class="metric-label">Valor em propostas</p><p class="metric-value text-lg">{money(totalValue)}</p><p class="metric-caption">{quotes.length} orçamento{quotes.length === 1 ? '' : 's'} no histórico</p></div></div>
      <div class="metric-card"><span class="metric-icon bg-emerald-50 text-emerald-600">✓</span><div><p class="metric-label">Convertido</p><p class="metric-value text-lg">{money(approvedValue)}</p><p class="metric-caption">{conversionRate}% de conversão</p></div></div>
      <div class="metric-card"><span class="metric-icon bg-amber-50 text-amber-600">↗</span><div><p class="metric-label">Margem estimada</p><p class="metric-value text-lg">{money(totalMargin)}</p><p class="metric-caption">após custo interno informado</p></div></div>
      <div class="metric-card"><span class="metric-icon bg-sky-50 text-sky-600">◎</span><div><p class="metric-label">Ticket médio</p><p class="metric-value text-lg">{money(averageTicket)}</p><p class="metric-caption">por orçamento criado</p></div></div>
    </section>

    <section class="surface p-4 sm:p-5">
      <div class="flex flex-col justify-between gap-2 sm:flex-row sm:items-center"><div><p class="eyebrow">Pipeline</p><h2 class="mt-1 text-base font-bold text-slate-900">Distribuição das propostas</h2></div><a href="/historico" class="text-xs font-bold text-indigo-600 hover:text-indigo-800">Ver histórico →</a></div>
      <div class="mt-4 grid grid-cols-2 gap-2 sm:grid-cols-3 lg:grid-cols-5">
        {#each pipelineStatuses as status}
          <a href={`/historico?status=${status.value}`} class="rounded-xl border border-slate-200 bg-white px-3 py-3 transition hover:border-indigo-200 hover:bg-indigo-50"><div class="flex items-center gap-2"><span class={`h-2 w-2 rounded-full ${status.dot}`}></span><span class="truncate text-xs font-bold text-slate-600">{status.label}</span></div><p class="mt-2 text-xl font-black text-slate-900">{countFor(status.value)}</p></a>
        {/each}
      </div>
    </section>

    <div class="grid items-start gap-6 lg:grid-cols-[minmax(0,1.2fr)_minmax(320px,0.8fr)]">
      <section class="surface p-4 sm:p-5">
        <div class="flex items-center justify-between gap-3"><div><p class="eyebrow">Evolução</p><h2 class="mt-1 text-base font-bold text-slate-900">Propostas nos últimos 6 meses</h2></div><span class="text-xs font-semibold text-slate-400">valor total</span></div>
        <div class="mt-6 space-y-4">
          {#each monthlyData as month}
            <div class="grid grid-cols-[42px_minmax(0,1fr)_82px] items-center gap-3"><span class="text-xs font-bold capitalize text-slate-500">{month.label}</span><div class="h-3 overflow-hidden rounded-full bg-slate-100"><div class="h-full rounded-full bg-indigo-500 transition-all" style={`width: ${(month.value / maxMonthlyValue) * 100}%`}></div></div><div class="text-right"><p class="text-xs font-extrabold text-slate-800">R$ {compactMoney(month.value)}</p><p class="text-[10px] text-slate-400">{month.count} proposta{month.count === 1 ? '' : 's'}</p></div></div>
          {/each}
        </div>
      </section>

      <section class="surface p-4 sm:p-5">
        <div class="flex items-center justify-between gap-3"><div><p class="eyebrow">Mix de serviços</p><h2 class="mt-1 text-base font-bold text-slate-900">Mais cotados</h2></div><a href="/servicos" class="text-xs font-bold text-indigo-600 hover:text-indigo-800">Catálogo →</a></div>
        {#if topServices.length === 0}
          <div class="mt-5 rounded-xl border border-dashed border-slate-200 px-4 py-8 text-center text-xs leading-5 text-slate-500">Os serviços mais cotados aparecerão aqui quando você criar propostas.</div>
        {:else}
          <div class="mt-4 divide-y divide-slate-100">
            {#each topServices as service, index}
              <div class="flex items-center gap-3 py-3"><span class="grid h-7 w-7 shrink-0 place-items-center rounded-lg bg-indigo-50 text-xs font-black text-indigo-600">{index + 1}</span><div class="min-w-0 flex-1"><p class="truncate text-sm font-bold text-slate-800">{service.nome}</p><p class="mt-0.5 text-[11px] text-slate-400">{service.count} inclusão{service.count === 1 ? '' : 'ões'}</p></div><span class="text-xs font-extrabold text-slate-700">{money(service.total)}</span></div>
            {/each}
          </div>
        {/if}
      </section>
    </div>
  {/if}
</div>

<style>
  .metric-card {
    @apply flex items-center gap-3 rounded-2xl border border-slate-200 bg-white px-4 py-3.5 shadow-sm;
  }

  .metric-icon {
    @apply grid h-10 w-10 shrink-0 place-items-center rounded-xl text-xs font-black;
  }

  .metric-label {
    @apply text-[11px] font-bold uppercase tracking-[0.08em] text-slate-400;
  }

  .metric-value {
    @apply mt-0.5 text-2xl font-black tracking-tight text-slate-900;
  }

  .metric-caption {
    @apply mt-0.5 text-[10px] font-medium text-slate-400;
  }
</style>
