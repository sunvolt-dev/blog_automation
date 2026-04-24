from __future__ import annotations

import re
import subprocess
import tempfile
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Transcript:
    raw: str
    cleaned: str
    thumbnail_url: str


def clean_transcript(text: str) -> str:
    t = text.replace("\u00a0", " ")
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


def _get_thumbnail_url(youtube_url: str) -> str:
    """yt-dlp로 영상 썸네일 URL을 가져옵니다."""
    try:
        result = subprocess.run(
            ["yt-dlp", "--print", "thumbnail", "--no-download", youtube_url],
            capture_output=True,
            text=True,
            check=True,
        )
        return result.stdout.strip()
    except Exception:
        return ""


def _run_yt_dlp_subs(
    *,
    youtube_url: str,
    output_template: str,
    auto: bool,
    sub_langs: str,
) -> None:
    """yt-dlp로 자막 다운로드. 실패해도 예외 던지지 않음."""
    flag = "--write-auto-sub" if auto else "--write-sub"
    subprocess.run(
        [
            "yt-dlp",
            flag,
            "--sub-langs", sub_langs,
            "--sub-format", "vtt",
            "--skip-download",
            "--output", output_template,
            youtube_url,
        ],
        capture_output=True,
        check=False,
    )


def transcribe_from_youtube_url(youtube_url: str) -> Transcript:
    thumbnail_url = _get_thumbnail_url(youtube_url)

    with tempfile.TemporaryDirectory() as tmpdir:
        output_template = str(Path(tmpdir) / "subtitle")

        # 1차: 한국어·영어 자동 자막 (ko-KR, en-US 등 변형 포함 정규식)
        _run_yt_dlp_subs(
            youtube_url=youtube_url,
            output_template=output_template,
            auto=True,
            sub_langs="ko.*,en.*",
        )
        vtt_files = list(Path(tmpdir).glob("*.vtt"))

        # 2차: 한국어·영어 수동 자막 (변형 포함)
        if not vtt_files:
            _run_yt_dlp_subs(
                youtube_url=youtube_url,
                output_template=output_template,
                auto=False,
                sub_langs="ko.*,en.*",
            )
            vtt_files = list(Path(tmpdir).glob("*.vtt"))

        # 3차 폴백: 모든 언어의 자동 자막 시도 (일본어 등 그 외 언어 허용)
        if not vtt_files:
            _run_yt_dlp_subs(
                youtube_url=youtube_url,
                output_template=output_template,
                auto=True,
                sub_langs="all",
            )
            vtt_files = list(Path(tmpdir).glob("*.vtt"))

        # 4차 폴백: 모든 언어의 수동 자막 시도
        if not vtt_files:
            _run_yt_dlp_subs(
                youtube_url=youtube_url,
                output_template=output_template,
                auto=False,
                sub_langs="all",
            )
            vtt_files = list(Path(tmpdir).glob("*.vtt"))

        if not vtt_files:
            raise RuntimeError(
                "자막을 찾을 수 없습니다. 이 영상은 어떤 언어의 자막도 제공하지 않습니다."
            )

        # 선호 순: 한국어 > 영어 > 그 외 (알파벳 순)
        ko_files = sorted(f for f in vtt_files if ".ko" in f.name)
        en_files = sorted(f for f in vtt_files if ".en" in f.name)
        other_files = sorted(
            f for f in vtt_files if ".ko" not in f.name and ".en" not in f.name
        )
        vtt_file = (ko_files or en_files or other_files)[0]

        raw_text = vtt_file.read_text(encoding="utf-8")
        parsed = _parse_vtt(raw_text)
        cleaned = clean_transcript(parsed)

        return Transcript(raw=raw_text, cleaned=cleaned, thumbnail_url=thumbnail_url)
