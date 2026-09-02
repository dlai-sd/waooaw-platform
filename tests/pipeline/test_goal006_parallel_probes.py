import os
import re
import subprocess
import textwrap
from pathlib import Path


WORKLOAD_MODULE = Path("infrastructure/terraform/phase2/modules/workload/main.tf")


def _probe_script() -> str:
    source = WORKLOAD_MODULE.read_text(encoding="utf-8")
    container = source.index('name    = "http-probes"')
    match = re.search(r"args = \[<<-EOT\n(?P<script>.*?)\n      EOT", source[container:], re.DOTALL)
    assert match is not None
    script = textwrap.dedent(match.group("script"))
    for name in (
        "web",
        "business_platform",
        "professional_runtime",
        "ai_runtime",
        "billing_engine",
        "identity_edge",
    ):
        script = script.replace(f"${{local.verification_urls.{name}}}", f"http://{name}")
    return script


def _run_probes(tmp_path: Path, failing_url_fragment: str) -> tuple[subprocess.CompletedProcess[str], str]:
    bin_directory = tmp_path / "bin"
    bin_directory.mkdir()
    probe_log = tmp_path / "probes.log"
    curl = bin_directory / "curl"
    curl.write_text(
        "#!/bin/sh\n"
        "for argument do url=$argument; done\n"
        'printf "%s\\n" "$url" >> "$PROBE_LOG"\n'
        'case "$url" in\n'
        '  *"$FAIL_URL_FRAGMENT"*) printf 503; exit 22 ;;\n'
        "  *) printf 200; exit 0 ;;\n"
        "esac\n",
        encoding="utf-8",
    )
    curl.chmod(0o755)
    sleep = bin_directory / "sleep"
    sleep.write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")
    sleep.chmod(0o755)
    environment = os.environ | {
        "PATH": f"{bin_directory}:{os.environ['PATH']}",
        "PROBE_LOG": str(probe_log),
        "FAIL_URL_FRAGMENT": failing_url_fragment,
    }
    result = subprocess.run(
        ["/bin/sh", "-c", _probe_script()],
        capture_output=True,
        check=False,
        env=environment,
        text=True,
        timeout=10,
    )
    return result, probe_log.read_text(encoding="utf-8")


def test_parallel_probes_succeed_only_when_all_probes_succeed(tmp_path: Path) -> None:
    result, probe_log = _run_probes(tmp_path, "never-match")

    assert result.returncode == 0
    assert "http://web" in probe_log
    assert "http://business_platform" in probe_log
    assert "http://professional_runtime" in probe_log
    assert "http://ai_runtime" in probe_log
    assert "http://billing_engine" in probe_log
    assert "http://identity_edge" in probe_log


def test_parallel_probes_wait_for_all_and_aggregate_failure(tmp_path: Path) -> None:
    result, probe_log = _run_probes(tmp_path, "business_platform")

    assert result.returncode == 1
    assert probe_log.count("http://business_platform") == 10
    assert "http://web" in probe_log
    assert "http://identity_edge" in probe_log