"""Инициализация пакета репозиториев"""

from repository.base_repository import SocialRepository
from repository.creator_repository import CreatorRepository
from repository.like_repository import LikeRepository
from repository.network_repository import NetworkRepository
from repository.note_repository import NoteRepository
from repository.social_network_repository import SocialNetworkRepository
from repository.sub_repository import SubRepository
from repository.topic_repository import TopicRepository

__all__ = [
    "NetworkRepository",
    "CreatorRepository",
    "NoteRepository",
    "SubRepository",
    "LikeRepository",
    "SocialNetworkRepository",
    "SocialRepository",
    "TopicRepository",
]
