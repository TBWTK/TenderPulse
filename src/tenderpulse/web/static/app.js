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
    if (!response.ok) throw new Error(payload.detail || 'Ошибка загрузки');
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
    if (!response.ok) throw new Error(payload.detail || 'Ошибка пакета');
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
      if (!response.ok) throw new Error(payload.detail || 'Ошибка извлечения');
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
  profile.version += 1;
  profile.name = String(data.get('name')).trim();
  profile.positive_keywords = String(data.get('keywords')).split(',').map((item) => item.trim()).filter(Boolean);
  status.textContent = `Сохраняю v${profile.version}…`;
  try {
    const response = await fetch(`/api/profiles/${profile.slug}`, {
      method: 'PUT', headers: {'Content-Type': 'application/json'}, body: JSON.stringify(profile),
    });
    const payload = await response.json();
    if (!response.ok) throw new Error(payload.detail || 'Ошибка профиля');
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
