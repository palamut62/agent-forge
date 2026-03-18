"""Load and merge YAML profiles."""

import yaml
from pathlib import Path
from .schema import ProfileSchema

BUILTIN_DIR = Path(__file__).parent


def get_builtin_profiles_dir() -> Path:
    return BUILTIN_DIR


def list_profiles(extra_dirs: list[Path] | None = None) -> list[str]:
    """Mevcut profil isimlerini listele."""
    names = []
    dirs = [BUILTIN_DIR] + (extra_dirs or [])
    for d in dirs:
        for f in d.glob("*.yaml"):
            names.append(f.stem)
    return sorted(set(names))


def _find_profile_file(name: str, extra_dirs: list[Path] | None = None) -> Path:
    dirs = [BUILTIN_DIR] + (extra_dirs or [])
    for d in dirs:
        p = d / f"{name}.yaml"
        if p.exists():
            return p
    raise FileNotFoundError(f"Profil bulunamadi: {name}")


def load_profile(name: str, extra_dirs: list[Path] | None = None) -> ProfileSchema:
    """Profili yukle, extends varsa parent ile birlestir."""
    path = _find_profile_file(name, extra_dirs)
    data = yaml.safe_load(path.read_text(encoding="utf-8"))

    extends = data.get("extends")
    if extends:
        parent = load_profile(extends, extra_dirs)
        data = _merge_profiles(parent.model_dump(), data)

    return ProfileSchema(**data)


def _merge_profiles(parent: dict, child: dict) -> dict:
    """Child, parent'in ustune yazilir. Listeler birlestirilir."""
    merged = dict(parent)
    for key, value in child.items():
        if key == "extends":
            continue
        if isinstance(value, list) and isinstance(merged.get(key), list):
            existing_names = {
                item.get("name") if isinstance(item, dict) else item for item in value
            }
            parent_items = [
                item
                for item in merged[key]
                if (item.get("name") if isinstance(item, dict) else item) not in existing_names
            ]
            merged[key] = parent_items + value
        elif isinstance(value, dict) and isinstance(merged.get(key), dict):
            merged[key] = {**merged[key], **value}
        else:
            merged[key] = value
    return merged
