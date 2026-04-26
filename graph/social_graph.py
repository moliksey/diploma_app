import pickle

import networkx as nx
from tqdm import tqdm

from config import DB_CONFIG
from dto import *
from repository import *


class SocialGraph:
    """Класс социального графа"""

    def __init__(self, network: NetworkType, creds: dict):
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

    def get_graph(self):
        return self._graph.copy()

    def make_graph(self, network):
        """Основной метод для построения графа"""
        self._working_network = network

        self._add_nodes()
        self._add_weighted_interaction_edges()

        return self.graph

    def _add_nodes(self):
        """Добавляет узлы (акторов) в граф"""
        total_users = self._creators_repo.count_by_network(self._working_network.id)
        offset = 0

        with tqdm.tqdm(
            total=total_users,
            desc="Все пользователи",
            unit=" пользователь",
            dynamic_ncols=True,
        ) as pbar:
            while offset < total_users:
                users, offset = self._creators_repo.get_users_to_process(
                    offset=offset,
                    limit=self._batch_size_nodes,
                    isperson=False,
                    network=self._working_network,
                )

                self._process_users_batch(users)
                self._save_checkpoint_if_needed(offset, self._batch_size_nodes)
                pbar.update(self._batch_size_nodes)

    def _add_weighted_interaction_edges(self):
        """
        Добавляет взвешенные ребра между пользователями на основе их взаимодействий.
        Для каждого пользователя находим всех, с кем он взаимодействовал,
        и добавляем ребро с рассчитанным весом.
        """
        total_users = self._creators_repo.count_by_network(self._working_network.id)
        offset = 0

        with tqdm.tqdm(
            total=total_users,
            desc="Построение взвешенных связей",
            unit=" пользователь",
            dynamic_ncols=True,
        ) as pbar:
            while offset < total_users:
                # Получаем батч пользователей
                users, offset = self._creators_repo.get_users_to_process(
                    offset=offset,
                    limit=self._batch_size_nodes,
                    isperson=False,
                    network=self._working_network,
                )

                self._process_edges_baatch(users)
                self._save_checkpoint_if_needed(offset, self._batch_size_nodes)
                pbar.update(self._batch_size_nodes)

    def _process_edges_baatch(self, users):
        """Обрабатывает батч связей"""
        for user in users:
            try:
                interactors = self._creators_repo.get_unique_interactors(
                    creator_id=user.id,
                )

                for interactor_id in interactors:
                    weight = self._social_network_repo.weight_interactions(
                        interactor_id,
                        user.id,
                        self._weight_like,
                        self._weight_comment,
                        self._weight_sub,
                    )
                    self.graph.add_edge(interactor_id, user.id, weight=weight)

            except Exception as e:
                print(f"Ошибка при обработке пользователя {user.id}: {e}")

    def _process_users_batch(self, users):
        """Обрабатывает батч пользователей"""
        for user in users:
            try:
                size = self._creators_repo.get_unique_interactors_count(user.id)
                self.graph.add_node(user.id, size=size)
            except Exception as e:
                print(f"Ошибка при добавлении пользователя {user.id}: {e}")

    def _save_checkpoint_if_needed(self, offset, batch_size):
        """Сохраняет чекпоинт при достижении интервала"""
        if offset > 0 and (offset // batch_size) % self._checkpoint_interval == 0:
            self._save_checkpoint()

    def _save_checkpoint(self):
        """Сохраняет текущее состояние графа"""
        try:
            with open(self._checkpoint_file, "wb") as output:
                pickle.dump(self.graph, output, pickle.HIGHEST_PROTOCOL)
        except Exception as e:
            print(f"Ошибка при сохранении чекпоинта: {e}")
