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

        # Получаем сеть
        self._working_network = self._networks_repo.get_or_create(network.name)

    def get_graph(self):
        return self._graph.copy()

    def make_graph(self, network):
        """Основной метод для построения графа"""
        self._working_network = network

        self._add_nodes()
        self._add_subscription_edges()
        self._add_like_edges()
        self._add_comment_edges()

        return self.graph

    def _add_nodes(self):
        """Добавляет узлы (пользователей) в граф"""
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

    def _process_users_batch(self, users):
        """Обрабатывает батч пользователей"""
        for user in users:
            try:
                size = self._calculate_user_size(user.id)
                self.graph.add_node(user.id, size=size)
            except Exception as e:
                print(f"Ошибка при добавлении пользователя {user.id}: {e}")

    def _calculate_user_size(self, user_id: int) -> int:
        """Рассчитывает размер узла на основе активности пользователя"""
        subscribers = self._subs_repo.get_subscribers_count(user_id)
        likes = self._likes_repo.get_user_likes_count(user_id)
        comments = self._notes_repo.get_user_comments_count(user_id)
        return subscribers + likes + comments

    def _add_subscription_edges(self):
        """Добавляет ребра подписок"""
        self._add_edges(
            total_count_fn=lambda: self._subs_repo.get_subs_count_over_network(
                self._working_network
            ),
            get_edges_fn=lambda offset, limit: self._subs_repo.get_subs_to_process(
                limit=limit, offset=offset
            ),
            transform_fn=lambda edges: [(sub.subscriber, sub.contentmaker) for sub in edges],
            description="Все подписочные связи",
        )

    def _add_like_edges(self):
        """Добавляет ребра лайков"""
        self._add_edges(
            total_count_fn=lambda: self._likes_repo.get_likes_count_over_network(
                self._working_network
            ),
            get_edges_fn=lambda offset, limit: self._likes_repo.get_like_edges_to_process(
                limit=limit, offset=offset
            ),
            transform_fn=lambda edges: edges,  # уже в правильном формате
            description="Все связи по лайкам",
        )

    def _add_comment_edges(self):
        """Добавляет ребра комментариев"""
        self._add_edges(
            total_count_fn=lambda: self._notes_repo.get_comments_count_over_network(
                self._working_network
            ),
            get_edges_fn=lambda offset, limit: self._notes_repo.get_comment_edges_to_process(
                limit=limit, offset=offset
            ),
            transform_fn=lambda edges: edges,  # уже в правильном формате
            description="Все связи по комментариям",
        )

    def _add_edges(self, total_count_fn, get_edges_fn, transform_fn, description):
        """Универсальный метод для добавления ребер любого типа"""
        total_edges = total_count_fn()
        offset = 0

        with tqdm.tqdm(
            total=total_edges,
            desc=description,
            unit=" связь",
            dynamic_ncols=True,
        ) as pbar:
            while offset < total_edges:
                try:
                    edges, offset = get_edges_fn(offset, self._batch_size_edges)
                    transformed_edges = transform_fn(edges)
                    self.graph.add_edges_from(transformed_edges)

                    self._save_checkpoint_if_needed(offset, self._batch_size_edges)
                    pbar.update(self._batch_size_edges)

                except Exception as e:
                    print(f"Ошибка при добавлении {description.lower()}: {e}")

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
