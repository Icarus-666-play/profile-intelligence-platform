# Profile Intelligence Platform — common developer targets
#
#   make backend    # FastAPI API (+ built SPA if present)
#   make frontend   # Vite React dev server
#   make build-ui   # Production SPA → src/profile_intelligence/web/dist
#   make run        # ./start.sh (uvicorn with reload)

.PHONY: backend frontend build-ui run help

help:
	@echo "Targets:"
	@echo "  make backend   - uvicorn profile_intelligence.api.main:app --reload"
	@echo "  make frontend  - cd frontend && npm run dev"
	@echo "  make build-ui  - cd frontend && npm run build"
	@echo "  make run       - ./start.sh"

backend:
	uvicorn profile_intelligence.api.main:app --reload

frontend:
	cd frontend && npm run dev

build-ui:
	cd frontend && npm run build

run:
	./start.sh
