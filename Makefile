# Profile Intelligence Platform — common developer targets
#
#   make backend    # FastAPI on :8000
#   make frontend   # Vite React on :5173
#   make build-ui   # Production SPA → web/dist
#   make run        # ./scripts/start.sh (backend + frontend)

.PHONY: backend frontend build-ui run help

help:
	@echo "Targets:"
	@echo "  make backend   - uvicorn profile_intelligence.api.main:app --reload"
	@echo "  make frontend  - cd frontend && npm run dev"
	@echo "  make build-ui  - ./scripts/build-ui.sh"
	@echo "  make run       - ./scripts/start.sh"

backend:
	uvicorn profile_intelligence.api.main:app --reload --host 127.0.0.1 --port 8000

frontend:
	cd frontend && npm run dev

build-ui:
	./scripts/build-ui.sh

run:
	./scripts/start.sh
