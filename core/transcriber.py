from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Callable

import requests
from yt_dlp import YoutubeDL


@dataclass(frozen=True)
class Transcript:
    raw: str
    cleaned: str
    thumbnail_url: str


def clean_transcript(text: str) -> str:
    t = text.replace(" ", " ")
    t = re.sub(r"[ \t]+", " ", t)
    t = re.sub(r"\n{3,}", "\n\n", t)
    return t.strip()


def _parse_vtt(vtt_text: str) -> str:
    """VTT 자막 파일에서 순수 텍스트만 추출합니다."""
    lines = vtt_text.splitlines()
    result = []
    prev_line = None

    for line in lines:
        line = line.strip()
        if line.startswith("WEBVTT") or line.startswith("Kind:") or line.startswith("Language:"):
            continue
        if "-->" in line:
            continue
        if not line:
            continue
        if re.match(r"^\d+$", line):
            continue
        # HTML 태그 제거 (예: <c>, <00:00:00.000>)
        line = re.sub(r"<[^>]+>", "", line).strip()
        if not line:
            continue
        # 연속 중복 제거 (유튜브 자동 자막 특성)
        if line != prev_line:
            result.append(line)
            prev_line = line

    return " ".join(result)


def _find_vtt_url(captions: dict, lang_filter: Callable[[str], bool]) -> str | None:
    """captions 딕셔너리에서 lang_filter 가 매치하는 첫 vtt URL 반환."""
    if not captions:
        return None
    for lang, items in captions.items():
        if not lang_filter(lang):
            continue
        for item in items or []:
            if item.get("ext") == "vtt" and item.get("url"):
                return item["url"]
    return None


def _select_caption_url(info: dict) -> str | None:
    """yt-dlp info dict 에서 자막 URL 선택.

    우선순위 (원본 CLI 호출 시맨틱과 동일):
      1) ko/en 자동 자막 (ko 우선)
      2) ko/en 수동 자막 (ko 우선)
      3) 임의 언어 자동 자막
      4) 임의 언어 수동 자막
    """
    auto = info.get("automatic_captions") or {}
    manual = info.get("subtitles") or {}
    is_ko: Callable[[str], bool] = lambda l: l.startswith("ko")
    is_en: Callable[[str], bool] = lambda l: l.startswith("en")
    any_lang: Callable[[str], bool] = lambda l: True

    for caps in (auto, manual):
        for filt in (is_ko, is_en):
            url = _find_vtt_url(caps, filt)
            if url:
                return url

    for caps in (auto, manual):
        url = _find_vtt_url(caps, any_lang)
        if url:
            return url

    return None


def transcribe_from_youtube_url(youtube_url: str) -> Transcript:
    ydl_opts = {
        "skip_download": True,
        "quiet": True,
        "no_warnings": True,
    }
    with YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(youtube_url, download=False)

    thumbnail_url = info.get("thumbnail", "") or ""

    sub_url = _select_caption_url(info)
    if not sub_url:
        raise RuntimeError(
            "자막을 찾을 수 없습니다. 이 영상은 어떤 언어의 자막도 제공하지 않습니다."
        )

    resp = requests.get(sub_url, timeout=30)
    resp.raise_for_status()
    raw_text = resp.text
    parsed = _parse_vtt(raw_text)
    cleaned = clean_transcript(parsed)

    return Transcript(raw=raw_text, cleaned=cleaned, thumbnail_url=thumbnail_url)
