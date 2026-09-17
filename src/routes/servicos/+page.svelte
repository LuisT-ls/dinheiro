<script lang="ts">
  import { onMount } from 'svelte';
  import { createService, getServices, type PricingType, type Service, type ServiceCategory } from '$lib/api';

  let services: Service[] = [];
  let loading = true;
  let saving = false;
  let error = '';
  let success = '';
  let form = {
    nome: '',
    categoria: 'hardware' as ServiceCategory,
    tipo_cobranca: 'fixo' as PricingType,
    valor_base: 0,
    permite_peca: false,
    descricao_padrao: '',
  };

  onMount(loadServices);

  async function loadServices() {
    loading = true;
    error = '';
    try {
      services = await getServices();
    } catch (reason) {
      error = reason instanceof Error ? reason.message : 'Não foi possível carregar o catálogo.';
    } finally {
      loading = false;
    }
  }

  function money(value: number) {
    return new Intl.NumberFormat('pt-BR', { style: 'currency', currency: 'BRL' }).format(value || 0);
  }

  function categoryLabel(category: ServiceCategory) {
    return { hardware: 'Hardware', dev: 'Dev', infra: 'Infra', outros: 'Outros' }[category];
  }

  function pricingLabel(type: PricingType) {
    return { fixo: 'Fixo', hora: 'Por hora', misto: 'Peça + MO' }[type];
  }

  function resetForm() {
    form = { nome: '', categoria: 'hardware', tipo_cobranca: 'fixo', valor_base: 0, permite_peca: false, descricao_padrao: '' };
  }

  async function addService() {
    if (!form.nome.trim()) {
      error = 'Informe um nome para o serviço.';
      return;
    }
    if (Number(form.valor_base) < 0) {
      error = 'O valor base não pode ser negativo.';
      return;
    }

    saving = true;
    error = '';
    success = '';
    try {
      const created = await createService({
        nome: form.nome.trim(),
        categoria: form.categoria,
        tipo_cobranca: form.tipo_cobranca,
        valor_base: Number(form.valor_base) || 0,
        permite_peca: form.permite_peca,
        descricao_padrao: form.descricao_padrao.trim() || null,
      });
      services = [...services, created].sort((a, b) => a.nome.localeCompare(b.nome, 'pt-BR'));
      resetForm();
      success = 'Serviço adicionado ao catálogo.';
      window.setTimeout(() => (success = ''), 3500);
    } catch (reason) {
      error = reason instanceof Error ? reason.message : 'Não foi possível criar o serviço.';
    } finally {
      saving = false;
    }
  }
</script>

<svelte:head>
  <title>Catálogo de serviços — Dinheiro</title>
  <meta name="description" content="Cadastre os serviços usados nos seus orçamentos." />
</svelte:head>

<div class="space-y-8">
  <section class="flex flex-col justify-between gap-5 sm:flex-row sm:items-end">
    <div>
      <p class="eyebrow">Configuração</p>
      <h1 class="mt-2 text-3xl font-extrabold tracking-[-0.055em] text-slate-950 sm:text-4xl">Catálogo de serviços</h1>
      <p class="mt-2 max-w-2xl text-sm leading-6 text-slate-500">Mantenha sua vitrine técnica pronta para aparecer no próximo orçamento.</p>
    </div>
    <a href="/" class="inline-flex items-center justify-center gap-2 rounded-xl border border-slate-200 bg-white px-4 py-2.5 text-xs font-bold text-slate-600 shadow-sm transition hover:border-indigo-200 hover:text-indigo-700">← Voltar ao orçamento</a>
  </section>

  {#if error}<div class="rounded-xl border border-rose-200 bg-rose-50 px-4 py-3 text-sm font-medium text-rose-700">{error}</div>{/if}
  {#if success}<div class="rounded-xl border border-emerald-200 bg-emerald-50 px-4 py-3 text-sm font-medium text-emerald-700">{success}</div>{/if}

  <div class="grid items-start gap-6 lg:grid-cols-[minmax(0,1fr)_380px]">
    <section class="surface overflow-hidden">
      <div class="flex items-center justify-between border-b border-slate-100 px-5 py-4 sm:px-6"><div><p class="text-sm font-bold text-slate-900">Serviços cadastrados</p><p class="mt-0.5 text-xs text-slate-500">{services.length} item{services.length === 1 ? '' : 's'}</p></div><button type="button" class="rounded-lg px-3 py-2 text-xs font-bold text-slate-500 transition hover:bg-slate-100 hover:text-indigo-700" on:click={loadServices} disabled={loading}>Atualizar</button></div>
      {#if loading}
        <div class="flex min-h-56 items-center justify-center text-sm text-slate-500"><span class="animate-pulse">Carregando catálogo…</span></div>
      {:else if services.length === 0}
        <div class="p-8 text-center text-sm text-slate-500">Nenhum serviço cadastrado ainda.</div>
      {:else}
        <div class="grid gap-3 p-5 sm:grid-cols-2 sm:p-6">
          {#each services as service}
            <article class="rounded-2xl border border-slate-200 p-4 transition hover:border-indigo-200 hover:shadow-md hover:shadow-indigo-100/50">
              <div class="flex items-start justify-between gap-3"><span class="rounded-full bg-slate-100 px-2.5 py-1 text-[10px] font-extrabold uppercase tracking-wider text-slate-500">{categoryLabel(service.categoria)}</span><span class="text-sm font-black text-slate-900">{service.tipo_cobranca === 'hora' ? `${money(service.valor_base)}/h` : money(service.valor_base)}</span></div>
              <h2 class="mt-4 font-bold tracking-tight text-slate-900">{service.nome}</h2>
              <p class="mt-1 min-h-10 text-xs leading-5 text-slate-500">{service.descricao_padrao || 'Sem descrição adicional.'}</p>
              <div class="mt-4 flex items-center justify-between border-t border-slate-100 pt-3 text-[11px] font-semibold text-slate-400"><span>{pricingLabel(service.tipo_cobranca)}</span>{#if service.permite_peca}<span class="text-indigo-600">Aceita peça</span>{/if}</div>
            </article>
          {/each}
        </div>
      {/if}
    </section>

    <section class="surface p-5 sm:p-6 lg:sticky lg:top-6">
      <p class="eyebrow">Adicionar serviço</p>
      <h2 class="mt-1 text-xl font-extrabold tracking-tight text-slate-900">Novo item no catálogo</h2>
      <p class="mt-2 text-sm leading-6 text-slate-500">Defina o valor de referência; ele poderá ser ajustado no orçamento.</p>
      <div class="mt-5 space-y-4">
        <label><span class="field-label">Nome do serviço</span><input class="field" bind:value={form.nome} placeholder="Ex.: Diagnóstico avançado" /></label>
        <div class="grid grid-cols-2 gap-3">
          <label><span class="field-label">Categoria</span><select class="field" bind:value={form.categoria}><option value="hardware">Hardware</option><option value="dev">Dev</option><option value="infra">Infra</option><option value="outros">Outros</option></select></label>
          <label><span class="field-label">Cobrança</span><select class="field" bind:value={form.tipo_cobranca}><option value="fixo">Fixo</option><option value="hora">Por hora</option><option value="misto">Peça + MO</option></select></label>
        </div>
        <label><span class="field-label">Valor base (R$)</span><input class="field" type="number" min="0" step="0.01" bind:value={form.valor_base} /></label>
        <label><span class="field-label">Descrição curta</span><textarea class="field min-h-24 resize-y" bind:value={form.descricao_padrao} placeholder="O que está incluído neste serviço?"></textarea></label>
        <label class="flex cursor-pointer items-center gap-3 rounded-xl border border-slate-200 px-3.5 py-3"><input class="h-4 w-4 accent-indigo-600" type="checkbox" bind:checked={form.permite_peca} /><span><span class="block text-sm font-semibold text-slate-700">Permite incluir peça</span><span class="mt-0.5 block text-xs text-slate-400">Exibe um campo de custo no orçamento.</span></span></label>
        <button type="button" class="flex w-full items-center justify-center rounded-xl bg-indigo-600 px-4 py-3 text-sm font-bold text-white shadow-lg shadow-indigo-200 transition hover:bg-indigo-700 disabled:cursor-not-allowed disabled:opacity-60" on:click={addService} disabled={saving}>{saving ? 'Adicionando…' : 'Adicionar ao catálogo'}</button>
      </div>
    </section>
  </div>
</div>
