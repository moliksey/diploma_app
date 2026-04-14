import time
from typing import List
from dto import Creator, NetworkType
import vk_api
from network_api_service.default_network_api_service import DefaultNetworkApiService

class VKService(DefaultNetworkApiService):
    def __init__(self, token: str) -> vk_api.VkTools:
        self.network=self.networks_repo.get_or_create(NetworkType.VK.value)
        self.vkApiSession = vk_api.VkApi(token)
        self.vkU = self.vkApiSession.get_api()
        self.tools=vk_api.VkTools(self.vkU)
        self.max_count=5000

    def get_friends(self, creator_ext_id: int)-> List[Creator]:
        try:
            friends_out = self.tools.get_all('friends.get', self.max_count, {'user_id': creator_ext_id})
            new_friends=[Creator(None, ext_id, True, self.network.id) for ext_id in friends_out['items']]
            time.sleep(1)
        except Exception as e:
            if "This profile is private" not in str(e):
                print(f"Error with processing batch: {e}")
                raise e
        return new_friends
    
    def get_groups(self, creator_ext_id: int) -> List[Creator]:
        try:
            groups_data = self.tools.get_all('groups.get', max_count=1000, 
                                             values={'user_id': creator_ext_id, 'extended': 0})
            new_groups=[Creator(None, ext_id, False, self.network.id) for ext_id in groups_data['items']]
        except Exception as e:
            if "This profile is private" not in str(e):
                print(f"Error with processing batch: {e}")
                raise e
        return new_groups