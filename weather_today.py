#!/usr/bin/env python3
"""Open-Meteo에서 오늘의 시간별 날씨를 조회한다."""

import argparse
import json
import os
import ssl
import sys
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen


API_URL = "https://api.open-meteo.com/v1/forecast"

WEATHER_CODES = {
    0: "맑음",
    1: "대체로 맑음",
    2: "부분적으로 흐림",
    3: "흐림",
    45: "안개",
    48: "서리 안개",
    51: "약한 이슬비",
    53: "이슬비",
    55: "강한 이슬비",
    56: "약한 어는 이슬비",
    57: "강한 어는 이슬비",
    61: "약한 비",
    63: "비",
    65: "강한 비",
    66: "약한 어는 비",
    67: "강한 어는 비",
    71: "약한 눈",
    73: "눈",
    75: "강한 눈",
    77: "싸락눈",
    80: "약한 소나기",
    81: "소나기",
    82: "강한 소나기",
    85: "약한 눈 소나기",
    86: "강한 눈 소나기",
    95: "뇌우",
    96: "약한 우박을 동반한 뇌우",
    99: "강한 우박을 동반한 뇌우",
}


def create_ssl_context() -> ssl.SSLContext:
    """Python 설치의 CA 설정이 비어 있을 때 시스템 인증서를 사용한다."""
    default_paths = ssl.get_default_verify_paths()
    if default_paths.cafile or os.environ.get("SSL_CERT_FILE"):
        return ssl.create_default_context()

    for certificate_file in ("/etc/ssl/cert.pem", "/private/etc/ssl/cert.pem"):
        if os.path.exists(certificate_file):
            return ssl.create_default_context(cafile=certificate_file)

    return ssl.create_default_context()


def fetch_json(url: str, headers: dict[str, str] | None = None) -> dict:
    """HTTPS JSON API를 호출해 응답을 반환한다."""
    request = Request(url, headers=headers or {})
    with urlopen(request, timeout=10, context=create_ssl_context()) as response:
        return json.load(response)


def fetch_today_weather(latitude: float, longitude: float, timezone: str) -> dict:
    """지정한 위치의 오늘 시간별 예보를 반환한다."""
    params = {
        "latitude": latitude,
        "longitude": longitude,
        "hourly": ",".join(
            [
                "temperature_2m",
                "apparent_temperature",
                "relative_humidity_2m",
                "precipitation_probability",
                "weather_code",
                "wind_speed_10m",
            ]
        ),
        "current": ",".join(
            [
                "temperature_2m",
                "apparent_temperature",
                "relative_humidity_2m",
                "precipitation",
                "weather_code",
                "wind_speed_10m",
            ]
        ),
        "timezone": timezone,
        "forecast_days": 1,
    }

    request_url = f"{API_URL}?{urlencode(params)}"
    return fetch_json(request_url)


def print_hourly_weather(data: dict) -> None:
    """API 응답에서 시간별 날씨를 표 형태로 출력한다."""
    hourly = data["hourly"]

    print(f"위치: 위도 {data['latitude']}, 경도 {data['longitude']}")
    print(f"시간대: {data['timezone']}")
    print("-" * 87)
    print(
        f"{'시간':<18} {'날씨':<18} {'기온':>7} {'체감':>7} "
        f"{'습도':>7} {'강수확률':>9} {'풍속':>9}"
    )
    print("-" * 87)

    for index, time in enumerate(hourly["time"]):
        code = hourly["weather_code"][index]
        description = WEATHER_CODES.get(code, f"알 수 없음({code})")
        display_time = time.replace("T", " ")

        print(
            f"{display_time:<18} "
            f"{description:<18} "
            f"{hourly['temperature_2m'][index]:>6.1f}°C "
            f"{hourly['apparent_temperature'][index]:>6.1f}°C "
            f"{hourly['relative_humidity_2m'][index]:>6}% "
            f"{hourly['precipitation_probability'][index]:>8}% "
            f"{hourly['wind_speed_10m'][index]:>7.1f}km/h"
        )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Open-Meteo API로 오늘의 시간별 날씨를 조회합니다."
    )
    parser.add_argument("--latitude", type=float, default=37.5665, help="위도")
    parser.add_argument("--longitude", type=float, default=126.9780, help="경도")
    parser.add_argument(
        "--timezone",
        default="Asia/Seoul",
        help="IANA 시간대 이름 (기본값: Asia/Seoul)",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    try:
        weather = fetch_today_weather(
            latitude=args.latitude,
            longitude=args.longitude,
            timezone=args.timezone,
        )
        print_hourly_weather(weather)
    except (HTTPError, URLError, TimeoutError, json.JSONDecodeError, KeyError) as error:
        print(f"날씨 정보를 가져오지 못했습니다: {error}", file=sys.stderr)
        raise SystemExit(1) from error


if __name__ == "__main__":
    main()
