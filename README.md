# HL GDTF Builder — MVP 0.1

PWA para importar manuales PDF, detectar posibles canales DMX, corregirlos y exportar GDTF preliminar.

## Ejecutar

```bash
python -m pip install -r requirements.txt
python -m uvicorn server:app --host 0.0.0.0 --port 8000
```

Abrí http://localhost:8000. Para iPhone se necesita desplegar con HTTPS.

## Limitaciones

Extracción heurística sin OCR ni IA. Un solo modo DMX, canales de 8 bits, geometría genérica y sin rangos detallados de Gobos. Los archivos exportados son experimentales: validar antes de usar en Vectorworks o grandMA3.

## Render

Build: `pip install -r requirements.txt`
Start: `uvicorn server:app --host 0.0.0.0 --port $PORT`
