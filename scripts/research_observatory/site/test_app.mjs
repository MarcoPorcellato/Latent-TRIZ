import test from 'node:test';
import assert from 'node:assert/strict';

import {
  renderInto,
  renderViewModel,
  selectMatrix,
  selectSources,
  sourceUrl,
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
});

test('preserves all admitted outcome states and rejects an unknown status', () => {
  const rows = renderViewModel(payload, 'matrix', {}).records;
  assert.deepEqual(rows.map((item) => item.status), statuses);
  const bad = structuredClone(payload);
  bad.observations[0].status = 'future_positive';
  assert.throws(() => renderViewModel(bad, 'matrix', {}), /unknown status/i);
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
  }
  set textContent(value) { this._textContent = String(value); this.children = []; }
  get textContent() { return this._textContent + this.children.map((item) => item.textContent).join(''); }
  set innerHTML(value) { this.innerHTMLWrites.push(String(value)); }
  appendChild(node) { this.children.push(node); return node; }
  replaceChildren(...nodes) { this.children = nodes; }
  setAttribute(name, value) { this.attributes[name] = String(value); }
  addEventListener(type, callback) { this.listeners[type] = callback; }
  dispatch(type, value) { this.listeners[type]?.({ target: { value } }); }
}

const fakeDocument = {
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

function findNode(root, predicate) {
  if (predicate(root)) return root;
  for (const child of root.children) {
    const match = findNode(child, predicate);
    if (match) return match;
  }
  return null;
}
