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

    def run_pipeline(self, offset=0):
        """Запуск пайплайна сбора данных"""
        self.parse_users(offset)


    def add_creators_friends(self, creator, friends):
        """Добавление друзей создателя в базу и создание подписок"""
        try:
            friends_saved=self.creators_repo.create_many_creators(friends)
            if friends_saved:
                self.subs_repo.create_many_friends([Sub(creator.id, friend_saved.id) for friend_saved in friends_saved])
            return friends_saved
        except Exception as e:
                print(f"❌ Ошибка: {e}")
                return None, []
        
    def parse_users(self, offset=0):
        length = self.creators_repo.count_people_by_network(self.working_network.id)
        new_offset = offset
        with tqdm.tqdm(total=length, initial=offset, desc="Processing groups", unit="users") as pbar:
            while new_offset < length:
                peoples, new_offset = self.creators_repo.get_users_to_process(
                    offset=new_offset, isperson=True
                )
                
                if not peoples:
                    print(f"Warning: Empty batch received at offset {new_offset}")
                    break
                
                # Обработка пользователей в текущем батче
                for creator in peoples:
                    try:
                        friends_out = self.network_api_service.get_friends(creator.external_id)
                        self.add_creators_friends(creator, friends_out)
                    except Exception as e:
                        if "Rate limit exceeded" in str(e) or "flood control" in str(e):
                            print("Rate limit hit, sleeping for 15 minutes...")
                            return new_offset  # Возвращаем текущий offset для продолжения позже
                    finally:
                        pbar.update(1)

        return new_offset
    
    def save_subscriptions(self, offset: int = 0):
        
        total_users = self.creators_repo.count_people_by_network(self.working_network.id)
        
        print(f"Всего пользователей для обработки: {total_users}")
        print(f"Начинаем с offset: {offset}")
        
        # Основной прогресс-бар для всех пользователей
        with tqdm.tqdm(total=total_users, initial=offset, desc="Все пользователи", 
                    unit="пользователь", unit_scale=False, dynamic_ncols=True) as main_pbar:
            
            while offset < total_users:
                try:
                    peoples, offset = self.creators_repo.get_users_to_process(offset=offset, isperson=True)
                    if not peoples:
                        print(f"Warning: Empty batch received at offset {offset}")
                        break       

                    # Вложенный прогресс-бар для текущего батча
                    for creator in tqdm.tqdm(
                        peoples, 
                        desc=f"Батч {offset-len(peoples)}-{offset}",
                        leave=False,
                        unit="пользователь"
                    ):
                        try:
                            groups_data = None
                            try:
                                groups_data = self.network_api_service.get_groups(creator.external_id)
                            except Exception as e:
                                if "flood control" in str(e):
                                    print(f"\nОграничение API для пользователя {creator_ext_id}: {e}")
                                    print("Делаем паузу 60 секунд...")
                                    return offset
                            
                            if groups_data and "items" in groups_data:
                                self.creators_repo.create_many_creators(groups_data)
                            
                            # Небольшая задержка между запросами
                            time.sleep(0.2)
                            
                        except Exception as e:
                            print(f"\nКритическая ошибка при обработке пользователя {creator_ext_id}: {e}")
                            conn.rollback()
                            continue
                    
                    # Обновляем основной прогресс-бар
                    main_pbar.update(len(peoples))
                    main_pbar.set_postfix({"offset": offset, "осталось": total_users-offset})
                    
                    # Сохраняем текущий прогресс каждые 100 пользователей
                    if offset % 100 == 0:
                        print(f"\nПрогресс сохранен. Обработано: {offset} из {total_users}")
                    
                except Exception as e:
                    print(f"\nОшибка при обработке батча: {e}")
                    print(f"Текущий offset: {offset}")
                    # Пауза при серьезных ошибках
                    time.sleep(10)
                    break
        
        print(f"\nОбработка завершена. Итоговый offset: {offset}")
        return offset