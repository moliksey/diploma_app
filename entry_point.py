from collecting_pipeline import PiplineCollector
from config import VK_TOKEN
from dto import NetworkType


def main():
    pipeline = PiplineCollector(
        user_external_id=365075119, network=NetworkType.VK, creds={"token": VK_TOKEN}
    )
    pipeline.run_pipeline()
