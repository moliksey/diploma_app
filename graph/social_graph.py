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
        self.graph = nx.DiGraph()
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

    def make_graph(self):
        lenth = self._creators_repo.count_by_network(self._working_network.id)
        offset = 0
        limit = 3000
        with tqdm.tqdm(
            total=lenth,
            initial=offset,
            desc="Все пользователи",
            unit=" пользователь",
            unit_scale=False,
            dynamic_ncols=True,
        ) as main_pbar:
            while offset < lenth:
                peoples, offset = self._creators_repo.get_users_to_process(
                    offset=offset, isperson=False, limit=3000, network=self._working_network
                )
                for creator in peoples:
                    try:
                        self.graph.add_node(
                            id,
                            size=(
                                self._subs_repo.get_subscribers_count(creator.id)
                                + self._likes_repo.get_user_likes_count(creator.id)
                                + self._notes_repo.get_user_comments_count(creator.id)
                            ),
                        )
                    except Exception as e:
                        print("Ошибочка вышла: ", e)
                if offset / limit % 10 == 0:
                    with open("friends_friends.pkl", "wb") as output:
                        pickle.dump(self.graph, output, pickle.HIGHEST_PROTOCOL)
                main_pbar.update(limit)
        edges_lenth = self._subs_repo.get_subs_count_over_network(self._working_network)
        edges_offset = 0
        edges_limit = 5000
        with tqdm.tqdm(
            total=edges_lenth,
            initial=edges_offset,
            desc="Все подписочные связи",
            unit=" связь",
            unit_scale=False,
            dynamic_ncols=True,
        ) as main_pbar:
            while edges_offset < edges_lenth:
                try:
                    edges, edges_offset = self._subs_repo.get_subs_to_process(
                        limit=edges_limit, offset=edges_offset
                    )
                    self.graph.add_edges_from([(sub.subscriber, sub.contentmaker) for sub in edges])
                except Exception as e:
                    print("Ошибочка вышла: ", e)
                if edges_offset / edges_limit % 10 == 0:
                    with open("friends_friends.pkl", "wb") as output:
                        pickle.dump(self.graph, output, pickle.HIGHEST_PROTOCOL)
                main_pbar.update(edges_limit)
        edges_lenth = self._likes_repo.get_likes_count_over_network(self._working_network)
        edges_offset = 0
        with tqdm.tqdm(
            total=edges_lenth,
            initial=edges_offset,
            desc="Все связи по лайкам",
            unit=" связь",
            unit_scale=False,
            dynamic_ncols=True,
        ) as main_pbar:
            while edges_offset < edges_lenth:
                try:
                    edges, edges_offset = self._likes_repo.get_like_edges_to_process(
                        limit=edges_limit, offset=edges_offset
                    )
                    self.graph.add_edges_from(edges)
                except Exception as e:
                    print("Ошибочка вышла: ", e)
                if edges_offset / edges_limit % 10 == 0:
                    with open("friends_friends.pkl", "wb") as output:
                        pickle.dump(self.graph, output, pickle.HIGHEST_PROTOCOL)
                main_pbar.update(edges_limit)
        edges_lenth = self._notes_repo.get_comments_count_over_network(self._working_network)
        edges_offset = 0
        with tqdm.tqdm(
            total=edges_lenth,
            initial=edges_offset,
            desc="Все связи по лайкам",
            unit=" связь",
            unit_scale=False,
            dynamic_ncols=True,
        ) as main_pbar:
            while edges_offset < edges_lenth:
                try:
                    edges, edges_offset = self._notes_repo.get_comment_edges_to_process(
                        limit=edges_limit, offset=edges_offset
                    )
                    self.graph.add_edges_from(edges)
                except Exception as e:
                    print("Ошибочка вышла: ", e)
                if edges_offset / edges_limit % 10 == 0:
                    with open("friends_friends.pkl", "wb") as output:
                        pickle.dump(self.graph, output, pickle.HIGHEST_PROTOCOL)
                main_pbar.update(edges_limit)
        return self.graph
