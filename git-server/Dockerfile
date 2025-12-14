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

# Create startup script
RUN echo '#!/bin/sh' > /start.sh && \
    echo 'spawn-fcgi -s /var/run/fcgiwrap.socket -M 666 /usr/bin/fcgiwrap' >> /start.sh && \
    echo 'nginx -g "daemon off;"' >> /start.sh && \
    chmod +x /start.sh

# Expose port
EXPOSE 8000

# Run nginx with fcgiwrap for git-http-backend
CMD ["/start.sh"]
