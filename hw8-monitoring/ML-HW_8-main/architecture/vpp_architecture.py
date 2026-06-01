"""Render the Kappa-style VPP (Virtual Product Placement) architecture diagram.

Run:
    python architecture/vpp_architecture.py
Output:
    architecture/vpp_architecture.png

Prerequisites:
    pip install -r architecture/requirements.txt
    + system graphviz binary (Windows: `winget install Graphviz.Graphviz`)
"""
from __future__ import annotations

from pathlib import Path

from diagrams import Cluster, Diagram, Edge
from diagrams.aws.network import CloudFront
from diagrams.generic.storage import Storage
from diagrams.onprem.analytics import Spark
from diagrams.onprem.client import User
from diagrams.onprem.compute import Server
from diagrams.onprem.database import PostgreSQL
from diagrams.onprem.inmemory import Redis
from diagrams.onprem.mlops import Mlflow
from diagrams.onprem.monitoring import Grafana, Prometheus
from diagrams.onprem.queue import Kafka

OUTPUT_DIR = Path(__file__).parent
OUTPUT_BASENAME = "vpp_architecture"

GRAPH_ATTR = {
    "splines": "spline",
    "bgcolor": "white",
    "fontname": "Helvetica",
    "labelloc": "t",
    "label": "Virtual Product Placement - Kappa-архитектура реалтайм инференса",
}

EDGE_KAFKA = {"label": "Kafka stream", "color": "darkorange", "style": "bold"}


def build() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    with Diagram(
        OUTPUT_BASENAME,
        filename=str(OUTPUT_DIR / OUTPUT_BASENAME),
        outformat="png",
        show=False,
        direction="LR",
        graph_attr=GRAPH_ATTR,
    ):
        viewer = User("Зритель")

        with Cluster("Источники видео"):
            cdn_in = CloudFront("Netflix CDN / OTT origin")
            ingest = Kafka("Topic: video_frames_raw")

        with Cluster("Stream Processing (Kappa)"):
            spark = Spark("Spark Structured Streaming\n(или Apache Flink)")

        with Cluster("Discriminative AI"):
            yolo = Server("YOLO object detection")
            seg = Server("Person / scene\nsegmentation")

        with Cluster("Generative AI"):
            inpaint = Server("Inpainting / diffusion\n(brand placement)")

        with Cluster("Контекст и таргетинг"):
            personalization = Server("Personalization service")
            feature_store = PostgreSQL("Feature Store\n(viewer profile)")
            brand_catalog = Storage("Brand catalog\n(regional matrix)")
            cache = Redis("Hot cache\n(per-stream session)")

        with Cluster("Stream out + delivery"):
            out_topic = Kafka("Topic:\nvideo_frames_enriched")
            assembler = Server("Re-assembly\n+ encoder")
            cdn_out = CloudFront("Edge CDN delivery")

        with Cluster("Observability"):
            prom = Prometheus("Prometheus")
            grafana = Grafana("Grafana dashboards")
            mlflow = Mlflow("MLflow tracking\n+ registry")

        with Cluster("Feedback loop"):
            ab = Server("A/B experimentation")
            retrain = Server("Continuous retrain\norchestrator")

        cdn_in >> Edge(**EDGE_KAFKA) >> ingest >> Edge(**EDGE_KAFKA) >> spark
        spark >> Edge(label="frame batch", style="dashed") >> yolo
        spark >> Edge(label="frame batch", style="dashed") >> seg
        yolo >> Edge(label="detections") >> inpaint
        seg >> Edge(label="masks") >> inpaint

        personalization >> Edge(label="viewer features") >> inpaint
        feature_store >> Edge(label="lookup") >> personalization
        brand_catalog >> Edge(label="region-aware brands") >> inpaint
        cache >> Edge(label="session state") >> personalization

        inpaint >> Edge(**EDGE_KAFKA) >> out_topic >> Edge(**EDGE_KAFKA) >> assembler
        assembler >> Edge(label="encoded HLS / DASH") >> cdn_out >> Edge(label="playback") >> viewer

        yolo >> Edge(color="grey", style="dotted", label="metrics") >> prom
        inpaint >> Edge(color="grey", style="dotted", label="metrics") >> prom
        spark >> Edge(color="grey", style="dotted", label="metrics") >> prom
        prom >> Edge(color="grey", style="dotted") >> grafana

        inpaint >> Edge(color="blue", style="dashed", label="model_version") >> mlflow

        viewer >> Edge(label="implicit feedback", color="green") >> ab
        ab >> Edge(label="online metrics", color="green") >> retrain
        retrain >> Edge(label="new model artifact", color="blue") >> mlflow
        mlflow >> Edge(label="promoted weights", color="blue") >> inpaint


if __name__ == "__main__":
    build()
    print(f"diagram generated -> {OUTPUT_DIR / (OUTPUT_BASENAME + '.png')}")
