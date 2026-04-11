import os
import re
import sys
from dataclasses import dataclass
from pathlib import Path


PACKAGE_ROOT = Path(__file__).resolve().parent
PROJECT_ROOT = PACKAGE_ROOT.parent
DEFAULT_MODEL = "gpt-5.4"
MODEL_PATTERN = re.compile(r"^gpt-[A-Za-z0-9][A-Za-z0-9._-]{0,62}$")


class ConfigError(RuntimeError):
    pass


@dataclass(frozen=True)
class Settings:
    api_key: str
    model: str
    env_path: Path | None


def _get_app_root() -> Path:
    # PyInstaller one-file apps extract Python files to a temp directory, so use the
    # executable location when running as a frozen app.
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return PROJECT_ROOT


APP_ROOT = _get_app_root()
ENV_KEY_PATTERN = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")


def _resolve_env_path() -> Path | None:
    override_path = os.getenv("FRIDGE_ENV_FILE", "").strip()
    if override_path:
        candidate = Path(override_path).expanduser()
        if not candidate.is_absolute():
            candidate = (APP_ROOT / candidate).resolve()
        else:
            candidate = candidate.resolve()

        if not candidate.is_file():
            raise ConfigError("FRIDGE_ENV_FILE이 존재하지 않는 파일을 가리키고 있습니다.")
        return candidate

    candidates = (
        APP_ROOT / "fridge.env",
        APP_ROOT / ".env",
        APP_ROOT / ".env" / ".env",
    )
    for candidate in candidates:
        if candidate.is_file():
            return candidate.resolve()

    return None


def _parse_env_line(raw_line: str, line_number: int, env_path: Path) -> tuple[str, str] | None:
    line = raw_line.strip()
    if not line or line.startswith("#"):
        return None

    if line.startswith("export "):
        line = line[7:].strip()

    if "=" not in line:
        raise ConfigError(f"{env_path}의 {line_number}번째 줄 형식이 잘못되었습니다.")

    key, value = line.split("=", 1)
    key = key.strip()
    value = value.strip()

    if not ENV_KEY_PATTERN.fullmatch(key):
        raise ConfigError(f"{env_path}의 {line_number}번째 줄 환경 변수 이름이 잘못되었습니다.")

    if len(value) >= 2 and value[0] == value[-1] and value[0] in {'"', "'"}:
        value = value[1:-1]
    elif " #" in value:
        value = value.split(" #", 1)[0].rstrip()

    return key, value


def _load_env_file(env_path: Path):
    for line_number, raw_line in enumerate(
        env_path.read_text(encoding="utf-8-sig").splitlines(),
        start=1,
    ):
        parsed = _parse_env_line(raw_line, line_number, env_path)
        if parsed is None:
            continue

        key, value = parsed
        os.environ.setdefault(key, value)


def load_settings() -> Settings:
    env_path = _resolve_env_path()
    if env_path is not None:
        _load_env_file(env_path)

    api_key = os.getenv("OPENAI_API_KEY", "").strip()
    if not api_key:
        default_path = APP_ROOT / "fridge.env"
        raise ConfigError(
            f"OPENAI_API_KEY가 없습니다. {default_path} 또는 .env 파일을 만들거나 FRIDGE_ENV_FILE을 설정해 주세요."
        )

    if any(char.isspace() for char in api_key):
        raise ConfigError("OPENAI_API_KEY에는 공백 문자가 들어갈 수 없습니다.")

    model = os.getenv("OPENAI_MODEL", DEFAULT_MODEL).strip()
    if not MODEL_PATTERN.fullmatch(model):
        raise ConfigError(
            "OPENAI_MODEL은 'gpt-'로 시작해야 하며 문자, 숫자, '.', '_' 또는 '-'만 포함할 수 있습니다."
        )

    return Settings(api_key=api_key, model=model, env_path=env_path)
