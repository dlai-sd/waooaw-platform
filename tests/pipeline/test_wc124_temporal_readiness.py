"""Reproduce startup waiting clients without weakening the qualification window."""

import os
import re
import subprocess
import textwrap
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
SOURCE = (ROOT / "infrastructure/terraform/phase2/modules/workload/main.tf").read_text()
JOB = SOURCE.split('resource "azurerm_container_app_job" "temporal_startup_qualification"', 1)[1].split("\nresource ", 1)[0]


def script(container):
    block = JOB.split(f'name    = "{container}"', 1)[1]
    return textwrap.dedent(re.search(r"args = \[<<-EOT\n(.*?)\n\s*EOT", block, re.S).group(1))


@pytest.mark.parametrize("permanent,expected", [(False, 0), (True, 1)])
def test_actual_sampler_bounds_warmup_and_keeps_sixty_strict_samples(tmp_path, permanent, expected):
    commands = tmp_path / "bin"
    commands.mkdir()
    counter = tmp_path / "counter"
    for name, body in {
        "nc": "#!/bin/sh\nexit 0\n",
        "sleep": "#!/bin/sh\nexit 0\n",
        "tar": "#!/bin/sh\nexit 0\n",
        "psql": f"""#!/bin/sh
case "$*" in
  *'SHOW POOLS;'*)
    n=$(cat '{counter}' 2>/dev/null || echo 0)
    n=$((n+1)); echo "$n" > '{counter}'
    waiting=0
    if [ "$n" -le 2 ] || [ "{int(permanent)}" = 1 ]; then waiting=1; fi
    printf 'database,cl_waiting,maxwait\\nwaooaw_temporal,%s,0\\nwaooaw_temporal_visibility,0,0\\n' "$waiting"
    ;;
  *) echo 19 ;;
esac
""",
    }.items():
        target = commands / name
        target.write_text(body)
        target.chmod(0o755)
    samples = tmp_path / "samples"
    body = (
        script("pool-sampler")
        .replace("/tmp/pool-samples", str(samples))
        .replace("/tmp/temporal-exited", str(tmp_path / "exited"))
    )
    result = subprocess.run(
        ["sh", "-c", body],
        env={**os.environ, "PATH": f"{commands}:{os.environ['PATH']}", "POSTGRES_PWD": "fixture", "POSTGRES_SEEDS": "fixture"},
        capture_output=True,
        text=True,
        timeout=10,
    )
    assert result.returncode == expected, result.stderr
    if not permanent:
        assert len(list(samples.glob("warmup-*.csv"))) == 7
        assert len(list(samples.glob("pools-*.csv"))) == 60
        assert (samples / "sampler.done").exists()
    else:
        assert len(list(samples.glob("warmup-*.csv"))) == 30
        assert not list(samples.glob("pools-*.csv"))
        assert (samples / "sampler.failed").exists()


@pytest.mark.parametrize("bad_sample", [None, 1, 60])
def test_actual_controller_rejects_waiting_anywhere_in_strict_window(tmp_path, bad_sample):
    samples = tmp_path / "samples"
    samples.mkdir()
    for sample in range(1, 61):
        waiting = int(sample == bad_sample)
        (samples / f"pools-{sample}.csv").write_text(
            f"database,cl_waiting,maxwait\nwaooaw_temporal,{waiting},0\nwaooaw_temporal_visibility,0,0\n"
        )
        (samples / f"headroom-{sample}.txt").write_text("19\n")
    log = tmp_path / "temporal.log"
    log.write_text("")
    aggregation = script("temporal-startup-qualification").split("max_waiting=0", 1)[1]
    result = subprocess.run(
        ["bash", "-c", f"set -euo pipefail\nsamples='{samples}'\nlog='{log}'\nmax_waiting=0{aggregation}"],
        text=True,
        capture_output=True,
        timeout=10,
    )
    assert (result.returncode == 0) == (bad_sample is None)
    assert result.stdout.count("WC124_POOL_SAMPLE ") == 60
    assert ('"status":"passed"' in result.stdout) == (bad_sample is None)


def test_grpc_readiness_precedes_sampler_signal_and_diagnostics_are_supported():
    controller = script("temporal-startup-qualification")
    assert controller.index("temporal operator cluster health") < controller.index("nc -l -p 17302")
    assert 'tail -n 150 "$log"' in controller
    workflow = (ROOT / ".github/workflows/environment-deployment.yaml").read_text()
    step = workflow.split("- name: Qualify exact Temporal startup through PgBouncer", 1)[1].split("\n      - name:", 1)[0]
    assert "--tail 1000" not in step
    assert step.count("--tail 300") == 2
    assert "--container pool-sampler" in step
