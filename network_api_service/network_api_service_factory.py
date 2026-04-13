from dto import Creator, NetworkType
from network_api_service.default_network_api_service import DefaultNetworkApiService
from network_api_service.vk_service.vk_api_service import VKService

def getNetworkApiService(network: NetworkType, creds: dict) -> DefaultNetworkApiService:
    if network==NetworkType.VK:
        return VKService(creds.get("token"))
    elif network == NetworkType.TWITTER:
        raise Exception("Пока не реализовано.")
    elif network == NetworkType.TELEGRAM:
        raise Exception("Пока не реализовано.")
    else:
        raise Exception("Пока не реализовано.")