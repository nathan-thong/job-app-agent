import json
from pathlib import Path

from app.models.profile import Profile


PROFILE_PATH = Path(__file__).parents[1] / "data" / "profile.json"


def load_profile(path: Path = PROFILE_PATH) -> Profile:
    try:
        with path.open(encoding="utf-8") as profile_file:
            return Profile.model_validate(json.load(profile_file))
    except (OSError, json.JSONDecodeError, ValueError) as exc:
        raise RuntimeError(f"Profile data is missing or invalid: {path}") from exc
