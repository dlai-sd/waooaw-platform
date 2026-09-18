#!/bin/sh
# Constitutional basis: C-023, C-071, C-080

set -eu

if [ "$#" -ne 2 ]; then
  echo "usage: $0 <compose-profile> <runner-service>" >&2
  exit 2
fi

profile=$1
runner=$2
image_ref=$(
  docker compose --profile "$profile" config --format json |
    jq -er --arg runner "$runner" '.services[$runner].image // (.name + "-" + $runner)'
)
docker image inspect --format '{{.Id}}' "$image_ref"