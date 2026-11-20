# Asistente de consulta Banamex


Nota de diseño · 19 de noviembre de 2026 · Ejercicio de evaluación

## 1. Alcance y decisión


Prototipo de chat en español e inglés para Joy y Clásica (costos, CAT y requisitos), MiCuenta y Switch (apertura y algunos servicios), canales oficiales y seguridad. No consulta cuentas, no ejecuta trámites y no se publica. Se eligió un catálogo acotado para que cada respuesta se pueda revisar contra una fuente pública.


El corpus tiene 24 fichas, 15 capturas de 12 URLs y 58 extractos auditados. Se conservan HTML, URL, fecha y huella SHA-256. Las cifras son capturas de noviembre de 2026; no constituyen una verificación de tarifas en vivo.

## 2. Flujo y componentes


Pregunta → privacidad/alcance → reglas de intención y búsqueda SQLite FTS5 → E5 opcional para apertura de cuentas → Qwen3 opcional para lo no resuelto → validación del plan → respuesta con fichas y citas. El orden no implica que cada consulta ejecute los tres componentes.


Qwen3:4b Q4_K_M en Ollama devuelve un plan JSON; Python valida tema, producto y operación. El texto visible y los importes se construyen con fichas y plantillas. El clasificador usa CPU, contexto 2048 y espera 25 s. Si falla, se aclara o se usa respaldo. E5 multilingual-small INT8 también usa CPU; sus umbrales son provisionales.


Las reglas de negación separan “ubicar sucursal” de “solicitar Clásica sin acudir”. Una mención ambigua puede consultar al clasificador y pedir aclaración. El seguimiento conserva la tarjeta. Si falta evidencia de que todo el trámite sea remoto, el asistente lo indica y enlaza la ficha oficial.

## 3. Demo reproducible


Preparar antes la .venv, E5 y el servicio Ollama con qwen3:4b según README. Ejecutar sin sudo: ./.venv/bin/python app.py --embeddings --ollama-model qwen3:4b. Abrir la dirección local impresa. Las instrucciones de ejecución tienen tres líneas; los modelos no se incluyen en el ZIP.


El mismo código admite python3 app.py para el modo básico sin dependencias externas. No se confunden sus resultados con los del modo completo. La interfaz muestra el aviso de ejercicio y las rutas utilizadas; las fuentes se abren solo si el usuario las elige.

## 4. Medición y limitaciones


Se ejecutaron 70 pruebas automatizadas (incluyen simulaciones de rutas y fallos) y 75 consultas idénticas por cada una de cuatro variantes. Las variantes con modelos ejecutaron inferencia real en Linux/WSL con Python 3.14.4. La rúbrica comprueba acción, hechos, citas, idioma y condiciones de texto; los tiempos son del motor, sin HTTP ni navegador.

| Variante | Cumple | p95 motor | Críticos |
|---|---:|---:|---:|
| Reglas locales | 66/75 | 0.87 ms | 0 |
| Reglas + Qwen3 CPU | 72/75 | 3741.64 ms | 2 |
| Reglas + E5 CPU | 66/75 | 1.02 ms | 0 |
| Reglas + E5 + Qwen3 CPU | 72/75 | 4653.80 ms | 2 |

El modo completo resolvió 39/42 contestables en primer turno y 30/30 límites/aclaraciones; el Excel pasó 20/20. Quedaron ES1 (comparación anual no resuelta), EN4 (respuesta incompleta sobre costo por poco uso) y SEM06 (hechos adicionales no exigidos). EN4 y SEM06 son críticos según la rúbrica: no se promete cero errores ni cero alucinación.


Qwen3 tardó 11.91 s en el calentamiento de esta corrida. El p95 de las llamadas al clasificador en modo completo fue 9.21 s. E5 no cambió los resultados ni emitió respuestas directas en este lote; no hay ganancia general demostrada. Parte del lote se usó durante los ajustes; hacen falta preguntas nuevas e independientes.

## 5. Riesgos y controles


Fuente desactualizada: revisar vigencias y cambios antes de responder a clientes reales. Intención equivocada: validar planes y medir errores por tarea; abstenerse ante evidencia insuficiente. Datos sensibles: filtros previos y sin historial persistente, sin prometer detección exhaustiva. Instrucciones maliciosas: tratar la pregunta como datos, esquema cerrado y plantillas, sin garantía absoluta frente a ataques. Fallo operativo: preparar modelos, comprobar servicio y probar el arranque antes de la demo.

## 6. Camino a producción y supuestos


Priorizar actualización/versionado de fuentes con responsables; revisión de cumplimiento y privacidad; evaluación independiente, revisión humana y derivación; observabilidad sin datos sensibles; límites de concurrencia, monitoreo, disponibilidad y pruebas de seguridad. Ampliar componentes solo cuando una medición justifique su costo. No se propone una pila empresarial como requisito previo.


Se usaron asistentes de IA para programación, revisión, pruebas y documentación. La bitácora distingue el trabajo inicial declarado del cierre posterior no cronometrado. El prototipo es una demostración acotada; los resultados completos y respuestas del Excel están en docs/RESULTADOS.md y evaluation/final_20261119/.

