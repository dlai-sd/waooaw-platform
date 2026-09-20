"""WC-104 hosted measurement acceptance tests."""

# Implements: work-contracts/WC-104-end-to-end-docker-runner-supply.md §7
# Constitutional basis: C-023, C-059, C-071, C-077, C-080

from validation_control.hosted_measurements import LIFECYCLES, RUNNERS, validate_hosted_samples


def passing_samples() -> list[dict[str, object]]:
    return [
        {
            "sample_id": f"{runner}-{lifecycle}-{sample}",
            "workflow_run": f"{lifecycle}-{sample}",
            "candidate_sha": "a" * 40,
            "runner_id": runner,
            "lifecycle": lifecycle,
            "runner_identity": "sha256:" + "b" * 64,
            "oci_digest": "sha256:" + "c" * 64,
            "scenario": "cache-miss" if sample == 0 else "source-only",
            "build_count": 1 if sample == 0 else 0,
            "duplicate_producers": 0,
            "consumer_build_count": 0,
            "consumer_digests": ["sha256:" + "c" * 64, "sha256:" + "c" * 64],
            "cache_source": "gha",
            "cache_source_verified": True,
            "build_duration_ms": 15_000 if sample == 0 else 0,
            "pull_duration_ms": 2_000 + sample,
            "cold_dependency_duration_ms": 20_000 + sample,
            "warm_dependency_duration_ms": 10_000 + sample,
            "startup_duration_ms": 1_000,
            "execute_duration_ms": 10_000,
            "focused_target_applies": True,
            "tests_selected": 2,
            "tests_executed": 2,
        }
        for runner in sorted(RUNNERS)
        for lifecycle in sorted(LIFECYCLES)
        for sample in range(3)
    ]


def test_three_samples_per_runner_and_lifecycle_pass() -> None:
    result = validate_hosted_samples(passing_samples())

    assert result["schema"] == "waooaw.wc104-hosted-measurements/v1"
    assert result["result"] == "PASS"
    assert result["sample_count"] == 24
    assert result["violations"] == []
    python_pr = result["measurements"]["python"]["pull_request"]
    assert python_pr["sample_count"] == 3
    assert python_pr["durations_ms"]["pull_duration_ms"] == {
        "median": 2_001,
        "range": [2_000, 2_002],
    }


def test_unsafe_reuse_and_incomplete_measurements_fail() -> None:
    samples = passing_samples()
    samples[0]["consumer_build_count"] = 1
    samples[1]["consumer_digests"] = ["sha256:a", "sha256:b"]
    samples[2]["tests_executed"] = 1
    samples = samples[:-1]

    result = validate_hosted_samples(samples)

    assert result["result"] == "FAIL"
    assert any("consumer builds" in violation for violation in result["violations"])
    assert any("disagree" in violation for violation in result["violations"])
    assert any("fewer than three" in violation for violation in result["violations"])


def test_repeated_or_unbound_samples_fail() -> None:
    samples = passing_samples()
    samples[1]["workflow_run"] = samples[0]["workflow_run"]
    samples[2]["candidate_sha"] = "not-a-commit"
    samples[3]["cache_source_verified"] = False

    result = validate_hosted_samples(samples)

    assert result["result"] == "FAIL"
    assert any("repeats workflow run" in violation for violation in result["violations"])
    assert any("invalid candidate commit" in violation for violation in result["violations"])
    assert any("verified GHA cache" in violation for violation in result["violations"])


def test_warm_median_must_be_faster_than_cold() -> None:
    samples = passing_samples()
    for sample in samples:
        sample["warm_dependency_duration_ms"] = sample["cold_dependency_duration_ms"]

    result = validate_hosted_samples(samples)

    assert result["result"] == "FAIL"
    assert len([violation for violation in result["violations"] if "warm median" in violation]) == 8
