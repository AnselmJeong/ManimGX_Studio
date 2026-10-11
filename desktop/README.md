# ManimGX Studio

수학·물리 개념을 설명하는 영상을 만드는 Rust / GPUI Kit 데스크톱 앱입니다.
ManimGX 0.1.1을 실제로 실행해 MP4를 생성합니다.

## 사용하기

`/Applications/ManimGX Studio.app`을 실행합니다.

1. **새 영상**을 누르고 만들고 싶은 내용을 자연어로 입력합니다.
   예: “빛의 굴절을 중학생에게 설명하는 30초 영상. 공기와 물의 경계를 보여줘.”
2. **AI 연결 → ChatGPT 로그인…**에서 Studio 전용 로그인을 완료합니다.
   설치된 Codex CLI 또는 Codex.app을 사용합니다. API 키는 필요하지 않습니다.
3. **AI로 영상 만들기**를 누르면 장면 구성을 표시하고, 코드를 작성해 MP4까지 렌더링합니다.
4. 미리보기에서 영상을 보면서 **“두 번째 장면을 더 천천히”**, **“빛을 노란색으로”**처럼
   요청하면 현재 장면 구성·코드·대화와 현재 미리보기 프레임을 전달해 수정합니다.
5. **이전 버전**으로 최근 10개의 성공한 수정 이전 상태를 복원할 수 있습니다.
6. **MP4 내보내기…**로 원본 H.264 / 30 fps 영상을 저장합니다.

AI 생성은 현재 자막을 포함한 무음 영상입니다. 앱 미리보기는 최대 12 fps의 샘플이며,
**영상 플레이어로 열기**에서 원본 프레임 속도로 볼 수 있습니다. 720p/1080p는 영상 설정에서 선택합니다.
학술 내용의 정확성과 장면 표현은 결과를 보며 검토해 주세요.

AI는 렌더링 오류를 최대 두 번 수정합니다. 실패·중단 시 기존 영상과 입력 요청은 보존됩니다.
생성 중에는 프로젝트 전환과 코드 편집을 잠그고, **생성 중단**으로 AI와 렌더러를 중지합니다.
생성된 Python은 사전 검사 후 macOS 샌드박스에서 실행합니다. 외부 파일·네트워크에
접근하는 장면과 외부 에셋은 지원하지 않습니다. 수동 Python 편집·렌더링은 기존 고급 기능입니다.

**AI 연결**에서 계정 모델 선택, 사용량 갱신, 로그아웃을 할 수 있습니다. 구독 사용 가능 여부를
매 호출 전에 확인하며, 한도 초과나 확인 불가 상태에서는 중단합니다. 다른 Codex 앱과 계정
사용량을 공유하며 유료 API로 자동 전환하지 않습니다. 사전 한도 확인은 서버의 과금 상한을
보장하는 기능은 아닙니다. Codex 설치 경로를 직접 지정하려면 `MANIMGX_STUDIO_CODEX`를 사용합니다.
로그인은 Studio 데이터 폴더의 전용 `codex/`에 보관하며 다른 앱의 인증 파일을 복사하지 않습니다.

기존 네 예제도 그대로 사용할 수 있습니다. **영상 설정**에서 수치를 바꾸거나 **Python 코드**
탭에서 장면을 직접 편집할 수 있습니다. 기본 클래스는 `Lesson`입니다.
`VALUE = 숫자`, `PACE = 숫자`를 유지하면 예제 슬라이더와 연동됩니다.

프로젝트는 `.mgx` JSON 파일로 저장하고 다시 열 수 있습니다. 이전 프로젝트도 열 수 있습니다.
새 프로젝트는 대화·장면 구성·입력 초안·최근 버전 기록을 함께 저장합니다.

| 단축키 | 작업 |
| --- | --- |
| ⌘N | 새 영상 |
| ⌘Enter | AI 제작 탭에서는 생성/수정, 다른 탭에서는 수동 렌더링 |
| ⌘S | 프로젝트 저장 |
| ⌘O | 프로젝트 열기 |
| ⌘E | MP4 내보내기 |
| ⌘P | 미리보기 재생 / 일시 정지 |

작업은 `~/Library/Application Support/ManimGX Studio/session.json`에 자동 저장됩니다.
`renders/`의 실행별 폴더에는 `scene.py`, `project.mgx`, `film.mp4`, `render.log`,
미리보기 프레임이 보관됩니다. 마지막 영상은 앱을 다시 열면 복구되며 렌더 기록을 자동 삭제하지 않습니다.

## 개발

Apple Silicon macOS가 현재 검증 대상입니다. Rust 버전은 `rust-toolchain.toml`로 고정하며,
렌더 엔진 자체의 Rust workspace와 분리되어 있습니다. GPUI 관련 의존성은 `gpui-kit` 하나입니다.

저장소 루트에서:

```sh
RUSTUP_TOOLCHAIN=1.99.0 uv sync --frozen
cd desktop
cargo run --locked
```

개발 실행은 저장소의 `.venv/bin/python`을 사용합니다. 필요하면
`MANIMGX_STUDIO_PYTHON=/absolute/path/to/python`으로 실행 환경을 선택할 수 있습니다.
`MANIMGX_STUDIO_DATA`는 자동 저장과 렌더 폴더를 격리하는 QA용 설정입니다.

```sh
cd desktop
cargo fmt --check
cargo clippy --locked --all-targets -- -D warnings
cargo test --locked
cd ..
RUSTUP_TOOLCHAIN=1.99.0 uv run --frozen pytest -q desktop/tests/test_ai.py
RUSTUP_TOOLCHAIN=1.99.0 uv run --frozen python desktop/tests/smoke.py
```

Rust 테스트는 저장·복구, 코드 수정 보존, 실패 로그, 렌더 중단과 실제 GPUI 뷰의 입력·선택을 검증합니다.
Python smoke 검사는 네 예제를 렌더링하고 MP4를 끝까지 디코딩해 확인합니다.
`qa-output/`에서 영상을 확인할 수 있으며, 실제 렌더에서 기본 미리보기 이미지도 생성합니다.

## macOS 앱 빌드

```sh
bash desktop/scripts/bundle.sh
open "desktop/dist/ManimGX Studio.app"
```

스크립트는 release 바이너리, 독립 실행 가능한 CPython, 고정한 Python 패키지와 한국어 글꼴을
묶고 로컬 서명을 검사합니다. 빌드 시에만 인터넷과 Rust / uv가 필요합니다. 완성한 앱의 실행에는
터미널 PATH, Homebrew Python, 저장소 또는 uv가 필요하지 않습니다. 앱을 Applications에 복사해
실행하는 것을 권장합니다. 현재 결과물은 로컬 서명이며, 공증된 배포판은 아닙니다.

구조: `src/studio.rs`는 화면과 작업 흐름, `src/project.rs`는 저장 형식,
`src/render_job.rs`는 렌더 프로세스 수명, `runtime/worker.py`는 ManimGX CLI 실행과 영상 디코딩을 담당합니다.
외부 프로세스는 셸 문자열 없이 인자 목록으로 실행하고, 렌더마다 독립 폴더를 사용합니다.
예제의 진자는 작은 진폭·마찰 없음의 근사이며, 피타고라스 예제는 넓이 관계의 시각화입니다.

참고: [ManimGX 문서](https://manimgx.academa.ai/) · [GPUI Kit](https://github.com/longbridge/gpui-kit)

AI 구현과 검증 범위: [AI_IMPLEMENTATION.md](AI_IMPLEMENTATION.md).
