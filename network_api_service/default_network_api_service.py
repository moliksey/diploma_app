from typing import List
from dto import Creator

class DefaultNetworkApiService:
    def get_friends(self, creator_ext_id: int)-> List[Creator]:
        """Метод возвращает друзей актора"""
        pass