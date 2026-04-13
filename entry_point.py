from config import DB_CONFIG, VK_TOKEN
from dto import NetworkType
import repository 
import vk_api


def main():
    network_repo=repository.NetworkRepository(DB_CONFIG.to_dict())
    network_repo.createOrIgnore(NetworkType.VK.value)
    