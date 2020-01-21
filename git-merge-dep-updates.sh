#!/usr/bin/env bash
set -e

branches=("$@")
branch="upgrading-dependencies-$(date -I)"

git checkout -b ${branch} > /dev/null

for ((i=0; i < $#; i++))
{
    hash=$(git log origin/master..origin/${branches[$i]} --pretty=format:'%h')
    git cherry-pick ${hash} > /dev/null
    echo "Picking ${hash} from branch ${branches[$i]}->${branch}"
}
