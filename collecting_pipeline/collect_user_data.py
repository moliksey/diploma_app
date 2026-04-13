import time

import tqdm

from config import DB_CONFIG
from dto import *
from repository import *
from network_api_service.default_network_api_service import DefaultNetworkApiService
from network_api_service import network_api_service_factory
class PiplineCollector():

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
        self.analising_creator = self.creators_repo.create(Creator(None, user_external_id, True, self.working_network.id))

    def get_groups_users(self, offset=0):
        lenth = self.creators_repo.count_people_by_network(self.working_network.id)
        new_offset = offset

        # Прогресс-бар для основного цикла
        with tqdm.tqdm(total=lenth, initial=offset, desc="Processing groups") as pbar:
            while new_offset < lenth:

                peoples, new_offset = self.creators_repo.get_users_to_process(offset=new_offset, isperson=False)
                # Прогресс-бар для обработки пользователей в текущем батче
                for creator in tqdm.tqdm(peoples, desc=f"Batch {offset}-{new_offset}", leave=False):
                    try:
                        friends_out = self.network_api_service.get_friends(creator.external_id)
                        #TODO Следующий шаг - сохранить друзей   
                    except Exception as e:
                        if "This profile is private" not in str(e):
                            print(f"Error with processing batch: {e}")
                            print(new_offset)
                    
                # Обновляем основной прогресс-бар
                pbar.update(len(peoples))

        return new_offset
