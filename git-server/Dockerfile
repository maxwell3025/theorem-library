FROM nginx:alpine

# Install git, fcgiwrap (for git-http-backend CGI), and spawn-fcgi
RUN apk add --no-cache git git-daemon fcgiwrap spawn-fcgi

# Copy test repositories
COPY repos/ /git-repos/

# Initialize git repositories and fix commit references
RUN cd /git-repos && \
    # First, initialize base-math (no dependencies)
    cd base-math && \
    git init && \
    git config user.email "test@example.com" && \
    git config user.name "Test User" && \
    git add -A && \
    git commit -m "Initial commit" && \
    COMMIT_BASE=$(git rev-parse HEAD) && \
    git update-server-info && \
    cd .. && \
    # Update algebra-theorems with base-math commit
    cd algebra-theorems && \
    sed -i "s/COMMIT_BASE_MATH/$COMMIT_BASE/g" lakefile.toml math-dependencies.json && \
    git init && \
    git config user.email "test@example.com" && \
    git config user.name "Test User" && \
    git add -A && \
    git commit -m "Initial commit" && \
    COMMIT_ALGEBRA=$(git rev-parse HEAD) && \
    git update-server-info && \
    cd .. && \
    # Update advanced-proofs with both commits
    cd advanced-proofs && \
    sed -i "s/COMMIT_BASE_MATH/$COMMIT_BASE/g" lakefile.toml math-dependencies.json && \
    sed -i "s/COMMIT_ALGEBRA_THEOREMS/$COMMIT_ALGEBRA/g" lakefile.toml math-dependencies.json && \
    git init && \
    git config user.email "test@example.com" && \
    git config user.name "Test User" && \
    git add -A && \
    git commit -m "Initial commit" && \
    git update-server-info

# Copy nginx configuration
COPY nginx.conf /etc/nginx/nginx.conf

# Create script to generate repository JSON with commits
RUN echo '#!/bin/sh' > /generate_repos.sh && \
    echo 'cd /git-repos' >> /generate_repos.sh && \
    echo 'count=0' >> /generate_repos.sh && \
    echo 'echo "{\"repositories\":[" > /tmp/repos.json' >> /generate_repos.sh && \
    echo 'first=true' >> /generate_repos.sh && \
    echo 'for repo in */; do' >> /generate_repos.sh && \
    echo '  repo_name=$(basename "$repo")' >> /generate_repos.sh && \
    echo '  if [ -d "$repo/.git" ]; then' >> /generate_repos.sh && \
    echo '    commit=$(cd "$repo" && git rev-parse HEAD)' >> /generate_repos.sh && \
    echo '    count=$((count + 1))' >> /generate_repos.sh && \
    echo '    if [ "$first" = true ]; then' >> /generate_repos.sh && \
    echo '      first=false' >> /generate_repos.sh && \
    echo '    else' >> /generate_repos.sh && \
    echo '      echo "," >> /tmp/repos.json' >> /generate_repos.sh && \
    echo '    fi' >> /generate_repos.sh && \
    echo '    echo "{\"name\":\"$repo_name\",\"url\":\"http://git-server:8000/$repo_name\",\"commit\":\"$commit\"}" >> /tmp/repos.json' >> /generate_repos.sh && \
    echo '  fi' >> /generate_repos.sh && \
    echo 'done' >> /generate_repos.sh && \
    echo 'echo "]}" >> /tmp/repos.json' >> /generate_repos.sh && \
    echo 'echo "{\"status\":\"healthy\",\"repositories\":$count}" > /tmp/health.json' >> /generate_repos.sh && \
    chmod +x /generate_repos.sh

# Create startup script
RUN echo '#!/bin/sh' > /start.sh && \
    echo '/generate_repos.sh' >> /start.sh && \
    echo 'spawn-fcgi -s /var/run/fcgiwrap.socket -M 666 /usr/bin/fcgiwrap' >> /start.sh && \
    echo 'nginx -g "daemon off;"' >> /start.sh && \
    chmod +x /start.sh

# Expose port
EXPOSE 8000

# Run nginx with fcgiwrap for git-http-backend
CMD ["/start.sh"]
