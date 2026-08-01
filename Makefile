.PHONY: setup install-backend build-whisper start-backend start-frontend start

setup: install-backend
	@echo "✅ Setup complete. Run 'make start-backend' and 'make start-frontend' to start."

install-backend:
	cd backend && python3 -m venv venv && . venv/bin/activate && pip install -r requirements.txt

build-whisper:
	bash scripts/build_whisper.sh

start-backend:
	cd backend && . venv/bin/activate && uvicorn main:app --host 0.0.0.0 --port 8000 --reload

start-frontend:
	cd frontend && npm install && npm run dev

start:
	make start-backend & make start-frontend & wait

link-dataset:
	@echo "Linking dataset from reference repo to backend..."
	ln -sf ../hackerrank-orchestrate-august26/dataset backend/dataset
