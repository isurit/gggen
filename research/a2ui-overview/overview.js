(async () => {
  const button = document.getElementById('export-html');
  const status = document.getElementById('export-status');
  const diagrams = [...document.querySelectorAll('.diagram')];

  async function renderDiagrams() {
    if (!window.mermaid) return 0;
    mermaid.initialize({
      startOnLoad: false,
      securityLevel: 'strict',
      theme: 'neutral',
      htmlLabels: false,
      flowchart: { nodeSpacing: 24, rankSpacing: 32 },
      sequence: { wrap: true, actorMargin: 24, width: 110 },
    });

    let rendered = 0;
    for (const [index, diagram] of diagrams.entries()) {
      const source = diagram.querySelector('.mermaid-source').textContent;
      try {
        const { svg } = await mermaid.render('overview-diagram-' + index, source);
        diagram.querySelector('.diagram-render').innerHTML = svg;
        rendered++;
      } catch {
        diagram.querySelector('details').open = true;
      }
    }
    return rendered;
  }

  const rendered = await renderDiagrams();
  if (rendered < diagrams.length) {
    status.textContent = '일부 다이어그램의 미리보기를 표시할 수 없습니다. Mermaid 원문은 문서에 포함됩니다.';
  }

  async function inlineImages(snapshot) {
    const images = [...snapshot.querySelectorAll('img[data-offline-image]')];
    await Promise.all(images.map(async image => {
      const response = await fetch(image.src, { mode: 'same-origin' });
      if (!response.ok) throw new Error('Preview download failed');
      const blob = await response.blob();
      image.src = await new Promise((resolve, reject) => {
        const reader = new FileReader();
        reader.onload = () => resolve(reader.result);
        reader.onerror = () => reject(reader.error);
        reader.readAsDataURL(blob);
      });
    }));
  }

  button.addEventListener('click', async () => {
    button.disabled = true;
    const snapshot = document.documentElement.cloneNode(true);
    snapshot.querySelectorAll('script, [data-online-only]').forEach(element => element.remove());
    try {
      await inlineImages(snapshot);
    } catch {
      status.textContent = 'Figma 미리보기를 불러오지 못했습니다. 잠시 후 HTML 저장을 다시 시도해 주세요.';
      return;
    } finally {
      button.disabled = false;
    }
    const html = '<!doctype html>\n' + snapshot.outerHTML;
    const url = URL.createObjectURL(new Blob([html], { type: 'text/html;charset=utf-8' }));
    const link = document.createElement('a');
    link.href = url;
    link.download = 'A2UI-개념-정리.html';
    document.body.append(link);
    link.click();
    link.remove();
    window.setTimeout(() => URL.revokeObjectURL(url), 1000);
    status.textContent = 'HTML을 저장했습니다. 시스템 흐름에서 Mermaid 원문을 펼쳐 복사할 수 있습니다.';
  });
  button.disabled = false;
})();
