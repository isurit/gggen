(() => {
  const $ = id => document.getElementById(id);
  let revision;
  function status(message, error = false) {
    $('status').textContent = message;
    $('status').dataset.error = String(error);
  }
  async function api(path, options) {
    const response = await fetch('/api/a2ui/' + path, {cache: 'no-store', ...options});
    const data = await response.json();
    if (!response.ok) throw new Error(data.error || '요청을 처리하지 못했습니다.');
    return data;
  }
  function populate(data) {
    revision = data.revision;
    $('prompt').value = data.prompt;
    $('model').value = data.model;
    $('pat-state').textContent = data.hasPat ? '저장됨' : '입력 필요';
    $('key-state').textContent = data.hasModelKey ? '사용 가능' : '입력 필요';
    $('app-key').value = data.appKey;
    $('endpoint').value = location.origin + data.endpoint;
  }
  document.querySelectorAll('[data-prompt]').forEach(button => {
    button.addEventListener('click', () => {
      $('prompt').value = button.dataset.prompt;
      status('예시를 입력했습니다. 설정 저장을 눌러 적용하세요.');
    });
  });
  $('settings').addEventListener('submit', async event => {
    event.preventDefault();
    $('save').disabled = true;
    try {
      const data = await api('settings', {method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({revision, prompt: $('prompt').value, model: $('model').value,
          pat: $('pat').value.trim(), modelKey: $('model-key').value.trim()})});
      populate(data);
      $('pat').value = '';
      $('model-key').value = '';
      status('저장했습니다. 휴대폰 앱에서 새로고침하세요. 설정 버전 ' + data.revision);
    } catch (error) { status(error.message, true); }
    finally { $('save').disabled = false; }
  });
  $('preview').addEventListener('click', async () => {
    $('preview').disabled = true;
    status('실제 기기 목록을 조회하고 화면을 구성하고 있습니다.');
    try {
      const data = await api('device-list');
      $('response').textContent = JSON.stringify(data.messages, null, 2);
      $('meta').textContent = '기기 ' + data.meta.deviceCount + '개 · 설정 버전 ' +
        data.meta.revision + ' · ' + (data.meta.layoutCached ? '배치 재사용' : '새 배치 생성') +
        ' · ' + data.meta.durationMs + 'ms';
      status('API 호출을 완료했습니다.');
    } catch (error) { status(error.message, true); }
    finally { $('preview').disabled = false; }
  });
  $('copy-key').addEventListener('click', async () => {
    try { await navigator.clipboard.writeText($('app-key').value); status('앱 연결 키를 복사했습니다.'); }
    catch { status('연결 키를 복사할 수 없습니다.', true); }
  });
  api('settings').then(data => { populate(data); status('프롬프트와 토큰을 저장하면 준비됩니다.'); })
    .catch(error => status(error.message, true));
})();
