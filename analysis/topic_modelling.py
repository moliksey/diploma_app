from hdbscan import HDBSCAN
from sentence_transformers import SentenceTransformer
from umap import UMAP

from dto import *
from repository import *


class TopicModelingService:
    def __init__(self, note_repo: NoteRepository, topic_repo: TopicRepo):
        self._note_repo = note_repo
        self._topic_repo = topic_repo
        self.model = None

        # Настройка модели BERTopic
        self.embedding_model = SentenceTransformer(
            "intfloat/multilingual-e5-large"
        )  # или "paraphrase-multilingual-MiniLM-L12-v2"

        self.umap_model = UMAP(
            n_neighbors=15, n_components=5, min_dist=0.0, metric="cosine", random_state=42
        )

        self.hdbscan_model = HDBSCAN(
            min_cluster_size=10,
            metric="euclidean",
            cluster_selection_method="eom",
            prediction_data=True,
        )

    def analyze_thread(self, thread_posts: List[Dict]) -> Dict:
        """
        Анализирует весь тред и определяет тему

        Args:
            thread_posts: Список постов в треде с полями id, msg, creator

        Returns:
            {
                "topic_id": int,
                "topic_probability": float,
                "topic_name": str,
                "keywords": List[Dict]
            }
        """
        # 1. Склеиваем текст всего треда (с учётом глубины)
        thread_text = self._build_thread_text(thread_posts)

        if not thread_text or len(thread_text) < 20:
            return None

        # 2. Получаем тему от модели
        if self.model is None:
            # Для первого треда - обучаем модель
            topics, probs = self.model.fit_transform([thread_text])
        else:
            # Для последующих - предсказываем
            topic_id, prob = self.model.transform([thread_text])
            topic_id = topic_id[0]

        # 3. Получаем информацию о теме
        topic_info = self.model.get_topic_info()
        topic_keywords = self.model.get_topic(topic_id)

        return {
            "topic_id": int(topic_id) if topic_id != -1 else -1,
            "topic_probability": float(prob) if topic_id != -1 else 0.0,
            "topic_name": topic_info[topic_info.Topic == topic_id]["Name"].values[0]
            if topic_id != -1
            else "Outliers",
            "keywords": [
                {"word": word, "weight": float(weight)} for word, weight in topic_keywords[:10]
            ],
        }

    def _build_thread_text(self, thread_posts: List[Dict]) -> str:
        """
        Склеивает текст треда в один документ с учётом иерархии
        """
        # Сортируем по глубине (сначала пост, потом комментарии)
        sorted_posts = sorted(thread_posts, key=lambda x: x.get("depth", 0))

        text_parts = []
        for post in sorted_posts:
            if post.get("msg") and len(post["msg"].strip()) > 0:
                # Добавляем маркеры глубины для контекста
                depth = post.get("depth", 0)
                indent = "  " * depth
                text_parts.append(f"{indent}{post['msg']}")

        return "\n".join(text_parts)

    def batch_analyze(self, network_id: int, batch_size: int = 100):
        """
        Пакетный анализ всех постов/тредов
        """
        unanalyzed = self._note_repo.get_unanalyzed_posts(network_id, limit=batch_size)

        # Группируем по тредам (parent = NULL - корневые посты)
        threads = {}
        for post in unanalyzed:
            if post["parent"] is None:
                # Это корневой пост - анализируем весь тред
                thread_posts = self._note_repo.get_thread_posts(post["id"])
                threads[post["id"]] = thread_posts

        # Анализируем каждый тред
        for thread_id, thread_posts in threads.items():
            result = self.analyze_thread(thread_posts)

            if result:
                # Сохраняем тему
                topic_dto = TopicDTO(
                    topic_id=result["topic_id"],
                    topic_name=result["topic_name"],
                    topic_description=" ".join([kw["word"] for kw in result["keywords"][:5]]),
                    keywords=result["keywords"],
                    representative_docs=[thread_posts[0]["msg"]],
                    frequency=1,
                )
                self._note_repo.save_topic(topic_dto)

                # Сохраняем связь для каждого поста в треде
                for post in thread_posts:
                    note_topic_dto = Note(
                        note_id=post["id"],
                        thread_id=thread_id,
                        topic_id=result["topic_id"],
                        topic_probability=result["topic_probability"],
                        is_thread_based=True,
                    )
                    self._note_repo.save_note_topic(note_topic_dto)
