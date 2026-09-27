import test from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';

import {
  renderInto,
  renderViewModel,
  selectMatrix,
  selectSources,
  sourceUrl,
  updateLiveStatus,
} from './app.mjs';

const statuses = [
  'positive_exploratory_proxy', 'analysis_only_recovery', 'auto_proxy_signal',
  'null', 'failed', 'unavailable', 'descriptive', 'recovered_unbound',
  'not_run', 'not_inspected', 'not_interpretable',
];

const source = (path, extra = {}) => ({
  path,
  sha256: 'a'.repeat(64),
  family: 'selected_docs',
  summary: 'Reviewed source record.',
  declared_date: null,
  freshness: 'current',
  stale_markers: [],
  conflict_markers: [],
  ...extra,
});

const payload = {
  schema: 'research-observatory-site-v1',
  generated_at: '2026-09-27T12:30:00Z',
  build_source: { head: 'b'.repeat(40), tree: 'c'.repeat(40) },
  source_inventory: { sha256: 'd'.repeat(64), source_base_head: 'e'.repeat(40), source_base_tree: 'f'.repeat(40) },
  catalogue_sha256: '1'.repeat(64),
  claims: [{ claim_id: 'W1', statement: 'Weak hypothesis', status: 'untested', evidence_level: 'E0', last_verified: '2026-09-01', source: 'docs/HYPOTHESES_AND_FALSIFICATION.md' }],
  observations: statuses.map((status, index) => ({
    model: `Model ${index}`,
    campaign: index % 2 ? 'EXP-002 baseline' : 'EXP-001 comparative',
    status,
    source: 'results/a0/report.json',
    source_paths: ['results/a0/report.json'],
    scope: 'Frozen study scope',
    notes: 'Recorded outcome',
    metric: null,
  })),
  decisions: [
    { id: 'D1', title: 'Protocol freeze', category: 'method', declared_date: '2026-09-01', source: 'docs/decisions.md', notes: 'Keep the comparison fixed.' },
    { id: 'D2', title: 'Validation gate', category: 'validation', declared_date: null, source: 'docs/decisions.md', notes: 'Expert review remains open.' },
  ],
  sources: [
    source('results/a0/report.json', { family: 'a0', summary: 'Published result manifest.' }),
    source('docs/decisions.md', { summary: 'Decision record.' }),
  ],
  warnings: ['Snapshot is curated.'],
  model_names: statuses.map((_, index) => `Model ${index}`),
  campaign_names: ['EXP-001 comparative', 'EXP-002 baseline'],
};

test('renders a view model for each of the six observatory views', () => {
  const views = ['start', 'matrix', 'results', 'route', 'decisions', 'sources'];
  for (const view of views) {
    assert.equal(renderViewModel(payload, view, {}).view, view);
  }
  assert.deepEqual(renderViewModel(payload, 'start', {}).hypotheses.map((item) => item.strength), ['weak', 'strong']);
  assert.deepEqual(renderViewModel(payload, 'route', {}).stages.map((item) => item.title), [
    'Decodability', 'Geometry', 'Generalization', 'Causality', 'Compositionality',
  ]);
  assert.deepEqual(renderViewModel(payload, 'route', {}).evidenceLevels.map((item) => item.code), ['E0', 'E1', 'E2', 'E3', 'E4', 'E5', 'E6']);
  assert.deepEqual(renderViewModel(payload, 'decisions', {}).categories, ['All', 'method', 'validation']);
  assert.equal(renderViewModel(payload, 'start', {}).sourceInventorySha256, 'd'.repeat(64));
  assert.equal(renderViewModel(payload, 'start', {}).catalogueSha256, '1'.repeat(64));
});

test('results are scoped to one selected campaign and disclose its complete denominator', () => {
  const model = renderViewModel(payload, 'results', {});
  assert.equal(model.selectedCampaign, 'EXP-001 comparative');
  assert.deepEqual(new Set(model.records.map((item) => item.campaign)), new Set(['EXP-001 comparative']));
  assert.deepEqual(model.coverage, { totalModels: 11, recorded: 6, inspected: 5, notInspected: 1, missing: 5 });
  assert.equal(model.records[0].sourceScope, 'Frozen study scope');
  assert.deepEqual(model.records[0].sources.map((item) => item.path), ['results/a0/report.json']);
  const other = renderViewModel(payload, 'results', { campaign: 'EXP-002 baseline' });
  assert.equal(other.selectedCampaign, 'EXP-002 baseline');
  assert.ok(other.records.every((item) => item.campaign === 'EXP-002 baseline'));
});

test('preserves all admitted outcome states and rejects an unknown status', () => {
  const rows = renderViewModel(payload, 'matrix', {}).records;
  assert.deepEqual(rows.map((item) => item.status), statuses);
  const bad = structuredClone(payload);
  bad.observations[0].status = 'future_positive';
  assert.throws(() => renderViewModel(bad, 'matrix', {}), /unknown status/i);
});

test('rejects unknown claim status and future evidence level rather than implying verification', () => {
  const unknownStatus = structuredClone(payload);
  unknownStatus.claims[0].status = 'confirmed_future';
  assert.throws(() => renderViewModel(unknownStatus, 'start', {}), /unknown claim status/i);
  const futureLevel = structuredClone(payload);
  futureLevel.claims[0].evidence_level = 'E1';
  assert.throws(() => renderViewModel(futureLevel, 'start', {}), /unverified claim evidence level/i);
});

test('filters matrix records by campaign, model, and status without pooling campaigns', () => {
  assert.deepEqual(selectMatrix(payload.observations, {
    campaign: 'EXP-002 baseline', model: 'Model 1', status: 'null',
  }).map((item) => item.model), []);
  assert.deepEqual(selectMatrix(payload.observations, {
    campaign: 'EXP-002 baseline', model: 'Model 1', status: 'analysis_only_recovery',
  }).map((item) => item.model), ['Model 1']);
});

test('result records link only to sources admitted in the payload at its exact commit', () => {
  const model = renderViewModel(payload, 'results', {}).records[0];
  assert.equal(model.sources[0].url,
    `https://github.com/MarcoPorcellato/Latent-TRIZ/blob/${'b'.repeat(40)}/results/a0/report.json`);
  const excluded = structuredClone(payload);
  excluded.observations[0].source_paths.push('private/sealed-target.json');
  assert.deepEqual(renderViewModel(excluded, 'results', {}).records[0].sources.map((item) => item.path), ['results/a0/report.json']);
});

test('source search includes safe path/title context and selected-source details', () => {
  assert.deepEqual(selectSources(payload.sources, 'decision').map((item) => item.path), ['docs/decisions.md']);
  const model = renderViewModel(payload, 'sources', { query: 'report' });
  assert.equal(model.selectedSource.path, 'results/a0/report.json');
  assert.equal(model.selectedSource.title, 'report.json');
  assert.equal(model.selectedSource.url.endsWith('/results/a0/report.json'), true);
  assert.deepEqual(selectSources(payload.sources, 'no match'), []);
});

test('source URLs reject unsafe commit identities and untrusted path syntax', () => {
  assert.equal(sourceUrl('b'.repeat(40), 'docs/readme.md'),
    `https://github.com/MarcoPorcellato/Latent-TRIZ/blob/${'b'.repeat(40)}/docs/readme.md`);
  for (const path of ['../private.txt', '/etc/passwd', 'javascript:alert(1)', 'docs\\..\\secret']) {
    assert.throws(() => sourceUrl('b'.repeat(40), path), /source path/i);
  }
  assert.throws(() => sourceUrl('not-a-commit', 'docs/readme.md'), /commit/i);
});

class FakeNode {
  constructor(tagName = '#document') {
    this.tagName = tagName;
    this.children = [];
    this.attributes = {};
    this._textContent = '';
    this.innerHTMLWrites = [];
    this.listeners = {};
    this.ownerDocument = fakeDocument;
    this.selectionStart = 0;
    this.selectionEnd = 0;
    this.selectionRangeCalls = 0;
  }
  set textContent(value) { this._textContent = String(value); this.children = []; }
  get textContent() { return this._textContent + this.children.map((item) => item.textContent).join(''); }
  set innerHTML(value) { this.innerHTMLWrites.push(String(value)); }
  appendChild(node) { this.children.push(node); return node; }
  replaceChildren(...nodes) { this.children = nodes; }
  setAttribute(name, value) { this.attributes[name] = String(value); }
  getAttribute(name) { return this.attributes[name] ?? null; }
  addEventListener(type, callback) { this.listeners[type] = callback; }
  dispatch(type, value) {
    if (type === 'input') {
      this.value = value;
      this.selectionStart = String(value).length;
      this.selectionEnd = String(value).length;
    }
    this.listeners[type]?.({ target: { value } });
  }
  focus() { this.ownerDocument.activeElement = this; }
  setSelectionRange(start, end) {
    this.selectionRangeCalls += 1;
    this.selectionStart = start;
    this.selectionEnd = end;
  }
}

const fakeDocument = {
  activeElement: null,
  createElement: (tag) => new FakeNode(tag),
  createTextNode: (text) => { const node = new FakeNode('#text'); node.textContent = text; return node; },
};

test('renders malicious source strings as text and uses only a safe admitted URL', () => {
  const poisoned = structuredClone(payload);
  poisoned.sources[0].path = 'results/a0/report.json';
  poisoned.sources[0].summary = '<img src=x onerror=alert(1)> & "quoted"';
  poisoned.observations[0].notes = '<script>alert(1)</script>';
  poisoned.observations[0].source_paths = ['results/a0/report.json', 'javascript:alert(1)'];
  const viewModel = renderViewModel(poisoned, 'sources', { query: '' });
  const root = new FakeNode();
  renderInto(fakeDocument, root, viewModel);
  const nodes = [];
  const visit = (node) => { nodes.push(node); node.children.forEach(visit); };
  visit(root);
  assert.equal(nodes.some((node) => node.innerHTMLWrites.length), false);
  assert.equal(root.textContent.includes('<img src=x onerror=alert(1)>'), true);
  assert.equal(root.textContent.includes('<script>alert(1)</script>'), false);
  const links = nodes.filter((node) => node.tagName === 'a');
  assert.equal(links.length, 2);
  assert.equal(links.every((node) => node.attributes.href.startsWith(`https://github.com/MarcoPorcellato/Latent-TRIZ/blob/${'b'.repeat(40)}/`)), true);
});

test('fake DOM renders all six views and wires accessible filters and source selection', () => {
  const roots = [];
  for (const view of ['start', 'matrix', 'results', 'route', 'decisions', 'sources']) {
    const root = new FakeNode();
    const model = renderViewModel(payload, view, {});
    model.allowedSources = payload.sources;
    renderInto(fakeDocument, root, model);
    assert.ok(root.textContent.includes(view === 'start' ? 'Weak hypothesis' : model.views.find((item) => item.id === view).title));
    roots.push(root);
  }
  let changed;
  const matrix = renderViewModel(payload, 'matrix', {});
  matrix.allowedSources = payload.sources;
  matrix.onFilter = (filters) => { changed = filters; };
  const matrixRoot = new FakeNode();
  renderInto(fakeDocument, matrixRoot, matrix);
  const campaign = findNode(matrixRoot, (node) => node.attributes['aria-label'] === 'Campaign');
  campaign.dispatch('change', 'EXP-002 baseline');
  assert.equal(changed.campaign, 'EXP-002 baseline');

  const results = renderViewModel(payload, 'results', {});
  results.onFilter = (filters) => { changed = filters; };
  const resultsRoot = new FakeNode();
  renderInto(fakeDocument, resultsRoot, results);
  findNode(resultsRoot, (node) => node.attributes['aria-label'] === 'Study campaign')
    .dispatch('change', 'EXP-002 baseline');
  assert.equal(changed.campaign, 'EXP-002 baseline');

  let selected;
  const sourceView = renderViewModel(payload, 'sources', {});
  sourceView.allowedSources = payload.sources;
  sourceView.onFilter = (filters) => { selected = filters; };
  const sourceRoot = new FakeNode();
  renderInto(fakeDocument, sourceRoot, sourceView);
  const search = findNode(sourceRoot, (node) => node.attributes['aria-label'] === 'Search sources');
  search.dispatch('input', 'decision');
  assert.equal(selected.query, 'decision');
  const selectSource = findNode(sourceRoot, (node) => node.attributes['aria-label'] === 'Select source docs/decisions.md');
  selectSource.dispatch('click');
  assert.equal(selected.sourcePath, 'docs/decisions.md');
  assert.equal(roots.length, 6);
});

test('UI exposes distinct snapshot digests, study coverage, cited scope, and non-validating claim labels', () => {
  const root = new FakeNode();
  const start = renderViewModel(payload, 'start', {});
  renderInto(fakeDocument, root, start);
  assert.ok(root.textContent.includes(`Source inventory SHA-256: ${'d'.repeat(64)}`));
  assert.ok(root.textContent.includes(`Catalogue SHA-256: ${'1'.repeat(64)}`));
  assert.ok(root.textContent.includes('Registry status (source label only): untested'));
  assert.ok(root.textContent.includes('E0 — hypothesis, untested'));
  assert.ok(root.textContent.includes('browser does not verify or promote claims'));

  const resultsRoot = new FakeNode();
  const results = renderViewModel(payload, 'results', {});
  results.onFilter = () => {};
  renderInto(fakeDocument, resultsRoot, results);
  assert.ok(resultsRoot.textContent.includes('5 inspected of 11 model slots'));
  assert.ok(resultsRoot.textContent.includes('1 not run/not inspected'));
  assert.ok(resultsRoot.textContent.includes('5 absent from this campaign catalogue'));
  assert.ok(resultsRoot.textContent.includes('Source-scoped record: Frozen study scope'));
  assert.ok(resultsRoot.textContent.includes('Cited source scope: Published result manifest.'));
  const resultHeadings = [];
  const collectHeadings = (node) => {
    if (node.tagName === 'h3') resultHeadings.push(node.textContent);
    node.children.forEach(collectHeadings);
  };
  collectHeadings(resultsRoot);
  assert.equal(resultHeadings.includes('Model 1'), false);
});

test('source search keeps focus and caret while successive characters trigger redraws', () => {
  const root = new FakeNode();
  let filters = {};
  const draw = () => {
    const model = renderViewModel(payload, 'sources', filters);
    model.onFilter = (next) => { filters = next; draw(); };
    renderInto(fakeDocument, root, model);
  };
  draw();
  let input = findNode(root, (node) => node.attributes['aria-label'] === 'Search sources');
  input.focus();
  input.setSelectionRange(0, 0);
  input.dispatch('input', 'd');
  input = findNode(root, (node) => node.attributes['aria-label'] === 'Search sources');
  assert.equal(fakeDocument.activeElement, input);
  input.setSelectionRange(1, 1);
  input.dispatch('input', 'de');
  input = findNode(root, (node) => node.attributes['aria-label'] === 'Search sources');
  assert.equal(fakeDocument.activeElement, input);
  assert.equal(input.selectionStart, 2);
  assert.equal(input.selectionEnd, 2);
  assert.equal(filters.query, 'de');
});

test('uses a dedicated status region instead of announcing the full app on redraw', () => {
  const html = readFileSync(new URL('./index.html', import.meta.url), 'utf8');
  assert.match(html, /<div id="app">/);
  assert.doesNotMatch(html, /<div id="app"[^>]*aria-live=/);
  assert.match(html, /id="app-status"[^>]*role="status"[^>]*aria-live="polite"/);

  const status = new FakeNode('p');
  const document = { querySelector: (selector) => selector === '#app-status' ? status : null };
  updateLiveStatus(document, '3 sources match.');
  assert.equal(status.textContent, '3 sources match.');
  updateLiveStatus(document, 'Start here view selected.');
  assert.equal(status.textContent, 'Start here view selected.');
  updateLiveStatus({ querySelector: () => null }, 'ignored');
  assert.equal(status.textContent, 'Start here view selected.');
});

test('bounds form controls and flexible navigation at narrow viewport widths', () => {
  const css = readFileSync(new URL('./style.css', import.meta.url), 'utf8');
  assert.match(css, /button, select, input\s*\{[^}]*max-width:\s*100%/s);
  assert.match(css, /label\s*\{[^}]*max-width:\s*100%/s);
  assert.match(css, /\.source-card h3\s*\{[^}]*overflow-wrap:\s*anywhere/s);
  assert.match(css, /\.source-card p\s*\{[^}]*overflow-wrap:\s*anywhere/s);
  assert.match(css, /@media\s*\(max-width:\s*580px\)[\s\S]*nav\s*\{[^}]*grid-template-columns:\s*repeat\(2,\s*minmax\(0,\s*1fr\)\)/s);
  assert.match(css, /nav button\s*\{[^}]*min-width:\s*0/s);
  assert.match(css, /@media\s*\(max-width:\s*580px\)[\s\S]*label\s*\{[^}]*margin-right:\s*0/s);
  assert.match(css, /@media\s*\(max-width:\s*580px\)[\s\S]*select,\s*input\s*\{[^}]*width:\s*100%/s);
});

test('restores focus to stable navigation, filter, and source-selection controls after redraw', () => {
  const root = new FakeNode();
  let view = 'start';
  let filters = {};
  const draw = () => {
    const model = renderViewModel(payload, view, filters);
    model.onNavigate = (next) => { view = next; draw(); };
    model.onFilter = (next) => { filters = next; draw(); };
    renderInto(fakeDocument, root, model);
  };
  draw();

  let control = findNode(root, (node) => node.tagName === 'button' && node.textContent === 'Experiments × models');
  control.focus();
  control.dispatch('click');
  control = findNode(root, (node) => node.tagName === 'button' && node.textContent === 'Experiments × models');
  assert.equal(fakeDocument.activeElement, control);

  control = findNode(root, (node) => node.tagName === 'select' && node.attributes['aria-label'] === 'Campaign');
  control.focus();
  control.dispatch('change', 'EXP-002 baseline');
  control = findNode(root, (node) => node.tagName === 'select' && node.attributes['aria-label'] === 'Campaign');
  assert.equal(fakeDocument.activeElement, control);

  const sourcesNav = findNode(root, (node) => node.tagName === 'button' && node.textContent === 'Explore sources');
  sourcesNav.focus();
  sourcesNav.dispatch('click');
  let chooseSource = findNode(root, (node) => node.attributes['aria-label'] === 'Select source docs/decisions.md');
  chooseSource.focus();
  chooseSource.dispatch('click');
  chooseSource = findNode(root, (node) => node.attributes['aria-label'] === 'Select source docs/decisions.md');
  assert.equal(fakeDocument.activeElement, chooseSource);
});

test('focuses the current view heading when a previously focused control disappears', () => {
  const root = new FakeNode();
  const staleControl = new FakeNode('button');
  staleControl.setAttribute('data-focus-key', 'missing-control');
  staleControl.focus();
  renderInto(fakeDocument, root, renderViewModel(payload, 'start', {}));
  const heading = findNode(root, (node) => node.tagName === 'h2' && node.attributes['data-focus-fallback'] === 'view-heading');
  assert.ok(heading);
  assert.equal(fakeDocument.activeElement, heading);
});

test('does not restore search caret onto a fallback heading when search disappears', () => {
  const root = new FakeNode();
  const staleSearch = new FakeNode('input');
  staleSearch.setAttribute('data-focus-key', 'search:sources');
  staleSearch.focus();
  renderInto(fakeDocument, root, renderViewModel(payload, 'start', {}));
  const heading = findNode(root, (node) => node.tagName === 'h2' && node.attributes['data-focus-fallback'] === 'view-heading');
  assert.equal(fakeDocument.activeElement, heading);
  assert.equal(heading.selectionRangeCalls, 0);
});

function findNode(root, predicate) {
  if (predicate(root)) return root;
  for (const child of root.children) {
    const match = findNode(child, predicate);
    if (match) return match;
  }
  return null;
}
