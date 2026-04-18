from dto import Creator, Note


class DefaultNetworkApiService:
    def get_friends(self, creator: Creator) -> list[Creator]:
        """Метод возвращает друзей актора"""
        pass

    def get_groups(self, creator: Creator) -> list[Creator]:
        """Метод возвращает группы актора"""
        pass

    def get_post(self, creator: Creator, start_time: int) -> list[Note]:
        """Метод возвращает посты актора за период начиная с start_time"""
        pass

    def get_comments(self, post: Note) -> list[Note]:
        """Метод возвращает посты актора за период начиная с start_time"""
        pass

    def get_likes(self, post: Note) -> list[Note]:
        """Метод возвращает посты актора за период начиная с start_time"""
        pass
