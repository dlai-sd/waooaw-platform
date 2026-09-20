#!/bin/sh
set -eu

input_dir=/workspace/test-results/wc104/c066
base_branch=$(cat "$input_dir/base-branch.txt")
pr_number=$(cat "$input_dir/pr-number.txt")
repository=$(cat "$input_dir/repository.txt")

test "$base_branch" = "main"
test -n "$pr_number"
test -n "$repository"
echo "C-066 PASS: CI is authorized; Founder review and merge remain mandatory."