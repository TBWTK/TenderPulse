const errorMessage = (payload, fallback) => {
  if (typeof payload?.detail === 'string') return payload.detail;
  if (Array.isArray(payload?.detail)) {
    return payload.detail.map((item) => `${item.loc?.slice(1).join('.') || 'input'}: ${item.msg}`).join(' · ');
  }
  return fallback;
};

const splitValues = (value, separator) => String(value).split(separator).map((item) => item.trim()).filter(Boolean);

const navLinks = [...document.querySelectorAll('.nav a[href^="#"]')];
const setActiveNavigation = (sectionId) => {
  navLinks.forEach((link) => {
    const active = link.getAttribute('href') === `#${sectionId}`;
    link.classList.toggle('active', active);
    if (active) link.setAttribute('aria-current', 'location');
    else link.removeAttribute('aria-current');
  });
};
navLinks.forEach((link) => link.addEventListener('click', () => setActiveNavigation(link.hash.slice(1))));
if ('IntersectionObserver' in window) {
  const sectionObserver = new IntersectionObserver((entries) => {
    const visible = entries.filter((entry) => entry.isIntersecting)
      .sort((left, right) => right.intersectionRatio - left.intersectionRatio)[0];
    if (visible?.target.id) setActiveNavigation(visible.target.id);
  }, {rootMargin: '-15% 0px -65% 0px', threshold: [0.05, 0.25, 0.5]});
  navLinks.map((link) => document.querySelector(link.hash)).filter(Boolean)
    .forEach((section) => sectionObserver.observe(section));
}

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
  const url = new URL(window.location.href);
  url.searchParams.set('profile', profileSwitch.value);
  window.location.assign(url);
});

const ingestionForm = document.querySelector('#ingestion-form');
ingestionForm?.addEventListener('submit', async (event) => {
  event.preventDefault();
  const status = document.querySelector('#ingestion-status');
  const data = new FormData(ingestionForm);
  const sources = data.getAll('sources');
  status.textContent = 'Получаю и фиксирую raw evidence…';
  try {
    const response = await fetch('/api/ingestion/run', {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({
        sources,
        limit: Number(data.get('limit')),
        ted_lookback_days: Number(data.get('ted_days')),
        eis_lookback_days: Number(data.get('eis_days')),
        usa_lookback_days: Number(data.get('usa_days')),
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
    const response = await fetch('/api/ingestion/eis-upload', {method: 'POST', body: new FormData(eisUploadForm)});
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
      const response = await fetch(`/api/records/${button.dataset.source}/${button.dataset.record}/evidence/extract`, {method: 'POST'});
      const payload = await response.json();
      if (!response.ok) throw new Error(errorMessage(payload, 'Ошибка извлечения'));
      renderEvidence(button.closest('.opportunity').querySelector('[data-evidence-output]'), payload);
      button.textContent = payload.status === 'validated' ? 'Evidence сохранён' : `Статус: ${payload.status}`;
    } catch (error) {
      button.textContent = `Не выполнено: ${error.message}`;
    } finally {
      window.setTimeout(() => { button.disabled = false; button.textContent = original; }, 3500);
    }
  });
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
      version: profile.version + 1,
      name: String(data.get('name')).trim(),
      capabilities: splitValues(data.get('capabilities'), /\r?\n/),
      positive_keywords: splitValues(data.get('keywords'), /[,\r\n]/),
      classification_prefixes: parseClassifications(data.get('classifications')),
      countries: splitValues(data.get('countries'), /[,;\s]+/),
      min_amount: String(data.get('min_amount')).trim() || null,
      max_amount: String(data.get('max_amount')).trim() || null,
    };
    status.textContent = `Сохраняю v${update.version}…`;
    const response = await fetch(`/api/profiles/${update.slug}`, {
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

document.querySelector('#sync-alerts')?.addEventListener('click', async (event) => {
  const button = event.currentTarget;
  button.disabled = true;
  button.textContent = 'Синхронизирую…';
  const response = await fetch(`/api/alerts/sync/${button.dataset.profile}`, {method: 'POST'});
  button.textContent = response.ok ? 'Alerts готовы' : 'Не выполнено';
  if (response.ok) window.setTimeout(() => window.location.reload(), 500);
});

document.querySelectorAll('.alert-item:not(.read)').forEach((button) => {
  button.addEventListener('click', async () => {
    const response = await fetch(`/api/alerts/${button.dataset.alert}/read`, {method: 'POST'});
    if (response.ok) button.classList.add('read');
  });
});
