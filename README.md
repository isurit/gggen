# Gen UI POC

SmartThings의 실제 기기 목록을 조회하고, 자연어 프롬프트가 생성한 A2UI 메시지를
Android Compose 화면에 표시하는 POC입니다.

## 동작

1. 테스트 페이지에서 SmartThings PAT와 Gemini API 키, 화면 프롬프트를 저장합니다.
2. Android 앱이 GET /api/a2ui/device-list를 호출합니다.
3. 서버가 SmartThings 기기 목록을 조회하고 Gemini로 생성한 레이아웃에 실제 값을 바인딩합니다.
4. 앱의 공식 AndroidX A2UI 프로세서와 Material Surface가 메시지를 렌더링합니다.

같은 설정의 레이아웃은 캐시하고 기기 목록은 매 요청 새로 조회합니다.
모델에는 프롬프트와 지원 컴포넌트 정보만 전달합니다.

## 서버 실행

Python 3.9 이상을 사용합니다. 서버는 Python 표준 라이브러리로 동작합니다.

    python3 bridge-server/a2ui_poc_server.py

브라우저에서 http://127.0.0.1:8080/을 엽니다.
테스트 페이지에서 기기 읽기 권한의 SmartThings PAT와 Gemini API 키를 입력합니다.
환경 변수 GEMINI_API_KEY 또는 GOOGLE_API_KEY를 사용해도 됩니다.

호스트와 포트는 HOST, PORT 환경 변수로 변경합니다.
설정은 웹 경로에서 차단된 서버 data 디렉터리의 권한 0600 파일로 저장합니다.
휴대폰 연결은 신뢰할 수 있는 사설 네트워크의 HTTPS 프록시로 구성합니다.
배포 환경의 접근 제어는 운영자가 설정해야 합니다.

## Android 빌드와 설치

JDK 17, Android SDK 37.0, Gradle wrapper를 사용합니다.
공식 AndroidX A2UI 1.0.0-alpha02, A2UI 메시지 v0.9.1을 사용합니다.

    cd android/a2ui-smartthings
    ./gradlew assembleDebug -PpocApiUrl=https://YOUR_HOST/api/a2ui/device-list

빌드한 app/build/outputs/apk/debug/app-debug.apk를 설치합니다.
앱의 연결 설정에 HTTPS API 주소와 테스트 페이지의 앱 연결 키를 입력합니다.
APK에는 계정 토큰이나 앱 연결 키를 포함하지 않습니다.

    adb install -r app/build/outputs/apk/debug/app-debug.apk

## 프롬프트 예시

- 기기를 리스트 형태로 보여줘. 이름과 종류를 세로로 배치해줘.
- 기기를 카드 형태로 보여줘.
- 기기를 카드 형태로 보여줘. 기기 type이 MOBILE이면 카드 배경을 파란색으로 칠해줘.

기기 type 조건은 SmartThings 응답의 원본 type 필드에 연결됩니다.
kind는 화면에 보여줄 기기 종류입니다.
색상 조건은 서버가 실제 기기 데이터로 평가합니다.
색상이 있는 카드는 확장 카탈로그 urn:gggen:device-catalog:v1의 ColoredCard를 사용합니다.
표준 Card 구현의 색상 속성은 고정되어 있으므로 앱에 이 확장 구현을 등록했습니다.
조건과 색상 값은 모델이 생성하고 서버가 검증합니다.
앱은 전달받은 RGB 색상과 자식 컴포넌트를 그립니다.

## 범위와 검증

기기 이름과 종류를 표시합니다.
방 이름과 실시간 상태는 아직 조회하지 않습니다.
기기 제어 동작은 포함하지 않습니다.
PAT 만료, 모델 오류, 빈 기기 목록을 처리합니다.
동시 설정 변경은 revision 충돌로 보호합니다.

    python3 -m unittest discover -s bridge-server/tests -p test_a2ui_poc.py

테스트는 컴포넌트 참조, 빈 목록, 잘못된 생성 결과, 페이지네이션의 토큰 전달 대상,
설정 충돌, 비밀값 비노출, 기기 타입별 카드 색상을 검증합니다.

## Figma 데모 선택

대시보드의 Figma 데모 선택에서 디자인을 고른 뒤 설정을 저장합니다.
같은 기기 목록 API와 Android 앱을 사용합니다.

- 1번 단순 카드는 기존의 세로 텍스트 두 줄과 MOBILE 파란 배경입니다.
- 2번 상세 카드는 상단 정보 영역, 큰 기기 이름, 종류·플랫폼 타입을 가로로 배치한 중첩 카드입니다.

Figma 원본에서 에이전트가 읽은 스냅샷을 사용합니다.
파일을 수정한 뒤 에이전트가 다시 읽어 스냅샷을 갱신하면 API 응답에 반영됩니다.
실제 기기 정보는 실행 시 SmartThings에서 조회해 바인딩합니다.
1번 스냅샷은 기존 설정과 호환되며, 디자인 번호가 없는 설정도 1번으로 처리합니다.
