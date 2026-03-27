---
description: "Revision rapida de codigo para detectar bugs, riesgos, regresiones y faltantes de tests"
name: "Review Rapida"
argument-hint: "Indica archivo, modulo, PR o cambio a revisar"
agent: "Code Review Riesgos"
---
Realiza una revision rapida del siguiente alcance: ${input}

Objetivo:
- Detectar riesgos reales con foco en comportamiento y estabilidad.
- Priorizar hallazgos accionables por severidad.
- Mantener el analisis breve y concreto.

Instrucciones:
1. Revisa primero errores funcionales, validaciones, manejo de errores y contratos API.
2. Señala regresiones potenciales y supuestos peligrosos.
3. Verifica si faltan pruebas importantes para cubrir casos borde y fallos esperados.
4. Evita observaciones cosmeticas salvo que impacten mantenibilidad critica.

Formato de salida obligatorio:
1. Findings:
- [Alta|Media|Baja] descripcion corta + archivo/linea + impacto.
2. Pruebas faltantes:
- Lista minima de tests sugeridos.
3. Resumen:
- Maximo 4 lineas con conclusion de riesgo.
