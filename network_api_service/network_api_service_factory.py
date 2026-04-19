from dto import NetworkType
from network_api_service.default_network_api_service import DefaultNetworkApiService
from network_api_service.vk_service.vk_api_service import VKService
from repository.creator_repository import CreatorRepository


def getNetworkApiService(
    network: NetworkType, creds: dict, creator_repo: CreatorRepository
) -> DefaultNetworkApiService:
    if network == NetworkType.VK:
        return VKService(creds.get("token"), creator_repo)
    elif network == NetworkType.TWITTER:
        raise Exception("Пока не реализовано.")
    elif network == NetworkType.TELEGRAM:
        raise Exception("Пока не реализовано.")
    else:
        raise Exception("Пока не реализовано.")
