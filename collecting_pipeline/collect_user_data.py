import time

import tqdm

from config import DB_CONFIG
from dto import *
from network_api_service import getNetworkApiService
from repository import *


class PiplineCollector:
    def __init__(self, user_external_id: int, network: NetworkType, creds: dict):
        """Инициализация коллектора с инъекцией репозиториев"""

        # Параметры подключения к БД
        db_params = DB_CONFIG.to_dict()

        # Инъекция всех репозиториев
        self._networks_repo = NetworkRepository(db_params)
        self._creators_repo = CreatorRepository(db_params)
        self._notes_repo = NoteRepository(db_params)
        self._subs_repo = SubRepository(db_params)
        self._likes_repo = LikeRepository(db_params)
        self._working_network = self._networks_repo.get_or_create(network.name)
        self._network_api_service = getNetworkApiService(
            network=network,
            creds=creds,
            creator_repo=self._creators_repo,
            network_repo=self._networks_repo,
        )
        # Инициализация пользователя
        self._analising_creator = self._creators_repo.create(
            Creator(None, user_external_id, True, self._working_network.id)
        )

    def _process_batch_with_pbar(self, total, desc, unit, processor_func, offset_start=0):
        """Универсальный метод для обработки данных с прогресс-баром"""
        offset = offset_start

        with tqdm.tqdm(total=total, initial=offset, desc=desc, unit=unit) as pbar:
            while offset < total:
                try:
                    offset = processor_func(offset, pbar)
                except Exception as e:
                    if "flood control" in str(e) or "Rate limit exceeded" in str(e):
                        print("⚠️ Лимит API, пауза 60 сек...")
                        time.sleep(60)
                        continue
                    print(f"❌ Критическая ошибка: {e}")
                    return offset
        return offset

    def _process_entity_batch(self, get_entities_func, process_entity_func, offset, pbar):
        """Обрабатывает батч сущностей (пользователей, постов и т.д.)"""
        entities, new_offset = get_entities_func(offset)

        if not entities:
            print(f"Warning: Empty batch received at offset {offset}")
            return offset

        for entity in entities:
            try:
                process_entity_func(entity)
            except Exception as e:
                self._handle_processing_error(e, entity)
                if self._is_rate_limit_error(e):
                    raise e
            finally:
                pbar.update(1)

        return new_offset

    def _is_rate_limit_error(self, error):
        """Проверяет, является ли ошибка ограничением API"""
        error_msg = str(error)
        return "flood control" in error_msg or "Rate limit exceeded" in error_msg

    def _handle_processing_error(self, error, entity):
        """Обрабатывает ошибки обработки"""
        error_msg = str(error)
        if "flood control" in error_msg:
            print(f"⚠️ Ограничение API при обработке {getattr(entity, 'external_id', entity)}")
        else:
            print(f"❌ Ошибка при обработке {getattr(entity, 'external_id', entity)}: {error}")

    # ========== МЕТОДЫ ДЛЯ РАЗНЫХ ТИПОВ ДАННЫХ ==========

    def _parse_users(self, first_offset=0):
        """Сбор пользователей и их друзей"""
        total = self._creators_repo.count_people_by_network(self._working_network.id)

        def process_user_batch(offset, pbar):
            peoples, new_offset = self._creators_repo.get_users_to_process(
                offset=offset, isperson=True
            )

            for creator in peoples:
                try:
                    friends = self._network_api_service.get_friends(creator)
                    self._add_creators_friends(creator, friends)
                except Exception as e:
                    if self._is_rate_limit_error(e):
                        raise e
                finally:
                    pbar.update(1)

            return new_offset

        return self._process_batch_with_pbar(
            total, "Сбор пользователей", "users", process_user_batch, first_offset
        )

    def _parse_subscriptions(self, first_offset=0):
        """Сбор подписок пользователей на группы"""
        total = self._creators_repo.count_people_by_network(self._working_network.id)

        def process_subscription_batch(offset, pbar):
            peoples, new_offset = self._creators_repo.get_users_to_process(
                offset=offset, isperson=True
            )

            for creator in peoples:
                try:
                    groups = self._network_api_service.get_groups(creator)
                    if groups:
                        self._creators_repo.create_many_creators(groups)
                        self._subs_repo.subscribe_for_many(creator, groups)
                except Exception as e:
                    if self._is_rate_limit_error(e):
                        raise e
                finally:
                    pbar.update(1)

            return new_offset

        return self._process_batch_with_pbar(
            total, "Сбор подписок", "users", process_subscription_batch, first_offset
        )

    def _parse_posts(self, offset_start=0):
        """Сбор постов пользователей"""
        total = self._creators_repo.count_people_by_network(self._working_network.id)
        two_weeks_ago = int(time.time()) - (14 * 24 * 60 * 60)

        def process_posts_batch(offset, pbar):
            peoples, new_offset = self._creators_repo.get_users_to_process(
                offset=offset, isperson=False
            )

            for creator in peoples:
                try:
                    posts = self._network_api_service.get_post(creator, two_weeks_ago)
                    self._notes_repo.create_many_posts(posts)
                except Exception as e:
                    if self._is_rate_limit_error(e):
                        raise e
                finally:
                    pbar.update(1)

            return new_offset

        return self._process_batch_with_pbar(
            total, "Сбор постов", "users", process_posts_batch, offset_start
        )

    def _parse_comments(self, offset_start=0):
        """Сбор комментариев к постам"""
        total = self._notes_repo.count_posts_by_network(self._working_network.id)

        def process_comments_batch(offset, pbar):
            posts, new_offset = self._notes_repo.get_posts_to_process(
                offset=offset, limit=self._batch_size, network_id=self._working_network.id
            )

            for post in posts:
                try:
                    comments = self._network_api_service.get_comments(post.external_id)
                    self._save_comments_with_authors(post, comments)
                    time.sleep(self._api_delay)
                except Exception as e:
                    print(f"Ошибка для поста {post.external_id}: {e}")
                finally:
                    pbar.update(1)

            return new_offset

        return self._process_batch_with_pbar(
            total, "Сбор комментариев", "постов", process_comments_batch, offset_start
        )

    def _parse_reacts(self, offset_start=0):
        """Сбор реакций (лайков) к постам"""
        total = self._notes_repo.count_posts_by_network(self._working_network.id)

        def process_reacts_batch(offset, pbar):
            posts, new_offset = self._notes_repo.get_posts_to_process(
                offset=offset, limit=self._batch_size, network_id=self._working_network.id
            )

            for post in posts:
                try:
                    liked_users = self._network_api_service.get_likes(post.external_id)
                    self._save_likes_with_users(post, liked_users)
                    time.sleep(self._api_delay)
                except Exception as e:
                    print(f"Ошибка для поста {post.external_id}: {e}")
                finally:
                    pbar.update(1)

            return new_offset

        return self._process_batch_with_pbar(
            total, "Сбор лайков", "постов", process_reacts_batch, offset_start
        )

    # ========== ВСПОМОГАТЕЛЬНЫЕ МЕТОДЫ ==========

    def _add_creators_friends(self, creator, friends):
        """Добавление друзей создателя в базу и создание подписок"""
        try:
            friends_saved = self._creators_repo.create_many_creators(friends)
            if friends_saved:
                self._subs_repo.create_many_friends(
                    [Sub(creator.id, friend_saved.id) for friend_saved in friends_saved]
                )
            return friends_saved
        except Exception as e:
            print(f"❌ Ошибка при сохранении друзей: {e}")
            return None

    def _save_comments_with_authors(self, post, comments):
        """Сохраняет комментарии и их авторов"""
        if not comments:
            return

        saved_comments = self._notes_repo.create_many_posts(comments)
        if not saved_comments:
            return

        self.stats["comments_processed"] = self.stats.get("comments_processed", 0) + len(
            saved_comments
        )

        # Создаем авторов комментариев
        comment_authors = [
            Creator(None, comment.creator, True, self._working_network.id)
            for comment in saved_comments
            if comment.creator
        ]

        if comment_authors:
            self._creators_repo.create_many_creators(comment_authors)

    def _save_likes_with_users(self, post, liked_users):
        """Сохраняет лайки и пользователей"""
        if not liked_users:
            return

        saved_users = self._creators_repo.create_many_creators(liked_users)
        if not saved_users:
            return

        self.stats["likes_processed"] = self.stats.get("likes_processed", 0) + len(saved_users)

        likes = [Like(post.id, user.id) for user in saved_users]
        if likes:
            self._likes_repo.create_many_likes(likes)
