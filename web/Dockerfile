FROM node:20-alpine AS dependencies
WORKDIR /app
RUN corepack enable && corepack prepare pnpm@9.15.9 --activate
COPY web/package.json web/pnpm-lock.yaml ./
RUN pnpm install --frozen-lockfile

FROM node:20-alpine AS build
WORKDIR /app
RUN corepack enable && corepack prepare pnpm@9.15.9 --activate
COPY --from=dependencies /app/node_modules ./node_modules
COPY web/ .
ENV BUILD_STANDALONE=true
RUN pnpm build

FROM node:20-alpine
RUN apk upgrade --no-cache \
	&& rm -rf /usr/local/lib/node_modules/npm \
	&& rm -f /usr/local/bin/npm /usr/local/bin/npx \
	&& addgroup -S waooaw \
	&& adduser -S waooaw -G waooaw
WORKDIR /app
COPY --from=build --chown=waooaw:waooaw /app/.next/standalone ./
COPY --from=build --chown=waooaw:waooaw /app/.next/static ./.next/static
COPY --from=build --chown=waooaw:waooaw /app/public ./public
USER waooaw
EXPOSE 3000
ENV HOSTNAME=0.0.0.0 PORT=3000
CMD ["node", "server.js"]