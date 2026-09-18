<script lang="ts">
  import { onMount } from 'svelte';
  import {
    createService,
    deleteService,
    getServices,
    seedServices,
    updateService,
    type PricingType,
    type Service,
    type ServiceCategory,
    type ServiceCreate,
  } from '$lib/api';

  type CategoryFilter = ServiceCategory | 'todos';

  type ServiceForm = {
    nome: string;
    categoria: ServiceCategory;
    tipo_cobranca: PricingType;
    valor_base: number;
    custo_base: number;
    permite_peca: boolean;
    descricao_padrao: string;
  };

  const categoryOptions: Array<{ value: CategoryFilter; label: string }> = [
    { value: 'todos', label: 'Todos' },
    { value: 'dev', label: 'Dev' },
    { value: 'hardware', label: 'Hardware' },
    { value: 'infra', label: 'Infra' },
    { value: 'outros', label: 'Outros' },
  ];

  const emptyForm = (): ServiceForm => ({
    nome: '',
    categoria: 'hardware',
    tipo_cobranca: 'fixo',
    valor_base: 0,
    custo_base: 0,
    permite_peca: false,
    descricao_padrao: '',
  });

  let services: Service[] = [];
  let loading = true;
  let saving = false;
  let seeding = false;
  let deletingId = '';
  let error = '';
  let success = '';
  let query = '';
  let activeCategory: CategoryFilter = 'todos';
  let editingId: string | null = null;
  let form: ServiceForm = emptyForm();
  let formPanel: HTMLElement;

  $: normalizedQuery = query.trim().toLocaleLowerCase('pt-BR');
  $: filteredServices = services.filter((service) => {
    if (activeCategory !== 'todos' && service.categoria !== activeCategory) return false;
    if (!normalizedQuery) return true;

    return `${service.nome} ${service.descricao_padrao ?? ''}`
      .toLocaleLowerCase('pt-BR')
      .includes(normalizedQuery);
  });
  $: editingService = editingId ? services.find((service) => service.id === editingId) : null;
  $: devCount = services.filter((service) => service.categoria === 'dev').length;
  $: hardwareCount = services.filter((service) => service.categoria === 'hardware').length;
  $: pieceCount = services.filter((service) => service.permite_peca).length;
  $: averageValue = services.length ? services.reduce((sum, service) => sum + service.valor_base, 0) / services.length : 0;
  $: hasFilters = Boolean(normalizedQuery) || activeCategory !== 'todos';

  onMount(loadServices);

  async function loadServices() {
    loading = true;
    error = '';

    try {
      services = (await getServices()).sort((a, b) => a.nome.localeCompare(b.nome, 'pt-BR'));
    } catch (reason) {
      error = reason instanceof Error ? reason.message : 'Não foi possível carregar o catálogo.';
    } finally {
      loading = false;
    }
  }

  async function loadDefaultCatalog() {
    seeding = true;
    error = '';
    success = '';

    try {
      services = (await seedServices()).sort((a, b) => a.nome.localeCompare(b.nome, 'pt-BR'));
      showSuccess('Catálogo padrão carregado com sucesso.');
    } catch (reason) {
      error = reason instanceof Error ? reason.message : 'Não foi possível carregar o catálogo padrão.';
    } finally {
      seeding = false;
    }
  }

  function money(value: number) {
    return new Intl.NumberFormat('pt-BR', { style: 'currency', currency: 'BRL' }).format(value || 0);
  }

  function categoryLabel(category: ServiceCategory) {
    return { hardware: 'Hardware', dev: 'Dev', infra: 'Infra', outros: 'Outros' }[category];
  }

  function pricingLabel(type: PricingType) {
    return { fixo: 'Fixo', hora: 'Por hora', misto: 'Peça + mão de obra' }[type];
  }

  function priceLabel(service: Service) {
    return service.tipo_cobranca === 'hora' ? `${money(service.valor_base)}/h` : money(service.valor_base);
  }

  function serviceIcon(category: ServiceCategory) {
    return { hardware: '⌘', dev: '✦', infra: '◒', outros: '+' }[category];
  }

  function countFor(category: CategoryFilter) {
    return category === 'todos' ? services.length : services.filter((service) => service.categoria === category).length;
  }

  function resetForm() {
    form = emptyForm();
    editingId = null;
  }

  function showSuccess(message: string) {
    success = message;
    window.setTimeout(() => (success = ''), 3500);
  }

  function scrollToForm() {
    window.setTimeout(() => formPanel?.scrollIntoView({ behavior: 'smooth', block: 'start' }), 0);
  }

  function startCreate() {
    resetForm();
    error = '';
    success = '';
    scrollToForm();
  }

  function startEdit(service: Service) {
    editingId = service.id;
    form = {
      nome: service.nome,
      categoria: service.categoria,
      tipo_cobranca: service.tipo_cobranca,
      valor_base: service.valor_base,
      custo_base: service.custo_base ?? 0,
      permite_peca: service.permite_peca,
      descricao_padrao: service.descricao_padrao ?? '',
    };
    error = '';
    success = '';
    scrollToForm();
  }

  function cancelEdit() {
    resetForm();
    error = '';
  }

  async function saveService() {
    const nome = form.nome.trim();
    const valorBase = Number(form.valor_base);

    if (!nome) {
      error = 'Informe um nome para o serviço.';
      return;
    }
    if (!Number.isFinite(valorBase) || valorBase < 0) {
      error = 'Informe um valor base válido e não negativo.';
      return;
    }

    const payload: ServiceCreate = {
      nome,
      categoria: form.categoria,
      tipo_cobranca: form.tipo_cobranca,
      valor_base: valorBase,
      custo_base: Math.max(0, Number(form.custo_base) || 0),
      permite_peca: form.permite_peca,
      descricao_padrao: form.descricao_padrao.trim() || null,
    };

    saving = true;
    error = '';
    success = '';

    try {
      if (editingId) {
        const updated = await updateService(editingId, payload);
        services = services
          .map((service) => (service.id === updated.id ? updated : service))
          .sort((a, b) => a.nome.localeCompare(b.nome, 'pt-BR'));
        resetForm();
        showSuccess('Serviço atualizado com sucesso.');
      } else {
        const created = await createService(payload);
        services = [...services, created].sort((a, b) => a.nome.localeCompare(b.nome, 'pt-BR'));
        resetForm();
        showSuccess('Serviço adicionado ao catálogo.');
      }
    } catch (reason) {
      error = reason instanceof Error ? reason.message : 'Não foi possível salvar o serviço.';
    } finally {
      saving = false;
    }
  }

  async function removeService(service: Service) {
    if (!window.confirm(`Excluir “${service.nome}” do catálogo? Essa ação não pode ser desfeita.`)) return;

    deletingId = service.id;
    error = '';
    success = '';

    try {
      await deleteService(service.id);
      services = services.filter((item) => item.id !== service.id);
      if (editingId === service.id) resetForm();
      showSuccess('Serviço removido do catálogo.');
    } catch (reason) {
      error = reason instanceof Error ? reason.message : 'Não foi possível remover o serviço.';
    } finally {
      deletingId = '';
    }
  }

  function clearFilters() {
    query = '';
    activeCategory = 'todos';
  }
</script>

<svelte:head>
  <title>Catálogo de serviços — Dinheiro</title>
  <meta name="description" content="Cadastre e organize os serviços usados nos seus orçamentos." />
</svelte:head>

<div class="space-y-7">
  <section class="flex flex-col justify-between gap-5 sm:flex-row sm:items-end">
    <div>
      <p class="eyebrow">Configuração do negócio</p>
      <h1 class="mt-2 text-3xl font-extrabold tracking-[-0.055em] text-slate-950 sm:text-4xl">Catálogo de serviços</h1>
      <p class="mt-2 max-w-2xl text-sm leading-6 text-slate-500">Organize sua vitrine técnica e encontre qualquer item em segundos ao montar um orçamento.</p>
    </div>
    <div class="flex flex-wrap gap-2">
      <a href="/" class="inline-flex items-center justify-center gap-2 rounded-xl border border-slate-200 bg-white px-4 py-2.5 text-xs font-bold text-slate-600 transition hover:border-indigo-200 hover:text-indigo-700">← Voltar ao orçamento</a>
      <button type="button" class="inline-flex items-center justify-center gap-2 rounded-xl bg-indigo-600 px-4 py-2.5 text-xs font-bold text-white transition hover:bg-indigo-700" on:click={startCreate}>+ Novo serviço</button>
    </div>
  </section>

  <section class="grid gap-3 sm:grid-cols-2 xl:grid-cols-4" aria-label="Resumo do catálogo">
    <div class="metric-card"><span class="metric-icon bg-indigo-50 text-indigo-600">#</span><div><p class="metric-label">Itens no catálogo</p><p class="metric-value">{services.length}</p></div></div>
    <div class="metric-card"><span class="metric-icon bg-sky-50 text-sky-600">✦</span><div><p class="metric-label">Desenvolvimento</p><p class="metric-value">{devCount}</p></div></div>
    <div class="metric-card"><span class="metric-icon bg-amber-50 text-amber-600">⌘</span><div><p class="metric-label">Hardware</p><p class="metric-value">{hardwareCount}</p></div></div>
    <div class="metric-card"><span class="metric-icon bg-emerald-50 text-emerald-600">R$</span><div><p class="metric-label">Valor médio</p><p class="metric-value text-lg">{money(averageValue)}</p><p class="metric-caption">{pieceCount} com custo de peça</p></div></div>
  </section>

  {#if error}
    <div class="flex items-start gap-3 rounded-2xl border border-rose-200 bg-rose-50 px-4 py-3 text-sm font-medium text-rose-700" role="alert"><span class="mt-0.5">!</span><p>{error}</p></div>
  {/if}
  {#if success}
    <div class="flex items-start gap-3 rounded-2xl border border-emerald-200 bg-emerald-50 px-4 py-3 text-sm font-medium text-emerald-700" role="status"><span class="mt-0.5">✓</span><p>{success}</p></div>
  {/if}

  <div class="grid items-start gap-6 lg:grid-cols-[minmax(0,1fr)_360px]">
    <section class="surface overflow-hidden" aria-labelledby="catalog-title">
      <div class="border-b border-slate-100 px-5 py-5 sm:px-6">
        <div class="flex flex-col justify-between gap-4 sm:flex-row sm:items-center">
          <div>
            <div class="flex items-center gap-2"><h2 id="catalog-title" class="text-sm font-bold text-slate-900">Serviços cadastrados</h2><span class="rounded-full bg-slate-100 px-2 py-0.5 text-[10px] font-extrabold text-slate-500">{filteredServices.length} exibido{filteredServices.length === 1 ? '' : 's'}</span></div>
            <p class="mt-1 text-xs text-slate-500">Clique em editar para ajustar preço, descrição ou regra de cobrança.</p>
          </div>
          <button type="button" class="inline-flex items-center justify-center gap-2 self-start rounded-lg px-3 py-2 text-xs font-bold text-slate-500 transition hover:bg-slate-100 hover:text-indigo-700 sm:self-auto" on:click={loadServices} disabled={loading}><span class:animate-spin={loading}>↻</span> Atualizar</button>
        </div>

        <div class="mt-5 flex flex-col gap-3 md:flex-row">
          <label class="relative block min-w-0 flex-1"><span class="sr-only">Buscar serviço</span><span class="pointer-events-none absolute left-3.5 top-1/2 -translate-y-1/2 text-base text-slate-400">⌕</span><input class="field pl-10 pr-10" type="search" bind:value={query} placeholder="Buscar por nome ou descrição…" /><button type="button" class="absolute right-2 top-1/2 -translate-y-1/2 rounded-lg px-2 py-1 text-lg leading-none text-slate-400 hover:bg-slate-100 hover:text-slate-700" class:hidden={!query} aria-label="Limpar busca" on:click={() => (query = '')}>×</button></label>
        </div>

        <div class="mt-4 -mb-1 flex gap-1 overflow-x-auto pb-1" role="tablist" aria-label="Filtrar por categoria">
          {#each categoryOptions as option}
            <button type="button" role="tab" aria-selected={activeCategory === option.value} class:filter-active={activeCategory === option.value} class="filter-pill whitespace-nowrap" on:click={() => (activeCategory = option.value)}>{option.label}<span class="filter-count">{countFor(option.value)}</span></button>
          {/each}
        </div>
      </div>

      {#if loading}
        <div class="grid gap-3 p-5 sm:grid-cols-2 sm:p-6" aria-label="Carregando catálogo">
          {#each Array(6) as _}
            <div class="h-44 animate-pulse rounded-2xl border border-slate-100 bg-slate-50"></div>
          {/each}
        </div>
      {:else if services.length === 0}
        <div class="p-10 text-center"><div class="mx-auto grid h-12 w-12 place-items-center rounded-2xl bg-indigo-50 text-xl text-indigo-600">✦</div><h3 class="mt-4 font-bold text-slate-900">Seu catálogo está vazio</h3><p class="mx-auto mt-1 max-w-sm text-sm leading-6 text-slate-500">Comece com os serviços padrão ou cadastre um item personalizado para montar seus orçamentos mais rápido.</p><div class="mt-5 flex flex-wrap justify-center gap-2"><button type="button" class="rounded-xl bg-indigo-600 px-4 py-2.5 text-xs font-bold text-white transition hover:bg-indigo-700 disabled:opacity-60" on:click={loadDefaultCatalog} disabled={seeding}>{seeding ? 'Carregando…' : 'Carregar catálogo padrão'}</button><button type="button" class="rounded-xl border border-slate-200 bg-white px-4 py-2.5 text-xs font-bold text-slate-600 transition hover:border-indigo-200 hover:text-indigo-700" on:click={startCreate}>Cadastrar manualmente</button></div></div>
      {:else if filteredServices.length === 0}
        <div class="p-10 text-center"><div class="mx-auto grid h-12 w-12 place-items-center rounded-2xl bg-slate-100 text-xl text-slate-500">⌕</div><h3 class="mt-4 font-bold text-slate-900">Nenhum serviço encontrado</h3><p class="mx-auto mt-1 max-w-sm text-sm leading-6 text-slate-500">Tente outro termo ou remova os filtros para ver todo o catálogo.</p><button type="button" class="mt-5 rounded-xl border border-slate-200 bg-white px-4 py-2.5 text-xs font-bold text-slate-600 transition hover:border-indigo-200 hover:text-indigo-700" on:click={clearFilters}>Limpar filtros</button></div>
      {:else}
        <div class="grid gap-3 p-5 sm:grid-cols-2 sm:p-6">
          {#each filteredServices as service (service.id)}
            <article class="service-card group">
              <div class="flex items-start justify-between gap-3">
                <div class="flex min-w-0 items-center gap-2"><span class="grid h-8 w-8 shrink-0 place-items-center rounded-xl bg-slate-100 text-sm font-black text-slate-500">{serviceIcon(service.categoria)}</span><span class="rounded-full bg-slate-100 px-2.5 py-1 text-[10px] font-extrabold uppercase tracking-wider text-slate-500">{categoryLabel(service.categoria)}</span></div>
                <span class="shrink-0 text-sm font-black text-slate-900">{priceLabel(service)}</span>
              </div>
              <h3 class="mt-4 font-bold tracking-tight text-slate-900">{service.nome}</h3>
              <p class="mt-1 min-h-10 text-xs leading-5 text-slate-500">{service.descricao_padrao || 'Sem descrição adicional.'}</p>
              <div class="mt-4 flex flex-wrap items-center gap-2 border-t border-slate-100 pt-3 text-[11px] font-semibold text-slate-400"><span>{pricingLabel(service.tipo_cobranca)}</span>{#if service.permite_peca}<span class="rounded-full bg-indigo-50 px-2 py-1 text-indigo-600">Aceita peça</span>{/if}<div class="ml-auto flex gap-1.5"><button type="button" class="card-action" aria-label={`Editar ${service.nome}`} on:click={() => startEdit(service)}>Editar</button><button type="button" class="card-action card-action-danger" aria-label={`Excluir ${service.nome}`} disabled={deletingId === service.id} on:click={() => removeService(service)}>{deletingId === service.id ? '…' : 'Excluir'}</button></div></div>
            </article>
          {/each}
        </div>
      {/if}
    </section>

    <section class="surface p-5 sm:p-6 lg:sticky lg:top-6" bind:this={formPanel} aria-labelledby="form-title">
      <div class="flex items-start justify-between gap-3">
        <div><p class="eyebrow">{editingId ? 'Editando serviço' : 'Adicionar serviço'}</p><h2 id="form-title" class="mt-1 text-xl font-extrabold tracking-tight text-slate-900">{editingId ? 'Atualizar item' : 'Novo item no catálogo'}</h2><p class="mt-2 text-sm leading-6 text-slate-500">O valor de referência aparece no orçamento e pode ser ajustado antes do envio.</p></div>
        {#if editingId}<button type="button" class="shrink-0 rounded-lg px-2 py-1 text-xs font-bold text-slate-400 transition hover:bg-slate-100 hover:text-slate-700" on:click={cancelEdit}>Cancelar</button>{/if}
      </div>

      <form class="mt-5 space-y-4" on:submit|preventDefault={saveService}>
        <label><span class="field-label">Nome do serviço</span><input class="field" bind:value={form.nome} maxlength="90" placeholder="Ex.: Diagnóstico avançado" autocomplete="off" /></label>
        <div class="grid grid-cols-2 gap-3"><label><span class="field-label">Categoria</span><select class="field" bind:value={form.categoria}><option value="hardware">Hardware</option><option value="dev">Dev</option><option value="infra">Infra</option><option value="outros">Outros</option></select></label><label><span class="field-label">Cobrança</span><select class="field" bind:value={form.tipo_cobranca}><option value="fixo">Fixo</option><option value="hora">Por hora</option><option value="misto">Peça + MO</option></select></label></div>
        <div class="grid grid-cols-2 gap-3"><label><span class="field-label">Valor de venda (R$){form.tipo_cobranca === 'hora' ? ' / hora' : ''}</span><input class="field" type="number" min="0" step="0.01" bind:value={form.valor_base} /></label><label><span class="field-label">Custo interno (R$)</span><input class="field" type="number" min="0" step="0.01" bind:value={form.custo_base} /><span class="mt-1 block text-[11px] text-slate-400">Não aparece para o cliente.</span></label></div>
        <label><span class="field-label">Descrição curta <span class="font-normal normal-case tracking-normal text-slate-400">(opcional)</span></span><textarea class="field min-h-24 resize-y" maxlength="180" bind:value={form.descricao_padrao} placeholder="O que está incluído neste serviço?"></textarea><span class="mt-1 block text-right text-[11px] text-slate-400">{form.descricao_padrao.length}/180</span></label>
        <label class="flex cursor-pointer items-start gap-3 rounded-2xl border border-slate-200 px-3.5 py-3.5 transition hover:border-indigo-200 hover:bg-indigo-50/30"><input class="mt-0.5 h-4 w-4 accent-indigo-600" type="checkbox" bind:checked={form.permite_peca} /><span><span class="block text-sm font-semibold text-slate-700">Permite incluir peça</span><span class="mt-0.5 block text-xs leading-5 text-slate-400">Exibe um campo para custo de peça no orçamento.</span></span></label>

        <div class="rounded-2xl bg-slate-50 px-4 py-3"><p class="text-[10px] font-extrabold uppercase tracking-[0.14em] text-slate-400">Prévia no orçamento</p><div class="mt-2 flex items-center justify-between gap-3"><p class="truncate text-sm font-bold text-slate-800">{form.nome.trim() || 'Nome do serviço'}</p><p class="shrink-0 text-sm font-black text-indigo-700">{form.tipo_cobranca === 'hora' ? `${money(Number(form.valor_base) || 0)}/h` : money(Number(form.valor_base) || 0)}</p></div><p class="mt-1 text-xs text-slate-500">{pricingLabel(form.tipo_cobranca)}{form.permite_peca ? ' · aceita custo de peça' : ''}</p></div>

        <button type="submit" class="flex w-full items-center justify-center rounded-xl bg-indigo-600 px-4 py-3 text-sm font-bold text-white transition hover:bg-indigo-700 disabled:cursor-not-allowed disabled:opacity-60" disabled={saving}>{saving ? 'Salvando…' : editingId ? 'Salvar alterações' : 'Adicionar ao catálogo'}</button>
      </form>
    </section>
  </div>
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

  .filter-pill {
    @apply inline-flex items-center gap-1.5 rounded-xl px-3 py-2 text-xs font-bold text-slate-500 transition hover:bg-slate-100 hover:text-slate-800;
  }

  .filter-active {
    @apply bg-slate-900 text-white hover:bg-slate-800 hover:text-white;
  }

  .filter-count {
    @apply rounded-full bg-slate-100 px-1.5 py-0.5 text-[10px] text-slate-400;
  }

  .filter-active .filter-count {
    @apply bg-white/15 text-white/80;
  }

  .service-card {
    @apply rounded-2xl border border-slate-200 bg-white p-4 transition hover:-translate-y-0.5 hover:border-indigo-200 hover:shadow-md hover:shadow-indigo-100/50;
  }

  .card-action {
    @apply rounded-lg border border-slate-200 bg-white px-2.5 py-1.5 text-[10px] font-bold text-slate-500 transition hover:border-indigo-200 hover:text-indigo-700 disabled:cursor-wait disabled:opacity-50;
  }

  .card-action-danger {
    @apply border-transparent text-rose-500 hover:border-rose-200 hover:bg-rose-50 hover:text-rose-700;
  }
</style>
