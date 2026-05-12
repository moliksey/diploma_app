import networkx as nx
from collections import defaultdict
from typing import Any

from config import DB_CONFIG
from dto import *
from repository import *


class WorldviewGraph:
    def __init__(self, network: NetworkType):
        """Инициализация коллектора с инъекцией репозиториев"""
        self._graph = nx.Graph()

        # Параметры подключения к БД
        db_params = DB_CONFIG.to_dict()

        # Инъекция репозиториев
        self._networks_repo = NetworkRepository(db_params)
        self._creators_repo = CreatorRepository(db_params)
        self._notes_repo = NoteRepository(db_params)
        self._subs_repo = SubRepository(db_params)
        self._likes_repo = LikeRepository(db_params)
        self._social_network_repo = SocialNetworkRepository(db_params)

        # Весовые коэффициенты для графа мировоззрения
        self._weight_like = 1.0
        self._weight_comment = 1.5
        self._weight_post = 2.0

        # Текущая сеть
        self._working_network = self._networks_repo.get_or_create(network.name)

    def _get_topic_metadata(self, topic_ids: list[int]) -> dict[int, dict[str, Any]]:
        return self._notes_repo.get_topic_metadata(topic_ids)

    def _get_user_topic_records(self) -> list[dict[str, Any]]:
        return self._notes_repo.get_user_topic_records(self._working_network.id)

    def _get_likes_by_note(self) -> dict[int, int]:
        return self._notes_repo.get_likes_by_note()

    def _get_comments_by_note(self) -> dict[int, int]:
        return self._notes_repo.get_comments_by_note()

    def build_worldview_graph(self, normalize: bool = True) -> nx.Graph:
        """Строит bipartite-граф пользователей и тем мировоззрения"""
        self._graph.clear()

        records = self._get_user_topic_records()
        if not records:
            return self._graph

        likes_by_note = self._get_likes_by_note()
        comments_by_note = self._get_comments_by_note()

        user_topic_stats: dict[tuple[int, int], dict[str, float]] = defaultdict(
            lambda: {"likes": 0.0, "comments": 0.0, "posts": 0.0}
        )
        user_totals: dict[int, dict[str, float]] = defaultdict(
            lambda: {"likes": 0.0, "comments": 0.0, "posts": 0.0}
        )

        topic_ids = set()
        for row in records:
            creator_id = row["creator_id"]
            topic_id = row["topic_id"]
            note_id = row["note_id"]
            topic_ids.add(topic_id)

            likes = likes_by_note.get(note_id, 0)
            comments = comments_by_note.get(note_id, 0)

            user_topic_stats[(creator_id, topic_id)]["likes"] += likes
            user_topic_stats[(creator_id, topic_id)]["comments"] += comments
            user_topic_stats[(creator_id, topic_id)]["posts"] += 1

            user_totals[creator_id]["likes"] += likes
            user_totals[creator_id]["comments"] += comments
            user_totals[creator_id]["posts"] += 1

        topic_meta = self._get_topic_metadata(list(topic_ids))

        # Создаём узлы тем
        for topic_id in topic_ids:
            node_id = f"topic:{topic_id}"
            self._graph.add_node(
                node_id,
                bipartite="topic",
                topic_id=topic_id,
                topic_name=topic_meta.get(topic_id, {}).get("topic_name"),
            )

        # Создаём рёбра user-topic
        for (creator_id, topic_id), stats in user_topic_stats.items():
            totals = user_totals[creator_id]
            if normalize:
                like_score = stats["likes"] / totals["likes"] if totals["likes"] else 0.0
                comment_score = (
                    stats["comments"] / totals["comments"] if totals["comments"] else 0.0
                )
                post_score = stats["posts"] / totals["posts"] if totals["posts"] else 0.0
            else:
                like_score = stats["likes"]
                comment_score = stats["comments"]
                post_score = stats["posts"]

            weight = (
                self._weight_like * like_score
                + self._weight_comment * comment_score
                + self._weight_post * post_score
            )
            if weight <= 0:
                continue

            user_node = f"user:{creator_id}"
            topic_node = f"topic:{topic_id}"
            self._graph.add_node(user_node, bipartite="user", creator_id=creator_id)
            self._graph.add_edge(
                user_node,
                topic_node,
                weight=weight,
                like_score=like_score,
                comment_score=comment_score,
                post_score=post_score,
            )

        return self._graph

    def get_graph(self) -> nx.Graph:
        return self._graph
