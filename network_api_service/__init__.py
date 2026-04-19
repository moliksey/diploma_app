"""Инициализация пакета репозиториев"""

from network_api_service.default_network_api_service import DefaultNetworkApiService
from network_api_service.network_api_service_factory import getNetworkApiService
from network_api_service.vk_service.vk_api_service import VKService

__all__ = ["DefaultNetworkApiService", "getNetworkApiService", "VKService"]
