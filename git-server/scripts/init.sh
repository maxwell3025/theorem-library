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

# Initialize repos with no dependencies or only base-math dependency
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

cd calculus-basics
sed -i "s/COMMIT_BASE_MATH/$COMMIT_BASE/g" lakefile.toml math-dependencies.json
git init
git config user.email "test@example.com"
git config user.name "Test User"
git add -A
git commit -m "Initial commit"
COMMIT_CALCULUS=$(git rev-parse HEAD)
git update-server-info
cd ..

cd topology-basics
sed -i "s/COMMIT_BASE_MATH/$COMMIT_BASE/g" lakefile.toml math-dependencies.json
git init
git config user.email "test@example.com"
git config user.name "Test User"
git add -A
git commit -m "Initial commit"
COMMIT_TOPOLOGY=$(git rev-parse HEAD)
git update-server-info
cd ..

# Initialize broken-syntax (no dependencies)
cd broken-syntax
git init
git config user.email "test@example.com"
git config user.name "Test User"
git add -A
git commit -m "Initial commit"
COMMIT_BROKEN_SYNTAX=$(git rev-parse HEAD)
git update-server-info
cd ..

# Initialize missing-lakefile (no dependencies, missing lakefile.toml)
cd missing-lakefile
git init
git config user.email "test@example.com"
git config user.name "Test User"
git add -A
git commit -m "Initial commit"
COMMIT_MISSING_LAKE=$(git rev-parse HEAD)
git update-server-info
cd ..

# Initialize invalid-json-deps (has base-math but JSON is broken)
cd invalid-json-deps
sed -i "s/COMMIT_BASE_MATH/$COMMIT_BASE/g" lakefile.toml math-dependencies.json
git init
git config user.email "test@example.com"
git config user.name "Test User"
git add -A
git commit -m "Initial commit"
COMMIT_INVALID_JSON=$(git rev-parse HEAD)
git update-server-info
cd ..

# Initialize circular dependency repos (they reference each other)
cd circular-dep-a
git init
git config user.email "test@example.com"
git config user.name "Test User"
git add -A
git commit -m "Initial commit"
COMMIT_CIRCULAR_A=$(git rev-parse HEAD)
git update-server-info
cd ..

cd circular-dep-b
git init
git config user.email "test@example.com"
git config user.name "Test User"
git add -A
git commit -m "Initial commit"
COMMIT_CIRCULAR_B=$(git rev-parse HEAD)
git update-server-info
cd ..

# Update circular dependencies with actual commit hashes
cd circular-dep-a
sed -i "s/COMMIT_CIRCULAR_DEP_B/$COMMIT_CIRCULAR_B/g" lakefile.toml math-dependencies.json
git add -A
git commit --amend -m "Initial commit with dependencies"
COMMIT_CIRCULAR_A=$(git rev-parse HEAD)
git update-server-info
cd ..

cd circular-dep-b
sed -i "s/COMMIT_CIRCULAR_DEP_A/$COMMIT_CIRCULAR_A/g" lakefile.toml math-dependencies.json
git add -A
git commit --amend -m "Initial commit with dependencies"
COMMIT_CIRCULAR_B=$(git rev-parse HEAD)
git update-server-info
cd ..

# Initialize broken-latex (no dependencies)
cd broken-latex
git init
git config user.email "test@example.com"
git config user.name "Test User"
git add -A
git commit -m "Initial commit"
COMMIT_BROKEN_LATEX=$(git rev-parse HEAD)
git update-server-info
cd ..

# Initialize nonexistent-dependency (references fake repo)
cd nonexistent-dependency
git init
git config user.email "test@example.com"
git config user.name "Test User"
git add -A
git commit -m "Initial commit"
COMMIT_NONEXISTENT=$(git rev-parse HEAD)
git update-server-info
cd ..

# Initialize empty-repo (no dependencies)
cd empty-repo
git init
git config user.email "test@example.com"
git config user.name "Test User"
git add -A
git commit -m "Initial commit"
COMMIT_EMPTY=$(git rev-parse HEAD)
git update-server-info
cd ..

# Initialize malformed-toml (no dependencies)
cd malformed-toml
git init
git config user.email "test@example.com"
git config user.name "Test User"
git add -A
git commit -m "Initial commit"
COMMIT_MALFORMED=$(git rev-parse HEAD)
git update-server-info
cd ..

# Initialize advanced-proofs with both commits
cd advanced-proofs
sed -i "s/COMMIT_BASE_MATH/$COMMIT_BASE/g" lakefile.toml math-dependencies.json
sed -i "s/COMMIT_ALGEBRA_THEOREMS/$COMMIT_ALGEBRA/g" lakefile.toml math-dependencies.json
git init
git config user.email "test@example.com"
git config user.name "Test User"
git add -A
git commit -m "Initial commit"
git update-server-info