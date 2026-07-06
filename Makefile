-include .env

.PHONY: help test lint format typecheck check ci security gitleaks cert clean share setup

FILE              ?= $(error ❌  FILE is required. Usage: make share FILE="/path/to/file")
ONEDROP_PORT      ?= 443
ONEDROP_BIND      ?= 0.0.0.0
ONEDROP_MAX_DL    ?= 1
ONEDROP_CERT      ?= onedrop.pem
ONEDROP_KEY       ?= onedrop-key.pem
ONEDROP_LOG       ?= access_audit.log

help:
	@printf "\n"
	@printf "\033[1;34m  OneDrop - Encrypted LAN File Transfer\033[0m\n"
	@printf "\033[90m  ─────────────────────────────────────────────────────\033[0m\n"
	@printf "\n"
	@printf "\033[1;33m  SHARE A FILE\033[0m\n"
	@printf "  \033[32mmake share FILE\033[0m=\"/path/to/file\"                       Share with auto-generated password\n"
	@printf "  \033[32mmake share FILE\033[0m=... \033[32mONEDROP_MAX_DL\033[0m=3           Allow 3 downloads before link expires\n"
	@printf "  \033[32mmake share FILE\033[0m=... \033[32mONEDROP_PORT\033[0m=9443           Use a different port\n"
	@printf "  \033[32mmake share FILE\033[0m=... \033[32mONEDROP_BIND\033[0m=192.168.1.5    Restrict to a specific LAN IP\n"
	@printf "  \033[32mmake share FILE\033[0m=... \033[32mONEDROP_PASSWORD\033[0m=secret      Set a fixed password\n"
	@printf "\n"
	@printf "\033[1;33m  CONFIGURATION (.env)\033[0m\n"
	@printf "  All defaults live in \033[33m.env\033[0m (copy from \033[33m.env.example\033[0m to get started).\n"
	@printf "  Current active values:\n"
	@printf "  \033[90m  ONEDROP_CERT     = $(ONEDROP_CERT)\033[0m\n"
	@printf "  \033[90m  ONEDROP_KEY      = $(ONEDROP_KEY)\033[0m\n"
	@printf "  \033[90m  ONEDROP_PORT     = $(ONEDROP_PORT)\033[0m\n"
	@printf "  \033[90m  ONEDROP_BIND     = $(ONEDROP_BIND)\033[0m\n"
	@printf "  \033[90m  ONEDROP_MAX_DL   = $(ONEDROP_MAX_DL)\033[0m\n"
	@printf "  \033[90m  ONEDROP_LOG      = $(ONEDROP_LOG)\033[0m\n"
	@printf "\n"
	@printf "\033[1;33m  CERTIFICATES\033[0m\n"
	@printf "  \033[32mmake cert\033[0m    Generate a locally-trusted cert with mkcert → onedrop.pem\n"
	@printf "\n"
	@printf "\033[1;33m  DEVELOPMENT\033[0m\n"
	@printf "  \033[32mmake setup\033[0m       Set up keys, dependencies, and environment configuration\n"
	@printf "  \033[32mmake ci\033[0m          Full CI pipeline (format + lint + typecheck + test + gitleaks)\n"
	@printf "  \033[32mmake check\033[0m       Lint + typecheck + tests\n"
	@printf "  \033[32mmake test\033[0m        Run pytest only\n"
	@printf "  \033[32mmake lint\033[0m        Run ruff static analysis\n"
	@printf "  \033[32mmake format\033[0m      Auto-format code with ruff\n"
	@printf "  \033[32mmake typecheck\033[0m   Run mypy type checker\n"
	@printf "  \033[32mmake security\033[0m    Run all security checks (bandit + pip-audit + gitleaks)\n"
	@printf "  \033[32mmake gitleaks\033[0m    Scan for secrets with Gitleaks\n"
	@printf "  \033[32mmake clean\033[0m       Remove build caches and coverage artifacts\n"
	@printf "\n"

share:
	@printf "\n\033[1;34m  OneDrop - Starting server\033[0m\n"
	@printf "\033[90m  ─────────────────────────────────────────────────────\033[0m\n"
	@printf "  \033[33mFile:      \033[0m$(FILE)\n"
	@printf "  \033[33mPort:      \033[0m$(ONEDROP_PORT)\n"
	@printf "  \033[33mCert:      \033[0m$(ONEDROP_CERT)\n"
	@printf "  \033[33mMax DLs:   \033[0m$(ONEDROP_MAX_DL)\n"
	@printf "\033[90m  ─────────────────────────────────────────────────────\033[0m\n\n"
	@ONEDROP_PORT="$(ONEDROP_PORT)" \
	 ONEDROP_BIND="$(ONEDROP_BIND)" \
	 ONEDROP_CERT="$(ONEDROP_CERT)" \
	 ONEDROP_KEY="$(ONEDROP_KEY)" \
	 ONEDROP_LOG="$(ONEDROP_LOG)" \
	 ONEDROP_MAX_DL="$(ONEDROP_MAX_DL)" \
	 onedrop "$(FILE)"

test:
	pytest

lint:
	ruff check .

format:
	ruff format .

typecheck:
	mypy src

security:
	bandit -r src/ --confidence-level high --severity-level medium --format screen
	pip-audit
	gitleaks detect --config .gitleaks.toml

ci:
	ruff format --check --diff .
	ruff check .
	mypy src
	pytest --cov=onedrop --cov-report=term-missing -v
	gitleaks detect --config .gitleaks.toml

check:
	ruff check .
	mypy src
	pytest

gitleaks:
	gitleaks detect --config .gitleaks.toml

setup:
	@chmod +x setup.sh
	@./setup.sh

cert:
	@PRIMARY_IP=$$(python3 -c "import socket; s=socket.socket(socket.AF_INET, socket.SOCK_DGRAM); s.connect(('8.8.8.8', 1)); print(s.getsockname()[0])" 2>/dev/null || echo ""); \
	if [ -n "$$PRIMARY_IP" ]; then \
		HOSTS="localhost 127.0.0.1 $$PRIMARY_IP"; \
	else \
		HOSTS="localhost 127.0.0.1"; \
	fi; \
	mkcert -cert-file onedrop.pem -key-file onedrop-key.pem $$HOSTS

clean:
	rm -rf build dist *.egg-info .pytest_cache .mypy_cache .ruff_cache .coverage htmlcov
	find . -type d -name __pycache__ -exec rm -rf {} +
