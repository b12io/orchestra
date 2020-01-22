#!/usr/bin/env bash
# The script will create a branch with upgrading-dependencies-* prefix and will
# cherry-pick commits from branch names passed as arguments and push branch to origin.

set -e

[[ $# -eq 0 ]] && { echo "Usage: $0 BRANCH [BRANCH ...]"; exit 1; }

branches=("$@")
branch="upgrading-dependencies-$(date -I)"

git checkout -b ${branch} > /dev/null

for ((i=0; i < $#; i++))
{
    hash=$(git log origin/master..origin/${branches[$i]} --pretty=format:'%h')
    git cherry-pick ${hash} > /dev/null
    echo "Picking ${hash} from branch ${branches[$i]}->${branch}"
}

git push -u origin ${branch}
