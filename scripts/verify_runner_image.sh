#!/bin/sh
# Constitutional basis: C-023, C-071, C-080

set -eu

if [ "$#" -ne 3 ]; then
  echo "usage: $0 <compose-profile> <runner-service> <expected-image-id>" >&2
  exit 2
fi

profile=$1
runner=$2
expected_image_id=$3

case "$expected_image_id" in
  sha256:????????????????????????????????????????????????????????????????) ;;
  *)
    echo "expected image identity must be a complete sha256 image ID" >&2
    exit 1
    ;;
esac

actual_image_id=$(scripts/runner_image_id.sh "$profile" "$runner")
if [ "$actual_image_id" != "$expected_image_id" ]; then
  echo "runner image identity mismatch for $runner" >&2
  echo "expected=$expected_image_id" >&2
  echo "actual=$actual_image_id" >&2
  exit 1
fi

printf 'verified_runner=%s image_id=%s\n' "$runner" "$actual_image_id"