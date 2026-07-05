#!/usr/bin/env python3
"""weather_today.py를 이용해 오늘 시간별 기온 그래프를 저장한다."""

import argparse
import os
from datetime import datetime
from pathlib import Path

os.environ.setdefault(
    "MPLCONFIGDIR",
    str(Path(__file__).resolve().parent / ".matplotlib"),
)

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
from matplotlib import font_manager

from weather_today import fetch_today_weather


def configure_korean_font() -> None:
    """운영체제에서 사용 가능한 한글 폰트를 Matplotlib에 설정한다."""
    font_files = [
        Path("/System/Library/Fonts/AppleSDGothicNeo.ttc"),
        Path("/System/Library/Fonts/Supplemental/AppleGothic.ttf"),
        Path("/Library/Fonts/NanumGothic.ttf"),
    ]
    for font_file in font_files:
        if font_file.exists():
            font_manager.fontManager.addfont(font_file)
            font_name = font_manager.FontProperties(fname=font_file).get_name()
            plt.rcParams["font.family"] = font_name
            plt.rcParams["axes.unicode_minus"] = False
            return

    available_fonts = {font.name for font in font_manager.fontManager.ttflist}
    candidates = [
        "Apple SD Gothic Neo",
        "NanumGothic",
        "Arial Unicode MS",
        "Noto Sans CJK KR",
    ]

    for font_name in candidates:
        if font_name in available_fonts:
            plt.rcParams["font.family"] = font_name
            break

    plt.rcParams["axes.unicode_minus"] = False


def plot_today_temperature(data: dict, output_path: Path) -> Path:
    """시간별 기온과 체감온도를 그려 PNG 파일로 저장한다."""
    hourly = data["hourly"]
    times = [datetime.fromisoformat(value) for value in hourly["time"]]
    temperatures = hourly["temperature_2m"]
    apparent_temperatures = hourly["apparent_temperature"]
    precipitation = hourly["precipitation_probability"]

    plt.style.use("seaborn-v0_8-whitegrid")
    configure_korean_font()

    figure, temperature_axis = plt.subplots(figsize=(13, 7))
    figure.patch.set_facecolor("#f4f9fd")
    temperature_axis.set_facecolor("#ffffff")

    temperature_axis.fill_between(
        times,
        temperatures,
        min(temperatures) - 2,
        color="#4f8df7",
        alpha=0.12,
    )
    temperature_axis.plot(
        times,
        temperatures,
        color="#246bfd",
        linewidth=3,
        marker="o",
        markersize=5,
        label="기온",
    )
    temperature_axis.plot(
        times,
        apparent_temperatures,
        color="#f59e52",
        linewidth=2,
        linestyle="--",
        label="체감온도",
    )

    rain_axis = temperature_axis.twinx()
    rain_axis.bar(
        times,
        precipitation,
        width=0.025,
        color="#86c9ff",
        alpha=0.22,
        label="강수확률",
    )
    rain_axis.set_ylim(0, 120)
    rain_axis.set_ylabel("강수확률 (%)", color="#5483a8", labelpad=12)
    rain_axis.tick_params(axis="y", colors="#6f8193")
    rain_axis.grid(False)

    minimum_index = temperatures.index(min(temperatures))
    maximum_index = temperatures.index(max(temperatures))
    for index, label, vertical_offset in (
        (minimum_index, "최저", -26),
        (maximum_index, "최고", 13),
    ):
        temperature_axis.annotate(
            f"{label} {temperatures[index]:.1f}°C",
            (times[index], temperatures[index]),
            xytext=(0, vertical_offset),
            textcoords="offset points",
            ha="center",
            color="#1746a2",
            fontsize=10,
            fontweight="bold",
        )

    date_label = times[0].strftime("%Y년 %m월 %d일")
    temperature_axis.set_title(
        f"{date_label} 서울 시간별 기온",
        loc="left",
        fontsize=22,
        fontweight="bold",
        color="#17324d",
        pad=20,
    )
    temperature_axis.text(
        0,
        1.01,
        "Open-Meteo 오늘 예보 · 기온과 체감온도",
        transform=temperature_axis.transAxes,
        color="#6f8193",
        fontsize=10,
    )
    temperature_axis.set_ylabel("기온 (°C)", color="#17324d", labelpad=12)
    temperature_axis.set_xlabel("시간", color="#17324d", labelpad=12)
    temperature_axis.set_xticks(times[::2])
    temperature_axis.set_xticklabels(
        [time.strftime("%H시") for time in times[::2]],
        rotation=0,
    )
    temperature_axis.spines[["top", "right", "left", "bottom"]].set_visible(False)
    rain_axis.spines[["top", "right", "left", "bottom"]].set_visible(False)
    temperature_axis.grid(axis="x", visible=False)
    temperature_axis.grid(axis="y", color="#dce8f2", linestyle="--", alpha=0.8)

    temperature_lines, temperature_labels = (
        temperature_axis.get_legend_handles_labels()
    )
    rain_lines, rain_labels = rain_axis.get_legend_handles_labels()
    temperature_axis.legend(
        temperature_lines + rain_lines,
        temperature_labels + rain_labels,
        loc="upper right",
        frameon=False,
        ncol=3,
    )

    output_path = output_path.resolve()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    figure.tight_layout()
    figure.savefig(
        output_path,
        dpi=180,
        bbox_inches="tight",
        facecolor=figure.get_facecolor(),
    )
    plt.close(figure)
    return output_path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="오늘 시간별 기온을 Matplotlib 그래프로 저장합니다."
    )
    parser.add_argument("--latitude", type=float, default=37.5665, help="위도")
    parser.add_argument("--longitude", type=float, default=126.9780, help="경도")
    parser.add_argument("--timezone", default="Asia/Seoul", help="IANA 시간대")
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("today_temperature.png"),
        help="저장할 PNG 경로",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    weather = fetch_today_weather(
        latitude=args.latitude,
        longitude=args.longitude,
        timezone=args.timezone,
    )
    saved_path = plot_today_temperature(weather, args.output)
    print(f"그래프를 저장했습니다: {saved_path}")


if __name__ == "__main__":
    main()
