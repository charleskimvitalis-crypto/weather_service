#!/usr/bin/env python3
"""오늘의 날씨를 검색하고 시각화하는 소형 웹 서버."""

import argparse
import json
import mimetypes
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import parse_qs, urlencode, urlparse

from weather_today import WEATHER_CODES, fetch_json, fetch_today_weather


BASE_DIR = Path(__file__).resolve().parent
STATIC_DIR = BASE_DIR / "static"
GEOCODING_API_URL = "https://geocoding-api.open-meteo.com/v1/search"
NOMINATIM_API_URL = "https://nominatim.openstreetmap.org/search"


def search_location(query: str) -> dict:
    """장소 이름을 위도, 경도, 시간대로 변환한다."""
    params = {
        "name": query,
        "count": 1,
        "language": "ko",
        "format": "json",
    }
    data = fetch_json(f"{GEOCODING_API_URL}?{urlencode(params)}")
    results = data.get("results", [])
    if results:
        result = results[0]
        return {
            "name": result["name"],
            "admin1": result.get("admin1", ""),
            "country": result.get("country", ""),
            "latitude": result["latitude"],
            "longitude": result["longitude"],
            "timezone": result.get("timezone", "auto"),
        }

    # Open-Meteo 지오코더가 한글 검색어를 찾지 못하는 경우를 보완한다.
    fallback_params = {
        "q": query,
        "format": "jsonv2",
        "limit": 1,
        "accept-language": "ko",
    }
    fallback_results = fetch_json(
        f"{NOMINATIM_API_URL}?{urlencode(fallback_params)}",
        headers={"User-Agent": "TodayWeatherDemo/1.0"},
    )
    if not fallback_results:
        raise ValueError("입력한 위치를 찾을 수 없습니다.")

    result = fallback_results[0]
    display_parts = result.get("display_name", "").split(", ")
    return {
        "name": result.get("name") or display_parts[0],
        "admin1": display_parts[1] if len(display_parts) > 2 else "",
        "country": display_parts[-1] if len(display_parts) > 1 else "",
        "latitude": float(result["lat"]),
        "longitude": float(result["lon"]),
        "timezone": "auto",
    }


def build_weather_response(query: str) -> dict:
    """검색된 장소와 오늘 날씨를 브라우저용 형태로 조합한다."""
    location = search_location(query)
    weather = fetch_today_weather(
        latitude=location["latitude"],
        longitude=location["longitude"],
        timezone=location["timezone"],
    )
    location["timezone"] = weather["timezone"]

    current = weather["current"]
    hourly = weather["hourly"]
    hourly_rows = []
    for index, time in enumerate(hourly["time"]):
        code = hourly["weather_code"][index]
        hourly_rows.append(
            {
                "time": time,
                "temperature": hourly["temperature_2m"][index],
                "apparentTemperature": hourly["apparent_temperature"][index],
                "humidity": hourly["relative_humidity_2m"][index],
                "precipitationProbability": hourly[
                    "precipitation_probability"
                ][index],
                "windSpeed": hourly["wind_speed_10m"][index],
                "weatherCode": code,
                "description": WEATHER_CODES.get(code, "알 수 없음"),
            }
        )

    current_code = current["weather_code"]
    return {
        "location": location,
        "current": {
            "time": current["time"],
            "temperature": current["temperature_2m"],
            "apparentTemperature": current["apparent_temperature"],
            "humidity": current["relative_humidity_2m"],
            "precipitation": current["precipitation"],
            "windSpeed": current["wind_speed_10m"],
            "weatherCode": current_code,
            "description": WEATHER_CODES.get(current_code, "알 수 없음"),
        },
        "hourly": hourly_rows,
        "units": {
            "temperature": hourly["temperature_2m"][0] is not None
            and weather["hourly_units"]["temperature_2m"],
            "windSpeed": weather["hourly_units"]["wind_speed_10m"],
        },
    }


class WeatherRequestHandler(BaseHTTPRequestHandler):
    """정적 파일과 날씨 JSON API를 제공한다."""

    def do_GET(self) -> None:
        parsed = urlparse(self.path)
        if parsed.path == "/api/weather":
            self.serve_weather_api(parse_qs(parsed.query))
            return

        self.serve_static_file(parsed.path)

    def serve_weather_api(self, query_params: dict[str, list[str]]) -> None:
        location_query = query_params.get("location", [""])[0].strip()
        if not location_query:
            self.send_json(
                {"error": "위치를 입력해 주세요."},
                status=HTTPStatus.BAD_REQUEST,
            )
            return
        if len(location_query) > 100:
            self.send_json(
                {"error": "위치 이름은 100자 이하로 입력해 주세요."},
                status=HTTPStatus.BAD_REQUEST,
            )
            return

        try:
            payload = build_weather_response(location_query)
            self.send_json(payload)
        except ValueError as error:
            self.send_json({"error": str(error)}, status=HTTPStatus.NOT_FOUND)
        except (HTTPError, URLError, TimeoutError, json.JSONDecodeError, KeyError):
            self.send_json(
                {"error": "날씨 서비스에 연결하지 못했습니다. 잠시 후 다시 시도해 주세요."},
                status=HTTPStatus.BAD_GATEWAY,
            )

    def serve_static_file(self, request_path: str) -> None:
        relative_path = "index.html" if request_path == "/" else request_path.lstrip("/")
        file_path = (STATIC_DIR / relative_path).resolve()

        try:
            file_path.relative_to(STATIC_DIR.resolve())
        except ValueError:
            self.send_error(HTTPStatus.NOT_FOUND)
            return

        if not file_path.is_file():
            self.send_error(HTTPStatus.NOT_FOUND)
            return

        content_type, _ = mimetypes.guess_type(file_path.name)
        body = file_path.read_bytes()
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", f"{content_type or 'application/octet-stream'}; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def send_json(
        self, payload: dict, status: HTTPStatus = HTTPStatus.OK
    ) -> None:
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, format: str, *args: object) -> None:
        print(f"[weather-web] {self.address_string()} - {format % args}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="날씨 검색 웹 서버를 실행합니다.")
    parser.add_argument("--host", default="127.0.0.1", help="바인딩할 호스트")
    parser.add_argument("--port", type=int, default=8000, help="사용할 포트")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    server = ThreadingHTTPServer((args.host, args.port), WeatherRequestHandler)
    print(f"날씨 웹페이지: http://{args.host}:{args.port}")
    print("종료하려면 Ctrl+C를 누르세요.")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n서버를 종료합니다.")
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
