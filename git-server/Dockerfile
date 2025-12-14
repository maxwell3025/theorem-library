FROM nginx:alpine

# Install git, fcgiwrap (for git-http-backend CGI), and spawn-fcgi
RUN apk add --no-cache git git-daemon fcgiwrap spawn-fcgi

COPY scripts/ /

COPY repos/ /git-repos/

RUN ./init.sh

COPY nginx.conf /etc/nginx/nginx.conf

EXPOSE 8000

CMD ["/start.sh"]
