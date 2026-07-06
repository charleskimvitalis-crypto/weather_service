# 오늘, 여기 날씨

도시나 지역 이름을 입력하면 Open-Meteo에서 오늘의 시간별 날씨를 가져와
기온과 강수확률 그래프로 보여주는 Flask 웹 애플리케이션입니다.

## 주요 기능

- 한글·영문 위치 검색
- 현재 기온, 체감온도, 습도, 바람, 강수량 표시
- 오늘의 시간별 기온과 강수확률 SVG 그래프
- 모바일·데스크톱 반응형 화면
- Flask API와 Vercel Python Runtime 지원

## 실행 환경

- Python 3.12 권장
- 인터넷 연결

## 로컬 실행

프로젝트 폴더에서 가상환경을 만들고 Flask를 설치합니다.

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Flask 개발 서버를 실행합니다.

```bash
python app.py
```

브라우저에서 다음 주소를 엽니다.

```text
http://127.0.0.1:8000
```

다른 포트를 사용하려면 `PORT` 환경 변수를 지정합니다.

```bash
PORT=8080 python app.py
```

서버를 종료하려면 실행 중인 터미널에서 `Ctrl+C`를 누릅니다.

## API

상태 확인:

```text
GET /api/health
```

날씨 검색:

```text
GET /api/weather?location=서울
```

## Vercel 배포

이 프로젝트는 루트의 `app.py`에서 Flask WSGI 객체 `app`을 내보내므로
Vercel이 Flask 프로젝트로 자동 감지합니다. 별도 Build Command나 Output
Directory를 설정하지 않습니다.

### Git 저장소로 배포

1. 프로젝트를 GitHub, GitLab 또는 Bitbucket 저장소에 푸시합니다.
2. [Vercel 새 프로젝트](https://vercel.com/new)에서 저장소를 가져옵니다.
3. Framework Preset과 빌드 설정은 자동 감지된 값을 유지합니다.
4. **Deploy**를 누릅니다.

### Vercel CLI로 배포

Vercel CLI를 설치한 뒤 프로젝트 루트에서 실행합니다.

```bash
npm install -g vercel
vercel
```

미리보기 배포를 확인한 후 프로덕션으로 배포합니다.

```bash
vercel --prod
```

배포 후 다음 주소로 상태를 확인할 수 있습니다.

```text
https://배포-도메인.vercel.app/api/health
```

## Matplotlib 그래프 생성

Matplotlib까지 포함된 개발용 의존성을 설치합니다.

```bash
pip install -r requirements-dev.txt
python plot_today_temperature.py
```

기본 결과는 `today_temperature.png`에 저장됩니다.

## 파일 구성

```text
.
├── app.py                       # Flask 앱과 날씨 API
├── weather_today.py             # Open-Meteo 날씨 조회 로직
├── plot_today_temperature.py    # Matplotlib 그래프 생성
├── requirements.txt             # Vercel 운영 의존성
├── requirements-dev.txt         # 그래프 생성을 포함한 개발 의존성
├── .python-version              # Vercel Python 버전
├── .vercelignore                # 배포 제외 파일
└── public/
    ├── index.html               # 웹페이지 구조
    ├── styles.css               # 반응형 화면 디자인
    └── app.js                   # 검색, 표시 및 SVG 그래프
```

## 문제 해결

- **위치를 찾을 수 없을 때**: 국가나 주 이름을 함께 입력합니다.
- **날씨 서비스에 연결할 수 없을 때**: 인터넷 연결을 확인하고 잠시 후 다시 시도합니다.
- **포트가 사용 중일 때**: `PORT=8080 python app.py`처럼 다른 포트를 지정합니다.

날씨 데이터는 [Open-Meteo](https://open-meteo.com/)를 사용하고, 위치 검색에는
[OpenStreetMap](https://www.openstreetmap.org/) 데이터를 사용합니다.
