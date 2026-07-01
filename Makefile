.PHONY: gen-certs up down

# Generates a locally-trusted TLS cert using mkcert.
# Usage: make gen-certs PUBLIC_HOST=192.168.1.100
# Requires: brew install mkcert && mkcert -install
PUBLIC_HOST ?= localhost

gen-certs:
	@command -v mkcert >/dev/null 2>&1 || \
		{ echo "mkcert not found. Run: brew install mkcert && mkcert -install"; exit 1; }
	mkdir -p certs
	JAVA_HOME="" mkcert \
		-cert-file certs/local.crt \
		-key-file  certs/local.key \
		localhost 127.0.0.1 $(PUBLIC_HOST)
	@echo ""
	@echo "Cert generated. Next steps:"
	@echo "  1. docker compose up -d --build client"
	@echo "  2. Open https://$(PUBLIC_HOST):8443 in browser"
	@echo ""
	@echo "iPhone/Android: install mkcert root CA once:"
	@echo "  cat \"\$$(mkcert -CAROOT)/rootCA.pem\" | pbcopy"
	@echo "  → AirDrop/email the rootCA.pem to device, install as profile"
	@echo "  → iOS: Settings → General → About → Certificate Trust Settings → enable"

up:
	docker compose up -d

down:
	docker compose down
