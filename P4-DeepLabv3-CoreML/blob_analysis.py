# ─────────────────────────────────────────────────────────────────────────────
# blob_analysis.py — Análisis de blobs estilo Antimodular
# P4 · Aún Sorprendo · JIFREX
#
# Rafael Lozano-Hemmer (Antimodular) utiliza análisis de blobs para distinguir
# presencia real de ruido visual. Este módulo implementa ese enfoque con 4
# métricas que describen no solo SI hay alguien, sino CÓMO está ese alguien
# en el espacio — lo cual es la base del vínculo conceptual con Picasso.
#
# Métricas (todas enviadas vía OSC a TouchDesigner):
#   largest_blob_area  — tamaño del cuerpo principal (en píxeles)
#   noise_level        — ratio de blobs pequeños vs blob principal (0.0 = limpio)
#   coverage_ratio     — fracción del frame cubierta por persona (0.0–1.0)
#   blob_count         — número de regiones detectadas (1 = una persona)
# ─────────────────────────────────────────────────────────────────────────────

import numpy as np
import cv2

import config


class BlobResult:
    """Resultado del análisis de blobs para un frame."""
    __slots__ = ("largest_area", "noise_level", "coverage_ratio",
                 "blob_count", "presence", "centroid")

    def __init__(self, largest_area, noise_level, coverage_ratio, blob_count, centroid):
        self.largest_area   = largest_area
        self.noise_level    = noise_level
        self.coverage_ratio = coverage_ratio
        self.blob_count     = blob_count
        self.presence       = int(largest_area >= config.AREA_THRESHOLD)
        self.centroid       = centroid  # (x, y) del blob más grande o None


def analyze(mask: np.ndarray) -> BlobResult:
    """
    Análisis de blobs Antimodular sobre la máscara binaria.

    Args:
        mask: np.ndarray uint8 H×W con valores 0 o 255

    Returns:
        BlobResult con las 4 métricas + presence + centroid
    """
    total_pixels = mask.size

    n_labels, labels, stats, centroids = cv2.connectedComponentsWithStats(
        mask, connectivity=8
    )

    # n_labels incluye el fondo (label 0), los blobs reales son 1..n_labels-1
    if n_labels <= 1:
        return BlobResult(0, 0.0, 0.0, 0, None)

    areas     = stats[1:, cv2.CC_STAT_AREA]    # sin el fondo
    blob_centroids = centroids[1:]

    largest_idx  = int(np.argmax(areas))
    largest_area = int(areas[largest_idx])
    centroid_xy  = (float(blob_centroids[largest_idx][0]),
                    float(blob_centroids[largest_idx][1]))

    # Blobs pequeños = todos los que son < 10% del blob mayor (umbral Antimodular)
    noise_area  = sum(
        int(a) for a in areas
        if a < largest_area * config.NOISE_BLOB_RATIO
    )
    noise_level  = noise_area / (largest_area + 1e-6)

    # Cobertura: proporción del frame cubierta por todos los blobs válidos
    valid_area   = sum(int(a) for a in areas if a >= config.AREA_THRESHOLD)
    coverage_ratio = valid_area / total_pixels

    # Número de blobs que superan el umbral mínimo de área
    valid_blobs = sum(1 for a in areas if a >= config.AREA_THRESHOLD)

    return BlobResult(
        largest_area   = largest_area,
        noise_level    = float(noise_level),
        coverage_ratio = float(coverage_ratio),
        blob_count     = valid_blobs,
        centroid       = centroid_xy if largest_area >= config.AREA_THRESHOLD else None,
    )
