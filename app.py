#!/usr/bin/env python3
"""오늘의 날씨를 검색하고 시각화하는 Flask 애플리케이션."""

import json
import os
from http import HTTPStatus
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode

from flask import Flask, jsonify, request, send_from_directory

from weather_today import WEATHER_CODES, fetch_json, fetch_today_weather


BASE_DIR = Path(__file__).resolve().parent
PUBLIC_DIR = BASE_DIR / "public"
GEOCODING_API_URL = "https://geocoding-api.open-meteo.com/v1/search"
NOMINATIM_API_URL = "https://nominatim.openstreetmap.org/search"

# Vercel이 자동으로 찾는 WSGI 진입점이다.
app = Flask(__name__, static_folder=None)


def search_location(query: str) -> dict:
    """장소 이름을 위도, 경도, 시간대로 변환한다."""
    params = {
        "q": query,
        "format": "jsonv2",
        "limit": 1,
        "accept-language": "ko",
    }
    results = fetch_json(
        f"{NOMINATIM_API_URL}?{urlencode(params)}",
        headers={"User-Agent": "TodayWeatherDemo/1.0"},
    )
    if results:
        result = results[0]
        display_parts = result.get("display_name", "").split(", ")
        return {
            "name": result.get("name") or display_parts[0],
            "admin1": display_parts[1] if len(display_parts) > 2 else "",
            "country": display_parts[-1] if len(display_parts) > 1 else "",
            "latitude": float(result["lat"]),
            "longitude": float(result["lon"]),
            "timezone": "auto",
        }

    # Nominatim에 결과가 없는 경우 Open-Meteo 지오코더로 한 번 더 찾는다.
    fallback_params = {
        "name": query,
        "count": 1,
        "language": "ko",
        "format": "json",
    }
    fallback_data = fetch_json(
        f"{GEOCODING_API_URL}?{urlencode(fallback_params)}"
    )
    fallback_results = fallback_data.get("results", [])
    if fallback_results:
        result = fallback_results[0]
        return {
            "name": result["name"],
            "admin1": result.get("admin1", ""),
            "country": result.get("country", ""),
            "latitude": result["latitude"],
            "longitude": result["longitude"],
            "timezone": result.get("timezone", "auto"),
        }

    raise ValueError("입력한 위치를 찾을 수 없습니다.")


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
            "temperature": weather["hourly_units"]["temperature_2m"],
            "windSpeed": weather["hourly_units"]["wind_speed_10m"],
        },
    }


@app.get("/")
def index():
    """로컬 Flask 실행 시 메인 페이지를 제공한다."""
    return send_from_directory(PUBLIC_DIR, "index.html")


@app.get("/<path:filename>")
def public_file(filename: str):
    """로컬 실행용 정적 파일 라우트다. Vercel에서는 public CDN이 처리한다."""
    return send_from_directory(PUBLIC_DIR, filename)


@app.get("/api/health")
def health():
    """배포 상태 확인용 경량 엔드포인트."""
    return jsonify({"status": "ok"})


@app.get("/api/weather")
def weather_api():
    """위치 이름을 받아 오늘 날씨를 JSON으로 반환한다."""
    location_query = request.args.get("location", "").strip()
    if not location_query:
        return jsonify({"error": "위치를 입력해 주세요."}), HTTPStatus.BAD_REQUEST
    if len(location_query) > 100:
        return (
            jsonify({"error": "위치 이름은 100자 이하로 입력해 주세요."}),
            HTTPStatus.BAD_REQUEST,
        )

    try:
        return jsonify(build_weather_response(location_query))
    except ValueError as error:
        return jsonify({"error": str(error)}), HTTPStatus.NOT_FOUND
    except (HTTPError, URLError, TimeoutError, json.JSONDecodeError, KeyError):
        return (
            jsonify(
                {
                    "error": (
                        "날씨 서비스에 연결하지 못했습니다. "
                        "잠시 후 다시 시도해 주세요."
                    )
                }
            ),
            HTTPStatus.BAD_GATEWAY,
        )


if __name__ == "__main__":
    port = int(os.environ.get("PORT", "8000"))
    app.run(host="127.0.0.1", port=port, debug=True)
