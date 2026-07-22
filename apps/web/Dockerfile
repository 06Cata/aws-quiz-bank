FROM node:22-alpine AS dependencies

WORKDIR /app
COPY package.json package-lock.json ./
COPY apps/web/package.json ./apps/web/package.json
RUN npm ci

FROM node:22-alpine AS builder

WORKDIR /app
COPY --from=dependencies /app/node_modules ./node_modules
COPY . .

ARG NEXT_PUBLIC_SUPABASE_URL
ARG NEXT_PUBLIC_SUPABASE_ANON_KEY
ARG NEXT_PUBLIC_API_BASE_URL
ARG NEXT_PUBLIC_APP_URL

# Compose only interpolates `.env` automatically. Keep empty build arguments from
# overriding apps/web/.env.local, while still allowing deployment platforms to
# inject explicit public settings during the image build.
RUN if [ -n "$NEXT_PUBLIC_SUPABASE_URL" ]; then export NEXT_PUBLIC_SUPABASE_URL; else unset NEXT_PUBLIC_SUPABASE_URL; fi \
  && if [ -n "$NEXT_PUBLIC_SUPABASE_ANON_KEY" ]; then export NEXT_PUBLIC_SUPABASE_ANON_KEY; else unset NEXT_PUBLIC_SUPABASE_ANON_KEY; fi \
  && if [ -n "$NEXT_PUBLIC_API_BASE_URL" ]; then export NEXT_PUBLIC_API_BASE_URL; else unset NEXT_PUBLIC_API_BASE_URL; fi \
  && if [ -n "$NEXT_PUBLIC_APP_URL" ]; then export NEXT_PUBLIC_APP_URL; else unset NEXT_PUBLIC_APP_URL; fi \
  && npm --workspace apps/web run build

FROM node:22-alpine AS runner

ENV NODE_ENV=production
ENV HOSTNAME=0.0.0.0
ENV PORT=3000
WORKDIR /app

RUN addgroup --system --gid 1001 nodejs \
  && adduser --system --uid 1001 nextjs

COPY --from=builder --chown=nextjs:nodejs /app/apps/web/.next/standalone ./
COPY --from=builder --chown=nextjs:nodejs /app/apps/web/.next/static ./apps/web/.next/static
COPY --from=builder --chown=nextjs:nodejs /app/apps/web/public ./apps/web/public

USER nextjs
EXPOSE 3000
CMD ["node", "apps/web/server.js"]
