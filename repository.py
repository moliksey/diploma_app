import psycopg2

def get_connection():
    """Создание подключения к базе данных"""
    try:
        conn = psycopg2.connect(
            host="localhost",
            port="5432",
            database="diploma_db",
            user="moliksey",
            password="diploma" # Для работы с результатами как со словарями
        )
        print("✅ Подключение к PostgreSQL успешно установлено")
        return conn
    except Exception as e:
        print(f"❌ Ошибка подключения: {e}")
        return None