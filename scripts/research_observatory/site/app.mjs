const STATUS_LABELS = Object.freeze({
  positive_exploratory_proxy: 'Exploratory proxy +',
  analysis_only_recovery: 'Analysis-only recovery',
  auto_proxy_signal: 'AUTO proxy signal',
  null: 'Null',
  failed: 'Engineering failure',
  unavailable: 'Unavailable',
  descriptive: 'Descriptive',
  recovered_unbound: 'Recovered, unbound',
  not_run: 'Not run',
  not_inspected: 'Not inspected',
  not_interpretable: 'Not interpretable',
});
const CLAIM_STATUSES = new Set([
  'untested', 'in-progress', 'preliminary', 'supported', 'weakened',
  'falsified', 'retracted', 'not_interpretable',
]);

const VIEWS = Object.freeze([
  { id: 'start', title: 'Start here' },
  { id: 'matrix', title: 'Experiments × models' },
  { id: 'results', title: 'What results mean' },
  { id: 'route', title: 'Scientific route' },
  { id: 'decisions', title: 'Decisions and lessons' },
  { id: 'sources', title: 'Explore sources' },
]);

const ROUTE_STAGES = Object.freeze([
  { title: 'Decodability', question: 'Can a frozen probe read the proposed operation from a representation?', checks: 'Held-out labels, layer controls and lexical controls.', source: 'docs/HYPOTHESES_AND_FALSIFICATION.md' },
  { title: 'Geometry', question: 'Are the relevant directions or subspaces stable and interpretable?', checks: 'Across cases, layers and matched negative directions.', source: 'docs/LAB05.md' },
  { title: 'Generalization', question: 'Does the same relationship transfer to new problems and domains?', checks: 'Held-out families, sources, domains and formulations.', source: 'docs/HYPOTHESES_AND_FALSIFICATION.md' },
  { title: 'Causality', question: 'Does a controlled intervention change the selected operation?', checks: 'Steering, ablation, dose, opposite-sign and capability-preservation tests.', source: 'docs/LAB06.md' },
  { title: 'Compositionality', question: 'Can two operations combine predictably?', checks: 'Two-operation and contradiction tasks only after the single-operator causal gate passes.', source: 'docs/HYPOTHESES_AND_FALSIFICATION.md' },
]);

const EVIDENCE_LEVELS = Object.freeze([
  { code: 'E0', name: 'Hypothesis', requirement: 'Precise claim, model scope and falsification condition; untested.' },
  { code: 'E1', name: 'Behavioral observation', requirement: 'A qualified behavioral effect.' },
  { code: 'E2', name: 'Cross-domain decodability', requirement: 'E1 plus lexical controls, cross-domain transfer and decodability.' },
  { code: 'E3', name: 'Causal steering', requirement: 'E2 plus positive intervention, dose response and preserved capability.' },
  { code: 'E4', name: 'Bidirectional causality', requirement: 'E3 plus a negative or opposite-sign intervention.' },
  { code: 'E5', name: 'Cross-model replication', requirement: 'E4 plus independent and cross-model replication.' },
  { code: 'E6', name: 'Controlled emergence', requirement: 'E5 plus controlled training from scratch.' },
]);

const HYPOTHESES = Object.freeze([
  {
    strength: 'weak', title: 'Weak hypothesis',
    statement: 'In a pretrained model, at least one abstract inventive operation has an internal representation that can be decoded and transfers to unseen domains beyond lexical, template and source shortcuts.',
    boundary: 'Current boundary: exploratory automated-proxy observations; independent expert construct validation and controlled representation tests remain open.',
  },
  {
    strength: 'strong', title: 'Strong hypothesis',
    statement: 'A model trained from scratch without TRIZ terminology, source wording or canonical examples develops a functionally comparable operator that transfers to new domains and supports a controlled causal intervention.',
    boundary: 'Current boundary: pretrained-model observations cannot establish controlled emergence. No such training study is qualified here.',
  },
]);

const isObject = (value) => value !== null && typeof value === 'object' && !Array.isArray(value);

function validatePayload(payload) {
  if (!isObject(payload) || payload.schema !== 'research-observatory-site-v1'
      || !Array.isArray(payload.claims) || !Array.isArray(payload.observations)
      || !Array.isArray(payload.decisions) || !Array.isArray(payload.sources)) {
    throw new TypeError('Unsupported or malformed observatory snapshot');
  }
  for (const item of payload.observations) {
    if (!isObject(item) || !Object.hasOwn(STATUS_LABELS, item.status)) {
      throw new TypeError(`Unknown status in observatory snapshot: ${String(item?.status)}`);
    }
  }
  for (const claim of payload.claims) {
    if (!isObject(claim) || !CLAIM_STATUSES.has(claim.status)) {
      throw new TypeError(`Unknown claim status in observatory snapshot: ${String(claim?.status)}`);
    }
    if (claim.evidence_level !== 'E0' && claim.evidence_level !== null) {
      throw new TypeError(`Unverified claim evidence level in observatory snapshot: ${String(claim.evidence_level)}`);
    }
  }
}

function validateSourcePath(path) {
  if (typeof path !== 'string' || path.length === 0 || path.length > 300
      || path.startsWith('/') || path.startsWith('\\') || path.includes('\\')
      || path.includes(':') || path.split('/').some((part) => part === '' || part === '.' || part === '..')
      || !/^[A-Za-z0-9._/-]+$/.test(path)) {
    throw new TypeError('Invalid source path');
  }
  return path;
}

export function sourceUrl(head, path) {
  if (typeof head !== 'string' || !/^[0-9a-f]{40}$/.test(head)) {
    throw new TypeError('Invalid full source commit identity');
  }
  return `https://github.com/MarcoPorcellato/Latent-TRIZ/blob/${head}/${validateSourcePath(path)}`;
}

export function selectMatrix(records, filters = {}) {
  return records.filter((item) => {
    if (!Object.hasOwn(STATUS_LABELS, item.status)) {
      throw new TypeError(`Unknown status in observatory snapshot: ${String(item.status)}`);
    }
    return (!filters.campaign || filters.campaign === 'All' || item.campaign === filters.campaign)
      && (!filters.model || filters.model === 'All' || item.model === filters.model)
      && (!filters.status || filters.status === 'All' || item.status === filters.status);
  });
}

function sourceTitle(path) {
  return path.split('/').at(-1) || path;
}

export function selectSources(sources, query = '') {
  const needle = String(query).trim().toLocaleLowerCase();
  return sources.filter((item) => !needle ||
    `${item.path} ${sourceTitle(item.path)} ${item.family} ${item.summary}`.toLocaleLowerCase().includes(needle));
}

function admittedSource(payload, path) {
  return payload.sources.find((item) => item.path === path);
}

function sourceLink(payload, path) {
  const item = admittedSource(payload, path);
  return item ? { path: item.path, title: sourceTitle(item.path), url: sourceUrl(payload.build_source.head, item.path) } : null;
}

function resultRecords(payload, campaign) {
  return selectMatrix(payload.observations, { campaign }).map((item) => ({
    ...item,
    statusLabel: STATUS_LABELS[item.status],
    sourceScope: item.scope,
    sources: [...new Set([...(Array.isArray(item.source_paths) ? item.source_paths : []), item.source])]
      .filter((path) => typeof path === 'string')
      .map((path) => {
        const link = sourceLink(payload, path);
        const admitted = admittedSource(payload, path);
        return link ? { ...link, summary: admitted.summary } : null;
      })
      .filter(Boolean),
  }));
}

export function renderViewModel(payload, view, filters = {}) {
  validatePayload(payload);
  if (!VIEWS.some((item) => item.id === view)) throw new TypeError(`Unknown observatory view: ${view}`);
  const sources = payload.sources;
  const selectedSources = selectSources(sources, filters.query || '');
  const selectedCampaign = payload.campaign_names?.includes(filters.campaign)
    ? filters.campaign
    : payload.campaign_names?.[0] || [...new Set(payload.observations.map((item) => item.campaign))][0] || '';
  const selectedResults = view === 'results' ? resultRecords(payload, selectedCampaign) : undefined;
  const resultModelCount = payload.model_names?.length || new Set(payload.observations.map((item) => item.model)).size;
  const resultRecordedModels = new Set((selectedResults || []).map((item) => item.model));
  const resultInspectedModels = new Set((selectedResults || [])
    .filter((item) => !['not_inspected', 'not_run'].includes(item.status)).map((item) => item.model));
  const resultUninspectedModels = new Set((selectedResults || [])
    .filter((item) => ['not_inspected', 'not_run'].includes(item.status)).map((item) => item.model));
  const requestedPath = filters.sourcePath;
  const selectedSource = (requestedPath && selectedSources.find((item) => item.path === requestedPath)) || selectedSources[0] || null;
  const safeSelectedSource = selectedSource ? {
    ...selectedSource,
    title: sourceTitle(selectedSource.path),
    url: sourceUrl(payload.build_source.head, selectedSource.path),
  } : null;
  return {
    view,
    views: VIEWS,
    generatedAt: payload.generated_at,
    head: payload.build_source.head,
    tree: payload.build_source.tree,
    sourceInventorySha256: payload.source_inventory.sha256,
    catalogueSha256: payload.catalogue_sha256,
    snapshotNotice: 'Curated snapshot — not live GitHub. Repository documents and evidence remain authoritative.',
    warnings: payload.warnings,
    allowedSources: payload.sources,
    filters,
    statuses: Object.entries(STATUS_LABELS).map(([value, label]) => ({ value, label })),
    modelNames: payload.model_names || [...new Set(payload.observations.map((item) => item.model))],
    campaignNames: payload.campaign_names || [...new Set(payload.observations.map((item) => item.campaign))],
    hypotheses: view === 'start' ? HYPOTHESES : undefined,
    claims: view === 'start' ? payload.claims.map((claim) => ({
      ...claim,
      registryStatus: claim.status,
      evidenceLabel: claim.evidence_level === 'E0' ? 'E0 — hypothesis, untested' : 'No evidence level asserted',
    })) : undefined,
    records: view === 'matrix' ? resultRecords(payload, filters.campaign || 'All').filter((item) =>
      (!filters.model || filters.model === 'All' || item.model === filters.model)
      && (!filters.status || filters.status === 'All' || item.status === filters.status)) : selectedResults,
    selectedCampaign: view === 'results' ? selectedCampaign : undefined,
    coverage: view === 'results' ? {
      totalModels: resultModelCount,
      recorded: resultRecordedModels.size,
      inspected: resultInspectedModels.size,
      notInspected: resultUninspectedModels.size,
      missing: Math.max(0, resultModelCount - resultRecordedModels.size),
    } : undefined,
    categories: view === 'decisions' ? ['All', ...new Set(payload.decisions.map((item) => item.category))] : undefined,
    decisions: view === 'decisions'
      ? payload.decisions.filter((item) => !filters.category || filters.category === 'All' || item.category === filters.category)
      : undefined,
    stages: view === 'route' ? ROUTE_STAGES.map((item) => ({ ...item, sourceLink: sourceLink(payload, item.source) })) : undefined,
    selectedStage: view === 'route' ? ROUTE_STAGES.find((item) => item.title === filters.stage)?.title || ROUTE_STAGES[0].title : undefined,
    evidenceLevels: view === 'route' ? EVIDENCE_LEVELS : undefined,
    sources: view === 'sources' ? selectedSources.map((item) => ({
      ...item, title: sourceTitle(item.path), url: sourceUrl(payload.build_source.head, item.path),
    })) : undefined,
    selectedSource: view === 'sources' ? safeSelectedSource : undefined,
  };
}

function appendText(document, parent, tag, value, className = '') {
  const node = document.createElement(tag);
  if (className) node.setAttribute('class', className);
  node.textContent = value == null ? '' : String(value);
  parent.appendChild(node);
  return node;
}

export function updateLiveStatus(document, message) {
  const status = document.querySelector('#app-status');
  if (status) status.textContent = String(message || '');
}

function statusSummary(model) {
  if (model.view === 'sources') return `${model.sources.length} sources match.`;
  if (model.view === 'matrix' || model.view === 'results') return `${(model.records || []).length} records shown.`;
  if (model.view === 'decisions') return `${model.decisions.length} decisions shown.`;
  if (model.view === 'route') return `${model.selectedStage} stage selected.`;
  return 'Start here view selected.';
}

function appendLink(document, parent, link) {
  if (!link) return;
  const anchor = document.createElement('a');
  anchor.setAttribute('href', link.url);
  anchor.setAttribute('target', '_blank');
  anchor.setAttribute('rel', 'noreferrer');
  anchor.textContent = `${link.title} · ${link.path}`;
  parent.appendChild(anchor);
}

function appendSelect(document, parent, label, options, selected, onChange) {
  const wrapper = document.createElement('label');
  wrapper.textContent = `${label} `;
  const select = document.createElement('select');
  select.setAttribute('aria-label', label);
  select.setAttribute('data-focus-key', `filter:${label}`);
  for (const option of options) {
    const item = document.createElement('option');
    item.setAttribute('value', option.value);
    item.textContent = option.label;
    if (option.value === selected) item.setAttribute('selected', '');
    select.appendChild(item);
  }
  if (onChange) select.addEventListener('change', (event) => onChange(event.target.value));
  wrapper.appendChild(select);
  parent.appendChild(wrapper);
}

function renderRecords(document, root, model) {
  const controls = document.createElement('section');
  controls.setAttribute('class', 'controls');
  appendSelect(document, controls, 'Campaign', [{ value: 'All', label: 'All' }, ...model.campaignNames.map((value) => ({ value, label: value }))], model.filters.campaign || 'All', model.onFilter && ((campaign) => model.onFilter({ ...model.filters, campaign })));
  appendSelect(document, controls, 'Model', [{ value: 'All', label: 'All' }, ...model.modelNames.map((value) => ({ value, label: value }))], model.filters.model || 'All', model.onFilter && ((value) => model.onFilter({ ...model.filters, model: value })));
  appendSelect(document, controls, 'Status', [{ value: 'All', label: 'All' }, ...model.statuses.map((item) => ({ value: item.value, label: item.label }))], model.filters.status || 'All', model.onFilter && ((value) => model.onFilter({ ...model.filters, status: value })));
  root.appendChild(controls);
  for (const record of model.records || []) {
    const card = document.createElement('article');
    card.setAttribute('class', 'card');
    appendText(document, card, 'h3', `${record.model} · ${record.campaign}`);
    appendText(document, card, 'p', record.statusLabel, `status status-${record.status}`);
    appendText(document, card, 'p', record.notes);
    appendText(document, card, 'p', `Scope: ${record.scope}`);
    for (const link of record.sources) appendLink(document, card, link);
    root.appendChild(card);
  }
}

export function renderInto(document, root, viewModel) {
  const focusKey = document.activeElement?.getAttribute?.('data-focus-key');
  const focusedSearch = focusKey === 'search:sources';
  const searchSelection = focusedSearch
    ? [document.activeElement.selectionStart ?? 0, document.activeElement.selectionEnd ?? 0]
    : null;
  root.replaceChildren();
  const main = document.createElement('main');
  main.setAttribute('class', 'shell');
  appendText(document, main, 'p', 'LATENT-TRIZ · RESEARCH OBSERVATORY', 'eyebrow');
  appendText(document, main, 'h1', 'See the whole investigation');
  appendText(document, main, 'p', viewModel.snapshotNotice, 'notice');
  appendText(document, main, 'p', `Snapshot generated ${viewModel.generatedAt} · commit ${viewModel.head} · tree ${viewModel.tree}`, 'snapshot');
  appendText(document, main, 'p', `Source inventory SHA-256: ${viewModel.sourceInventorySha256}`, 'snapshot');
  appendText(document, main, 'p', `Catalogue SHA-256: ${viewModel.catalogueSha256}`, 'snapshot');
  const nav = document.createElement('nav');
  nav.setAttribute('aria-label', 'Observatory views');
  for (const view of viewModel.views) {
    const button = document.createElement('button');
    button.setAttribute('type', 'button');
    button.setAttribute('data-focus-key', `nav:${view.id}`);
    if (viewModel.view === view.id) button.setAttribute('aria-current', 'page');
    button.textContent = view.title;
    if (viewModel.onNavigate) button.addEventListener('click', () => viewModel.onNavigate(view.id));
    nav.appendChild(button);
  }
  main.appendChild(nav);
  const viewHeading = appendText(document, main, 'h2', viewModel.views.find((item) => item.id === viewModel.view)?.title || 'Observatory');
  viewHeading.setAttribute('tabindex', '-1');
  viewHeading.setAttribute('data-focus-fallback', 'view-heading');

  if (viewModel.view === 'start') {
    appendText(document, main, 'p', 'Two distinct hypotheses share a research program, but need different evidence. The current catalogue establishes neither.');
    const hypotheses = document.createElement('section');
    hypotheses.setAttribute('class', 'grid');
    for (const item of viewModel.hypotheses) {
      const card = document.createElement('article');
      card.setAttribute('class', `card hypothesis-${item.strength}`);
      appendText(document, card, 'h3', item.title);
      appendText(document, card, 'p', item.statement);
      appendText(document, card, 'p', item.boundary);
      appendLink(document, card, sourceLinkFromView(viewModel, 'docs/HYPOTHESES_AND_FALSIFICATION.md'));
      hypotheses.appendChild(card);
    }
    main.appendChild(hypotheses);
    appendText(document, main, 'h3', 'Evidence levels E0–E6');
    for (const item of EVIDENCE_LEVELS) appendText(document, main, 'p', `${item.code} · ${item.name}: ${item.requirement}`);
    for (const claim of viewModel.claims) {
      const card = document.createElement('article');
      card.setAttribute('class', 'card');
      appendText(document, card, 'h3', `${claim.claim_id}: ${claim.statement}`);
      appendText(document, card, 'p', `Registry status (source label only): ${claim.registryStatus}`);
      appendText(document, card, 'p', `Evidence: ${claim.evidenceLabel}. The browser does not verify or promote claims.`);
      main.appendChild(card);
    }
  } else if (viewModel.view === 'matrix') {
    renderRecords(document, main, viewModel);
  } else if (viewModel.view === 'results') {
    appendSelect(document, main, 'Study campaign', viewModel.campaignNames.map((value) => ({ value, label: value })), viewModel.selectedCampaign,
      viewModel.onFilter && ((campaign) => viewModel.onFilter({ ...viewModel.filters, campaign })));
    appendText(document, main, 'p', `${viewModel.selectedCampaign}: ${viewModel.coverage.inspected} inspected of ${viewModel.coverage.totalModels} model slots; ${viewModel.coverage.notInspected} not run/not inspected; ${viewModel.coverage.missing} absent from this campaign catalogue. No cross-study pooling.`, 'notice');
    for (const record of viewModel.records || []) {
      const card = document.createElement('article');
      card.setAttribute('class', 'card');
      appendText(document, card, 'h3', record.model);
      appendText(document, card, 'p', record.statusLabel, `status status-${record.status}`);
      appendText(document, card, 'p', `Source-scoped record: ${record.sourceScope}`);
      appendText(document, card, 'p', record.notes);
      for (const link of record.sources) {
        appendText(document, card, 'p', `Cited source scope: ${link.summary}`);
        appendLink(document, card, link);
      }
      main.appendChild(card);
    }
  } else if (viewModel.view === 'route') {
    const stageOptions = viewModel.stages.map((item) => ({ value: item.title, label: item.title }));
    appendSelect(document, main, 'Route stage', stageOptions, viewModel.selectedStage, viewModel.onFilter && ((stage) => viewModel.onFilter({ ...viewModel.filters, stage })));
    for (const stage of viewModel.stages) appendText(document, main, 'p', stage.title);
    const selected = viewModel.stages.find((item) => item.title === viewModel.selectedStage);
    appendText(document, main, 'h3', selected.title);
    appendText(document, main, 'p', `Question: ${selected.question}`);
    appendText(document, main, 'p', `Required checks: ${selected.checks}`);
    appendLink(document, main, selected.sourceLink);
    appendText(document, main, 'p', 'This route organizes questions, not completed milestones. Expert validation remains a separate prerequisite.');
    for (const level of viewModel.evidenceLevels) appendText(document, main, 'p', `${level.code} · ${level.name}: ${level.requirement}`);
  } else if (viewModel.view === 'decisions') {
    const options = viewModel.categories.map((value) => ({ value, label: value }));
    appendSelect(document, main, 'Decision category', options, viewModel.filters.category || 'All', viewModel.onFilter && ((category) => viewModel.onFilter({ ...viewModel.filters, category })));
    for (const item of viewModel.decisions) {
      const card = document.createElement('article');
      card.setAttribute('class', 'card');
      appendText(document, card, 'p', `${item.declared_date || 'Undated in source'} · ${item.category} · ${item.id}`);
      appendText(document, card, 'h3', item.title);
      appendText(document, card, 'p', item.notes);
      appendLink(document, card, sourceLinkFromView(viewModel, item.source));
      main.appendChild(card);
    }
  } else if (viewModel.view === 'sources') {
    const label = document.createElement('label');
    label.textContent = 'Search sources ';
    const input = document.createElement('input');
    input.setAttribute('type', 'search');
    input.setAttribute('aria-label', 'Search sources');
    input.setAttribute('data-focus-key', 'search:sources');
    input.setAttribute('value', viewModel.filters.query || '');
    input.value = viewModel.filters.query || '';
    input.addEventListener('input', (event) => viewModel.onFilter?.({ ...viewModel.filters, query: event.target.value }));
    label.appendChild(input);
    main.appendChild(label);
    for (const item of viewModel.sources) {
      const row = document.createElement('article');
      row.setAttribute('class', 'card source-card');
      appendText(document, row, 'h3', item.title);
      appendText(document, row, 'code', item.path);
      appendText(document, row, 'p', `Family: ${item.family} · Date: ${item.declared_date || 'not stated'} · Freshness: ${item.freshness}`);
      appendText(document, row, 'p', item.summary);
      const choose = document.createElement('button');
      choose.setAttribute('type', 'button');
      choose.setAttribute('aria-label', `Select source ${item.path}`);
      choose.setAttribute('data-focus-key', `source:${item.path}`);
      choose.textContent = viewModel.selectedSource?.path === item.path ? 'Selected source' : 'Select source';
      choose.addEventListener('click', () => viewModel.onFilter?.({ ...viewModel.filters, sourcePath: item.path }));
      row.appendChild(choose);
      appendLink(document, row, item);
      appendText(document, row, 'p', `SHA-256: ${item.sha256}`);
      main.appendChild(row);
    }
    if (!viewModel.sources.length) appendText(document, main, 'p', 'No allowlisted source matches this search.', 'notice');
    if (viewModel.selectedSource) {
      appendText(document, main, 'h3', `Selected source · ${viewModel.selectedSource.title}`);
      appendText(document, main, 'p', `${viewModel.selectedSource.path} · ${viewModel.selectedSource.family} · ${viewModel.selectedSource.freshness}`);
    }
  }
  for (const warning of viewModel.warnings || []) appendText(document, main, 'p', `Source note: ${warning}`, 'warning');
  root.appendChild(main);
  if (focusKey) {
    const control = findByFocusKey(root, focusKey) || findByFocusFallback(root);
    control?.focus();
    if (focusedSearch && control?.getAttribute?.('data-focus-key') === 'search:sources'
        && typeof control.setSelectionRange === 'function') {
      control.setSelectionRange(...searchSelection);
    }
  }
}

function findByFocusKey(root, key) {
  if (root.getAttribute?.('data-focus-key') === key) return root;
  for (const child of root.children || []) {
    const match = findByFocusKey(child, key);
    if (match) return match;
  }
  return null;
}

function findByFocusFallback(root) {
  if (root.getAttribute?.('data-focus-fallback') === 'view-heading') return root;
  for (const child of root.children || []) {
    const match = findByFocusFallback(child);
    if (match) return match;
  }
  return null;
}

function sourceLinkFromView(viewModel, path) {
  const source = viewModel.allowedSources?.find((item) => item.path === path);
  if (!source) return null;
  return { path, title: sourceTitle(path), url: sourceUrl(viewModel.head, path) };
}

function startBrowser() {
  const root = document.querySelector('#app');
  let payload;
  let state = { view: 'start', filters: {} };
  const showError = (message) => {
    root.replaceChildren();
    const notice = document.createElement('main');
    notice.setAttribute('class', 'shell error');
    appendText(document, notice, 'h1', 'Snapshot unavailable');
    appendText(document, notice, 'p', `The curated observatory data could not be loaded or validated. ${message}`);
    appendText(document, notice, 'p', 'This page does not display an empty dashboard as a successful load. Try again later or inspect the repository sources.');
    root.appendChild(notice);
  };
  const draw = () => {
    try {
      const model = renderViewModel(payload, state.view, state.filters);
      model.allowedSources = payload.sources;
      model.onNavigate = (view) => {
        state = { ...state, view };
        const next = draw();
        if (next) updateLiveStatus(document, `${next.views.find((item) => item.id === view)?.title || 'Observatory'} view selected.`);
      };
      model.onFilter = (filters) => {
        state = { ...state, filters };
        const next = draw();
        if (next) updateLiveStatus(document, statusSummary(next));
      };
      renderInto(document, root, model);
      return model;
    } catch (error) {
      showError(error.message);
      updateLiveStatus(document, 'Snapshot unavailable.');
      return null;
    }
  };
  fetch('./site-data.json', { cache: 'no-cache' })
    .then((response) => { if (!response.ok) throw new Error(`HTTP ${response.status}`); return response.json(); })
    .then((value) => {
      validatePayload(value);
      payload = value;
      const model = draw();
      if (model) updateLiveStatus(document, 'Observatory snapshot loaded. Start here view selected.');
    })
    .catch((error) => {
      showError(error.message);
      updateLiveStatus(document, 'Snapshot unavailable.');
    });
}

if (typeof document !== 'undefined' && typeof window !== 'undefined') startBrowser();
