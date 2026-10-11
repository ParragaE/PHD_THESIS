# Interpretación científica

A: mismo archivo, offset y tamaño iguales, tiempos solapados.
B: mismo archivo, rangos parcialmente coincidentes y tiempos solapados.
C: concurrencia en recurso compartido identificado o inferido (OST/NFS), sin requerir offset común.

Mapa Offset × Tiempo: cuenta pares A/B que intersectan cada celda; histogramas marginales son sumas de estas celdas. No es una medida de degradación.
Matriz Proceso × Proceso: recuento simétrico de pares concurrentes.

Para demostrar degradación hacen falta métricas comparables y controles de volumen, carga, filesystem y configuración.
