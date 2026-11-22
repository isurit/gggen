# Gen UI · A2UI 화면 예제

서버가 화면 구조와 데이터를 A2UI JSON으로 보내면 Android 앱이 Compose로 렌더링하는 예제입니다. 콘솔에서 프롬프트 또는 디자인을 선택하고, 같은 응답을 콘솔에서는 JSON으로, Android에서는 화면으로 확인할 수 있습니다.

[A2UI 개념 정리 다운로드](https://raw.githubusercontent.com/isurit/gggen/main/docs/a2ui-overview.html) · HTML을 저장해 브라우저에서 열면 사내에서 대시보드에 접속하지 않고 읽을 수 있습니다. 카드 미리보기와 다이어그램이 포함되어 있고, 각 다이어그램의 Mermaid 원문은 Confluence에서 재사용할 수 있습니다.

## 서버와 콘솔 실행

Python 3.9 이상이 필요합니다. 서버는 표준 라이브러리만 사용합니다.

```sh
python3 bridge-server/a2ui_poc_server.py
```

브라우저에서 콘솔 `http://127.0.0.1:8080/`을 열고 다음 순서로 확인합니다.

1. **4번 · 기능 제안** 또는 **3번 · 에어 케어**를 선택하고 **설정 저장**을 누릅니다. 두 예제는 저장된 예시 데이터를 사용하므로 SmartThings나 Gemini 키 없이 실행됩니다.
2. 콘솔에서 **API 호출**을 눌러 메시지와 데이터를 확인합니다. 상단 **A2UI 개념 정리**에서 편집 가능한 문서를 열 수 있습니다.
3. **1번 · 단순 카드**와 **2번 · 상세 카드**는 SmartThings 기기 읽기 권한이 있는 PAT를 저장한 뒤 확인합니다.
4. **자연어 프롬프트** 모드는 PAT와 Gemini API 키를 사용합니다. 모델 키는 콘솔에서 저장하거나 서버 환경 변수 `GEMINI_API_KEY`로 지정합니다. 같은 설정에서 생성한 레이아웃을 재사용하고, 기기 목록은 요청 시 조회합니다.

서버의 기본 바인딩은 로컬입니다. Android에서 연결할 때는 조직에서 승인한 접근 제한 HTTPS 프록시로 콘솔과 API를 제공합니다. 콘솔은 설정을 변경하고 앱 연결 키를 표시하므로 접근 가능한 사용자를 제한해야 합니다. 설정은 `bridge-server/data/a2ui-poc/settings.json`에 로컬로 저장됩니다. PAT와 모델 키는 서버에서 사용하고 Android에는 앱 연결 키만 입력합니다.

## Android 빌드와 연결

JDK 17과 Android SDK API 37을 설치하고 Android Studio에서 `android/a2ui-smartthings`를 엽니다. 터미널에서는 Gradle Wrapper로 빌드할 수 있습니다.

```sh
cd android/a2ui-smartthings
./gradlew assembleDebug
adb install -r app/build/outputs/apk/debug/app-debug.apk
```

앱의 **연결 설정**에 HTTPS로 접근 가능한 `/api/a2ui/device-list` 전체 주소와 콘솔의 앱 연결 키를 입력하고 **새로고침**을 누릅니다. 콘솔을 로컬 HTTP로 띄웠다면 Android에는 프록시의 HTTPS 주소를 입력합니다. 빌드 시 `-PpocApiUrl=https://your-host.example/api/a2ui/device-list`로 기본 주소를 설정할 수도 있습니다.

현재 예제 앱은 AndroidX A2UI `1.0.0-alpha02`와 A2UI 메시지 `v0.9.1`을 사용합니다.

## 요청부터 화면까지

1. 콘솔은 `/api/a2ui/settings`에 디자인 선택 또는 프롬프트를 저장합니다.
2. 앱이 `GET /api/a2ui/device-list`를 호출합니다. 서버는 디자인 스냅샷 또는 생성된 배치에 데이터를 채웁니다.
3. 응답의 `messages` 배열은 `createSurface`, `updateDataModel`, `updateComponents` 순서입니다. 앱이 각 메시지를 프로세서에 전달하고 `A2uiSurface`가 등록된 카탈로그로 화면을 표시합니다. 기기 목록 예제는 Surface 하나에 여러 카드를 담습니다.
4. 4번은 앱이 `X-A2UI-Feature-Suggestion: 1`로 지원을 알리면 `FeatureSuggestionCard`를 보냅니다. 나머지 요청에는 같은 내용을 기본 `Card`, `Row`, `Image`, `Text` 등으로 구성해 보냅니다.

## 무엇을 어디에서 수정하나

| 작업 | 위치 |
| --- | --- |
| 응답 데이터, 프롬프트 허용 범위, A2UI 메시지 조립 변경 | [서버 로직](bridge-server/a2ui_poc.py) |
| 디자인 스냅샷의 레이아웃과 예시 데이터 변경 | [콘솔의 디자인 JSON과 이미지](research/a2ui-test). Figma에서 바꾼 내용은 스냅샷에 반영한 뒤 콘솔에서 선택합니다. |
| 콘솔 화면과 호출 방식 변경 | [콘솔 HTML, CSS, JS](research/a2ui-test) |
| Surface 연결, 사용자 동작, 앱 카탈로그와 이미지 로더 구현 | [Android 소스](android/a2ui-smartthings/app/src/main/java/dev/dashboard/smartthings) |
| A2UI 개념, 카드 예제, Mermaid 다이어그램 수정 | [문서 원본](research/a2ui-overview/index.html). 수정 후 문서 상단의 **오프라인 HTML 저장**으로 [배포용 HTML](docs/a2ui-overview.html)을 갱신합니다. |

앱이 이미 지원하는 컴포넌트와 속성으로 문구, 데이터, 카드 순서, 배치를 바꿀 때는 서버의 응답을 수정하면 됩니다. 새로운 타입이나 제스처, 이미지 표시 기능이 필요하면 Android 구현과 카탈로그를 추가해 배포합니다. 예를 들어 3번의 `AirCarePager`는 두 페이지를 받으며, 4번의 이미지 로더는 지정된 예제 URL과 내장 예시 사진을 사용합니다. 상세 판단 기준은 [오프라인 문서](docs/a2ui-overview.html)의 **앱 재배포가 필요한 경우**를 참고하세요.

## 테스트

```sh
python3 -m unittest discover -s bridge-server/tests -p test_a2ui_poc.py
```

콘솔에서 3번과 4번을 각각 적용해 JSON을 확인한 뒤, 연결된 Android 앱에서 새로고침하면 3번의 스와이프와 4번의 이미지 카드를 확인할 수 있습니다.
