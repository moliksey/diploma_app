import time

import vk_api

from dto import Creator, NetworkType, Note
from network_api_service.default_network_api_service import DefaultNetworkApiService


class VKService(DefaultNetworkApiService):
    def __init__(self, token: str) -> vk_api.VkTools:
        self.network = self.networks_repo.get_or_create(NetworkType.VK.value)
        self.vkApiSession = vk_api.VkApi(token)
        self.vkU = self.vkApiSession.get_api()
        self.tools = vk_api.VkTools(self.vkU)
        self.max_count = 5000

    def get_friends(self, creator: Creator) -> list[Creator]:
        try:
            friends_out = self.tools.get_all(
                "friends.get", self.max_count, {"user_id": creator.external_id}
            )
            new_friends = [
                Creator(None, ext_id, True, self.network.id) for ext_id in friends_out["items"]
            ]
            time.sleep(1)
        except Exception as e:
            if "This profile is private" not in str(e):
                print(f"Error with processing batch: {e}")
                raise e
        return new_friends

    def get_groups(self, creator: Creator) -> list[Creator]:
        try:
            groups_data = self.tools.get_all(
                "groups.get", max_count=1000, values={"user_id": creator.external_id, "extended": 0}
            )
            new_groups = [
                Creator(None, ext_id, False, self.network.id) for ext_id in groups_data["items"]
            ]
            return new_groups
        except Exception as e:
            if "This profile is private" not in str(e):
                print(f"Error with processing batch: {e}")
                raise e

    def get_post(self, creator: Creator, start_time: int) -> list[Note]:
        """Метод возвращает посты актора"""
        try:
            items = self.tools.get_all("wall.get", 100, {"owner_id": creator.external_id})
            # Формируем запись только для свежих постов
            posts = [
                Note(
                    None, post["text"], "vk/" + str(post["id"]) + "/", None, creator.id, post["id"]
                )
                for post in items
                if post["date"] < start_time
            ]
            return posts
        except Exception as e:
            if "This profile is private" not in str(e):
                print(f"Error with processing batch: {e}")
                raise e

    def get_comments(self, post: Note) -> list[Note]:
        """
        Метод возвращает комментарии к посту
        Документация VK: wall.getComments
        """
        try:
            comments_data = self.tools.get_all(
                "wall.getComments",
                max_count=100,
                values={
                    "post_id": post.external_id,
                    "need_likes": 1,  # Получаем информацию о лайках комментариев
                    "extended": 1,  # Получаем информацию об авторах комментариев
                },
            )
            comments = []
            for comment in comments_data.get("items", []):
                # Создаем Note для комментария
                comment_note = Note(
                    id=None,
                    msg=comment.get("text", ""),
                    img=f"vk/comment_{comment['id']}/",
                    parent=post.id,  # parent указывает на ID поста
                    creator=comment.get(
                        "from_id"
                    ),  # FIXME подвязать к пользователю через id наверное с помощью get_or_create
                    external_id=comment["id"],
                )
                comments.append(comment_note)

                # Рекурсивно получаем ответы на комментарии
                if comment.get("thread", {}).get("count", 0) > 0:
                    replies = self._get_comment_replies(post, comment_note)
                    comments.extend(replies)

            time.sleep(0.5)  # Задержка для соблюдения лимитов API
            return comments

        except Exception as e:
            if "This profile is private" not in str(e):
                print(f"Error getting comments for post {post.external_id}: {e}")
            return []

    def _get_comment_replies(self, post: Note, comment: Note) -> list[Note]:
        """
        Вспомогательный метод для получения ответов на комментарий
        """
        try:
            replies_data = self.tools.get_all(
                "wall.getComments",
                max_count=100,
                values={
                    "post_id": post.external_id,
                    "comment_id": comment.external_id,
                    "need_likes": 1,
                    "extended": 1,
                },
            )

            replies = []
            for reply in replies_data.get("items", []):
                reply_note = Note(
                    id=None,
                    msg=reply.get("text", ""),
                    img=f"vk/comment_{reply['id']}/",
                    parent=comment.id,  # parent указывает на ID комментария
                    creator=reply.get(
                        "from_id"
                    ),  # FIXME подвязать к пользователю через id наверное с помощью get_or_create
                    external_id=reply["id"],
                )
                replies.append(reply_note)

            return replies

        except Exception as e:
            print(f"Error getting replies for comment {comment.external_id}: {e}")
            return []

    def get_likes(self, post: Note) -> list[Creator]:
        """
        Метод возвращает список пользователей, которые лайкнули пост
        Документация VK: likes.getList
        """
        try:
            # Получаем список лайкнувших пост
            likes_data = self.tools.get_all(
                "likes.getList",
                max_count=1000,
                values={
                    "type": "post",
                    "owner_id": post.creator,  # FIXME изменить на external если решу на 71 и 112
                    "item_id": post.external_id,
                    "filter": "likes",  # Только лайки (не копии)
                    "extended": 1,  # Получаем расширенную информацию о пользователях
                },
            )

            # Создаем список Creator для пользователей, которые лайкнули пост
            liked_users = []
            for user in likes_data.get("items", []):
                # user может быть как ID, так и объект с данными
                if isinstance(user, dict):
                    user_id = user.get("id")
                else:
                    user_id = user

                liked_user = Creator(
                    id=None, external_id=user_id, is_person=True, network_type=self.network.id
                )
                liked_users.append(liked_user)

            time.sleep(0.5)  # Задержка для соблюдения лимитов API
            return liked_users

        except Exception as e:
            print(f"Error getting likes for post {post.external_id}: {e}")
            return []
