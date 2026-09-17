<script lang="ts">
  import { onMount } from 'svelte';
  import {
    createQuote,
    getServices,
    parseClientRequest,
    seedServices,
    type AIInterpretation,
    type ClientInfo,
    type QuoteCreate,
    type QuoteResponse,
    type Service,
  } from '$lib/api';

  type CategoryFilter = 'todos' | 'hardware' | 'dev' | 'infra';
  type QuoteDraft = {
    service: Service;
    custo_peca: number;
    horas_estimadas: number | null;
    taxa_hora: number | null;
    margem_seguranca: number;
  };

  const filters: { key: CategoryFilter; label: string }[] = [
    { key: 'todos', label: 'Todos' },
    { key: 'hardware', label: 'Hardware' },
    { key: 'dev', label: 'Dev' },
    { key: 'infra', label: 'Infra' },
  ];

  let services: Service[] = [];
  let selectedItems: QuoteDraft[] = [];
  let activeCategory: CategoryFilter = 'todos';
  let customer: ClientInfo = { nome: '', telefone: '', identificador_aparelho: '' };
  let clientMessage = '';
  let discount = 0;
  let travelFee = 0;
  let showAiPanel = true;
  let loadingServices = true;
  let analyzing = false;
  let saving = false;
  let pageError = '';
  let aiError = '';
  let saveError = '';
  let toast = '';
  let aiResult: AIInterpretation | null = null;
  let savedQuote: QuoteResponse | null = null;

  $: filteredServices = services.filter(
    (service) => activeCategory === 'todos' || service.categoria === activeCategory,
  );
  $: selectedCount = selectedItems.length;
  $: laborSubtotal = selectedItems.reduce((sum, item) => sum + calculateLabor(item), 0);
  $: partsSubtotal = selectedItems.reduce((sum, item) => sum + (Number(item.custo_peca) || 0), 0);
  $: grossSubtotal = roundMoney(laborSubtotal + partsSubtotal);
  $: finalTotal = roundMoney(grossSubtotal + (Number(travelFee) || 0) - (Number(discount) || 0));

  onMount(loadCatalog);

  async function loadCatalog() {
    loadingServices = true;
    pageError = '';
    try {
      let catalog = await getServices();
      if (catalog.length === 0) {
        catalog = await seedServices();
      }
      services = catalog;
    } catch (error) {
      pageError = errorMessage(error, 'Não foi possível carregar o catálogo.');
    } finally {
      loadingServices = false;
    }
  }

  function errorMessage(error: unknown, fallback: string) {
    return error instanceof Error ? error.message : fallback;
  }

  function roundMoney(value: number) {
    return Math.round(value * 100) / 100;
  }

  function money(value: number) {
    return new Intl.NumberFormat('pt-BR', { style: 'currency', currency: 'BRL' }).format(value || 0);
  }

  function categoryLabel(category: Service['categoria']) {
    return { hardware: 'Hardware', dev: 'Dev', infra: 'Infra', outros: 'Outros' }[category];
  }

  function pricingLabel(type: Service['tipo_cobranca']) {
    return { fixo: 'Fixo', hora: 'Por hora', misto: 'Peça + MO' }[type];
  }

  function serviceIcon(category: Service['categoria']) {
    return { hardware: '⌘', dev: '✦', infra: '◒', outros: '＋' }[category];
  }

  function isSelected(serviceId: string) {
    return selectedItems.some((item) => item.service.id === serviceId);
  }

  function draftFor(service: Service): QuoteDraft {
    return {
      service,
      custo_peca: 0,
      horas_estimadas: service.tipo_cobranca === 'hora' ? 1 : null,
      taxa_hora: service.tipo_cobranca === 'hora' ? service.valor_base : null,
      margem_seguranca: 1.25,
    };
  }

  function toggleService(service: Service) {
    savedQuote = null;
    const existingIndex = selectedItems.findIndex((item) => item.service.id === service.id);
    if (existingIndex >= 0) {
      selectedItems = selectedItems.filter((_, index) => index !== existingIndex);
      return;
    }
    selectedItems = [...selectedItems, draftFor(service)];
  }

  function calculateLabor(item: QuoteDraft) {
    if (item.service.tipo_cobranca === 'hora') {
      const hours = Number(item.horas_estimadas) || 0;
      const rate = Number(item.taxa_hora) || 0;
      return roundMoney(hours * rate * (Number(item.margem_seguranca) || 1.25));
    }
    return Number(item.service.valor_base) || 0;
  }

  async function analyzeWithAi() {
    if (!clientMessage.trim()) {
      aiError = 'Cole uma mensagem do cliente antes de analisar.';
      return;
    }

    analyzing = true;
    aiError = '';
    try {
      const result = await parseClientRequest(clientMessage.trim());
      aiResult = result;
      const suggestions = result.servicos_sugeridos
        .map((suggestion) => services.find((service) => service.id === suggestion.service_id))
        .filter((service): service is Service => Boolean(service));
      const missing = suggestions.filter((service) => !isSelected(service.id));
      selectedItems = [...selectedItems, ...missing.map(draftFor)];
      savedQuote = null;
      if (missing.length > 0) {
        toast = `${missing.length} serviço${missing.length > 1 ? 's' : ''} pré-selecionado${missing.length > 1 ? 's' : ''}.`;
        window.setTimeout(() => (toast = ''), 3500);
      }
    } catch (error) {
      aiError = errorMessage(error, 'Não foi possível analisar a mensagem.');
    } finally {
      analyzing = false;
    }
  }

  function buildQuote(): QuoteCreate {
    return {
      cliente: {
        nome: customer.nome.trim(),
        telefone: customer.telefone?.trim() || null,
        identificador_aparelho: customer.identificador_aparelho?.trim() || null,
      },
      itens: selectedItems.map((item) => ({
        service_id: item.service.id,
        nome: item.service.nome,
        mao_de_obra: item.service.tipo_cobranca === 'hora' ? 0 : item.service.valor_base,
        custo_peca: roundMoney(Number(item.custo_peca) || 0),
        horas_estimadas: item.horas_estimadas,
        taxa_hora: item.taxa_hora,
        margem_seguranca: item.margem_seguranca,
        descricao_customizada: item.service.descricao_padrao,
      })),
      desconto: roundMoney(Number(discount) || 0),
      taxa_deslocamento: roundMoney(Number(travelFee) || 0),
    };
  }

  async function saveQuote() {
    if (!customer.nome.trim()) {
      saveError = 'Informe o nome do cliente.';
      return;
    }
    if (selectedItems.length === 0) {
      saveError = 'Selecione pelo menos um serviço.';
      return;
    }

    saving = true;
    saveError = '';
    try {
      savedQuote = await createQuote(buildQuote());
      toast = 'Orçamento salvo com sucesso.';
      window.setTimeout(() => (toast = ''), 3500);
    } catch (error) {
      saveError = errorMessage(error, 'Não foi possível salvar o orçamento.');
    } finally {
      saving = false;
    }
  }

  function whatsappUrl(quote: QuoteResponse) {
    const digits = (quote.cliente.telefone || '').replace(/\D/g, '');
    const phone = digits ? (digits.startsWith('55') ? digits : `55${digits}`) : '';
    return `https://wa.me/${phone}?text=${encodeURIComponent(quote.mensagem_whatsapp)}`;
  }

  function openWhatsApp() {
    if (!savedQuote || !savedQuote.cliente.telefone) return;
    window.open(whatsappUrl(savedQuote), '_blank', 'noopener,noreferrer');
  }

  async function copyWhatsApp() {
    if (!savedQuote) return;
    try {
      await navigator.clipboard.writeText(savedQuote.mensagem_whatsapp);
      toast = 'Mensagem copiada para a área de transferência.';
      window.setTimeout(() => (toast = ''), 3500);
    } catch {
      toast = 'Não foi possível copiar automaticamente.';
    }
  }
</script>

<svelte:head>
  <title>Novo orçamento — Dinheiro</title>
  <meta name="description" content="Monte e envie orçamentos técnicos em poucos minutos." />
</svelte:head>

<div class="space-y-8">
  <section class="flex flex-col justify-between gap-5 sm:flex-row sm:items-end">
    <div>
      <p class="eyebrow">Workspace comercial</p>
      <h1 class="mt-2 text-3xl font-extrabold tracking-[-0.055em] text-slate-950 sm:text-4xl">Novo orçamento</h1>
      <p class="mt-2 max-w-2xl text-sm leading-6 text-slate-500">Entenda o pedido, escolha os serviços e entregue um orçamento claro para o cliente.</p>
    </div>
    <a href="/docs" class="inline-flex items-center gap-2 self-start rounded-xl border border-slate-200 bg-white px-4 py-2.5 text-xs font-bold text-slate-600 shadow-sm transition hover:border-indigo-200 hover:text-indigo-700 sm:self-auto">Abrir API <span aria-hidden="true">↗</span></a>
  </section>

  {#if toast}
    <div class="fixed bottom-5 left-1/2 z-50 -translate-x-1/2 rounded-xl bg-slate-950 px-4 py-3 text-sm font-semibold text-white shadow-xl">{toast}</div>
  {/if}

  <section class="surface p-5 sm:p-6">
    <div class="mb-5 flex items-center justify-between gap-4">
      <div>
        <p class="eyebrow">01 · Contexto</p>
        <h2 class="mt-1 text-lg font-bold tracking-tight text-slate-900">Para quem é este orçamento?</h2>
      </div>
      <span class="hidden rounded-full bg-indigo-50 px-3 py-1 text-[11px] font-bold text-indigo-700 sm:inline-flex">Rascunho novo</span>
    </div>
    <div class="grid gap-4 md:grid-cols-3">
      <label>
        <span class="field-label">Nome do cliente</span>
        <input class="field" bind:value={customer.nome} placeholder="Ex.: Ana Souza" />
      </label>
      <label>
        <span class="field-label">Telefone / WhatsApp</span>
        <input class="field" bind:value={customer.telefone} inputmode="tel" placeholder="(71) 99999-0000" />
      </label>
      <label>
        <span class="field-label">Aparelho ou projeto</span>
        <input class="field" bind:value={customer.identificador_aparelho} placeholder="Ex.: MacBook Pro / Landing page" />
      </label>
    </div>
  </section>

  <section class="surface overflow-hidden">
    <button type="button" class="flex w-full items-center justify-between gap-4 p-5 text-left sm:p-6" on:click={() => (showAiPanel = !showAiPanel)} aria-expanded={showAiPanel}>
      <span class="flex items-center gap-3">
        <span class="grid h-10 w-10 place-items-center rounded-xl bg-indigo-100 text-lg text-indigo-700">✦</span>
        <span>
          <span class="eyebrow block">02 · Atalho inteligente</span>
          <span class="mt-1 block text-lg font-bold tracking-tight text-slate-900">Colar mensagem do WhatsApp</span>
        </span>
      </span>
      <span class="text-xl text-slate-400" aria-hidden="true">{showAiPanel ? '−' : '+'}</span>
    </button>
    {#if showAiPanel}
      <div class="border-t border-slate-100 px-5 pb-5 pt-4 sm:px-6 sm:pb-6">
        <div class="flex flex-col gap-3 sm:flex-row sm:items-end">
          <label class="flex-1">
            <span class="field-label">Mensagem ou transcrição do áudio</span>
            <textarea class="field min-h-[108px] resize-y" bind:value={clientMessage} placeholder="Ex.: Meu PC está esquentando, travando e quero colocar um SSD mais rápido..."></textarea>
          </label>
          <button type="button" class="inline-flex min-h-11 items-center justify-center gap-2 rounded-xl bg-indigo-600 px-5 py-3 text-sm font-bold text-white shadow-lg shadow-indigo-200 transition hover:bg-indigo-700 disabled:cursor-not-allowed disabled:opacity-60" on:click={analyzeWithAi} disabled={analyzing || loadingServices}>
            {#if analyzing}<span class="animate-pulse">Analisando…</span>{:else}<span>✦ Analisar com IA</span>{/if}
          </button>
        </div>
        {#if aiError}<p class="mt-3 text-sm font-medium text-rose-600">{aiError}</p>{/if}
        {#if aiResult}
          <div class="mt-4 rounded-xl border border-indigo-100 bg-indigo-50/60 p-4">
            <p class="text-sm font-semibold text-indigo-950">{aiResult.resumo_problema}</p>
            <p class="mt-1 text-xs leading-5 text-indigo-800">{aiResult.observacoes_tecnicas}</p>
            {#if aiResult.servicos_sugeridos.length > 0}
              <div class="mt-3 flex flex-wrap gap-2">
                {#each aiResult.servicos_sugeridos as suggestion}
                  <span class="rounded-full bg-white px-3 py-1.5 text-xs font-semibold text-indigo-700 shadow-sm">✓ {suggestion.nome}</span>
                {/each}
              </div>
            {/if}
          </div>
        {/if}
      </div>
    {/if}
  </section>

  {#if pageError}
    <div class="rounded-xl border border-rose-200 bg-rose-50 px-4 py-3 text-sm font-medium text-rose-700">{pageError}</div>
  {/if}

  <div class="grid items-start gap-6 lg:grid-cols-[minmax(0,1fr)_360px]">
    <section class="min-w-0">
      <div class="mb-5 flex flex-col justify-between gap-4 sm:flex-row sm:items-end">
        <div>
          <p class="eyebrow">03 · Catálogo</p>
          <h2 class="mt-1 text-2xl font-extrabold tracking-[-0.04em] text-slate-950">Escolha os serviços</h2>
        </div>
        <div class="flex rounded-xl bg-slate-200/70 p-1" role="tablist" aria-label="Filtrar catálogo">
          {#each filters as filter}
            <button type="button" role="tab" aria-selected={activeCategory === filter.key} class:tab-active={activeCategory === filter.key} class="rounded-lg px-3 py-2 text-xs font-bold text-slate-500 transition hover:text-slate-900" on:click={() => (activeCategory = filter.key)}>{filter.label}</button>
          {/each}
        </div>
      </div>

      {#if loadingServices}
        <div class="surface flex min-h-56 items-center justify-center text-sm text-slate-500"><span class="animate-pulse">Carregando catálogo…</span></div>
      {:else if filteredServices.length === 0}
        <div class="surface flex min-h-56 flex-col items-center justify-center px-6 text-center"><span class="text-3xl">◌</span><p class="mt-3 font-bold text-slate-700">Nenhum serviço nesta categoria</p><p class="mt-1 text-sm text-slate-500">Adicione serviços no catálogo ou escolha outro filtro.</p></div>
      {:else}
        <div class="grid gap-3 sm:grid-cols-2">
          {#each filteredServices as service}
            <button type="button" class="group rounded-2xl border bg-white p-4 text-left shadow-sm transition hover:-translate-y-0.5 hover:border-indigo-300 hover:shadow-lg hover:shadow-indigo-100/50" class:border-indigo-400={isSelected(service.id)} class:bg-indigo-50={isSelected(service.id)} class:border-slate-200={!isSelected(service.id)} aria-pressed={isSelected(service.id)} on:click={() => toggleService(service)}>
              <div class="flex items-start justify-between gap-3">
                <span class="grid h-10 w-10 shrink-0 place-items-center rounded-xl bg-slate-100 text-lg text-slate-600 transition group-hover:bg-indigo-100 group-hover:text-indigo-700">{serviceIcon(service.categoria)}</span>
                {#if isSelected(service.id)}<span class="rounded-full bg-indigo-600 px-2.5 py-1 text-[10px] font-extrabold uppercase tracking-wider text-white">Selecionado</span>{:else}<span class="rounded-full bg-slate-100 px-2.5 py-1 text-[10px] font-bold uppercase tracking-wider text-slate-500">{categoryLabel(service.categoria)}</span>{/if}
              </div>
              <h3 class="mt-4 font-bold tracking-tight text-slate-900">{service.nome}</h3>
              <p class="mt-1 min-h-10 text-xs leading-5 text-slate-500">{service.descricao_padrao || 'Serviço técnico sob demanda.'}</p>
              <div class="mt-4 flex items-end justify-between gap-3 border-t border-slate-100 pt-3">
                <span class="text-xs font-semibold text-slate-500">{pricingLabel(service.tipo_cobranca)}{service.permite_peca ? ' · aceita peça' : ''}</span>
                <span class="text-sm font-extrabold text-slate-900">{service.tipo_cobranca === 'hora' ? `${money(service.valor_base)}/h` : money(service.valor_base)}</span>
              </div>
            </button>
          {/each}
        </div>
      {/if}
    </section>

    <aside class="surface overflow-hidden lg:sticky lg:top-6">
      <div class="border-b border-slate-100 bg-slate-950 p-5 text-white">
        <div class="flex items-center justify-between gap-4">
          <div><p class="text-[10px] font-bold uppercase tracking-[0.16em] text-indigo-300">04 · Resumo</p><h2 class="mt-1 text-lg font-bold">Orçamento atual</h2></div>
          <span class="rounded-full bg-white/10 px-2.5 py-1 text-xs font-bold text-slate-300">{selectedCount} {selectedCount === 1 ? 'item' : 'itens'}</span>
        </div>
      </div>
      <div class="space-y-4 p-5">
        {#if selectedItems.length === 0}
          <div class="rounded-xl border border-dashed border-slate-200 px-4 py-7 text-center"><p class="text-sm font-semibold text-slate-600">Seu orçamento está vazio</p><p class="mt-1 text-xs leading-5 text-slate-400">Clique em um serviço para começar a montar.</p></div>
        {:else}
          <div class="space-y-3">
            {#each selectedItems as item}
              <div class="rounded-xl border border-slate-200 bg-slate-50/70 p-3">
                <div class="flex items-start justify-between gap-3">
                  <div><p class="text-sm font-bold text-slate-800">{item.service.nome}</p><p class="mt-0.5 text-xs text-slate-500">{money(calculateLabor(item))} mão de obra</p></div>
                  <button type="button" class="rounded-lg px-2 py-1 text-xs font-bold text-slate-400 transition hover:bg-rose-50 hover:text-rose-600" aria-label={`Remover ${item.service.nome}`} on:click={() => toggleService(item.service)}>Remover</button>
                </div>
                {#if item.service.permite_peca}
                  <label class="mt-3 block"><span class="field-label">Custo da peça (R$)</span><input class="field bg-white" type="number" min="0" step="0.01" bind:value={item.custo_peca} on:input={() => (savedQuote = null)} placeholder="0,00" /></label>
                {/if}
                {#if item.service.tipo_cobranca === 'hora'}
                  <div class="mt-3 grid grid-cols-2 gap-2">
                    <label><span class="field-label">Horas estimadas</span><input class="field bg-white" type="number" min="0" step="0.5" bind:value={item.horas_estimadas} on:input={() => (savedQuote = null)} /></label>
                    <label><span class="field-label">Taxa / hora</span><input class="field bg-white" type="number" min="0" step="0.01" bind:value={item.taxa_hora} on:input={() => (savedQuote = null)} /></label>
                  </div>
                {/if}
              </div>
            {/each}
          </div>
        {/if}

        <div class="space-y-3 border-t border-slate-100 pt-4">
          <div class="grid grid-cols-2 gap-2">
            <label><span class="field-label">Desconto (R$)</span><input class="field" type="number" min="0" step="0.01" bind:value={discount} on:input={() => (savedQuote = null)} /></label>
            <label><span class="field-label">Deslocamento (R$)</span><input class="field" type="number" min="0" step="0.01" bind:value={travelFee} on:input={() => (savedQuote = null)} /></label>
          </div>
          <div class="space-y-2 text-sm">
            <div class="flex justify-between gap-4 text-slate-500"><span>Mão de obra</span><span class="font-semibold text-slate-700">{money(laborSubtotal)}</span></div>
            <div class="flex justify-between gap-4 text-slate-500"><span>Peças</span><span class="font-semibold text-slate-700">{money(partsSubtotal)}</span></div>
            {#if discount > 0}<div class="flex justify-between gap-4 text-emerald-600"><span>Desconto</span><span class="font-semibold">− {money(discount)}</span></div>{/if}
            {#if travelFee > 0}<div class="flex justify-between gap-4 text-slate-500"><span>Deslocamento</span><span class="font-semibold text-slate-700">{money(travelFee)}</span></div>{/if}
          </div>
          <div class="flex items-end justify-between gap-4 border-t border-slate-200 pt-4"><span class="text-sm font-bold text-slate-700">Total final</span><span class="text-2xl font-black tracking-tight text-indigo-700">{money(finalTotal)}</span></div>
        </div>

        {#if saveError}<p class="rounded-lg bg-rose-50 px-3 py-2 text-xs font-semibold text-rose-700">{saveError}</p>{/if}
        <button type="button" class="flex w-full items-center justify-center rounded-xl bg-indigo-600 px-4 py-3 text-sm font-bold text-white shadow-lg shadow-indigo-200 transition hover:bg-indigo-700 disabled:cursor-not-allowed disabled:opacity-50" on:click={saveQuote} disabled={saving || selectedItems.length === 0}>{saving ? 'Salvando…' : 'Salvar orçamento'}</button>
        <div class="grid grid-cols-2 gap-2">
          <button type="button" class="rounded-xl border border-slate-200 px-3 py-2.5 text-xs font-bold text-slate-600 transition hover:border-indigo-200 hover:text-indigo-700 disabled:cursor-not-allowed disabled:opacity-40" on:click={copyWhatsApp} disabled={!savedQuote}>Copiar mensagem</button>
          <button type="button" class="rounded-xl bg-emerald-600 px-3 py-2.5 text-xs font-bold text-white transition hover:bg-emerald-700 disabled:cursor-not-allowed disabled:opacity-40" on:click={openWhatsApp} disabled={!savedQuote || !savedQuote.cliente.telefone}>Abrir WhatsApp</button>
        </div>
        {#if savedQuote && !savedQuote.cliente.telefone}<p class="text-center text-[11px] leading-4 text-amber-600">Adicione um telefone para abrir a conversa automaticamente.</p>{/if}
      </div>
    </aside>
  </div>
</div>

<style>
  :global(.tab-active) {
    background: white;
    color: #4338ca;
    box-shadow: 0 1px 3px rgba(15, 23, 42, 0.1);
  }
</style>
