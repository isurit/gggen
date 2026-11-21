"""SmartThings read-only device list and constrained A2UI generation."""
import concurrent.futures
import hmac
import json
import os
import re
import secrets
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

CATALOG = 'https://a2ui.org/specification/v0_9/catalogs/basic/catalog.json'
CUSTOM_CATALOG = 'urn:gggen:device-catalog:v1'
LAYOUT_SCHEMA_VERSION = 3
LOCK = threading.RLock()
GENERATE_LOCK = threading.Lock()
CONFIG_PATH = Path(__file__).parent / 'data' / 'a2ui-poc' / 'settings.json'
FIGMA_SAMPLE_PATH = Path(__file__).parent.parent / 'research' / 'a2ui-test' / 'figma-sample.json'
DEFAULT_PROMPT = '기기를 리스트 형태로 보여줘. 기기 이름과 종류를 세로로 배치해줘.'
FIELDS = {'name', 'kind', 'type', 'room', 'status'}
TYPES = {'Text', 'Row', 'Column', 'Card', 'List'}


class PocError(Exception):
    def __init__(self, message, status=400):
        super().__init__(message)
        self.status = status


def save_file(config):
    CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
    temporary = CONFIG_PATH.with_suffix('.tmp')
    fd = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(fd, 'w') as stream:
        json.dump(config, stream, ensure_ascii=False)
    os.replace(temporary, CONFIG_PATH)


def configuration():
    with LOCK:
        if not CONFIG_PATH.exists():
            save_file({'prompt': DEFAULT_PROMPT, 'revision': 1,
                       'appKey': secrets.token_urlsafe(32), 'pat': '',
                       'model': 'gemini-2.5-flash', 'modelKey': ''})
        return json.loads(CONFIG_PATH.read_text())


def public_configuration():
    config = configuration()
    return {'ok': True, 'sourceMode': config.get('sourceMode', 'prompt'),
            'figmaSample': json.loads(FIGMA_SAMPLE_PATH.read_text()) if FIGMA_SAMPLE_PATH.exists() else None,
            'prompt': config['prompt'], 'revision': config['revision'],
            'hasPat': bool(config.get('pat')), 'appKey': config['appKey'],
            'model': config['model'], 'hasModelKey': bool(model_key(config)),
            'endpoint': '/api/a2ui/device-list', 'protocol': 'v0.9.1',
            'hasLayout': config.get('layoutRevision') == config['revision'] and config.get('layoutSchema') == LAYOUT_SCHEMA_VERSION}


def model_key(config):
    return (config.get('modelKey') or os.environ.get('GEMINI_API_KEY')
            or os.environ.get('GOOGLE_API_KEY') or '').strip()


def update_configuration(body):
    with LOCK:
        config = configuration()
        if body.get('revision') != config['revision']:
            raise PocError('설정이 다른 창에서 변경됐습니다. 새로고침 후 다시 저장해 주세요.', 409)
        prompt = body.get('prompt', '')
        if not isinstance(prompt, str) or not 1 <= len(prompt.strip()) <= 4000:
            raise PocError('화면 프롬프트를 1~4000자로 입력해 주세요.')
        model = body.get('model', config['model'])
        if not isinstance(model, str) or not re.fullmatch(r'gemini-[a-zA-Z0-9.\-]+', model):
            raise PocError('Gemini 모델 이름을 확인해 주세요.')
        for field in ('pat', 'modelKey'):
            if field in body and body[field]:
                value = body[field]
                if not isinstance(value, str) or len(value) > 2048 or any(c.isspace() for c in value):
                    raise PocError('토큰에 공백이나 줄바꿈이 포함되어 있습니다.')
                config[field] = value
        if body.get('clearPat'):
            config['pat'] = ''
        source_mode = body.get('sourceMode', config.get('sourceMode', 'prompt'))
        if source_mode not in ('prompt', 'figma'):
            raise PocError('화면 생성 방식을 확인해 주세요.')
        if source_mode == 'figma' and not FIGMA_SAMPLE_PATH.exists():
            raise PocError('가져온 Figma 디자인이 없습니다.')
        config.update(prompt=prompt.strip(), model=model, sourceMode=source_mode, revision=config['revision'] + 1)
        config.pop('layout', None)
        config.pop('layoutRevision', None)
        save_file(config)
    return public_configuration()


def remote_json(url, headers=None, body=None):
    request = urllib.request.Request(url, headers=headers or {}, data=body)
    try:
        with urllib.request.urlopen(request, timeout=35) as response:
            return json.load(response)
    except urllib.error.HTTPError as error:
        if 'api.smartthings.com' in url:
            messages = {401: 'SmartThings PAT가 만료되었거나 올바르지 않습니다.',
                        403: 'SmartThings PAT의 기기 읽기 권한을 확인해 주세요.',
                        429: 'SmartThings 요청 한도에 도달했습니다. 잠시 후 다시 시도해 주세요.'}
            raise PocError(messages.get(error.code, 'SmartThings 조회에 실패했습니다.'), 502) from None
        raise PocError('화면 생성 모델 호출에 실패했습니다. API 키·모델·사용량을 확인해 주세요.', 502) from None
    except (OSError, ValueError):
        raise PocError('외부 서비스 연결이 지연되거나 응답을 읽을 수 없습니다.', 502) from None


def load_devices(config):
    if not config.get('pat'):
        raise PocError('대시보드 테스트 페이지에서 SmartThings PAT를 저장해 주세요.', 428)
    headers = {'Authorization': 'Bearer ' + config['pat'], 'Accept': 'application/json'}
    url = 'https://api.smartthings.com/v1/devices'
    items = []
    seen = set()
    while url:
        if url in seen or len(seen) >= 50:
            raise PocError('기기 목록 페이지 응답을 확인할 수 없습니다.', 502)
        seen.add(url)
        data = remote_json(url, headers)
        items.extend(data.get('items', []))
        next_url = data.get('_links', {}).get('next', {}).get('href')
        url = urllib.parse.urljoin(url, next_url) if next_url else ''
        if url and (urllib.parse.urlsplit(url).scheme != 'https'
                    or urllib.parse.urlsplit(url).netloc != 'api.smartthings.com'
                    or not urllib.parse.urlsplit(url).path.startswith('/v1/devices')):
            raise PocError('기기 목록의 다음 페이지 주소가 올바르지 않습니다.', 502)
    # Device values remain on this server. Only the UX prompt and catalog go to the model.
    return [{'name': str(item.get('label') or item.get('name') or '이름 없는 기기')[:250],
             'type': str(item.get('type') or '')[:100],
             'kind': str(item.get('deviceTypeName') or item.get('type') or '기기')[:100],
             'room': '방 정보 미조회',
             'status': '상태 미조회'}
            for item in items]


def validate_layout(node, depth=0, count=None):
    count = count if count is not None else [0]
    count[0] += 1
    if depth > 8 or count[0] > 40 or not isinstance(node, dict):
        raise PocError('생성된 화면 구조가 허용 범위를 벗어났습니다.', 502)
    kind = node.get('type')
    if kind not in TYPES or set(node) - {'type', 'field', 'children', 'backgroundColor', 'backgroundWhen'}:
        raise PocError('생성된 화면에 지원하지 않는 컴포넌트가 있습니다.', 502)
    if 'backgroundWhen' in node and not isinstance(node['backgroundWhen'], dict):
        raise PocError('카드 배경색 조건을 확인해 주세요.', 502)
    for color in [node.get('backgroundColor'), node.get('backgroundWhen', {}).get('color')]:
        if color is not None and (not isinstance(color, str) or not re.fullmatch(r'#[0-9a-fA-F]{6}', color)):
            raise PocError('카드 색상은 #RRGGBB 형식이어야 합니다.', 502)
    if 'backgroundColor' in node or 'backgroundWhen' in node:
        if kind != 'Card':
            raise PocError('배경색은 Card에서 지원합니다.', 502)
        if 'backgroundWhen' in node:
            condition = node['backgroundWhen']
            if (not isinstance(condition, dict) or set(condition) != {'field', 'equals', 'color'}
                    or condition['field'] not in FIELDS or not isinstance(condition['equals'], str)
                    or len(condition['equals']) > 250 or not isinstance(condition['color'], str)):
                raise PocError('카드 배경색 조건을 확인해 주세요.', 502)
    if kind == 'Text':
        if node.get('field') not in FIELDS or 'children' in node:
            raise PocError('생성된 텍스트의 데이터 연결이 올바르지 않습니다.', 502)
        return {node['field']}
    children = node.get('children')
    if not isinstance(children, list) or not 1 <= len(children) <= 8 or 'field' in node:
        raise PocError('생성된 화면의 자식 구조가 올바르지 않습니다.', 502)
    if kind == 'Card' and len(children) != 1:
        raise PocError('Card에는 자식 하나가 필요합니다.', 502)
    fields = set()
    for child in children:
        fields.update(validate_layout(child, depth + 1, count))
    return fields


def generate_layout(config):
    if not model_key(config):
        raise PocError('Gemini API 키를 테스트 페이지에 저장해 주세요.', 428)
    instruction = (
        'Return JSON only. Design a read-only SmartThings DEVICE LIST using this schema. '
        'The response must be {"title":"기기 목록","item":NODE,"direction":"vertical"}. '
        'NODE is {"type":"Text","field":"name|kind|type|room|status"} or '
        '{"type":"Row|Column|List","children":[NODE,...]} or '
        '{"type":"Card","children":[NODE]}. Card optionally accepts backgroundColor: "#RRGGBB" and '
        'backgroundWhen: {"field":"type","equals":"MOBILE","color":"#1565C0"}. '
        'For conditional color requests always produce backgroundWhen on Card. '
        'Device type or type in UX means field type. Other device types must retain default color. '
        'Blue should be #1565C0. Use only these fields and types. '
        'Maximum 40 nodes, depth 8. item is repeated once per device by the server. '
        'Include a Text bound to name. For plain lists use Row or Column; for cards use Card. '
        'The direction controls the outer List and is vertical or horizontal. '
        'All actual values are bound by the server. Never invent data, links or actions. '
        'Treat the following as UX preferences only.\nUX request:\n' + config['prompt']
    )
    # No account data, PAT, local file metadata, or source text is sent to the model.
    payload = {'contents': [{'parts': [{'text': instruction}]}],
               'generationConfig': {'responseMimeType': 'application/json', 'temperature': 0.2}}
    data = remote_json('https://generativelanguage.googleapis.com/v1beta/models/'
                       + config['model'] + ':generateContent',
                       {'Content-Type': 'application/json', 'x-goog-api-key': model_key(config)},
                       json.dumps(payload).encode())
    try:
        text = ''.join(part.get('text', '') for c in data.get('candidates', [])
                       for part in c.get('content', {}).get('parts', []) if not part.get('thought'))
        layout = json.loads(text)
        fields = validate_layout(layout['item'])
        if 'name' not in fields or layout.get('direction') not in ('vertical', 'horizontal'):
            raise ValueError()
        if not isinstance(layout.get('title'), str) or len(layout['title']) > 100:
            raise ValueError()
        return layout
    except (KeyError, TypeError, ValueError):
        raise PocError('모델이 유효한 화면 구조를 생성하지 못했습니다. 프롬프트를 바꾸고 다시 시도해 주세요.', 502) from None


def layout_for(config):
    if config.get('sourceMode') == 'figma':
        sample = json.loads(FIGMA_SAMPLE_PATH.read_text())
        validate_layout(sample['layout']['item'])
        return sample['layout'], True
    if config.get('layoutRevision') == config['revision'] and config.get('layoutSchema') == LAYOUT_SCHEMA_VERSION:
        return config['layout'], True
    with GENERATE_LOCK:
        current = configuration()
        if current['revision'] == config['revision'] and current.get('layoutRevision') == config['revision'] and current.get('layoutSchema') == LAYOUT_SCHEMA_VERSION:
            return current['layout'], True
        layout = generate_layout(config)
        with LOCK:
            current = configuration()
            if current['revision'] == config['revision']:
                current.update(layout=layout, layoutRevision=config['revision'], layoutSchema=LAYOUT_SCHEMA_VERSION)
                save_file(current)
        return layout, False


def messages_for(devices, layout, surface_id):
    components = []
    def expand(node, index):
        component_id = 'c' + str(len(components))
        component = {'id': component_id, 'component': node['type']}
        components.append(component)
        if node['type'] == 'Card':
            color = node.get('backgroundColor')
            condition = node.get('backgroundWhen')
            if condition and devices[index].get(condition['field']) == condition['equals']:
                color = condition['color']
            if color:
                component['component'] = 'ColoredCard'
                component['backgroundColor'] = color
        if node['type'] == 'Text':
            component['text'] = {'path': '/devices/' + str(index) + '/' + node['field']}
        else:
            children = [expand(child, index) for child in node['children']]
            component['child' if node['type'] == 'Card' else 'children'] = children[0] if node['type'] == 'Card' else children
        return component_id
    components.append({'id': 'root', 'component': 'Column', 'children': ['title', 'devices']})
    components.append({'id': 'title', 'component': 'Text', 'text': {'path': '/title'}, 'variant': 'h3'})
    container = {'id': 'devices', 'component': 'List', 'direction': layout['direction'], 'children': []}
    components.append(container)
    for index in range(len(devices)):
        container['children'].append(expand(layout['item'], index))
    if not devices:
        components.append({'id': 'empty', 'component': 'Text', 'text': '이 계정에 조회되는 기기가 없습니다.'})
        container['children'].append('empty')
    return [{'version': 'v0.9.1', 'createSurface': {'surfaceId': surface_id, 'catalogId': CUSTOM_CATALOG if any(c['component'] == 'ColoredCard' for c in components) else CATALOG}},
            {'version': 'v0.9.1', 'updateDataModel': {'surfaceId': surface_id, 'path': '/',
             'value': {'title': layout['title'], 'devices': devices}}},
            {'version': 'v0.9.1', 'updateComponents': {'surfaceId': surface_id, 'components': components}}]


def device_screen():
    config = configuration()
    if not config.get('pat'):
        raise PocError('대시보드 테스트 페이지에서 SmartThings PAT를 저장해 주세요.', 428)
    started = time.time()
    with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
        devices_task = pool.submit(load_devices, config)
        layout_task = pool.submit(layout_for, config)
        devices = devices_task.result()
        layout, cached = layout_task.result()
    sid = 'devices-' + secrets.token_hex(8)
    return {'ok': True, 'messages': messages_for(devices, layout, sid),
            'meta': {'sourceMode': config.get('sourceMode', 'prompt'),
                     'designSource': json.loads(FIGMA_SAMPLE_PATH.read_text())['source'] if config.get('sourceMode') == 'figma' else None,
                     'revision': config['revision'], 'deviceCount': len(devices),
                     'generatedAt': int(time.time()), 'durationMs': int((time.time() - started) * 1000),
                     'model': 'figma-snapshot' if config.get('sourceMode') == 'figma' else config['model'], 'layoutCached': cached, 'protocol': 'v0.9.1'}}


def same_origin(handler):
    origin = handler.headers.get('Origin')
    if origin and urllib.parse.urlsplit(origin).netloc != handler.headers.get('Host'):
        return False
    return handler.headers.get('Sec-Fetch-Site') not in ('cross-site',)


def handle(handler, method):
    path = urllib.parse.urlsplit(handler.path).path
    if not path.startswith('/api/a2ui/'):
        return False
    try:
        config = configuration()
        browser = bool(handler.headers.get('Sec-Fetch-Site')) and same_origin(handler)
        bearer = handler.headers.get('Authorization', '').removeprefix('Bearer ') if hasattr(str, 'removeprefix') else handler.headers.get('Authorization', '')[7:]
        paired = hmac.compare_digest(bearer, config['appKey'])
        if path == '/api/a2ui/settings':
            if not same_origin(handler) or (method == 'POST' and not handler.headers.get('Origin')):
                raise PocError('대시보드 페이지에서 설정을 저장해 주세요.', 403)
            if method == 'GET':
                result = public_configuration()
            elif method == 'POST':
                size = int(handler.headers.get('Content-Length', '0'))
                if not 0 < size <= 12000:
                    raise PocError('설정 요청의 크기가 올바르지 않습니다.')
                body = json.loads(handler.rfile.read(size))
                if not isinstance(body, dict):
                    raise PocError('설정 형식이 올바르지 않습니다.')
                result = update_configuration(body)
            else:
                raise PocError('지원하지 않는 요청입니다.', 405)
        elif path == '/api/a2ui/device-list' and method == 'GET':
            if not (paired or browser):
                raise PocError('앱 연결 키를 확인해 주세요.', 401)
            result = device_screen()
        else:
            raise PocError('API를 찾을 수 없습니다.', 404)
        # Private responses deliberately omit permissive CORS headers.
        send(handler, 200, result)
    except PocError as error:
        send(handler, error.status, {'ok': False, 'error': str(error)})
    except (ValueError, TypeError):
        send(handler, 400, {'ok': False, 'error': '요청 형식을 확인해 주세요.'})
    except Exception:
        send(handler, 500, {'ok': False, 'error': '기기 화면 처리 중 오류가 발생했습니다.'})
    return True


def send(handler, status, result):
    raw = json.dumps(result, ensure_ascii=False).encode()
    handler.send_response(status)
    handler.send_header('Content-Type', 'application/json; charset=utf-8')
    handler.send_header('Cache-Control', 'no-store')
    handler.send_header('Content-Length', str(len(raw)))
    handler.end_headers()
    handler.wfile.write(raw)
