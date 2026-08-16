const errorMessage = (payload, fallback) => {
  if (typeof payload?.detail === 'string') return payload.detail;
  if (Array.isArray(payload?.detail)) {
    return payload.detail.map((item) => `${item.loc?.slice(1).join('.') || 'input'}: ${item.msg}`).join(' · ');
  }
  return fallback;
};

const cookieValue = (name) => document.cookie
  .split(';')
  .map((item) => item.trim())
  .find((item) => item.startsWith(`${name}=`))
  ?.slice(name.length + 1);

const apiFetch = (url, options = {}) => {
  const headers = new Headers(options.headers || {});
  const csrf = cookieValue('tenderpulse_csrf');
  if (csrf && !['GET', 'HEAD', 'OPTIONS'].includes(String(options.method || 'GET').toUpperCase())) {
    headers.set('X-CSRF-Token', decodeURIComponent(csrf));
  }
  return fetch(url, {...options, headers});
};

document.querySelector('#logout-button')?.addEventListener('click', async (event) => {
  const button = event.currentTarget;
  button.disabled = true;
  const response = await apiFetch('/logout', {method: 'POST'});
  if (response.ok) window.location.assign('/login');
  else button.disabled = false;
});

const splitValues = (value, separator) => String(value).split(separator).map((item) => item.trim()).filter(Boolean);

const parseClassifications = (value) => {
  const result = {};
  splitValues(value, /\r?\n/).forEach((line) => {
    const separator = line.indexOf(':');
    if (separator < 1) throw new Error(`Классификатор без SYSTEM: ${line}`);
    const system = line.slice(0, separator).trim();
    const prefixes = splitValues(line.slice(separator + 1), ',');
    if (!prefixes.length) throw new Error(`Не указаны prefixes для ${system}`);
    result[system] = [...(result[system] || []), ...prefixes];
  });
  if (!Object.keys(result).length) throw new Error('Укажите хотя бы один классификатор');
  return result;
};

const textElement = (tag, value, className = '') => {
  const element = document.createElement(tag);
  element.textContent = value;
  if (className) element.className = className;
  return element;
};

const renderEvidence = (container, payload) => {
  container.replaceChildren();
  container.className = `ai-evidence ${payload.status}`;
  const head = document.createElement('div');
  head.className = 'ai-evidence-head';
  head.append(
    textElement('span', `AI evidence · current record v${payload.record_version}`),
    textElement('b', payload.status),
  );
  container.append(head);
  if (!payload.claims) {
    container.append(textElement('p', payload.error_code || 'claims unavailable', 'ai-gaps'));
    return;
  }
  const coverage = document.createElement('div');
  coverage.className = 'coverage-row';
  coverage.append(
    textElement('span', `requirements: ${payload.claims.requirements_status}`),
    textElement('span', `deadlines: ${payload.claims.deadlines_status}`),
  );
  container.append(coverage);
  const claimList = document.createElement('div');
  claimList.className = 'claim-list';
  const addClaim = (label, citation) => {
    const claim = document.createElement('p');
    claim.append(
      textElement('b', label),
      textElement('small', `${citation.field} · ${citation.quote}`),
    );
    claimList.append(claim);
  };
  payload.claims.requirements.forEach((claim) => addClaim(claim.text, claim.citation));
  payload.claims.deadlines.forEach((claim) => addClaim(`${claim.label} · ${claim.value}`, claim.citation));
  if (claimList.childElementCount) container.append(claimList);
  if (payload.claims.gaps.length) {
    container.append(textElement('p', `gaps · ${payload.claims.gaps.join(' · ')}`, 'ai-gaps'));
  }
};

const profileSwitch = document.querySelector('#profile-switch');
profileSwitch?.addEventListener('change', () => {
  const url = new URL(window.location.pathname, window.location.origin);
  if (url.pathname.startsWith('/companies/') && url.pathname !== '/companies/new') {
    url.pathname = `/companies/${encodeURIComponent(profileSwitch.value)}`;
  }
  url.searchParams.set('profile', profileSwitch.value);
  window.location.assign(url);
});

const detailProfileSwitch = document.querySelector('#detail-profile-switch');
detailProfileSwitch?.addEventListener('change', () => {
  const source = detailProfileSwitch.dataset.source;
  const record = detailProfileSwitch.dataset.record;
  window.location.assign(`/tenders/${source}/${record}?profile=${encodeURIComponent(detailProfileSwitch.value)}`);
});

const ingestionForm = document.querySelector('#ingestion-form');
ingestionForm?.addEventListener('submit', async (event) => {
  event.preventDefault();
  const status = document.querySelector('#ingestion-status');
  const data = new FormData(ingestionForm);
  const sources = data.getAll('sources');
  status.textContent = 'Получаю и фиксирую raw evidence…';
  try {
    const response = await apiFetch('/api/ingestion/run', {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({
        sources,
        limit: Number(data.get('limit')),
        eis_lookback_days: Number(data.get('eis_days')),
      }),
    });
    const payload = await response.json();
    if (!response.ok) throw new Error(errorMessage(payload, 'Ошибка загрузки'));
    status.textContent = payload.map((item) => `${item.source}: ${item.status}, ${item.record_count}`).join(' · ');
    window.setTimeout(() => window.location.reload(), 900);
  } catch (error) {
    status.textContent = `Не выполнено: ${error.message}`;
  }
});

const eisUploadForm = document.querySelector('#eis-upload-form');
eisUploadForm?.addEventListener('submit', async (event) => {
  event.preventDefault();
  const status = document.querySelector('#eis-upload-status');
  status.textContent = 'Проверяю и сохраняю пакет…';
  try {
    const response = await apiFetch('/api/ingestion/eis-upload', {method: 'POST', body: new FormData(eisUploadForm)});
    const payload = await response.json();
    if (!response.ok) throw new Error(errorMessage(payload, 'Ошибка пакета'));
    status.textContent = `ЕИС: ${payload.status}, ${payload.record_count} записей`;
    window.setTimeout(() => window.location.reload(), 800);
  } catch (error) {
    status.textContent = `Не загружено: ${error.message}`;
  }
});

document.querySelectorAll('.ai-button').forEach((button) => {
  button.addEventListener('click', async () => {
    const original = button.textContent;
    button.disabled = true;
    button.textContent = 'Проверяю evidence…';
    try {
      const response = await apiFetch(`/api/records/${button.dataset.source}/${button.dataset.record}/evidence/extract`, {method: 'POST'});
      const payload = await response.json();
      if (!response.ok) throw new Error(errorMessage(payload, 'Ошибка извлечения'));
      renderEvidence(button.closest('.tender-card').querySelector('[data-evidence-output]'), payload);
      button.textContent = payload.status === 'validated' ? 'Evidence сохранён' : `Статус: ${payload.status}`;
    } catch (error) {
      button.textContent = `Не выполнено: ${error.message}`;
    } finally {
      window.setTimeout(() => { button.disabled = false; button.textContent = original; }, 3500);
    }
  });
});

document.querySelectorAll('.detail-ai-button').forEach((button) => {
  button.addEventListener('click', async () => {
    button.disabled = true;
    button.textContent = 'Проверяю сохранённую версию…';
    try {
      const response = await apiFetch(`/api/records/${button.dataset.source}/${button.dataset.record}/evidence/extract`, {method: 'POST'});
      const payload = await response.json();
      if (!response.ok) throw new Error(errorMessage(payload, 'Ошибка извлечения'));
      renderEvidence(document.querySelector('[data-evidence-output]'), payload);
      button.textContent = 'Evidence сохранён';
    } catch (error) {
      button.textContent = `Не выполнено: ${error.message}`;
      button.disabled = false;
    }
  });
});

const profileFields = (data) => ({
  description: String(data.get('description') || '').trim(),
  services: splitValues(data.get('services'), /\r?\n/),
  capabilities: splitValues(data.get('capabilities'), /\r?\n/),
  positive_keywords: splitValues(data.get('keywords'), /[,\r\n]/),
  negative_keywords: splitValues(data.get('negative_keywords'), /[,\r\n]/),
  classification_prefixes: parseClassifications(data.get('classifications')),
  countries: splitValues(data.get('countries'), /[,;\s]+/),
  customer_types: splitValues(data.get('customer_types'), /\r?\n/),
  base_region: String(data.get('base_region') || '').trim() || null,
  service_regions: splitValues(data.get('service_regions'), /[,;\s]+/),
  delivery_mode: String(data.get('delivery_mode')),
  nationwide: data.has('nationwide'),
  travel_allowed: data.has('travel_allowed'),
  contractors_allowed: data.has('contractors_allowed'),
  excluded_regions: splitValues(data.get('excluded_regions'), /[,;\s]+/),
  participation_constraints: splitValues(data.get('participation_constraints'), /\r?\n/),
  min_amount: String(data.get('min_amount')).trim() || null,
  max_amount: String(data.get('max_amount')).trim() || null,
  review_above_amount: String(data.get('review_above_amount')).trim() || null,
});

const profilePanel = document.querySelector('#profile');
const profileForm = document.querySelector('#profile-form');
profileForm?.addEventListener('submit', async (event) => {
  event.preventDefault();
  const status = document.querySelector('#profile-status');
  const profile = JSON.parse(profilePanel.dataset.profile);
  const data = new FormData(profileForm);
  try {
    const update = {
      ...profile,
      ...profileFields(data),
      version: profile.version + 1,
      name: String(data.get('name')).trim(),
    };
    status.textContent = `Сохраняю v${update.version}…`;
    const response = await apiFetch(`/api/profiles/${update.slug}`, {
      method: 'PUT', headers: {'Content-Type': 'application/json'}, body: JSON.stringify(update),
    });
    const payload = await response.json();
    if (!response.ok) throw new Error(errorMessage(payload, 'Ошибка профиля'));
    status.textContent = `Версия ${payload.version} активна. Пересчитываю рекомендации…`;
    window.setTimeout(() => window.location.reload(), 700);
  } catch (error) {
    status.textContent = `Не сохранено: ${error.message}`;
  }
});

const createProfileForm = document.querySelector('#create-profile-form');
createProfileForm?.addEventListener('submit', async (event) => {
  event.preventDefault();
  const data = new FormData(createProfileForm);
  const status = document.querySelector('#create-profile-status');
  try {
    const profile = {
      slug: String(data.get('slug')).trim(),
      version: 1,
      name: String(data.get('name')).trim(),
      ...profileFields(data),
    };
    status.textContent = 'Создаю версионируемый профиль…';
    const response = await apiFetch('/api/profiles', {
      method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify(profile),
    });
    const payload = await response.json();
    if (!response.ok) throw new Error(errorMessage(payload, 'Ошибка создания профиля'));
    status.textContent = 'Профиль создан. Открываю карточку…';
    window.setTimeout(() => window.location.assign(`/companies/${encodeURIComponent(payload.slug)}`), 500);
  } catch (error) {
    status.textContent = `Не создано: ${error.message}`;
  }
});

document.querySelector('#sync-alerts')?.addEventListener('click', async (event) => {
  const button = event.currentTarget;
  button.disabled = true;
  button.textContent = 'Синхронизирую…';
  const response = await apiFetch(`/api/alerts/sync/${button.dataset.profile}`, {method: 'POST'});
  button.textContent = response.ok ? 'Alerts готовы' : 'Не выполнено';
  if (response.ok) window.setTimeout(() => window.location.reload(), 500);
});

document.querySelectorAll('.alert-item:not(.read)').forEach((button) => {
  button.addEventListener('click', async () => {
    const response = await apiFetch(`/api/alerts/${button.dataset.alert}/read`, {method: 'POST'});
    if (response.ok) button.classList.add('read');
  });
});
