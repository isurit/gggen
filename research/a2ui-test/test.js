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
    $('source-mode').value = data.sourceMode || 'prompt';
    $('prompt').disabled = data.sourceMode === 'figma';
    $('source-hint').textContent = data.sourceMode === 'figma'
      ? 'Figma에서 가져온 디자인을 사용합니다. 아래에서 원본과 변환 결과를 볼 수 있습니다.'
      : '입력한 프롬프트로 화면 구조를 생성합니다.';
    if (data.figmaSample) {
      $('figma-link').href = data.figmaSample.source.url;
      $('figma-data').textContent = JSON.stringify(data.figmaSample, null, 2);
    }
    $('prompt').value = data.prompt;
    $('model').value = data.model;
    $('pat-state').textContent = data.hasPat ? '저장됨' : '입력 필요';
    $('key-state').textContent = data.hasModelKey ? '사용 가능' : '입력 필요';
    $('app-key').value = data.appKey;
    $('endpoint').value = location.origin + data.endpoint;
  }
  $('source-mode').addEventListener('change', () => {
    $('prompt').disabled = $('source-mode').value === 'figma';
    status('선택한 원본을 적용하려면 설정 저장을 누르세요.');
  });
  document.querySelectorAll('[data-prompt]').forEach(button => {
    button.addEventListener('click', () => {
      $('source-mode').value = 'prompt';
      $('prompt').disabled = false;
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
        body: JSON.stringify({revision, sourceMode: $('source-mode').value, prompt: $('prompt').value, model: $('model').value,
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
      $('meta').textContent = (data.meta.sourceMode === 'figma' ? 'Figma 디자인 · ' : '') + '기기 ' + data.meta.deviceCount + '개 · 설정 버전 ' +
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
  api('settings').then(data => { populate(data); status(data.sourceMode === 'figma' ? 'Figma 디자인이 준비됐습니다. API 호출 또는 휴대폰 새로고침으로 확인하세요.' : '프롬프트와 토큰을 저장하면 준비됩니다.'); })
    .catch(error => status(error.message, true));
})();
