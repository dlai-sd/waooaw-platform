#!/bin/sh
set -eu

repository=$(git rev-parse --show-toplevel)
git config core.hooksPath "$repository/.githooks"
printf 'Git hooks installed from %s/.githooks\n' "$repository"