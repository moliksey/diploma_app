from typing import Dict, List, Optional
import os

from bertopic import BERTopic
from hdbscan import HDBSCAN
from sentence_transformers import SentenceTransformer
from umap import UMAP

from dto import *
from repository import *


class TopicModelingService:
    def __init__(self, note_repo: NoteRepository):
        self._note_repo = note_repo
        self.MIN_TOPIC_PROBABILITY = 0.6
        self.model = None
        self.is_fitted = False
        
        # Настройки для инкрементального обучения
        self.new_texts_buffer = []  # Буфер для новых текстов
        self.buffer_size_for_update = 1000  
        self.buffer_offset = 0 
        
        # Настройка модели BERTopic
        self.embedding_model = SentenceTransformer(
            "intfloat/multilingual-e5-large"
        )

        self.umap_model = UMAP(
            n_neighbors=35, n_components=8, min_dist=0.1, metric="cosine", random_state=42
        )

        self.hdbscan_model = HDBSCAN(
            min_cluster_size=25,
            metric="euclidean",
            cluster_selection_method="eom",
            prediction_data=True,
        )

    def _get_or_create_model(self) -> BERTopic:
        """Создаёт или возвращает существующую модель"""
        if self.model is None:
            self.model = BERTopic(
                embedding_model=self.embedding_model,
                umap_model=self.umap_model,
                hdbscan_model=self.hdbscan_model,
                verbose=True
            )
        return self.model

    def _save_model(self, model: BERTopic, filepath: str = "bertopic_model.pkl"):
        """Сохраняет модель на диск"""
        self.model = model
        if self.model and self.is_fitted:
            try:
                self.model.save(filepath)
                print(f"✅ Модель сохранена в {filepath}")
            except Exception as e:
                print(f"❌ Ошибка сохранения модели: {e}")

    def _load_model(self, filepath: str = "bertopic_model.pkl") -> bool:
        """Загружает модель с диска"""
        if os.path.exists(filepath):
            try:
                self.model = BERTopic.load(filepath)
                self.is_fitted = True
                print(f"✅ Модель загружена из {filepath}")
                return True
            except Exception as e:
                print(f"❌ Ошибка загрузки модели: {e}")
        return False

    def initialize_model(self, network_id: int, force_retrain: bool = False):
        """
        Инициализирует модель:
        1. Пытается загрузить сохранённую модель
        2. Если нет или force_retrain=True - обучает на всех исторических данных батчами
        """
        if not force_retrain and self._load_model():
            return
        
        if force_retrain:
            self.buffer_offset = 0 
        print("🔄 Начинаем обучение модели на исторических данных...")
        # Получаем все исторические треды из БД
        all_threads, self.buffer_offset = self._note_repo.get_threads_to_analize(network_id, offset=self.buffer_offset, limit=self.buffer_size_for_update)
        
        if len(all_threads) < 10:
            print(f"⚠️ Недостаточно данных для обучения: {len(all_threads)}/10")
            return
        
        # Собираем тексты тредов
        documents = self._get_texts(all_threads)
        
        print(f"📚 Обучаем модель на {len(documents)} тредах...")
        
        # Обучаем модель
        model = self._get_or_create_model()
        topics,  = model.fit_transform(documents)
        self.is_fitted = True
        
        # Сохраняем модель
        self._save_model(model)
        
        threads_count= self._note_repo.get_threads_count(network_id)

        while self.buffer_offset < threads_count:
            thread_batch, self.buffer_offset = self._note_repo.get_threads_to_analize(network_id, offset=self.buffer_offset, limit=self.buffer_size_for_update)
            documents = self._get_texts(thread_batch)
            self._update_model_with_new_texts(documents)

    def _get_texts(self, all_threads: List[Dict]) -> List[str]:
        """Получает тексты для обучения модели"""
        # Здесь можно реализовать логику получения текстов из БД или других источников
        documents = []
        for thread in all_threads:
            thread_posts = self._note_repo.get_thread_posts(thread["id"])
            thread_text = self._build_thread_text(thread_posts)
            if thread_text and len(thread_text) >= 20:
                documents.append(thread_text)
        return documents
    
    def _update_model_with_new_texts(self, new_texts: List[str]):
        """
        Инкрементально обновляет модель новыми текстами
        """
        if not self.is_fitted or not new_texts:
            return
        try:
            self.model.partial_fit(new_texts)
        except Exception as e:
            print(f"⚠️ Ошибка при обновлении модели: {e}")
            print("Рекомендуется полное переобучение через force_retrain=True")

    def analyze_thread(self, thread_posts: List[Dict]) -> Optional[Dict]:
        """
        Анализирует весь тред и определяет тему
        """
        # Проверяем, инициализирована ли модель
        if not self.is_fitted or self.model is None:
            print("⚠️ Модель не инициализирована. Вызовите initialize_model() сначала")
            return None
        
        # Склеиваем текст треда
        thread_text = self._build_thread_text(thread_posts)

        if not thread_text or len(thread_text) < 20:
            return None
        
        # Получаем тему от модели
        try:
            topic_ids, probs = self.model.transform([thread_text])
            topic_id = topic_ids[0]
            prob = probs[0] if probs is not None else 1.0
        except Exception as e:
            print(f"❌ Ошибка при предсказании темы: {e}")
            return None

        # Получаем информацию о теме
        if topic_id != -1 and prob >= self.MIN_TOPIC_PROBABILITY:
            try:
                topic_info = self.model.get_topic_info()
                topic_keywords = self.model.get_topic(topic_id)
                
                topic_name_row = topic_info[topic_info.Topic == topic_id]
                if len(topic_name_row) > 0:
                    topic_name = topic_name_row["Name"].values[0]
                else:
                    topic_name = f"Topic_{topic_id}"
            except Exception as e:
                print(f"❌ Ошибка получения информации о теме: {e}")
                topic_name = "Outliers"
                topic_keywords = []
        else:
            topic_name = "Outliers"
            topic_keywords = []

        return {
            "topic_id": int(topic_id) if topic_id != -1 else -1,
            "topic_probability": float(prob) if topic_id != -1 else 0.0,
            "topic_name": topic_name,
            "keywords": [
                {"word": word, "weight": float(weight)} 
                for word, weight in (topic_keywords[:10] if topic_keywords else [])
            ],
        }

    def _build_thread_text(self, thread_posts: List[Dict]) -> str:
        """Склеивает текст треда в один документ с учётом иерархии"""
        sorted_posts = sorted(thread_posts, key=lambda x: x.get("depth", 0))

        text_parts = []
        for post in sorted_posts:
            if post.get("msg") and len(post["msg"].strip()) > 0:
                depth = post.get("depth", 0)
                indent = "  " * depth
                text_parts.append(f"{indent}{post['msg']}")

        return "\n".join(text_parts)

    def batch_analyze(self, network_id: int, batch_size: int = 100):
        """
        Пакетный анализ всех постов/тредов
        """
        # Инициализируем модель, если ещё не инициализирована
        if not self.is_fitted:
            self.initialize_model(network_id)
        
        unanalyzed = self._note_repo.get_unanalyzed_posts(network_id, limit=batch_size)
        
        if not unanalyzed:
            print("📭 Нет неанализированных постов")
            return

        # Группируем по тредам
        threads = {}
        for post in unanalyzed:
            if post["parent"] is None:
                thread_posts = self._note_repo.get_thread_posts(post["id"])
                threads[post["id"]] = thread_posts

        print(f"📊 Анализируем {len(threads)} тредов...")
        
        # Анализируем каждый тред
        analyzed_count = 0
        topics_cache = {}  # Кеш для тем, чтобы не сохранять метаданные темы много раз
        
        for thread_id, thread_posts in threads.items():
            result = self.analyze_thread(thread_posts)

            if result and result["topic_id"] != -1:
                # Сохраняем метаданные темы только если её ещё нет в кеше
                if result["topic_id"] not in topics_cache:
                    topic_dto = Topic(
                        topic_id=result["topic_id"],
                        topic_name=result["topic_name"],
                        keywords=result["keywords"],
                    )
                    self._note_repo.save_topic(topic_dto)
                    topics_cache[result["topic_id"]] = True

                # Сохраняем связь для каждого поста в треде
                for post in thread_posts:
                    note_topic_dto = NoteTopic(
                        note_id=post["id"],
                        topic_id=result["topic_id"],
                        topic_probability=result["topic_probability"],
                        is_thread_based=True,
                    )
                    self._note_repo.save_note_topic(note_topic_dto)
                    analyzed_count += 1
        
        print(f"✅ Проанализировано {analyzed_count} постов в {len(threads)} тредах")
        
    def force_retrain(self, network_id: int):
        """
        Принудительное полное переобучение модели на всех данных
        """
        print("🔄 Принудительное полное переобучение модели...")
        self.initialize_model(network_id, force_retrain=True)