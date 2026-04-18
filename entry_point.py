import repository
from config import DB_CONFIG
from dto import NetworkType


def main():
    network_repo = repository.NetworkRepository(DB_CONFIG.to_dict())
    network_repo.createOrIgnore(NetworkType.VK.value)
