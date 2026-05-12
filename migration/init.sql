-- Сначала создаем таблицы без зависимостей
CREATE TABLE IF NOT EXISTS network (
    id SERIAL PRIMARY KEY,
    network_name TEXT NOT NULL UNIQUE
);

CREATE TABLE IF NOT EXISTS creator (
    id SERIAL PRIMARY KEY,
    external_id BIGINT NOT NULL UNIQUE,
    is_person BOOLEAN NOT NULL,
    network_type BIGINT NOT NULL,
    CONSTRAINT fk_creator_network 
        FOREIGN KEY (network_type) 
        REFERENCES network(id)
        ON DELETE SET NULL
);

-- Теперь создаем таблицу note с внешними ключами
CREATE TABLE IF NOT EXISTS note (
    id SERIAL PRIMARY KEY,
    msg TEXT,
    img TEXT,
    parent BIGINT,
    creator BIGINT,
    external_id BIGINT NOT NULL,
    CONSTRAINT fk_note_parent 
        FOREIGN KEY (parent) 
        REFERENCES note(id)
        ON DELETE CASCADE,
    CONSTRAINT fk_note_creator 
        FOREIGN KEY (creator) 
        REFERENCES creator(id)
        ON DELETE CASCADE
);

-- Таблица подписок
CREATE TABLE IF NOT EXISTS sub (
    contentmaker BIGINT,
    subscriber BIGINT,
    PRIMARY KEY (contentmaker, subscriber),
    CONSTRAINT fk_sub_contentmaker 
        FOREIGN KEY (contentmaker) 
        REFERENCES creator(id)
        ON DELETE CASCADE,
    CONSTRAINT fk_sub_subscriber 
        FOREIGN KEY (subscriber) 
        REFERENCES creator(id)
        ON DELETE CASCADE,
    CONSTRAINT chk_sub_different 
        CHECK (contentmaker != subscriber)
);

-- Таблица лайков
CREATE TABLE IF NOT EXISTS like (
    post BIGINT,
    person BIGINT,
   PRIMARY KEY (post, person),
    CONSTRAINT fk_like_post 
        FOREIGN KEY (post) 
        REFERENCES note(id)
        ON DELETE CASCADE,
    CONSTRAINT fk_like_person 
        FOREIGN KEY (person) 
        REFERENCES creator(id)
        ON DELETE CASCADE
);

-- Таблица для хранения метаданных тем
CREATE TABLE IF NOT EXISTS topic (
    id SERIAL PRIMARY KEY,
    topic_id INTEGER NOT NULL UNIQUE,      -- ID от BERTopic (-1 для выбросов)
    topic_name TEXT,                       -- Название темы ("python_программирование")
    keywords JSONB,                        -- Ключевые слова с весами
    created_at TIMESTAMP DEFAULT NOW(),
);

-- Таблица связи пост-тема (для каждого поста)
CREATE TABLE IF NOT EXISTS note_topic (
    id SERIAL PRIMARY KEY,
    note_id BIGINT NOT NULL,               -- ID поста
    topic_id INTEGER NOT NULL,             -- ID темы
    topic_probability FLOAT,               -- Уверенность для этого поста
    is_thread_based BOOLEAN DEFAULT TRUE,  -- Анализ на уровне треда
    analyzed_at TIMESTAMP DEFAULT NOW(),
    CONSTRAINT fk_note_topic_note 
        FOREIGN KEY (note_id) 
        REFERENCES note(id)
        ON DELETE CASCADE
);

-- Создаем индексы для ускорения поиска
CREATE INDEX IF NOT EXISTS idx_note_parent ON note(parent);
CREATE INDEX IF NOT EXISTS idx_note_creator ON note(creator);
CREATE INDEX IF NOT EXISTS idx_creator_network ON creator(network_type);
CREATE INDEX IF NOT EXISTS idx_sub_contentmaker ON sub(contentmaker);
CREATE INDEX IF NOT EXISTS idx_sub_subscriber ON sub(subscriber);
CREATE INDEX IF NOT EXISTS idx_like_post ON like(post);
CREATE INDEX IF NOT EXISTS idx_like_person ON like(person);
CREATE INDEX IF NOT EXISTS idx_topic_topic_id ON topic(topic_id);
CREATE INDEX IF NOT EXISTS idx_note_topic_note_id ON note_topic(note_id);
CREATE INDEX IF NOT EXISTS idx_note_topic_topic_id ON note_topic(topic_id);
