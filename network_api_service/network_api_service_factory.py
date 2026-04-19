from dto import NetworkType
from network_api_service import DefaultNetworkApiService, VKService
from repository import CreatorRepository, NetworkRepository


def getNetworkApiService(
    network: NetworkType,
    creds: dict,
    creator_repo: CreatorRepository,
    network_repo: NetworkRepository,
) -> DefaultNetworkApiService:
    if network == NetworkType.VK:
        return VKService(creds.get("token"), creator_repo, network_repo)
    elif network == NetworkType.TWITTER:
        raise Exception("Пока не реализовано.")
    elif network == NetworkType.TELEGRAM:
        raise Exception("Пока не реализовано.")
    else:
        raise Exception("Пока не реализовано.")
