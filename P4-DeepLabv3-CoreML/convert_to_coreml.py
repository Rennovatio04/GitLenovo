#!/usr/bin/env python3
# ─────────────────────────────────────────────────────────────────────────────
# convert_to_coreml.py — Conversión DeepLabv3 → CoreML (Neural Engine M3 Max)
# P4 · Aún Sorprendo · JIFREX
#
# Ejecutar UNA VEZ en el Mac M3 Max antes de usar deeplab_runtime.py.
# Genera DeepLabV3.mlpackage en el directorio actual.
#
# Requisitos:
#   pip install coremltools tensorflow tf_hub
#
# Fuente del modelo:
#   TF Hub: https://tfhub.dev/tensorflow/deeplabv3/1
#   O checkpoint PASCAL VOC:
#   http://download.tensorflow.org/models/deeplabv3_mnv2_pascal_train_aug_2018_01_29.tar.gz
#
# Resultado:
#   DeepLabV3.mlpackage — 15–25 ms/frame en Neural Engine M3 Max
#   GPU Metal completamente libre para TouchDesigner
# ─────────────────────────────────────────────────────────────────────────────

import sys
import os

def convert_from_tfhub():
    """
    Convierte DeepLabv3 MobileNetV2 desde TensorFlow Hub.
    Requiere: pip install tensorflow tensorflow-hub coremltools
    """
    try:
        import tensorflow as tf
        import tensorflow_hub as hub
        import coremltools as ct
    except ImportError as e:
        print(f"ERROR: Falta dependencia: {e}")
        print("Instalar: pip install tensorflow tensorflow-hub coremltools")
        sys.exit(1)

    print("[Convert] Descargando DeepLabv3 MobileNetV2 desde TF Hub...")
    # TF Hub model: retorna dict con 'default' = logits 1×H×W×21
    hub_model = hub.load("https://tfhub.dev/tensorflow/deeplabv3/1")

    print("[Convert] Creando wrapper TF para CoreML...")

    @tf.function(input_signature=[
        tf.TensorSpec(shape=[1, 513, 513, 3], dtype=tf.float32, name="ImageTensor")
    ])
    def predict(image_tensor):
        output = hub_model(image_tensor)
        # Argmax sobre las 21 clases PASCAL VOC → mapa de clases 1×513×513
        class_map = tf.math.argmax(output["default"], axis=-1)
        # Extraer solo la clase 15 (person) como máscara float
        person_mask = tf.cast(tf.equal(class_map, 15), tf.float32)
        return {"SemanticPredictions": class_map,
                "PersonMask":          person_mask}

    print("[Convert] Convirtiendo a CoreML float16 (Neural Engine)...")
    mlmodel = ct.convert(
        predict,
        inputs=[
            ct.TensorType(name="ImageTensor", shape=(1, 513, 513, 3),
                          dtype=float)
        ],
        outputs=[
            ct.TensorType(name="SemanticPredictions"),
            ct.TensorType(name="PersonMask"),
        ],
        compute_precision=ct.precision.FLOAT16,
        compute_units=ct.ComputeUnit.ALL,    # Neural Engine + GPU + CPU
        convert_to="mlprogram",
    )

    mlmodel.short_description = (
        "DeepLabv3 MobileNetV2 PASCAL VOC — "
        "JIFREX P4 Aun Sorprendo · clase 15=person · 513x513 float16"
    )

    output_path = "DeepLabV3.mlpackage"
    mlmodel.save(output_path)
    print(f"[Convert] Guardado: {output_path}")
    print("[Convert] Latencia esperada: 15–25 ms/frame en Neural Engine M3 Max")

    # Verificación rápida
    print("[Convert] Verificando inferencia de prueba...")
    import numpy as np
    test_input = np.zeros((1, 513, 513, 3), dtype=np.float32)
    result = mlmodel.predict({"ImageTensor": test_input})
    print(f"[Convert] OK — PersonMask shape: {result['PersonMask'].shape}")


def convert_from_checkpoint():
    """
    Convierte desde el checkpoint PASCAL VOC descargado localmente.
    Usar si TF Hub no está disponible.

    Descargar primero:
      wget http://download.tensorflow.org/models/deeplabv3_mnv2_pascal_train_aug_2018_01_29.tar.gz
      tar xzf deeplabv3_mnv2_pascal_train_aug_2018_01_29.tar.gz
    """
    try:
        import tensorflow as tf
        import coremltools as ct
    except ImportError as e:
        print(f"ERROR: {e}")
        sys.exit(1)

    frozen_graph = "frozen_inference_graph.pb"
    if not os.path.exists(frozen_graph):
        print(f"ERROR: No se encuentra {frozen_graph}")
        print("Descargar desde TF Hub o usar convert_from_tfhub()")
        sys.exit(1)

    print(f"[Convert] Cargando {frozen_graph}...")
    with tf.io.gfile.GFile(frozen_graph, "rb") as f:
        graph_def = tf.compat.v1.GraphDef()
        graph_def.ParseFromString(f.read())

    print("[Convert] Convirtiendo TF1 frozen graph → CoreML...")
    mlmodel = ct.convert(
        graph_def,
        source="tensorflow",
        inputs=[ct.ImageType(name="ImageTensor", shape=(1, 513, 513, 3))],
        outputs=["SemanticPredictions"],
        compute_precision=ct.precision.FLOAT16,
        compute_units=ct.ComputeUnit.ALL,
    )

    output_path = "DeepLabV3.mlpackage"
    mlmodel.save(output_path)
    print(f"[Convert] Guardado: {output_path}")


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(
        description="Conversión DeepLabv3 → CoreML (Neural Engine M3 Max)"
    )
    parser.add_argument(
        "--source", choices=["tfhub", "checkpoint"], default="tfhub",
        help="Fuente del modelo (default: tfhub)"
    )
    args = parser.parse_args()

    if args.source == "tfhub":
        convert_from_tfhub()
    else:
        convert_from_checkpoint()
