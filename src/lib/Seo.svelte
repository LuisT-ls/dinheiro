<script lang="ts">
  import { page } from '$app/stores';

  export let title: string;
  export let description: string;
  export let type: 'website' | 'article' = 'website';
  export let noindex = true;

  const configuredOrigin = (import.meta.env.VITE_SITE_URL ?? '').replace(/\/$/, '');
  $: canonicalUrl = `${configuredOrigin || $page.url.origin}${$page.url.pathname}`;
  $: socialImageUrl = `${configuredOrigin || $page.url.origin}/og.png`;
  $: robots = noindex ? 'noindex, nofollow, noarchive, nosnippet' : 'index, follow';
  $: structuredData = {
    '@context': 'https://schema.org',
    '@graph': [
      {
        '@type': 'WebApplication',
        name: 'Dinheiro',
        description,
        url: canonicalUrl,
        image: socialImageUrl,
        inLanguage: 'pt-BR',
        applicationCategory: 'BusinessApplication',
        operatingSystem: 'Web',
      },
      {
        '@type': 'WebSite',
        name: 'Dinheiro',
        url: canonicalUrl,
        inLanguage: 'pt-BR',
      },
    ],
  };
</script>

<svelte:head>
  <title>{title}</title>
  <meta name="description" content={description} />
  <meta name="robots" content={robots} />
  <meta name="googlebot" content={robots} />
  <link rel="canonical" href={canonicalUrl} />
  <link rel="alternate" hreflang="pt-BR" href={canonicalUrl} />
  <link rel="alternate" hreflang="x-default" href={canonicalUrl} />
  <meta property="og:type" content={type} />
  <meta property="og:site_name" content="Dinheiro" />
  <meta property="og:locale" content="pt_BR" />
  <meta property="og:title" content={title} />
  <meta property="og:description" content={description} />
  <meta property="og:url" content={canonicalUrl} />
  <meta property="og:image" content={socialImageUrl} />
  <meta property="og:image:type" content="image/png" />
  <meta property="og:image:width" content="1200" />
  <meta property="og:image:height" content="630" />
  <meta property="og:image:alt" content="Dinheiro — Orçamentos técnicos profissionais" />
  <meta name="twitter:card" content="summary_large_image" />
  <meta name="twitter:title" content={title} />
  <meta name="twitter:description" content={description} />
  <meta name="twitter:image" content={socialImageUrl} />
  <meta name="twitter:image:alt" content="Dinheiro — Orçamentos técnicos profissionais" />
  <script type="application/ld+json">{JSON.stringify(structuredData)}</script>
</svelte:head>
