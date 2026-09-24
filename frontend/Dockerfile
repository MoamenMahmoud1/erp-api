FROM node:22-alpine AS build

WORKDIR /app

COPY package.json package-lock.json ./
RUN npm ci --ignore-scripts --no-audit --no-fund

COPY . .

# Keep exactly one frontend configuration source in the image.
# Vite otherwise gives mode-specific env files precedence over .env.
RUN rm -f .env.production .env.development .env.local .env.production.local .env.development.local \
    && npm run build

FROM nginx:1.29-alpine AS runtime

COPY nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=build /app/dist /usr/share/nginx/html

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]
