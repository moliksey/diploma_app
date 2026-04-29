import networkx as nx

from config import DB_CONFIG
from dto import *
from repository import *


class WorldviewGraph:
    def __init__(self, network: NetworkType):
        """Инициализация коллектора с инъекцией репозиториев"""
        self._graph = nx.DiGraph()

        # Параметры подключения к БД
        db_params = DB_CONFIG.to_dict()

        # Инъекция всех репозиториев
        self._networks_repo = NetworkRepository(db_params)
        self._creators_repo = CreatorRepository(db_params)
        self._notes_repo = NoteRepository(db_params)
        self._subs_repo = SubRepository(db_params)
        self._likes_repo = LikeRepository(db_params)
        self._social_network_repo = SocialNetworkRepository(db_params)
        # FIXME подобрать веса
        self._weight_like = 1.0
        self._weight_comment = 1.5
        self._weight_sub = 2.0
        # Получаем сеть
        self._working_network = self._networks_repo.get_or_create(network.name)
