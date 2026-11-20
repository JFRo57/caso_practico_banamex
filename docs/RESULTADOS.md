# Resultados de la versión final

Corrida real del 19 de noviembre de 2026 en Linux/WSL, Python 3.14.4. Qwen3:4b Q4_K_M mediante Ollama 0.40.16, forzado a CPU, contexto 2048 y espera máxima de 25 s; E5 INT8 mediante ONNX Runtime en CPU. La suite usa 75 casos idénticos por variante (300 ejecuciones), incluido el Excel de 20 preguntas. ES1 conserva la formulación de presentación del ZIP recibido; las cifras históricas con otro texto no se consideran una comparación pareada.

| Variante | Criterios cumplidos | Excel | Errores críticos de rúbrica | p50 motor | p95 motor |
|---|---:|---:|---:|---:|---:|
| Reglas locales | 66/75 | 20/20 | 0 | 0.19 ms | 0.87 ms |
| Reglas + Qwen3 CPU | 72/75 | 20/20 | 2 | 0.22 ms | 3741.64 ms |
| Reglas + E5 CPU | 66/75 | 20/20 | 0 | 0.22 ms | 1.02 ms |
| Reglas + E5 + Qwen3 CPU | 72/75 | 20/20 | 2 | 0.24 ms | 4653.80 ms |

El modo completo cumplió 39/42 consultas respondibles en primer turno y 30/30 casos de límites/aclaraciones. No equivale a 100% de seguridad ni de corrección general. E5 no cambió los veredictos de este lote y no produjo respuestas directas: las reglas previas ya resolvieron los casos cubiertos de apertura. Se mantiene como componente opcional para otras formulaciones, sin afirmar una ganancia probada aquí.

El calentamiento de Qwen3 tardó 11.91 s y los índices E5 4.23 / 3.91 s. Estas cifras se miden por separado. El p95 de las llamadas al clasificador en modo completo fue 9.21 s; hubo 10 intentos y 1 respaldo. El p95 de todo el motor mezcla reglas rápidas y llamadas al modelo; no es el tiempo típico exclusivo de Qwen3.

## Resultados del Excel en el modo completo

| Caso | Pregunta | Comportamiento observado | Ruta | Tiempo motor | Cumple |
|---|---|---|---|---:|---|
| 1 | ¿Qué requisitos necesito para solicitar una tarjeta de crédito? | Respuesta con citas | local | 3.856 ms | Sí |
| 2 | ¿Cuánto cuesta la anualidad de la tarjeta de crédito más básica? | Respuesta con citas | local | 1.590 ms | Sí |
| 3 | ¿Qué diferencia hay entre dos de sus tarjetas de crédito? | Respuesta con citas | local | 0.367 ms | Sí |
| 4 | ¿Qué es el CAT y cuál es el de esta tarjeta? | Aclaración | local | 0.254 ms | Sí |
| 5 | ¿Qué necesito para abrir una cuenta de débito? | Respuesta con citas | local | 0.228 ms | Sí |
| 6 | ¿Puedo abrir una cuenta desde la app sin ir a sucursal? | Respuesta con citas | local | 0.244 ms | Sí |
| 7 | ¿La cuenta cobra comisión por manejo de cuenta? | Aclaración | local | 0.088 ms | Sí |
| 8 | ¿Qué tipos de crédito personal ofrecen? | Abstención | local | 0.048 ms | Sí |
| 9 | ¿Cuánto me prestan si gano 15 mil pesos al mes? | Derivación oficial | local | 0.070 ms | Sí |
| 10 | ¿Qué requisitos piden para un crédito hipotecario? | Abstención | local | 0.065 ms | Sí |
| 11 | ¿Qué seguros puedo contratar con el banco? | Abstención | local | 0.091 ms | Sí |
| 12 | ¿Qué opciones de inversión tienen para personas fisicas? | Abstención | local | 0.062 ms | Sí |
| 13 | ¿Cuál es el horario de atención telefónica? | Respuesta con citas | local | 0.210 ms | Sí |
| 14 | ¿Cómo encuentro la sucursal más cercana? | Respuesta con citas | local | 0.191 ms | Sí |
| 15 | ¿El banco me puede pedir mi NIP por teléfono? | Respuesta con citas | local | 0.181 ms | Sí |
| 16 | ¿Cómo hago una aclaración por un cargo que no reconozcó | Respuesta con citas | local | 0.189 ms | Sí |
| 17 | ¿Cuál es el tipo de cambio del dólar hoy? | Abstención | local | 0.044 ms | Sí |
| 18 | ¿Me recomiendas comprar acciones de alguna empresa? | Derivación oficial | local | 0.059 ms | Sí |
| 19 | ¿Cuál es la capital de Australia? | Abstención | local | 0.038 ms | Sí |
| 20 | no entiendo nada de las tarjetas cual me combiene si casi no la uso | Respuesta con citas | local | 0.242 ms | Sí |

Las respuestas completas y citas están en [results_adaptive.csv](../evaluation/final_20261119/results_adaptive.csv). [Excel original](../asistente_banamex/evaluation/cases/preguntas_prueba.xlsx).

## Tres casos pendientes del modo completo

| Caso | Fallo observado | Crítico según rúbrica |
|---|---|---|
| ES1 | La comparación anual de Joy/Clásica no quedó resuelta; se usó respaldo. | No |
| EN4 | Devolvió cargo por inactividad, pero omitió el dato de administración exigido en ese caso. | Sí |
| SEM06 | Respondió requisitos e ingreso cuando la expectativa exigía únicamente el dato de ingreso. | Sí |

Estas marcas expresan las comprobaciones de acción/hechos/citas de cada caso. No significan necesariamente una cifra inventada, pero impiden afirmar ausencia de errores. Los modelos no fijan cifras: seleccionan fichas; una selección incompleta o excesiva también puede ser incorrecta.

## Cómo se midió y límites

El evaluador audita SHA-256 de las copias y la presencia de 58 extractos en 15 capturas (12 URLs únicas, 24 fichas). Por caso contrasta acción, hechos esperados, citas, idioma y condiciones textuales. Se conservan las expectativas; no se editaron para convertir estos fallos en aciertos. Los tiempos del motor excluyen navegador, HTTP y arranque. Una sola corrida, muestras conocidas durante el desarrollo y temperatura 0 no garantizan repetibilidad exacta ni generalización a las preguntas nuevas del panel.

70 pruebas automatizadas pasan; algunas simulan el clasificador y E5 para cubrir rutas y fallos. La corrida de 300 preguntas usa inferencia real para las variantes activadas. Los casos de canal de solicitud se validaron adicionalmente: no confundir el localizador con evitar sucursal y no afirmar trámite enteramente remoto sin evidencia. No se evaluó interacción visual automatizada del navegador.

## Reproducir sin mezclar reportes

```bash
python3 -m unittest discover -s tests -p 'test_*.py'
./.venv/bin/python evaluate.py --embeddings --ollama-model qwen3:4b --output evaluation/nueva_corrida
```

[Resumen íntegro](../evaluation/final_20261119/summary.json). CSV separados para local, hybrid, embeddings_only y adaptive en la misma carpeta. Los informes antiguos se preservan en los originales; no forman parte de los resultados vigentes de este ZIP.
