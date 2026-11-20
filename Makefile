.PHONY: help run demo eval test chat prepare-embeddings clean

help:
	@echo "Comandos disponibles:"
	@echo "  make run                - Inicia el servidor HTTP del chat (puerto 8000)"
	@echo "  make eval               - Ejecuta la suite de evaluación local de 75 casos"
	@echo "  make test               - Ejecuta las pruebas unitarias automatizadas"
	@echo "  make chat               - Inicia sesión interactiva de chat en terminal"
	@echo "  make prepare-embeddings - Descarga y verifica el modelo ONNX en .models/"
	@echo "  make clean              - Limpia archivos de caché y temporales"

run:
	python3 app.py

demo:
	./.venv/bin/python app.py --embeddings --ollama-model qwen3:4b

eval:
	python3 evaluate.py

test:
	python3 -m unittest discover -s tests -p "test_*.py"

chat:
	python3 -m asistente_banamex.cli chat

prepare-embeddings:
	python3 prepare_embeddings.py

clean:
	find . -type d -name "__pycache__" -exec rm -rf {} +
	find . -type d -name ".pytest_cache" -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete
	find . -type f -name "*~" -delete
