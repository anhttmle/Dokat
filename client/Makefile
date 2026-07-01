.PHONY: install run-web build-web docker-build docker-run

# Local flutter run (không qua Docker). Docker web dùng /api proxy runtime.
BASE_URL ?= http://localhost:8000

install:
	flutter pub get

run-web:
	flutter run -d chrome --dart-define=BASE_URL=$(BASE_URL)

build-web:
	flutter build web --release --dart-define=BASE_URL=$(BASE_URL)

docker-build:
	docker build -t dokat-client-web .

docker-run:
	docker run --rm -p 8080:80 dokat-client-web
