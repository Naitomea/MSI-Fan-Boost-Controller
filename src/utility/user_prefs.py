import json
from pathlib import Path
from typing import Any

from platformdirs import user_config_dir


class UserPrefs:
    _app_name: str | None = None
    _app_author: str | None = None

    _file_path: Path | None = None
    _data: dict[str, Any] = {}

    _initialized: bool = False
    _auto_save: bool = True

    @classmethod
    def init(
        cls,
        app_name: str,
        app_author: str | None = None,
        filename: str = "_userPrefs_.json",
        defaults: dict[str, Any] | None = None,
        auto_save: bool = True,
    ) -> None:
        cls._app_name = app_name
        cls._app_author = app_author
        cls._auto_save = auto_save

        config_dir = Path(user_config_dir(app_name, app_author))
        cls._file_path = config_dir / filename

        cls._data = {}

        if defaults:
            cls._data.update(defaults)

        cls.load(merge_with_current=True)

        cls._initialized = True

        if defaults and not cls._file_path.exists():
            cls.save()

    @classmethod
    def load(cls, merge_with_current: bool = False) -> None:
        cls._ensure_file_path()

        if not cls._file_path.exists():
            return

        try:
            loaded = json.loads(cls._file_path.read_text(encoding="utf-8"))

            if not isinstance(loaded, dict):
                return

            if merge_with_current:
                cls._data.update(loaded)
            else:
                cls._data = loaded

        except Exception as e:
            print(f"Failed to load user prefs: {e}", flush=True)

    @classmethod
    def save(cls) -> None:
        cls._ensure_file_path()

        cls._file_path.parent.mkdir(parents=True, exist_ok=True)

        temp_path = cls._file_path.with_suffix(".tmp")

        temp_path.write_text(
            json.dumps(cls._data, indent=4, ensure_ascii=False),
            encoding="utf-8",
        )

        temp_path.replace(cls._file_path)

    @classmethod
    def get(cls, key: str, default: Any = None) -> Any:
        cls._ensure_initialized()
        return cls._data.get(key, default)

    @classmethod
    def set(cls, key: str, value: Any, save: bool | None = None) -> None:
        cls._ensure_initialized()

        cls._data[key] = value

        should_save = cls._auto_save if save is None else save

        if should_save:
            cls.save()

    @classmethod
    def has(cls, key: str) -> bool:
        cls._ensure_initialized()
        return key in cls._data
    
    @classmethod
    def delete(cls, key: str, save: bool | None = None) -> None:
        cls._ensure_initialized()

        if key in cls._data:
            del cls._data[key]

        should_save = cls._auto_save if save is None else save

        if should_save:
            cls.save()

    @classmethod
    def clear(cls, save: bool | None = None) -> None:
        cls._ensure_initialized()

        cls._data.clear()

        should_save = cls._auto_save if save is None else save

        if should_save:
            cls.save()

    @classmethod
    def get_file_path(cls) -> Path:
        cls._ensure_file_path()
        return cls._file_path

    @classmethod
    def _ensure_initialized(cls) -> None:
        if not cls._initialized:
            raise RuntimeError("UserPrefs is not initialized. Call UserPrefs.init(...) first.")

    @classmethod
    def _ensure_file_path(cls) -> None:
        if cls._file_path is None:
            raise RuntimeError("UserPrefs file path is not set. Call UserPrefs.init(...) first.")

        