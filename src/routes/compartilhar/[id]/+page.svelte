<script lang="ts">
  import { page } from '$app/stores';
  import { onMount } from 'svelte';
  import { getPublicQuote, updatePublicQuoteStatus, type QuoteResponse, type QuoteStatus } from '$lib/api';
  import { gerarOrcamentoPDF } from '$lib/pdfGenerator';
  import { getBusinessSettings, type BusinessSettings } from '$lib/settings';
  import Seo from '$lib/Seo.svelte';

  let quote: QuoteResponse | null = null;
  let business: BusinessSettings = getBusinessSettings();
  let loading = true;
  let error = '';
  let updating = false;
  let feedback = '';
  let shareToken = '';

  onMount(async () => {
    business = getBusinessSettings();
    shareToken = $page.url.searchParams.get('token') ?? '';
    if (!shareToken) {
      error = 'Este link público é inválido ou está incompleto.';
      loading = false;
      return;
    }
    try {
      quote = await getPublicQuote($page.params.id, shareToken);
    } catch (reason) {
      error = reason instanceof Error ? reason.message : 'Não foi possível carregar esta proposta.';
    } finally {
      loading = false;
    }
  });

  function money(value: number) {
    return new Intl.NumberFormat('pt-BR', { style: 'currency', currency: 'BRL' }).format(value || 0);
  }

  function dateLabel(value: string) {
    return new Intl.DateTimeFormat('pt-BR', { day: '2-digit', month: 'long', year: 'numeric' }).format(new Date(value));
  }

  function statusLabel(status: QuoteStatus) {
    return { rascunho: 'Rascunho', enviado: 'Enviado', negociacao: 'Em negociação', aprovado: 'Aprovado', recusado: 'Recusado', concluido: 'Concluído' }[status];
  }

  async function respond(status: 'aprovado' | 'recusado') {
    if (!quote || updating) return;
    updating = true;
    try {
      quote = await updatePublicQuoteStatus(quote.id, shareToken, status);
      feedback = status === 'aprovado' ? 'Obrigado! A aprovação foi registrada.' : 'Sua resposta foi registrada. Entraremos em contato.';
    } catch (reason) {
      error = reason instanceof Error ? reason.message : 'Não foi possível registrar sua resposta.';
    } finally {
      updating = false;
    }
  }
</script>

<Seo
  title={quote ? `Proposta para ${quote.cliente.nome} | ${business.nome}` : `Proposta comercial | ${business.nome}`}
  description={quote ? `Proposta comercial de ${business.nome} para ${quote.cliente.nome}.` : 'Visualização compartilhável de uma proposta comercial.'}
  type="article"
/>

{#if loading}
  <div class="flex min-h-[60vh] items-center justify-center text-sm text-slate-500"><span class="animate-pulse">Carregando proposta…</span></div>
{:else if error || !quote}
  <section class="surface mx-auto max-w-lg p-8 text-center"><div class="mx-auto grid h-12 w-12 place-items-center rounded-2xl bg-rose-50 text-xl text-rose-600">!</div><h1 class="mt-4 text-xl font-extrabold text-slate-900">Proposta indisponível</h1><p class="mt-2 text-sm leading-6 text-slate-500">{error || 'Não encontramos este orçamento.'}</p></section>
{:else}
  <div class="mx-auto max-w-4xl space-y-6 pb-8">
    <section class="surface overflow-hidden">
      <div class="bg-indigo-600 px-6 py-7 text-white sm:px-8"><p class="text-[11px] font-bold uppercase tracking-[0.16em] text-indigo-100">Proposta comercial</p><h1 class="mt-2 text-2xl font-extrabold tracking-tight sm:text-3xl">{business.nome}</h1><p class="mt-1 text-sm text-indigo-100">{business.subtitulo}</p><div class="mt-6 flex flex-wrap items-end justify-between gap-4"><div><p class="text-[10px] font-bold uppercase tracking-wider text-indigo-200">Cliente</p><p class="mt-1 text-lg font-bold">{quote.cliente.nome}</p></div><div class="text-left sm:text-right"><p class="text-[10px] font-bold uppercase tracking-wider text-indigo-200">Emitido em</p><p class="mt-1 text-sm font-semibold">{dateLabel(quote.criado_em)}</p></div></div></div>
      <div class="space-y-6 p-6 sm:p-8">
        <div class="grid gap-4 sm:grid-cols-3"><div><p class="field-label">Projeto / equipamento</p><p class="text-sm font-semibold text-slate-800">{quote.cliente.identificador_aparelho || 'Não informado'}</p></div><div><p class="field-label">Contato</p><p class="text-sm font-semibold text-slate-800">{quote.cliente.telefone || 'Não informado'}</p></div><div><p class="field-label">Status</p><span class="inline-flex rounded-full bg-indigo-50 px-2.5 py-1 text-xs font-bold text-indigo-700">{statusLabel(quote.status)}</span></div></div>

        <div><div class="mb-3 flex items-center justify-between gap-3"><h2 class="text-base font-bold text-slate-900">Itens da proposta</h2><span class="text-xs text-slate-500">{quote.itens.length} serviço{quote.itens.length === 1 ? '' : 's'}</span></div><div class="divide-y divide-slate-100 rounded-2xl border border-slate-200"><div class="hidden grid-cols-[minmax(0,1fr)_auto] gap-4 bg-slate-50 px-4 py-3 text-[10px] font-extrabold uppercase tracking-wider text-slate-500 sm:grid"><span>Descrição</span><span>Subtotal</span></div>{#each quote.itens as item}<div class="flex items-start justify-between gap-4 px-4 py-4"><div><p class="text-sm font-bold text-slate-900">{item.nome}</p>{#if item.descricao_customizada}<p class="mt-1 text-xs leading-5 text-slate-500">{item.descricao_customizada}</p>{/if}</div><p class="shrink-0 text-sm font-extrabold text-slate-900">{money(item.subtotal)}</p></div>{/each}</div></div>

        {#if quote.observacoes}<div class="rounded-2xl bg-slate-50 px-4 py-3"><p class="field-label">Observações e prazo</p><p class="text-sm leading-6 text-slate-700">{quote.observacoes}</p></div>{/if}

        <div class="ml-auto max-w-sm space-y-2 border-t border-slate-200 pt-4 text-sm"><div class="flex justify-between gap-4 text-slate-500"><span>Mão de obra</span><span>{money(quote.total_mao_de_obra)}</span></div><div class="flex justify-between gap-4 text-slate-500"><span>Peças</span><span>{money(quote.total_pecas)}</span></div>{#if quote.taxa_deslocamento > 0}<div class="flex justify-between gap-4 text-slate-500"><span>Deslocamento</span><span>{money(quote.taxa_deslocamento)}</span></div>{/if}{#if quote.desconto > 0}<div class="flex justify-between gap-4 text-emerald-600"><span>Desconto</span><span>− {money(quote.desconto)}</span></div>{/if}<div class="flex items-end justify-between gap-4 border-t border-slate-200 pt-3"><span class="font-bold text-slate-800">Total final</span><strong class="text-2xl font-black text-indigo-700">{money(quote.valor_total)}</strong></div></div>

        <div class="flex flex-col gap-3 border-t border-slate-100 pt-5 sm:flex-row sm:items-center sm:justify-between"><p class="text-xs leading-5 text-slate-500">Proposta válida por {business.validade_dias} dias a partir da emissão.</p><div class="flex flex-wrap gap-2"><button type="button" class="rounded-xl border border-slate-200 px-3 py-2.5 text-xs font-bold text-slate-600 transition hover:border-indigo-200 hover:bg-indigo-50 hover:text-indigo-700" on:click={() => gerarOrcamentoPDF(quote)}>Baixar PDF</button>{#if quote.status !== 'aprovado' && quote.status !== 'concluido'}<button type="button" class="rounded-xl bg-indigo-600 px-3 py-2.5 text-xs font-bold text-white transition hover:bg-indigo-700 disabled:opacity-60" on:click={() => respond('aprovado')} disabled={updating}>{updating ? 'Registrando…' : 'Aprovar orçamento'}</button>{/if}</div></div>
        {#if feedback}<div class="rounded-xl border border-emerald-200 bg-emerald-50 px-4 py-3 text-sm font-semibold text-emerald-700" role="status">✓ {feedback}</div>{/if}
      </div>
    </section>
    <p class="text-center text-xs text-slate-400">{business.rodape}</p>
  </div>
{/if}
