import time

import tqdm

from config import DB_CONFIG
from dto import *
from network_api_service import network_api_service_factory
from repository import *


class PiplineCollector:
    def __init__(self, user_external_id: int, network: NetworkType, creds: dict):
        """Инициализация коллектора с инъекцией репозиториев"""

        # Параметры подключения к БД
        db_params = DB_CONFIG.to_dict()

        # Инъекция всех репозиториев
        self.networks_repo = NetworkRepository(db_params)
        self.creators_repo = CreatorRepository(db_params)
        self.notes_repo = NoteRepository(db_params)
        self.subs_repo = SubRepository(db_params)
        self.likes_repo = LikeRepository(db_params)
        self.working_network = self.networks_repo.get_or_create(network.name)
        self.network_api_service = network_api_service_factory.getNetworkApiService(network, creds)
        # Инициализация пользователя
        self.analising_creator = self.creators_repo.create(
            Creator(None, user_external_id, True, self.working_network.id)
        )

    def run_pipeline(self, offset=0, groups_offset=0, post_offset=0):
        """Запуск пайплайна сбора данных"""
        self.parse_users(offset)
        self.parse_subscriptions(groups_offset)
        self.parse_posts(post_offset)
        self.parse_comments()
        self.parse_reacts()

    def parse_users(self, first_offset=0):
        total_users = self.creators_repo.count_people_by_network(self.working_network.id)
        offset = first_offset
        with tqdm.tqdm(
            total=total_users, initial=0, desc="Processing groups", unit="users"
        ) as pbar:
            while offset < total_users:
                peoples, offset = self.creators_repo.get_users_to_process(
                    offset=offset, isperson=True
                )
                if not peoples:
                    print(f"Warning: Empty batch received at offset {offset}")
                    continue
                try:
                    self._process_user_batch(peoples, pbar, offset)
                except Exception:
                    return offset
        return offset

    def _process_user_batch(self, peoples: list[Creator], pbar) -> int:
        for creator in peoples:
            try:
                friends_out = self.network_api_service.get_friends(creator)
                self._add_creators_friends(creator, friends_out)
            except Exception as e:
                if "Rate limit exceeded" in str(e) or "flood control" in str(e):
                    raise e
            finally:
                pbar.update(1)

    def _add_creators_friends(self, creator, friends):
        """Добавление друзей создателя в базу и создание подписок"""
        try:
            friends_saved = self.creators_repo.create_many_creators(friends)
            if friends_saved:
                self.subs_repo.create_many_friends(
                    [Sub(creator.id, friend_saved.id) for friend_saved in friends_saved]
                )
            return friends_saved
        except Exception as e:
            print(f"❌ Ошибка: {e}")
            return None, []

    def parse_subscriptions(self, first_offset: int = 0):
        total_users = self.creators_repo.count_people_by_network(self.working_network.id)
        offset = first_offset
        with tqdm.tqdm(
            total=total_users, initial=0, desc="Processing groups", unit="users"
        ) as main_pbar:
            while offset < total_users:
                try:
                    peoples, offset = self.creators_repo.get_users_to_process(
                        offset=offset, isperson=True
                    )
                    if not peoples:
                        print(f"Warning: Empty batch received at offset {offset}")
                        break
                    self._process_group_batch(peoples, main_pbar)
                except Exception:
                    return offset
        return offset

    def _process_group_batch(self, peoples: list[Creator], pbar) -> int:
        for creator in peoples:
            try:
                groups = self.network_api_service.get_groups(creator)
                if groups:
                    self.creators_repo.create_many_creators(groups)
                    self.subs_repo.subscribe_for_many(creator, groups)
            except Exception as e:
                print(f"\nКритическая ошибка при обработке пользователя {creator.external_id}: {e}")
                if "flood control" in str(e):
                    print(f"\nОграничение API для пользователя {creator.external_id}: {e}")
                    raise e
            finally:
                pbar.update(1)

    def parse_posts(self, offset_start: int = 0):
        total_users = self.creators_repo.count_people_by_network(self.working_network.id)
        two_weeks_ago = int(time.time()) - (14 * 24 * 60 * 60)
        offset = offset_start
        with tqdm.tqdm(
            total=total_users, initial=0, desc="Processing groups", unit="users"
        ) as pbar:
            while offset < total_users:
                peoples, offset = self.creators_repo.get_users_to_process(
                    offset=offset, isperson=False
                )
                for creator in peoples:
                    try:
                        posts = self.network_api_service.get_post(creator, two_weeks_ago)
                        self.notes_repo.create_many_posts(posts)
                    except Exception as e:
                        print(
                            f"\nКритическая ошибка при обработке пользователя {creator.external_id}: {e}"
                        )
                        if "flood control" in str(e):
                            print(f"Error with processing batch: {e}")
                            print(e)
                            return offset
                    finally:
                        pbar.update(1)

    def parse_comments(self, offset_start: int = 0):
        """Сбор комментариев к постам"""
        total_posts = self.notes_repo.count_posts_by_network(self.working_network.id)
        offset = offset_start

        with tqdm(
            total=total_posts, initial=offset, desc="Сбор комментариев", unit="постов"
        ) as pbar:
            while offset < total_posts:
                try:
                    # Получаем пакет постов
                    posts, offset = self.notes_repo.get_posts_to_process(
                        offset=offset, limit=100, network_id=self.working_network.id
                    )

                    if not posts:
                        print(f"Warning: Empty posts batch at offset {offset}")
                        break

                    self._process_comments_batch(posts, pbar)

                except Exception as e:
                    print(f"\nОшибка при сборе комментариев: {e}")
                    if "flood control" in str(e):
                        print("⚠️ Лимит API, пауза 60 сек...")
                        time.sleep(60)
                        continue
                    else:
                        return offset

        return offset

    def _process_comments_batch(self, posts: list[Note], pbar):
        """Обработка пакета постов для сбора комментариев"""
        for post in posts:
            try:
                # Получаем комментарии к посту
                comments = self.network_api_service.get_comments(post.external_id)

                if comments:
                    # Сохраняем комментарии
                    saved_comments = self.notes_repo.create_many_posts(comments)

                    if saved_comments:
                        self.stats["comments_processed"] += len(saved_comments)

                        # Создаем подписки между авторами комментариев и автором поста
                        comment_creators = [
                            Creator(None, comment.creator, True, self.working_network.id)
                            for comment in saved_comments
                            if comment.creator
                        ]

                        if comment_creators:
                            self.creators_repo.create_many_creators(comment_creators)

                time.sleep(0.3)  # Небольшая задержка между запросами

            except Exception as e:
                print(f"Ошибка при сборе комментариев для поста {post.external_id}: {e}")
            finally:
                pbar.update(1)

    def parse_reacts(self, offset_start: int = 0):
        """
        Сбор реакций (лайков) к постам
        """
        total_posts = self.notes_repo.count_posts_by_network(self.working_network.id)
        offset = offset_start

        with tqdm(total=total_posts, initial=offset, desc="Сбор лайков", unit="постов") as pbar:
            while offset < total_posts:
                try:
                    # Получаем пакет постов
                    posts, offset = self.notes_repo.get_posts_to_process(
                        offset=offset, limit=100, network_id=self.working_network.id
                    )

                    if not posts:
                        print(f"Warning: Empty posts batch at offset {offset}")
                        break

                    self._process_reacts_batch(posts, pbar)

                except Exception as e:
                    print(f"\nОшибка при сборе лайков: {e}")
                    if "flood control" in str(e):
                        print("⚠️ Лимит API, пауза 60 сек...")
                        time.sleep(60)
                        continue
                    else:
                        return offset

        return offset

    def _process_reacts_batch(self, posts: list[Note], pbar):
        """Обработка пакета постов для сбора лайков"""
        for post in posts:
            try:
                # Получаем пользователей, которые лайкнули пост
                liked_users = self.network_api_service.get_likes(post.external_id)

                if liked_users:
                    # Сохраняем пользователей, если их нет в БД
                    saved_users = self.creators_repo.create_many_creators(liked_users)

                    if saved_users:
                        self.stats["likes_processed"] += len(saved_users)

                        # Создаем записи о лайках
                        likes = []
                        for user in saved_users:
                            likes.append(Like(post.id, user.id))

                        if likes:
                            self.likes_repo.create_many_likes(likes)

                time.sleep(0.3)  # Небольшая задержка между запросами

            except Exception as e:
                print(f"Ошибка при сборе лайков для поста {post.external_id}: {e}")
            finally:
                pbar.update(1)
