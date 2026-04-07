from typing import List, Dict, Any, Tuple
from typing import Dict, Any, List, Optional
from dto.note_dto import Note
from dto.creator_dto import Creator
from repositories.network_repository import NetworkRepository
from repositories.creator_repository import CreatorRepository
from repositories.note_repository import NoteRepository
from repositories.sub_repository import SubRepository
from repositories.like_repository import LikeRepository

class SocialNetworkRepository:
    """Фасадный репозиторий, объединяющий все репозитории"""
    
    def __init__(self, db_params: Dict[str, Any]):
        self.db_params = db_params
        self.networks = NetworkRepository(db_params)
        self.creators = CreatorRepository(db_params)
        self.notes = NoteRepository(db_params)
        self.subs = SubRepository(db_params)
        self.likes = LikeRepository(db_params)
    
    def get_full_post_info(self, post_id: int) -> Dict[str, Any]:
        """Получить полную информацию о посте с лайками и подписками"""
        post = self.notes.get_by_id(post_id)
        if not post:
            return {}
        
        return {
            'post': post,
            'likes_count': self.likes.get_likes_count(post_id),
            'replies_count': len(self.notes.get_replies(post_id)),
            'is_liked_by_user': None,  # Нужно передать user_id
            'creator': self.creators.get_by_id(post.creator) if post.creator else None
        }
    
    def get_creator_profile(self, creator_id: int) -> Dict[str, Any]:
        """Получить полный профиль создателя"""
        creator = self.creators.get_by_id(creator_id)
        if not creator:
            return {}
        
        return {
            'creator': creator,
            'posts_count': self.notes.get_creator_posts_count(creator_id),
            'subscribers_count': self.subs.get_subscribers_count(creator_id),
            'subscriptions_count': self.subs.get_subscriptions_count(creator_id),
            'recent_posts': self.notes.get_by_creator(creator_id, limit=10),
            'top_subscribers': self.subs.get_subscribers(creator_id, limit=5)
        }
    
    def get_user_feed(self, user_id: int, skip: int = 0, limit: int = 50) -> List[Note]:
        """Получить ленту постов от подписок пользователя"""
        query = """
            SELECT DISTINCT n.*, c.external_id as creator_external_id
            FROM note n
            JOIN creator c ON n.creator = c.id
            JOIN sub s ON s.contentmaker = n.creator
            WHERE s.subscriber = %s
            ORDER BY n.id DESC
            LIMIT %s OFFSET %s
        """
        results = self.notes.execute_query(query, (user_id, limit, skip))
        return [Note.from_dict(r) for r in results]