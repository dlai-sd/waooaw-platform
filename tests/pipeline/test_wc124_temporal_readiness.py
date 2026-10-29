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


@pytest.mark.parametrize("permanent,headroom_error,expected", [(False, False, 0), (True, False, 1), (False, True, 2)])
@pytest.mark.parametrize("admission_busy", [False, True])
def test_actual_sampler_bounds_warmup_and_keeps_sixty_strict_samples(
    tmp_path, permanent, headroom_error, expected, admission_busy
):
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
    case "$*" in *'--host fixture '*) ;; *) exit 91 ;; esac
    n=$(cat '{counter}' 2>/dev/null || echo 0)
    n=$((n+1)); echo "$n" > '{counter}'
    if [ "$n" -le {1 + 2 * int(admission_busy)} ]; then
      active=0
      if [ "$n" -lt {1 + 2 * int(admission_busy)} ]; then active=4; fi
      printf 'database,cl_active,cl_waiting,sv_active,maxwait\\nwaooaw_temporal,%s,0,%s,0\\n' "$active" "$active"
      exit 0
    fi
    waiting=0
    if [ "$n" -le {3 + 2 * int(admission_busy)} ] || [ "{int(permanent)}" = 1 ]; then waiting=1; fi
    printf 'database,cl_waiting,maxwait\\nwaooaw_temporal,%s,0\\nwaooaw_temporal_visibility,0,0\\n' "$waiting"
    ;;
  *)
    case "$*" in *'--host direct '*) ;; *) exit 92 ;; esac
    test "$PGSSLMODE" = require || exit 93
    test "$PGCONNECT_TIMEOUT" = 5 || exit 94
    if [ "{int(headroom_error)}" = 1 ]; then echo "monitor unavailable" >&2; exit 2; fi
    echo 19 ;;
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
        env={
            **os.environ,
            "PATH": f"{commands}:{os.environ['PATH']}",
            "POSTGRES_PWD": "fixture",
            "POSTGRES_SEEDS": "fixture",
            "MONITOR_POSTGRES_HOST": "direct",
        },
        capture_output=True,
        text=True,
        timeout=10,
    )
    assert result.returncode == expected, result.stderr
    assert len(list(samples.glob("admission-*.csv"))) == 1 + 2 * int(admission_busy)
    if expected == 0:
        assert len(list(samples.glob("warmup-*.csv"))) == 7
        assert len(list(samples.glob("pools-*.csv"))) == 60
        assert (samples / "sampler.done").exists()
    elif permanent:
        assert len(list(samples.glob("warmup-*.csv"))) == 30
        assert not list(samples.glob("pools-*.csv"))
        assert (samples / "sampler.failed").exists()
    else:
        assert not (samples / "sampler.done").exists()
        assert (samples / "sampler.failed").read_text().strip() == "2"
        assert "phase=direct_headroom" in (samples / "sampler.log").read_text()
        assert "monitor unavailable" in (samples / "sampler.log").read_text()


def test_controller_surfaces_sampler_failure_diagnostics(tmp_path):
    (tmp_path / "sampler.failed").write_text("2\n")
    (tmp_path / "sampler.log").write_text("phase=direct_headroom\nmonitor unavailable\n")
    failure_check = script("temporal-startup-qualification").split('if [ -e "$samples/sampler.failed" ]; then', 1)[1]
    failure_check = 'if [ -e "$samples/sampler.failed" ]; then' + failure_check.split('test -e "$samples/sampler.done"', 1)[0]
    result = subprocess.run(
        ["bash", "-c", f"set -euo pipefail\nsamples='{tmp_path}'\n{failure_check}"],
        text=True,
        capture_output=True,
        timeout=10,
    )
    assert result.returncode == 1
    assert "sampler failed with status 2" in result.stderr
    assert "phase=direct_headroom" in result.stderr
    assert "monitor unavailable" in result.stderr


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


@pytest.mark.parametrize(
    "admission",
    [
        "database,cl_active,cl_waiting,sv_active\nwaooaw_temporal,4,0,4\n",
        "database,cl_active,cl_waiting,sv_active\nwaooaw_temporal,0,1,0\n",
        "database,cl_active,cl_waiting,sv_active\nwaooaw_temporal_visibility,1,0,1\n",
        "database,cl_active,cl_waiting,sv_active\nwaooaw_temporal,invalid,0,0\n",
        "database,cl_waiting\nwaooaw_temporal,0\n",
        "",
    ],
)
def test_actual_sampler_refuses_occupied_or_unproven_pools_before_admitting_startup(tmp_path, admission):
    commands = tmp_path / "bin"
    commands.mkdir()
    calls = tmp_path / "calls"
    for name, body in {
        "psql": f"#!/bin/sh\nprintf '%s' '{admission}'\n",
        "sleep": "#!/bin/sh\nexit 0\n",
        "tar": "#!/bin/sh\nexit 0\n",
        "nc": f'#!/bin/sh\necho "$*" >> "{calls}"\nexit 0\n',
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
        text=True,
        capture_output=True,
        timeout=10,
    )
    assert result.returncode == 1, result.stderr
    assert len(list(samples.glob("admission-*.csv"))) == 12
    assert not list(samples.glob("warmup-*.csv"))
    assert "refusing overlapping startup" in (samples / "sampler.log").read_text()
    assert "refusing overlapping startup" in result.stderr
    assert "-z" not in calls.read_text()


def test_controller_cannot_start_temporal_before_pool_admission():
    controller = script("temporal-startup-qualification")
    assert controller.index('test "$(cat /tmp/pool-admission)" = ready') < controller.index(
        "/etc/temporal/entrypoint.sh autosetup"
    )
