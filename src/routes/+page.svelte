<script lang="ts">
  import { goto } from '$app/navigation';
  import { onMount } from 'svelte';
  import {
    createQuote,
    getQuote,
    getServices,
    parseClientRequest,
    seedServices,
    updateQuote,
    type AIInterpretation,
    type ClientInfo,
    type QuoteCreate,
    type QuoteResponse,
    type Service,
  } from '$lib/api';
  import { gerarOrcamentoPDF } from '$lib/pdfGenerator';

  type CategoryFilter = 'todos' | 'hardware' | 'dev' | 'infra' | 'outros';
  type QuoteDraft = {
    service: Service;
    mao_de_obra: number;
    custo_peca: number;
    horas_estimadas: number | null;
    taxa_hora: number | null;
    margem_seguranca: number;
    descricao_customizada: string | null;
  };

  const filters: { key: CategoryFilter; label: string }[] = [
    { key: 'todos', label: 'Todos' },
    { key: 'hardware', label: 'Hardware' },
    { key: 'dev', label: 'Dev' },
    { key: 'infra', label: 'Infra' },
    { key: 'outros', label: 'Outros' },
  ];

  let services: Service[] = [];
  let selectedItems: QuoteDraft[] = [];
  let activeCategory: CategoryFilter = 'todos';
  let serviceSearch = '';
  let customer: ClientInfo = { nome: '', telefone: '', identificador_aparelho: '' };
  let observations = '';
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
  let draftMode: 'new' | 'edit' | 'clone' = 'new';
  let draftSourceId = '';
  let loadingDraft = false;

  $: normalizedServiceSearch = serviceSearch.trim().toLocaleLowerCase('pt-BR');
  $: filteredServices = services.filter((service) => {
    if (activeCategory !== 'todos' && service.categoria !== activeCategory) return false;
    if (!normalizedServiceSearch) return true;
    return `${service.nome} ${service.descricao_padrao ?? ''}`
      .toLocaleLowerCase('pt-BR')
      .includes(normalizedServiceSearch);
  });
  $: selectedCount = selectedItems.length;
  $: laborSubtotal = selectedItems.reduce((sum, item) => sum + calculateLabor(item), 0);
  $: partsSubtotal = selectedItems.reduce((sum, item) => sum + (Number(item.custo_peca) || 0), 0);
  $: grossSubtotal = roundMoney(laborSubtotal + partsSubtotal);
  $: finalTotal = roundMoney(grossSubtotal + (Number(travelFee) || 0) - (Number(discount) || 0));
  $: hasServiceFilters = Boolean(normalizedServiceSearch) || activeCategory !== 'todos';
  $: customerReady = Boolean(customer.nome.trim());

  onMount(async () => {
    await loadCatalog();
    await loadDraftFromQuery();
  });

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

  function priceLabel(service: Service) {
    return service.tipo_cobranca === 'hora' ? `${money(service.valor_base)}/h` : money(service.valor_base);
  }

  function serviceIcon(category: Service['categoria']) {
    return { hardware: '⌘', dev: '✦', infra: '◒', outros: '＋' }[category];
  }

  function serviceCount(category: CategoryFilter) {
    return category === 'todos' ? services.length : services.filter((service) => service.categoria === category).length;
  }

  function clearServiceFilters() {
    serviceSearch = '';
    activeCategory = 'todos';
  }

  function isSelected(serviceId: string) {
    return selectedItems.some((item) => item.service.id === serviceId);
  }

  function draftFor(service: Service): QuoteDraft {
    return {
      service,
      mao_de_obra: service.tipo_cobranca === 'hora' ? 0 : service.valor_base,
      custo_peca: 0,
      horas_estimadas: service.tipo_cobranca === 'hora' ? 1 : null,
      taxa_hora: service.tipo_cobranca === 'hora' ? service.valor_base : null,
      margem_seguranca: 1.25,
      descricao_customizada: service.descricao_padrao,
    };
  }

  function draftFromQuoteItem(quote: QuoteResponse, item: QuoteResponse['itens'][number]): QuoteDraft {
    const catalogService = services.find((service) => service.id === item.service_id);
    const service: Service = catalogService ?? {
      id: item.service_id,
      nome: item.nome,
      categoria: item.categoria ?? 'outros',
      tipo_cobranca: item.horas_estimadas != null && item.taxa_hora != null ? 'hora' : 'fixo',
      valor_base: item.mao_de_obra,
      permite_peca: Number(item.custo_peca) > 0,
      descricao_padrao: item.descricao_customizada ?? null,
      criado_em: quote.criado_em,
    };

    return {
      service,
      mao_de_obra: service.tipo_cobranca === 'hora' ? 0 : item.mao_de_obra,
      custo_peca: Number(item.custo_peca) || 0,
      horas_estimadas: item.horas_estimadas,
      taxa_hora: item.taxa_hora,
      margem_seguranca: item.margem_seguranca ?? 1.25,
      descricao_customizada: item.descricao_customizada ?? service.descricao_padrao,
    };
  }

  async function loadDraftFromQuery() {
    const params = new URLSearchParams(window.location.search);
    const editId = params.get('edit');
    const cloneId = params.get('clone');
    const sourceId = editId || cloneId;
    if (!sourceId) return;

    loadingDraft = true;
    pageError = '';
    try {
      const quote = await getQuote(sourceId);
      customer = { ...quote.cliente };
      observations = quote.observacoes ?? '';
      discount = quote.desconto;
      travelFee = quote.taxa_deslocamento;
      selectedItems = quote.itens.map((item) => draftFromQuoteItem(quote, item));
      draftMode = editId ? 'edit' : 'clone';
      draftSourceId = sourceId;
      savedQuote = editId ? quote : null;
      toast = editId ? `Orçamento #${sourceId} carregado para edição.` : `Orçamento #${sourceId} duplicado.`;
      window.setTimeout(() => (toast = ''), 3500);
    } catch (error) {
      pageError = errorMessage(error, 'Não foi possível carregar o orçamento.');
    } finally {
      loadingDraft = false;
    }
  }

  function cancelDraft() {
    goto('/');
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

  function clearSelectedItems() {
    selectedItems = [];
    savedQuote = null;
  }

  function calculateLabor(item: QuoteDraft) {
    if (item.service.tipo_cobranca === 'hora') {
      const hours = Number(item.horas_estimadas) || 0;
      const rate = Number(item.taxa_hora) || 0;
      return roundMoney(hours * rate * (Number(item.margem_seguranca) || 1.25));
    }
    return Number(item.mao_de_obra) || 0;
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
        categoria: item.service.categoria,
        mao_de_obra: item.service.tipo_cobranca === 'hora' ? 0 : item.mao_de_obra,
        custo_peca: roundMoney(Number(item.custo_peca) || 0),
        horas_estimadas: item.horas_estimadas,
        taxa_hora: item.taxa_hora,
        margem_seguranca: item.margem_seguranca,
        descricao_customizada: item.descricao_customizada,
      })),
      desconto: roundMoney(Number(discount) || 0),
      taxa_deslocamento: roundMoney(Number(travelFee) || 0),
      observacoes: observations.trim() || null,
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
      if (draftMode === 'edit' && draftSourceId) {
        savedQuote = await updateQuote(draftSourceId, buildQuote());
        await goto('/historico');
        return;
      }

      savedQuote = await createQuote(buildQuote());
      draftMode = 'new';
      draftSourceId = '';
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
  {#if draftMode !== 'new'}
    <section class="flex flex-col justify-between gap-4 rounded-2xl border border-indigo-200 bg-indigo-50 px-5 py-4 sm:flex-row sm:items-center sm:px-6">
      <div>
        <p class="eyebrow text-indigo-600">{draftMode === 'edit' ? 'Modo de edição' : 'Novo a partir de um existente'}</p>
        <p class="mt-1 text-sm font-bold text-indigo-950">{draftMode === 'edit' ? `Editando Orçamento #${draftSourceId}` : `Duplicando Orçamento #${draftSourceId}`}</p>
      </div>
      <button type="button" class="rounded-xl border border-indigo-200 bg-white px-4 py-2.5 text-xs font-bold text-indigo-700 transition hover:bg-indigo-100" on:click={cancelDraft}>Cancelar e voltar</button>
    </section>
  {/if}

  <section class="flex flex-col justify-between gap-5 sm:flex-row sm:items-end">
    <div>
      <p class="eyebrow">Workspace comercial</p>
      <h1 class="mt-2 text-3xl font-extrabold tracking-[-0.055em] text-slate-950 sm:text-4xl">{draftMode === 'edit' ? 'Editar orçamento' : draftMode === 'clone' ? 'Duplicar orçamento' : 'Novo orçamento'}</h1>
      <p class="mt-2 max-w-2xl text-sm leading-6 text-slate-500">Entenda o pedido, escolha os serviços e entregue um orçamento claro para o cliente.</p>
    </div>
    <a href="/docs" class="inline-flex items-center gap-2 self-start rounded-xl border border-slate-200 bg-white px-4 py-2.5 text-xs font-bold text-slate-600 shadow-sm transition hover:border-indigo-200 hover:text-indigo-700 sm:self-auto">Abrir API <span aria-hidden="true">↗</span></a>
  </section>

  <section class="grid gap-3 sm:grid-cols-2 xl:grid-cols-4" aria-label="Resumo do orçamento atual">
    <div class="metric-card"><span class="metric-icon bg-indigo-50 text-indigo-600">#</span><div><p class="metric-label">Serviços escolhidos</p><p class="metric-value">{selectedCount}</p><p class="metric-caption">de {services.length} disponíveis</p></div></div>
    <div class="metric-card"><span class="metric-icon bg-sky-50 text-sky-600">MO</span><div><p class="metric-label">Mão de obra</p><p class="metric-value text-lg">{money(laborSubtotal)}</p><p class="metric-caption">subtotal calculado</p></div></div>
    <div class="metric-card"><span class="metric-icon bg-amber-50 text-amber-600">◈</span><div><p class="metric-label">Peças</p><p class="metric-value text-lg">{money(partsSubtotal)}</p><p class="metric-caption">custos informados</p></div></div>
    <div class="metric-card metric-card-highlight"><span class="metric-icon bg-indigo-600 text-white">R$</span><div><p class="metric-label text-indigo-700">Total estimado</p><p class="metric-value text-lg text-indigo-950">{money(finalTotal)}</p><p class="metric-caption text-indigo-600">atualizado em tempo real</p></div></div>
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
      <span class:status-ready={customerReady} class="hidden rounded-full bg-slate-100 px-3 py-1 text-[11px] font-bold text-slate-500 sm:inline-flex">{customerReady ? 'Cliente identificado' : 'Falta o nome'}</span>
    </div>
    <div class="grid gap-4 md:grid-cols-3">
      <label>
        <span class="field-label">Nome do cliente</span>
        <input class="field" bind:value={customer.nome} on:input={() => (savedQuote = null)} placeholder="Ex.: Ana Souza" />
      </label>
      <label>
        <span class="field-label">Telefone / WhatsApp</span>
        <input class="field" bind:value={customer.telefone} on:input={() => (savedQuote = null)} inputmode="tel" placeholder="(71) 99999-0000" />
      </label>
      <label>
        <span class="field-label">Aparelho ou projeto</span>
        <input class="field" bind:value={customer.identificador_aparelho} on:input={() => (savedQuote = null)} placeholder="Ex.: MacBook Pro / Landing page" />
      </label>
    </div>
    <p class="mt-4 text-xs text-slate-400">O telefone é opcional, mas necessário para abrir o WhatsApp automaticamente depois de salvar.</p>
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
            <textarea class="field min-h-[108px] resize-y" maxlength="1600" bind:value={clientMessage} placeholder="Ex.: Meu PC está esquentando, travando e quero colocar um SSD mais rápido..."></textarea>
            <span class="mt-1 block text-right text-[11px] text-slate-400">{clientMessage.length}/1600</span>
          </label>
          <button type="button" class="inline-flex min-h-11 items-center justify-center gap-2 rounded-xl bg-indigo-600 px-5 py-3 text-sm font-bold text-white shadow-lg shadow-indigo-200 transition hover:bg-indigo-700 disabled:cursor-not-allowed disabled:opacity-60" on:click={analyzeWithAi} aria-busy={analyzing} disabled={analyzing || loadingServices}>
            {#if analyzing}<span class="animate-pulse">Analisando…</span>{:else}<span>✦ Analisar com IA</span>{/if}
          </button>
        </div>
        {#if aiError}<p class="mt-3 text-sm font-medium text-rose-600">{aiError}</p>{/if}
        {#if aiResult}
          <div class="mt-4 rounded-xl border border-indigo-100 bg-indigo-50/60 p-4">
            <p class="text-sm font-semibold text-indigo-950">{aiResult.resumo_problema}</p>
            <p class="mt-1 text-xs leading-5 text-indigo-800">{aiResult.observacoes_tecnicas}</p>
            {#if aiResult.servicos_sugeridos.length > 0}
              <div class="mt-3 grid gap-2 sm:grid-cols-2">
                {#each aiResult.servicos_sugeridos as suggestion}
                  <div class="rounded-xl bg-white px-3 py-2 shadow-sm"><p class="text-xs font-bold text-indigo-700">✓ {suggestion.nome}</p><p class="mt-0.5 text-[11px] leading-4 text-slate-500">{suggestion.motivo}</p></div>
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
    <section class="surface min-w-0 overflow-hidden" aria-labelledby="catalog-title">
      <div class="border-b border-slate-100 px-5 py-5 sm:px-6">
        <div class="flex flex-col justify-between gap-4 sm:flex-row sm:items-center">
          <div>
            <div class="flex items-center gap-2"><p class="eyebrow">03 · Catálogo</p><span class="rounded-full bg-slate-100 px-2 py-0.5 text-[10px] font-extrabold text-slate-500">{selectedCount} selecionado{selectedCount === 1 ? '' : 's'}</span></div>
            <h2 id="catalog-title" class="mt-1 text-2xl font-extrabold tracking-[-0.04em] text-slate-950">Escolha os serviços</h2>
            <p class="mt-1 text-xs text-slate-500">Clique em um card para adicionar ou remover do orçamento.</p>
          </div>
          {#if selectedCount > 0}<button type="button" class="rounded-lg px-3 py-2 text-xs font-bold text-slate-500 transition hover:bg-rose-50 hover:text-rose-600" on:click={clearSelectedItems}>Limpar seleção</button>{/if}
        </div>

        <label class="relative mt-5 block"><span class="sr-only">Buscar serviço</span><span class="pointer-events-none absolute left-3.5 top-1/2 -translate-y-1/2 text-base text-slate-400">⌕</span><input class="field pl-10 pr-10" type="search" bind:value={serviceSearch} placeholder="Buscar por nome ou descrição…" /><button type="button" class:hidden={!serviceSearch} class="absolute right-2 top-1/2 -translate-y-1/2 rounded-lg px-2 py-1 text-lg leading-none text-slate-400 hover:bg-slate-100 hover:text-slate-700" aria-label="Limpar busca" on:click={() => (serviceSearch = '')}>×</button></label>

        <div class="mt-4 flex gap-1 overflow-x-auto pb-1" role="tablist" aria-label="Filtrar catálogo">
          {#each filters as filter}
            <button type="button" role="tab" aria-selected={activeCategory === filter.key} class:filter-active={activeCategory === filter.key} class="filter-pill whitespace-nowrap" on:click={() => (activeCategory = filter.key)}>{filter.label}<span class="filter-count">{serviceCount(filter.key)}</span></button>
          {/each}
        </div>
      </div>

      {#if loadingServices}
        <div class="grid gap-3 p-5 sm:grid-cols-2 sm:p-6" aria-label="Carregando catálogo">
          {#each Array(6) as _}<div class="h-44 animate-pulse rounded-2xl border border-slate-100 bg-slate-50"></div>{/each}
        </div>
      {:else if filteredServices.length === 0}
        <div class="p-10 text-center"><div class="mx-auto grid h-12 w-12 place-items-center rounded-2xl bg-slate-100 text-xl text-slate-500">⌕</div><h3 class="mt-4 font-bold text-slate-900">{hasServiceFilters ? 'Nenhum serviço encontrado' : 'Nenhum serviço cadastrado'}</h3><p class="mx-auto mt-1 max-w-sm text-sm leading-6 text-slate-500">{hasServiceFilters ? 'Tente outro termo ou remova os filtros para ver todo o catálogo.' : 'Cadastre serviços na área de catálogo para começar.'}</p>{#if hasServiceFilters}<button type="button" class="mt-5 rounded-xl border border-slate-200 bg-white px-4 py-2.5 text-xs font-bold text-slate-600 transition hover:border-indigo-200 hover:text-indigo-700" on:click={clearServiceFilters}>Limpar filtros</button>{/if}</div>
      {:else}
        <div class="grid gap-3 p-5 sm:grid-cols-2 sm:p-6">
          {#each filteredServices as service (service.id)}
            <button type="button" class="service-card group text-left" class:service-card-selected={isSelected(service.id)} aria-pressed={isSelected(service.id)} aria-label={`${isSelected(service.id) ? 'Remover' : 'Adicionar'} ${service.nome}`} on:click={() => toggleService(service)}>
              <div class="flex items-start justify-between gap-3">
                <div class="flex min-w-0 items-center gap-2"><span class="grid h-8 w-8 shrink-0 place-items-center rounded-xl bg-slate-100 text-sm font-black text-slate-500 transition group-hover:bg-indigo-100 group-hover:text-indigo-700">{serviceIcon(service.categoria)}</span><span class="rounded-full bg-slate-100 px-2.5 py-1 text-[10px] font-extrabold uppercase tracking-wider text-slate-500">{categoryLabel(service.categoria)}</span></div>
                {#if isSelected(service.id)}<span class="shrink-0 rounded-full bg-indigo-600 px-2.5 py-1 text-[10px] font-extrabold uppercase tracking-wider text-white">✓ Adicionado</span>{/if}
              </div>
              <h3 class="mt-4 font-bold tracking-tight text-slate-900">{service.nome}</h3>
              <p class="mt-1 min-h-10 text-xs leading-5 text-slate-500">{service.descricao_padrao || 'Serviço técnico sob demanda.'}</p>
              <div class="mt-4 flex items-center justify-between gap-3 border-t border-slate-100 pt-3"><span class="text-xs font-semibold text-slate-500">{pricingLabel(service.tipo_cobranca)}{service.permite_peca ? ' · aceita peça' : ''}</span><span class="text-sm font-extrabold text-slate-900">{priceLabel(service)}</span></div>
              <div class="mt-2 text-right text-[11px] font-bold text-indigo-600 opacity-0 transition group-hover:opacity-100 group-focus-visible:opacity-100">{isSelected(service.id) ? 'Remover do orçamento' : 'Adicionar ao orçamento'} →</div>
            </button>
          {/each}
        </div>
      {/if}
    </section>

    <aside class="surface overflow-hidden lg:sticky lg:top-6">
      <div class="border-b border-indigo-500/30 bg-indigo-600 p-5 text-white">
        <div class="flex items-center justify-between gap-4">
          <div><p class="text-[10px] font-bold uppercase tracking-[0.16em] text-indigo-100">04 · Resumo</p><h2 class="mt-1 text-lg font-bold">Orçamento atual</h2><p class="mt-1 text-xs text-indigo-100">Revise os valores antes de salvar.</p></div>
          <span class="rounded-full bg-white/15 px-2.5 py-1 text-xs font-bold text-indigo-50">{selectedCount} {selectedCount === 1 ? 'item' : 'itens'}</span>
        </div>
      </div>
      <div class="space-y-4 p-5">
        {#if selectedItems.length === 0}
          <div class="rounded-xl border border-dashed border-slate-200 px-4 py-7 text-center"><p class="text-sm font-semibold text-slate-600">Seu orçamento está vazio</p><p class="mt-1 text-xs leading-5 text-slate-400">Clique em um serviço para começar a montar.</p></div>
        {:else}
          <div class="space-y-3">
            {#each selectedItems as item (item.service.id)}
              <div class="rounded-xl border border-slate-200 bg-slate-50/70 p-3">
                <div class="flex items-start justify-between gap-3">
                  <div class="min-w-0"><p class="truncate text-sm font-bold text-slate-800">{item.service.nome}</p><p class="mt-0.5 text-xs text-slate-500">{pricingLabel(item.service.tipo_cobranca)} · {money(calculateLabor(item))} mão de obra</p></div>
                  <button type="button" class="shrink-0 rounded-lg px-2 py-1 text-xs font-bold text-slate-400 transition hover:bg-rose-50 hover:text-rose-600" aria-label={`Remover ${item.service.nome}`} on:click={() => toggleService(item.service)}>×</button>
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
                <div class="mt-3 flex justify-between gap-3 border-t border-slate-200 pt-2 text-xs"><span class="text-slate-500">Subtotal do item</span><span class="font-extrabold text-slate-800">{money(calculateLabor(item) + (Number(item.custo_peca) || 0))}</span></div>
              </div>
            {/each}
          </div>
        {/if}

        <div class="space-y-3 border-t border-slate-100 pt-4">
          <div class="grid grid-cols-2 gap-2">
            <label><span class="field-label">Desconto (R$)</span><input class="field" type="number" min="0" step="0.01" bind:value={discount} on:input={() => (savedQuote = null)} /></label>
            <label><span class="field-label">Deslocamento (R$)</span><input class="field" type="number" min="0" step="0.01" bind:value={travelFee} on:input={() => (savedQuote = null)} /></label>
          </div>
          <label class="block"><span class="field-label">Observações / prazo</span><textarea class="field min-h-20 resize-y" bind:value={observations} on:input={() => (savedQuote = null)} placeholder="Prazo, condições ou observações para o cliente"></textarea></label>
          <div class="space-y-2 text-sm">
            <div class="flex justify-between gap-4 text-slate-500"><span>Mão de obra</span><span class="font-semibold text-slate-700">{money(laborSubtotal)}</span></div>
            <div class="flex justify-between gap-4 text-slate-500"><span>Peças</span><span class="font-semibold text-slate-700">{money(partsSubtotal)}</span></div>
            {#if discount > 0}<div class="flex justify-between gap-4 text-emerald-600"><span>Desconto</span><span class="font-semibold">− {money(discount)}</span></div>{/if}
            {#if travelFee > 0}<div class="flex justify-between gap-4 text-slate-500"><span>Deslocamento</span><span class="font-semibold text-slate-700">{money(travelFee)}</span></div>{/if}
          </div>
          <div class="flex items-end justify-between gap-4 border-t border-slate-200 pt-4"><span class="text-sm font-bold text-slate-700">Total final</span><span class="text-2xl font-black tracking-tight text-indigo-700">{money(finalTotal)}</span></div>
        </div>

        {#if saveError}<p class="rounded-lg bg-rose-50 px-3 py-2 text-xs font-semibold text-rose-700">{saveError}</p>{/if}
        {#if !customerReady && selectedCount > 0}<p class="text-center text-[11px] leading-4 text-amber-600">Informe o nome do cliente para liberar o salvamento.</p>{/if}
        <button type="button" class="flex w-full items-center justify-center rounded-xl bg-indigo-600 px-4 py-3 text-sm font-bold text-white shadow-lg shadow-indigo-200 transition hover:bg-indigo-700 disabled:cursor-not-allowed disabled:opacity-50" on:click={saveQuote} disabled={saving || loadingDraft || selectedItems.length === 0}>{saving ? (draftMode === 'edit' ? 'Atualizando…' : 'Gerando…') : draftMode === 'edit' ? 'Atualizar orçamento' : 'Gerar orçamento'}</button>
        <div class="grid grid-cols-2 gap-2">
          <button type="button" class="rounded-xl border border-indigo-200 bg-indigo-50 px-3 py-2.5 text-xs font-bold text-indigo-700 transition hover:bg-indigo-100 disabled:cursor-not-allowed disabled:opacity-40" on:click={() => savedQuote && gerarOrcamentoPDF(savedQuote)} disabled={!savedQuote}>Baixar PDF</button>
          <button type="button" class="rounded-xl border border-slate-200 px-3 py-2.5 text-xs font-bold text-slate-600 transition hover:border-indigo-200 hover:text-indigo-700 disabled:cursor-not-allowed disabled:opacity-40" on:click={copyWhatsApp} disabled={!savedQuote}>Copiar mensagem</button>
          <button type="button" class="col-span-2 rounded-xl bg-emerald-600 px-3 py-2.5 text-xs font-bold text-white transition hover:bg-emerald-700 disabled:cursor-not-allowed disabled:opacity-40" on:click={openWhatsApp} disabled={!savedQuote || !savedQuote.cliente.telefone}>Abrir WhatsApp</button>
        </div>
        {#if savedQuote && !savedQuote.cliente.telefone}<p class="text-center text-[11px] leading-4 text-amber-600">Adicione um telefone para abrir a conversa automaticamente.</p>{/if}
      </div>
    </aside>
  </div>
</div>

<style>
  .metric-card {
    @apply flex items-center gap-3 rounded-2xl border border-slate-200 bg-white px-4 py-3.5 shadow-sm;
  }

  .metric-card-highlight {
    @apply border-indigo-800 bg-slate-950;
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

  .status-ready {
    @apply bg-emerald-50 text-emerald-700;
  }

  .filter-pill {
    @apply inline-flex items-center gap-1.5 rounded-xl px-3 py-2 text-xs font-bold text-slate-500 transition hover:bg-slate-100 hover:text-slate-800;
  }

  .filter-active {
    @apply bg-slate-900 text-white shadow-sm hover:bg-slate-800 hover:text-white;
  }

  .filter-count {
    @apply rounded-full bg-slate-100 px-1.5 py-0.5 text-[10px] text-slate-400;
  }

  .filter-active .filter-count {
    @apply bg-white/15 text-white/80;
  }

  .service-card {
    @apply rounded-2xl border border-slate-200 bg-white p-4 shadow-sm transition hover:-translate-y-0.5 hover:border-indigo-200 hover:shadow-lg hover:shadow-indigo-100/50 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-indigo-500 focus-visible:ring-offset-2;
  }

  .service-card-selected {
    @apply border-indigo-400 bg-indigo-50/70 shadow-sm shadow-indigo-100;
  }
</style>
