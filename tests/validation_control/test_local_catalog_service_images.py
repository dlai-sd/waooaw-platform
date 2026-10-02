from pathlib import Path
from unittest.mock import call, patch

from validation_control.local_catalog_gate import ensure_service_image


def test_missing_service_image_is_pulled_before_identity_capture(tmp_path: Path) -> None:
    with (
        patch("validation_control.local_catalog_gate.image_id", side_effect=[None, "sha256:" + "a" * 64]) as inspect,
        patch("validation_control.local_catalog_gate.docker_executable", return_value="docker"),
        patch("validation_control.local_catalog_gate.subprocess.run") as run,
    ):
        run.return_value.returncode = 0

        resolved = ensure_service_image(tmp_path, "postgres@example")

    assert resolved == "sha256:" + "a" * 64
    assert inspect.call_args_list == [call("postgres@example", tmp_path), call("postgres@example", tmp_path)]
    run.assert_called_once_with(["docker", "pull", "postgres@example"], cwd=tmp_path, check=False)


def test_available_service_image_is_not_pulled(tmp_path: Path) -> None:
    image_identity = "sha256:" + "b" * 64
    with (
        patch("validation_control.local_catalog_gate.image_id", return_value=image_identity),
        patch("validation_control.local_catalog_gate.subprocess.run") as run,
    ):
        resolved = ensure_service_image(tmp_path, "postgres@example")

    assert resolved == image_identity
    run.assert_not_called()
