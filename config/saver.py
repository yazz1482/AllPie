"""Safe, atomic persistence for AllPie configuration files."""

from __future__ import annotations

import json
import os
import shutil
import tempfile
from pathlib import Path
from typing import Any, Mapping, Optional

from ..core.validation import validate_config


class ConfigSaveError(OSError):
    """Raised when a configuration cannot be validated or safely saved."""


def save_config(
    config: Mapping[str, Any],
    path: Any,
    *,
    backup: bool = True,
    indent: int = 4,
) -> Path:
    """Validate and atomically save a config, optionally preserving a .bak.

    A failed validation or temporary-file write never replaces the active
    configuration. When a destination already exists, its previous contents
    are copied to ``<filename>.bak`` before the atomic replacement.
    """
    report = validate_config(dict(config))
    if not report.valid or report.config is None:
        details = "\n".join(str(issue) for issue in report.errors)
        raise ConfigSaveError(f"Refusing to save invalid AllPie configuration:\n{details}")

    destination = Path(path).expanduser()
    parent = destination.parent
    temporary_path: Optional[Path] = None

    try:
        parent.mkdir(parents=True, exist_ok=True)
        file_descriptor, temporary_name = tempfile.mkstemp(
            prefix=f".{destination.name}.",
            suffix=".tmp",
            dir=str(parent),
        )
        temporary_path = Path(temporary_name)

        with os.fdopen(file_descriptor, "w", encoding="utf-8", newline="\n") as output:
            json.dump(
                report.config,
                output,
                ensure_ascii=False,
                indent=indent,
                allow_nan=False,
            )
            output.write("\n")
            output.flush()
            os.fsync(output.fileno())

        backup_path = destination.with_name(destination.name + ".bak")
        if backup and destination.exists():
            shutil.copy2(destination, backup_path)

        os.replace(str(temporary_path), str(destination))
        temporary_path = None
        return destination
    except (OSError, TypeError, ValueError) as error:
        raise ConfigSaveError(f"Could not save AllPie configuration to '{destination}': {error}") from error
    finally:
        if temporary_path is not None:
            try:
                temporary_path.unlink(missing_ok=True)
            except OSError:
                pass
