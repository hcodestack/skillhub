# Build the SPA, then ship a single Python image serving API + static UI.
FROM node:22-alpine AS webbuild
WORKDIR /app/web
COPY web/package.json web/pnpm-lock.yaml ./
RUN corepack enable && pnpm install --frozen-lockfile
COPY web/ .
RUN pnpm build

FROM python:3.12-slim
WORKDIR /app
COPY server/ server/
RUN pip install --no-cache-dir ./server
COPY --from=webbuild /app/web/dist /app/web/dist

ENV SKILLHUB_HOST=0.0.0.0 \
    SKILLHUB_PORT=8787 \
    SKILLHUB_STATIC=/app/web/dist \
    SKILLHUB_DB=/data/skillhub.db \
    SKILLHUB_LIBRARY_ROOT=/library
# Deliberately no SKILLHUB_LIBRARY_INDEX: unset means the hub scans /library
# for SKILL.md itself, which is the mode that works without any extra tooling.
# Setting it here forced index mode on every container, so a user who mounted a
# plain skills library got "index not readable" and an empty catalog. Point
# SKILLHUB_LIBRARY_INDEX at a file only if something already maintains one.

EXPOSE 8787
VOLUME /data
CMD ["skillhub-server"]
