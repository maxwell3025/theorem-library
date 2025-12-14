#!/bin/sh
cd /git-repos
# First, initialize base-math (no dependencies)
cd base-math
git init
git config user.email "test@example.com"
git config user.name "Test User"
git add -A
git commit -m "Initial commit"
COMMIT_BASE=$(git rev-parse HEAD)
git update-server-info
cd ..
# Update algebra-theorems with base-math commit
cd algebra-theorems
sed -i "s/COMMIT_BASE_MATH/$COMMIT_BASE/g" lakefile.toml math-dependencies.json
git init
git config user.email "test@example.com"
git config user.name "Test User"
git add -A
git commit -m "Initial commit"
COMMIT_ALGEBRA=$(git rev-parse HEAD)
git update-server-info
cd ..
# Update advanced-proofs with both commits
cd advanced-proofs
sed -i "s/COMMIT_BASE_MATH/$COMMIT_BASE/g" lakefile.toml math-dependencies.json
sed -i "s/COMMIT_ALGEBRA_THEOREMS/$COMMIT_ALGEBRA/g" lakefile.toml math-dependencies.json
git init
git config user.email "test@example.com"
git config user.name "Test User"
git add -A
git commit -m "Initial commit"
git update-server-info