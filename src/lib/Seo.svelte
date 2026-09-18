<script lang="ts">
  import { page } from '$app/stores';

  export let title: string;
  export let description: string;
  export let type: 'website' | 'article' = 'website';
  export let noindex = true;

  const configuredOrigin = (import.meta.env.VITE_SITE_URL ?? '').replace(/\/$/, '');
  $: canonicalUrl = `${configuredOrigin || $page.url.origin}${$page.url.pathname}`;
  $: robots = noindex ? 'noindex, nofollow, noarchive, nosnippet' : 'index, follow';
  $: structuredData = {
    '@context': 'https://schema.org',
    '@type': 'WebApplication',
    name: 'Dinheiro',
    description,
    url: canonicalUrl,
    inLanguage: 'pt-BR',
    applicationCategory: 'BusinessApplication',
    operatingSystem: 'Web',
  };
</script>

<svelte:head>
  <title>{title}</title>
  <meta name="description" content={description} />
  <meta name="robots" content={robots} />
  <meta name="googlebot" content={robots} />
  <link rel="canonical" href={canonicalUrl} />
  <meta property="og:type" content={type} />
  <meta property="og:site_name" content="Dinheiro" />
  <meta property="og:locale" content="pt_BR" />
  <meta property="og:title" content={title} />
  <meta property="og:description" content={description} />
  <meta property="og:url" content={canonicalUrl} />
  <meta name="twitter:card" content="summary" />
  <meta name="twitter:title" content={title} />
  <meta name="twitter:description" content={description} />
  <script type="application/ld+json">{JSON.stringify(structuredData)}</script>
</svelte:head>
