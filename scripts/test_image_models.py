"""이미지 생성 모델 품질 비교 테스트 스크립트.

같은 프롬프트를 여러 모델에 돌려 결과를 `logs/image_test_<타임스탬프>/` 폴더에 저장.
블로그 파이프라인(Gemini·WordPress)은 건드리지 않음. 순수 이미지 품질 비교용.

사용법:
    python scripts/test_image_models.py
        → 가장 최근 generation_*.md 로그의 IMAGE_PROMPT를 추출해 사용

    python scripts/test_image_models.py --prompt "A cinematic product shot of..."
        → 직접 프롬프트 지정

    python scripts/test_image_models.py --models flux-dev,sdxl
        → 특정 모델만 선택 (기본은 4개 전부)
"""

from __future__ import annotations

import argparse
import re
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

import requests

# scripts/ → 프로젝트 루트로 경로 보정
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from config.settings import load_settings  # noqa: E402


# 모델 카탈로그.
# - backend="hf"  : HuggingFace Inference Router (네트워크 호출)
# - backend="mflux": 로컬 MLX 실행 (mflux-generate CLI). M4 Max 128GB 환경 가정.
MODELS: dict[str, dict] = {
    "flux-schnell": {
        "backend": "hf",
        "id": "black-forest-labs/FLUX.1-schnell",
        "note": "HF API. 현재 사용 중 (baseline, 4-step 고속)",
    },
    "flux-dev": {
        "backend": "hf",
        "id": "black-forest-labs/FLUX.1-dev",
        "note": "HF API. FLUX 고품질 버전 (20~50 step, 비상용 라이선스)",
    },
    "sd35-large": {
        "backend": "hf",
        "id": "stabilityai/stable-diffusion-3.5-large",
        "note": "HF API. Stable Diffusion 3.5 Large (Community 라이선스)",
    },
    "sdxl": {
        "backend": "hf",
        "id": "stabilityai/stable-diffusion-xl-base-1.0",
        "note": "HF API. Stable Diffusion XL (OpenRAIL, 상업 OK)",
    },
    # --- 로컬 mflux ---
    # mflux 0.17.5 의 --base-model 만으로는 path resolution 이 None 이 되어 실패.
    # --model 에 HF repo 를 명시해야 정상 동작 (mflux 의 알려진 동작).
    "mflux-dev": {
        "backend": "mflux",
        "model": "black-forest-labs/FLUX.1-dev",
        "base_model": "dev",
        "steps": 50,
        "guidance": 3.5,
        "note": "로컬 mflux. FLUX.1-dev BF16 50-step. 첫 실행 시 ~24GB 다운로드. HF 라이선스 수락 필요",
    },
    "mflux-schnell": {
        "backend": "mflux",
        "model": "black-forest-labs/FLUX.1-schnell",
        "base_model": "schnell",
        "steps": 4,
        "guidance": 0.0,
        "note": "로컬 mflux. FLUX.1-schnell 4-step. 비-gated, HF schnell 과 1:1 비교용",
    },
}


def extract_prompt_from_latest_log() -> tuple[str, Path]:
    """가장 최근 generation_*.md 파일에서 `## 이미지 프롬프트` 섹션을 추출."""
    logs_dir = ROOT / "logs"
    files = sorted(logs_dir.glob("generation_*.md"), reverse=True)
    if not files:
        raise SystemExit(
            "logs/ 폴더에 generation_*.md 파일이 없습니다. "
            "먼저 python main.py <url> 로 한 번 생성하거나 --prompt 로 직접 지정하세요."
        )

    latest = files[0]
    text = latest.read_text(encoding="utf-8")

    # "## 이미지 프롬프트" 다음의 백틱 블록 또는 일반 단락 추출
    # 포맷 1: `단일 라인 프롬프트`
    # 포맷 2: 여러 줄
    match = re.search(
        r"^##\s*이미지 프롬프트\s*\n+(.+?)(?=\n##\s|\Z)",
        text,
        re.MULTILINE | re.DOTALL,
    )
    if not match:
        raise SystemExit(f"{latest.name} 에서 '## 이미지 프롬프트' 섹션을 찾지 못했습니다.")

    raw = match.group(1).strip()
    # 앞뒤 백틱 제거
    raw = raw.strip("`").strip()
    return raw, latest


def generate_with_hf(prompt: str, model_id: str, hf_token: str) -> bytes:
    """HuggingFace Inference Router로 이미지 생성."""
    url = f"https://router.huggingface.co/hf-inference/models/{model_id}"
    resp = requests.post(
        url,
        headers={"Authorization": f"Bearer {hf_token}"},
        json={"inputs": prompt},
        timeout=300,
    )
    if resp.status_code != 200:
        body = resp.text[:500]
        raise RuntimeError(f"HTTP {resp.status_code} from {model_id}: {body}")
    return resp.content


def generate_with_mflux(
    prompt: str,
    *,
    model: str,
    base_model: str,
    steps: int,
    guidance: float,
    out_path: Path,
    hf_token: str,
    width: int = 1024,
    height: int = 1024,
    seed: int = 42,
) -> bytes:
    """로컬 mflux CLI 로 이미지 생성. 결과 파일 경로 반환 + bytes 도 반환.

    HF_TOKEN 을 서브프로세스 환경에 명시적으로 주입한다 — gated 모델
    (FLUX.1-dev 등) 다운로드에 필요.
    """
    import os

    mflux_bin = ROOT / ".venv" / "bin" / "mflux-generate"
    if not mflux_bin.exists():
        raise RuntimeError(
            f"{mflux_bin} 가 없습니다. .venv 활성화 후 `uv pip install mflux` 실행."
        )

    cmd = [
        str(mflux_bin),
        "--model", model,
        "--base-model", base_model,
        "--prompt", prompt,
        "--steps", str(steps),
        "--guidance", str(guidance),
        "--width", str(width),
        "--height", str(height),
        "--seed", str(seed),
        "--output", str(out_path),
    ]
    env = os.environ.copy()
    if hf_token:
        env["HF_TOKEN"] = hf_token
    env.setdefault("HF_HUB_ENABLE_HF_TRANSFER", "1")

    # 첫 실행은 가중치 다운로드(~24GB) → 시간 넉넉히
    proc = subprocess.run(
        cmd, capture_output=True, text=True, timeout=3600, env=env
    )
    if proc.returncode != 0:
        raise RuntimeError(
            f"mflux-generate 실패 (rc={proc.returncode})\n"
            f"STDERR: {proc.stderr[-1500:]}"
        )
    if not out_path.exists():
        raise RuntimeError(f"mflux 가 출력을 만들지 않음: {out_path}")
    return out_path.read_bytes()


def main() -> None:
    parser = argparse.ArgumentParser(
        description="여러 이미지 모델을 같은 프롬프트로 테스트해 품질 비교",
    )
    parser.add_argument(
        "--prompt",
        type=str,
        default=None,
        help="직접 테스트할 영어 프롬프트. 미지정 시 최근 로그에서 추출",
    )
    parser.add_argument(
        "--models",
        type=str,
        default=",".join(MODELS.keys()),
        help=f"테스트할 모델 이름 (콤마 구분). 전체: {','.join(MODELS.keys())}",
    )
    args = parser.parse_args()

    # 프롬프트 확정
    if args.prompt:
        prompt = args.prompt.strip()
        prompt_source = "CLI argument"
    else:
        prompt, log_path = extract_prompt_from_latest_log()
        prompt_source = log_path.name

    # 모델 필터링
    selected_models = [m.strip() for m in args.models.split(",") if m.strip()]
    invalid = [m for m in selected_models if m not in MODELS]
    if invalid:
        raise SystemExit(f"알 수 없는 모델 이름: {invalid}. 사용 가능: {list(MODELS)}")

    # 설정 로드. HF 백엔드는 항상 토큰 필요. mflux 도 gated 모델 (FLUX.1-dev) 다운로드에 필요.
    settings = load_settings()
    needs_hf = any(MODELS[m]["backend"] in ("hf", "mflux") for m in selected_models)
    if needs_hf and not settings.hf_token:
        raise SystemExit(
            ".env에 HF_TOKEN이 없습니다. "
            "HF 백엔드 호출 또는 gated mflux 모델 다운로드에 필요합니다."
        )

    # 출력 디렉토리
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    out_dir = ROOT / "logs" / f"image_test_{ts}"
    out_dir.mkdir(parents=True, exist_ok=True)

    (out_dir / "prompt.txt").write_text(prompt, encoding="utf-8")

    print(f"\n프롬프트 출처: {prompt_source}")
    print(f"출력 폴더: {out_dir}")
    print(f"테스트 모델: {', '.join(selected_models)}")
    print("─" * 60)

    results: list[dict] = []
    for name in selected_models:
        info = MODELS[name]
        backend = info["backend"]
        note = info["note"]
        label = info.get("id") or f"mflux:{info.get('base_model')}"
        print(f"▶ [{name}] {label}")
        print(f"  ({note})")
        start = time.time()
        try:
            if backend == "hf":
                img_bytes = generate_with_hf(prompt, info["id"], settings.hf_token)
                out_path = out_dir / f"{name}.jpg"
                out_path.write_bytes(img_bytes)
            elif backend == "mflux":
                # mflux는 PNG 로 저장
                out_path = out_dir / f"{name}.png"
                img_bytes = generate_with_mflux(
                    prompt,
                    model=info["model"],
                    base_model=info["base_model"],
                    steps=info["steps"],
                    guidance=info["guidance"],
                    out_path=out_path,
                    hf_token=settings.hf_token,
                )
            else:
                raise RuntimeError(f"알 수 없는 backend: {backend}")
            elapsed = time.time() - start
            print(f"  ✓ 성공: {out_path.name} ({elapsed:.1f}s, {len(img_bytes):,} bytes)\n")
            results.append(
                {
                    "name": name,
                    "model_id": label,
                    "note": note,
                    "status": "OK",
                    "elapsed": elapsed,
                    "file": out_path.name,
                    "error": None,
                }
            )
        except Exception as e:
            elapsed = time.time() - start
            err = str(e)[:300]
            print(f"  ✗ 실패: {err}\n")
            results.append(
                {
                    "name": name,
                    "model_id": label,
                    "note": note,
                    "status": "FAIL",
                    "elapsed": elapsed,
                    "file": None,
                    "error": err,
                }
            )

    # 요약 리포트
    report_lines: list[str] = [
        f"# 이미지 모델 비교 테스트 — {ts}",
        "",
        f"- **프롬프트 출처**: {prompt_source}",
        f"- **테스트 모델**: {', '.join(selected_models)}",
        "",
        "## 프롬프트",
        "```",
        prompt,
        "```",
        "",
        "## 결과",
        "",
        "| 모델 | 상태 | 소요시간 | 파일 | 비고 |",
        "|---|---|---|---|---|",
    ]
    for r in results:
        status_emoji = "✅" if r["status"] == "OK" else "❌"
        file_cell = f"[{r['file']}]({r['file']})" if r["file"] else "—"
        err_note = f" {r['error']}" if r["error"] else ""
        report_lines.append(
            f"| {r['name']} | {status_emoji} {r['status']} | {r['elapsed']:.1f}s "
            f"| {file_cell} | {r['note']}{err_note} |"
        )

    report_lines += [
        "",
        "## 평가 가이드",
        "",
        "각 이미지를 열어서 아래 기준으로 비교하세요:",
        "1. **프롬프트 준수도** — 구도·피사체·스타일이 프롬프트 요구와 일치하는가",
        "2. **텍스트 렌더링** — 가짜 글자(gibberish) 최소화됐는가 (프롬프트가 'no text'면 정말 없는가)",
        "3. **스타일 선명성** — 단일 컨셉 유지됐는가, 섞인 느낌 없는가",
        "4. **세부 표현력** — 조명·질감·색감이 전문적이고 깔끔한가",
        "5. **AI 티** — 과장된 채도, 플라스틱 CGI 느낌, 부자연스러운 디테일이 적은가",
    ]

    (out_dir / "report.md").write_text("\n".join(report_lines), encoding="utf-8")
    print("─" * 60)
    print(f"리포트: {out_dir / 'report.md'}")
    print("\n평가 후 가장 품질 좋은 모델이 무엇인지 알려주세요.")


if __name__ == "__main__":
    main()
