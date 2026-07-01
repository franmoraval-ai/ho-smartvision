#!/usr/bin/env python3
"""Resuelve la URL HLS en vivo de un video de YouTube y la imprime como fuente go2rtc.

Uso (lo invoca go2rtc mediante la fuente `echo:`):
    py yt_source.py <YOUTUBE_VIDEO_ID_O_URL>

Imprime una línea tipo:
    ffmpeg:https://...m3u8#video=h264

go2rtc toma esa salida como origen y transcodifica a H264 limpio para WebRTC/MSE.
Solo debe usarse con transmisiones PÚBLICAS que el autor publica abiertamente.
"""
import shutil
import subprocess
import sys


def find_yt_dlp() -> list[str]:
    exe = shutil.which("yt-dlp")
    if exe:
        return [exe]
    # Fallback: módulo de Python (lanzador de Windows `py`).
    return [sys.executable or "py", "-m", "yt_dlp"]


def main() -> int:
    if len(sys.argv) < 2:
        print("falta el id/url de YouTube", file=sys.stderr)
        return 2

    arg = sys.argv[1]
    url = arg if arg.startswith("http") else f"https://www.youtube.com/watch?v={arg}"

    cmd = find_yt_dlp() + [
        "-f",
        "best[protocol=m3u8_native]/best",
        "-g",
        url,
    ]
    out = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
    hls = out.stdout.strip().splitlines()
    if out.returncode != 0 or not hls:
        sys.stderr.write(out.stderr)
        return 1

    # Transcodifica a H264 limpio para que reproduzca fluido en el navegador.
    print(f"ffmpeg:{hls[0]}#video=h264")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
