from __future__ import annotations

import logging
import os
import subprocess
import sys
import tempfile
import time
from pathlib import Path

logger = logging.getLogger(__name__)

# 프로젝트 루트 (.venv 위치 기준점)
_PROJECT_ROOT = Path(__file__).resolve().parent.parent

# mflux 0.17.5: --base-model 만 주면 path resolution 이 None 으로 끝나는 버그가 있어
# 반드시 --model 에 HF repo 또는 로컬 경로를 함께 명시한다.
_DEFAULT_MFLUX_BIN = str(_PROJECT_ROOT / ".venv" / "bin" / "mflux-generate")
_DEFAULT_MODEL = "black-forest-labs/FLUX.1-dev"
_DEFAULT_BASE_MODEL = "dev"
_DEFAULT_STEPS = 50
_DEFAULT_GUIDANCE = 3.5
_DEFAULT_WIDTH = 1024
_DEFAULT_HEIGHT = 1024
# 1회 호출 타임아웃 (초). 첫 실행 시 가중치 다운로드(~24GB)까지 포함되므로 넉넉하게.
_MFLUX_TIMEOUT_S = 3600


def _split_negative(prompt: str) -> tuple[str, str | None]:
    """LLM 이 만든 image_prompt 안에 'Negative: ...' 가 섞여 있으면 분리해 반환."""
    marker = "\nNegative:"
    if marker in prompt:
        pos, neg = prompt.split(marker, 1)
        return pos.strip(), neg.strip() or None
    return prompt.strip(), None


def _run_mflux(
    *,
    positive: str,
    negative: str | None,
    out_path: Path,
    seed: int | None,
) -> None:
    """mflux-generate 서브프로세스를 호출해 out_path 에 PNG 를 쓴다.

    환경변수로 모델/스텝/가이던스 등을 오버라이드할 수 있다.
    실패 시 RuntimeError. stderr 의 마지막 부분을 메시지에 포함.
    """
    mflux_bin = os.environ.get("MFLUX_BIN", _DEFAULT_MFLUX_BIN)
    if not Path(mflux_bin).exists():
        raise RuntimeError(
            f"mflux-generate 실행 파일을 찾지 못함: {mflux_bin}. "
            f"`uv pip install mflux` 또는 MFLUX_BIN 환경변수 확인."
        )

    model = os.environ.get("MFLUX_MODEL", _DEFAULT_MODEL)
    base_model = os.environ.get("MFLUX_BASE_MODEL", _DEFAULT_BASE_MODEL)
    steps = int(os.environ.get("MFLUX_STEPS", _DEFAULT_STEPS))
    guidance = float(os.environ.get("MFLUX_GUIDANCE", _DEFAULT_GUIDANCE))
    width = int(os.environ.get("MFLUX_WIDTH", _DEFAULT_WIDTH))
    height = int(os.environ.get("MFLUX_HEIGHT", _DEFAULT_HEIGHT))

    cmd: list[str] = [
        mflux_bin,
        "--model", model,
        "--base-model", base_model,
        "--prompt", positive,
        "--steps", str(steps),
        "--guidance", str(guidance),
        "--width", str(width),
        "--height", str(height),
        "--output", str(out_path),
    ]
    if seed is not None:
        cmd += ["--seed", str(seed)]
    # schnell 은 guidance=0 이라 negative-prompt 가 효과 없음. dev/그 외에서만 전달.
    if negative and base_model != "schnell":
        cmd += ["--negative-prompt", negative]

    # gated 모델 다운로드(첫 1회)에 HF_TOKEN 필요. 이미 받았으면 환경변수 없어도 OK.
    env = os.environ.copy()
    env.setdefault("HF_HUB_ENABLE_HF_TRANSFER", "1")

    logger.info(
        "mflux 호출: model=%s base=%s steps=%d guidance=%.1f size=%dx%d",
        model, base_model, steps, guidance, width, height,
    )
    proc = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        timeout=_MFLUX_TIMEOUT_S,
        env=env,
    )
    if proc.returncode != 0:
        tail = (proc.stderr or proc.stdout or "")[-1500:]
        raise RuntimeError(f"mflux-generate 실패 (rc={proc.returncode}): {tail}")
    # mflux 0.17.5: --output foo.png 를 줘도 실제로는 foo_1.png 로 저장하는 경우가 있다.
    # 원본 경로가 비어있으면 같은 디렉토리에서 stem 으로 시작하는 PNG 를 찾아 옮긴다.
    if not out_path.exists() or out_path.stat().st_size == 0:
        candidates = sorted(
            out_path.parent.glob(out_path.stem + "_*" + out_path.suffix),
            key=lambda p: p.stat().st_mtime,
            reverse=True,
        )
        recovered = next((p for p in candidates if p.stat().st_size > 0), None)
        if recovered is None:
            raise RuntimeError(f"mflux 가 빈 출력을 생성: {out_path}")
        recovered.replace(out_path)


def generate_and_upload_image(
    prompt: str,
    *,
    hf_token: str,  # noqa: ARG001 — 시그니처 호환용. 로컬 mflux 는 매 호출에 토큰 불필요
    wp_base_url: str,
    wp_username: str,
    wp_password: str,
    max_attempts: int = 3,
) -> int:
    """로컬 mflux (FLUX.1-dev BF16, 기본 50-step) 로 이미지를 생성하고
    WordPress 에 업로드한 뒤 media ID 를 반환한다.

    - 첫 호출 시 ~24GB 가중치를 HF 캐시로 한 번 받는다 (HF_TOKEN 필요).
    - 이후 호출은 완전 오프라인. 매 호출 1024×1024 50-step 생성 ~60–120s @ M4 Max.
    - LLM 출력 프롬프트에 'Negative: ...' 섹션이 있으면 자동 분리해 mflux 에 전달.
    """
    from core.wordpress import upload_media_from_bytes

    positive, negative = _split_negative(prompt)
    if negative:
        logger.info("이미지 프롬프트에서 negative 섹션 분리 (%d chars)", len(negative))

    last_error: Exception | None = None
    for attempt in range(1, max_attempts + 1):
        # 매 시도마다 새 임시파일 (mflux 가 기존 파일에 덮어쓰는 동작 의존하지 않게)
        tmp = tempfile.NamedTemporaryFile(
            suffix=".png", prefix="mflux_", delete=False
        )
        tmp.close()
        out_path = Path(tmp.name)
        try:
            _run_mflux(
                positive=positive,
                negative=negative,
                out_path=out_path,
                seed=None,  # 매 호출 다른 시드 (mflux 가 자동)
            )
            image_data = out_path.read_bytes()
            return upload_media_from_bytes(
                wp_base_url=wp_base_url,
                wp_username=wp_username,
                wp_password=wp_password,
                image_data=image_data,
                mime_type="image/png",
            )
        except subprocess.TimeoutExpired as e:
            last_error = e
            logger.warning(
                "mflux 타임아웃 (attempt %d/%d, %ds 초과)",
                attempt, max_attempts, _MFLUX_TIMEOUT_S,
            )
        except Exception as e:
            last_error = e
            wait = min(2**attempt, 30)
            logger.warning(
                "mflux 호출 실패 (attempt %d/%d, %ds 후 재시도): %s",
                attempt, max_attempts, wait, e,
            )
            time.sleep(wait)
        finally:
            try:
                out_path.unlink(missing_ok=True)
                for leftover in out_path.parent.glob(out_path.stem + "_*" + out_path.suffix):
                    leftover.unlink(missing_ok=True)
            except OSError:
                pass

    raise RuntimeError(
        f"mflux 이미지 생성 실패 ({max_attempts}회 재시도 후): {last_error}"
    )


# 모듈 단독 실행 시 간단 스모크 테스트 (WordPress 업로드 없이 PNG 만 생성)
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    test_prompt = sys.argv[1] if len(sys.argv) > 1 else (
        "A cinematic product shot of a modern lithium-ion battery on a clean white "
        "studio background with soft rim lighting, professional advertising style, "
        "high detail, 4K.\nNegative: text, watermark, blurry"
    )
    pos, neg = _split_negative(test_prompt)
    out = Path("/tmp/mflux_smoke.png")
    _run_mflux(positive=pos, negative=neg, out_path=out, seed=42)
    print(f"OK: {out} ({out.stat().st_size:,} bytes)")
