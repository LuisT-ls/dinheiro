<svelte:head>
  <title>Dinheiro — Orçamentos técnicos</title>
  <meta
    name="description"
    content="Geração rápida de orçamentos para software e assistência técnica."
  />
</svelte:head>

<script>
  const serviceGroups = [
    {
      icon: '⌘',
      title: 'Desenvolvimento',
      description: 'Landing pages, sistemas sob medida e novas features.',
    },
    {
      icon: '⚙',
      title: 'Assistência técnica',
      description: 'Manutenção, upgrades e troca de peças para computadores.',
    },
  ];
</script>

<main>
  <nav class="topbar" aria-label="Navegação principal">
    <a class="brand" href="/" aria-label="Dinheiro início">
      <span class="brand-mark">$</span>
      <span>dinheiro<span class="brand-dot">.</span></span>
    </a>
    <span class="status"><span class="status-dot"></span> ambiente pronto</span>
  </nav>

  <section class="hero">
    <div class="eyebrow">ORÇAMENTOS TÉCNICOS, SEM COMPLICAÇÃO</div>
    <h1>Transforme seu trabalho em um orçamento <em>claro.</em></h1>
    <p class="intro">
      Escolha os serviços, ajuste os valores e tenha um resumo profissional pronto para enviar.
    </p>
    <div class="actions">
      <a class="primary-button" href="/docs">Abrir API e Swagger <span>↗</span></a>
      <span class="hint">A interface de orçamento vem na próxima etapa.</span>
    </div>
  </section>

  <section class="groups" aria-label="Tipos de serviço">
    {#each serviceGroups as group}
      <article class="group-card">
        <div class="card-icon">{group.icon}</div>
        <div>
          <h2>{group.title}</h2>
          <p>{group.description}</p>
        </div>
        <span class="card-arrow">→</span>
      </article>
    {/each}
  </section>

  <footer>
    <span>fundação do projeto</span>
    <span>FastAPI <b>·</b> SvelteKit <b>·</b> Firestore</span>
  </footer>
</main>

<style>
  :global(*) {
    box-sizing: border-box;
  }

  :global(body) {
    margin: 0;
    min-width: 320px;
    background: #f7f8f5;
    color: #18211d;
    font-family:
      Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
  }

  :global(a) {
    color: inherit;
    text-decoration: none;
  }

  main {
    width: min(1120px, calc(100% - 48px));
    min-height: 100vh;
    margin: 0 auto;
    display: flex;
    flex-direction: column;
  }

  .topbar {
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 30px 0;
    border-bottom: 1px solid #dfe5df;
  }

  .brand {
    display: inline-flex;
    align-items: center;
    gap: 10px;
    font-size: 19px;
    font-weight: 750;
    letter-spacing: -0.04em;
  }

  .brand-mark {
    display: grid;
    width: 30px;
    height: 30px;
    place-items: center;
    border-radius: 9px;
    background: #d8f253;
    color: #26320f;
    font-size: 18px;
    font-weight: 800;
  }

  .brand-dot {
    color: #8cae20;
  }

  .status {
    color: #758078;
    font-size: 12px;
    letter-spacing: 0.02em;
  }

  .status-dot {
    display: inline-block;
    width: 7px;
    height: 7px;
    margin-right: 7px;
    border-radius: 50%;
    background: #8db12c;
    box-shadow: 0 0 0 4px #eaf3c6;
  }

  .hero {
    max-width: 790px;
    padding: clamp(80px, 13vw, 150px) 0 100px;
  }

  .eyebrow {
    margin-bottom: 22px;
    color: #8ba621;
    font-size: 11px;
    font-weight: 800;
    letter-spacing: 0.16em;
  }

  h1 {
    max-width: 780px;
    margin: 0;
    font-size: clamp(42px, 7vw, 78px);
    font-weight: 650;
    letter-spacing: -0.075em;
    line-height: 0.98;
  }

  h1 em {
    color: #94b329;
    font-family: Georgia, serif;
    font-weight: 400;
  }

  .intro {
    max-width: 490px;
    margin: 30px 0 0;
    color: #67736c;
    font-size: 18px;
    line-height: 1.55;
  }

  .actions {
    display: flex;
    align-items: center;
    flex-wrap: wrap;
    gap: 18px;
    margin-top: 38px;
  }

  .primary-button {
    display: inline-flex;
    align-items: center;
    gap: 22px;
    padding: 14px 18px 14px 20px;
    border-radius: 9px;
    background: #1b2620;
    color: #fff;
    font-size: 13px;
    font-weight: 700;
    transition: transform 150ms ease, background 150ms ease;
  }

  .primary-button:hover {
    background: #34453a;
    transform: translateY(-2px);
  }

  .primary-button span {
    color: #d8f253;
    font-size: 18px;
  }

  .hint {
    color: #8a958d;
    font-size: 12px;
  }

  .groups {
    display: grid;
    grid-template-columns: repeat(2, 1fr);
    gap: 14px;
    padding-bottom: 70px;
  }

  .group-card {
    display: grid;
    grid-template-columns: auto 1fr auto;
    align-items: center;
    gap: 17px;
    padding: 23px;
    border: 1px solid #dfe5df;
    border-radius: 13px;
    background: rgba(255, 255, 255, 0.52);
  }

  .card-icon {
    display: grid;
    width: 39px;
    height: 39px;
    place-items: center;
    border-radius: 10px;
    background: #edf5cf;
    color: #779116;
    font-size: 20px;
  }

  h2 {
    margin: 0 0 5px;
    font-size: 15px;
    letter-spacing: -0.02em;
  }

  .group-card p {
    margin: 0;
    color: #77827a;
    font-size: 12px;
    line-height: 1.4;
  }

  .card-arrow {
    color: #9caf68;
    font-size: 21px;
  }

  footer {
    display: flex;
    justify-content: space-between;
    gap: 20px;
    margin-top: auto;
    padding: 22px 0 30px;
    border-top: 1px solid #dfe5df;
    color: #97a099;
    font-size: 11px;
    letter-spacing: 0.05em;
    text-transform: uppercase;
  }

  footer b {
    color: #bfce8b;
    font-weight: 400;
  }

  @media (max-width: 680px) {
    main {
      width: min(100% - 32px, 520px);
    }

    .status {
      font-size: 0;
    }

    .status-dot {
      margin-right: 0;
    }

    .hero {
      padding: 90px 0 80px;
    }

    .groups {
      grid-template-columns: 1fr;
    }

    footer {
      flex-direction: column;
    }
  }
</style>
