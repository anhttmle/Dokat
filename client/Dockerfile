# syntax=docker/dockerfile:1

# --- Build Flutter web (release) -------------------------------------------
FROM ghcr.io/cirruslabs/flutter:stable AS build

WORKDIR /app

COPY pubspec.yaml pubspec.lock ./
COPY analysis_options.yaml ./
RUN flutter pub get

COPY assets ./assets
COPY lib ./lib
COPY web ./web

# API URL resolved at runtime on web via resolveApiBaseUrl() → {origin}/api
RUN flutter build web --release

# --- Serve static files with nginx -----------------------------------------
FROM nginx:1.27-alpine

COPY nginx/default.conf /etc/nginx/conf.d/default.conf
COPY --from=build /app/build/web /usr/share/nginx/html

EXPOSE 80
