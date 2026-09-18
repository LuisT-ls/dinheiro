<script lang="ts">
  import { onMount } from 'svelte';
  import { DEFAULT_BUSINESS_SETTINGS, getBusinessSettings, resetBusinessSettings, saveBusinessSettings, type BusinessSettings } from '$lib/settings';
  import Seo from '$lib/Seo.svelte';

  let form: BusinessSettings = { ...DEFAULT_BUSINESS_SETTINGS };
  let saved = '';

  onMount(() => {
    form = getBusinessSettings();
  });

  function save() {
    form = { ...form, nome: form.nome.trim(), subtitulo: form.subtitulo.trim(), rodape: form.rodape.trim() };
    saveBusinessSettings(form);
    saved = 'Configurações salvas neste dispositivo.';
    window.setTimeout(() => (saved = ''), 3000);
  }

  function reset() {
    if (!window.confirm('Restaurar as configurações padrão?')) return;
    form = { ...resetBusinessSettings() };
    saved = 'Configurações padrão restauradas.';
    window.setTimeout(() => (saved = ''), 3000);
  }
</script>

<Seo title="Configurações comerciais | Dinheiro" description="Personalize identidade, validade, pagamento e garantias das suas propostas." />

<div class="space-y-7">
  <section class="flex flex-col justify-between gap-5 sm:flex-row sm:items-end">
    <div><p class="eyebrow">Configuração do negócio</p><h1 class="mt-2 text-3xl font-extrabold tracking-[-0.055em] text-slate-950 sm:text-4xl">Dados comerciais</h1><p class="mt-2 max-w-2xl text-sm leading-6 text-slate-500">Essas informações aparecem no PDF e ajudam a deixar cada proposta com a sua identidade.</p></div>
    <a href="/" class="inline-flex items-center justify-center rounded-xl border border-slate-200 bg-white px-4 py-2.5 text-xs font-bold text-slate-600 transition hover:border-indigo-200 hover:text-indigo-700">← Voltar ao orçamento</a>
  </section>

  {#if saved}<div class="rounded-2xl border border-emerald-200 bg-emerald-50 px-4 py-3 text-sm font-semibold text-emerald-700" role="status">✓ {saved}</div>{/if}

  <form class="grid items-start gap-6 lg:grid-cols-[minmax(0,1fr)_360px]" on:submit|preventDefault={save}>
    <section class="surface p-5 sm:p-6">
      <p class="eyebrow">Identidade</p><h2 class="mt-1 text-xl font-extrabold tracking-tight text-slate-900">Como você aparece para o cliente</h2><p class="mt-2 text-sm leading-6 text-slate-500">Use um nome e subtítulo curtos para manter o cabeçalho do orçamento elegante.</p>
      <div class="mt-5 grid gap-4 sm:grid-cols-2"><label><span class="field-label">Nome / marca</span><input class="field" bind:value={form.nome} required maxlength="100" placeholder="Ex.: Luís Teixeira" /></label><label><span class="field-label">Subtítulo</span><input class="field" bind:value={form.subtitulo} maxlength="120" placeholder="Soluções digitais & suporte técnico" /></label></div>
      <div class="mt-4 grid gap-4 sm:grid-cols-2"><label><span class="field-label">Telefone comercial</span><input class="field" bind:value={form.telefone} inputmode="tel" placeholder="(71) 99999-0000" /></label><label><span class="field-label">E-mail</span><input class="field" bind:value={form.email} type="email" placeholder="contato@seudominio.com" /></label></div>
      <label class="mt-4 block"><span class="field-label">Endereço ou cidade</span><input class="field" bind:value={form.endereco} placeholder="Salvador — BA" /></label>
    </section>

    <aside class="surface p-5 sm:p-6 lg:sticky lg:top-6"><p class="eyebrow">Proposta</p><h2 class="mt-1 text-xl font-extrabold tracking-tight text-slate-900">Padrões comerciais</h2><div class="mt-5 space-y-4"><label><span class="field-label">Validade (dias)</span><input class="field" type="number" min="1" max="90" bind:value={form.validade_dias} /></label><label><span class="field-label">Condição de pagamento</span><textarea class="field min-h-20 resize-y" bind:value={form.pagamento}></textarea></label><label><span class="field-label">Garantia de hardware</span><textarea class="field min-h-20 resize-y" bind:value={form.garantia_hardware}></textarea></label><label><span class="field-label">Suporte para desenvolvimento</span><textarea class="field min-h-20 resize-y" bind:value={form.garantia_dev}></textarea></label><label><span class="field-label">Rodapé do documento</span><textarea class="field min-h-20 resize-y" bind:value={form.rodape}></textarea></label></div></aside>

    <div class="flex flex-wrap gap-2 lg:col-span-2"><button type="submit" class="rounded-xl bg-indigo-600 px-5 py-3 text-sm font-bold text-white transition hover:bg-indigo-700">Salvar configurações</button><button type="button" class="rounded-xl border border-slate-200 bg-white px-5 py-3 text-sm font-bold text-slate-600 transition hover:border-rose-200 hover:bg-rose-50 hover:text-rose-700" on:click={reset}>Restaurar padrão</button></div>
  </form>
</div>
