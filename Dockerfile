FROM nginxinc/nginx-unprivileged:1.30.4-alpine-slim

LABEL org.opencontainers.image.source="https://github.com/sogis/datenportal-dokumentation"

USER root
RUN rm /docker-entrypoint.d/10-listen-on-ipv6-by-default.sh \
    && rm -rf /usr/share/nginx/html/*
USER 101

COPY nginx/default.conf /etc/nginx/conf.d/default.conf
COPY build/site/ /usr/share/nginx/html/
RUN test -s /usr/share/nginx/html/index.html \
    && test -s /usr/share/nginx/html/search-index.json

EXPOSE 8080
HEALTHCHECK --interval=10s --timeout=3s --start-period=5s --retries=3 \
    CMD wget -q -O /dev/null http://127.0.0.1:8080/index.html || exit 1
