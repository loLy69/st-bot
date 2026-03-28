-- Пользователи
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    telegram_id INTEGER UNIQUE NOT NULL,
    role TEXT NOT NULL DEFAULT 'pending',
    admin_level INTEGER DEFAULT 0,
    full_name TEXT NOT NULL DEFAULT '',
    phone TEXT DEFAULT '',
    grade_or_group TEXT DEFAULT '',
    is_approved INTEGER DEFAULT 0,
    is_blocked INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_active TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Связь родитель → ребёнок
CREATE TABLE IF NOT EXISTS parent_student (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    parent_id INTEGER REFERENCES users(id),
    student_id INTEGER REFERENCES users(id),
    UNIQUE(parent_id, student_id)
);

-- Курсы / направления
CREATE TABLE IF NOT EXISTS courses (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL,
    description TEXT DEFAULT '',
    teacher_id INTEGER REFERENCES users(id),
    price_per_month REAL DEFAULT 0,
    schedule_text TEXT DEFAULT '',
    max_students INTEGER DEFAULT 20,
    is_active INTEGER DEFAULT 1,
    category TEXT DEFAULT 'general'
);

-- Записи на курс
CREATE TABLE IF NOT EXISTS enrollments (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    student_id INTEGER REFERENCES users(id),
    course_id INTEGER REFERENCES courses(id),
    enrolled_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    status TEXT DEFAULT 'active',
    UNIQUE(student_id, course_id)
);

-- Занятия (расписание)
CREATE TABLE IF NOT EXISTS lessons (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    course_id INTEGER REFERENCES courses(id),
    date TEXT NOT NULL,
    time TEXT NOT NULL,
    duration_min INTEGER DEFAULT 60,
    room TEXT DEFAULT '',
    notes TEXT DEFAULT '',
    is_cancelled INTEGER DEFAULT 0
);

-- Посещаемость
CREATE TABLE IF NOT EXISTS attendance (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    lesson_id INTEGER REFERENCES lessons(id),
    student_id INTEGER REFERENCES users(id),
    status TEXT DEFAULT 'unknown',
    UNIQUE(lesson_id, student_id)
);

-- Домашние задания
CREATE TABLE IF NOT EXISTS homework (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    course_id INTEGER REFERENCES courses(id),
    teacher_id INTEGER REFERENCES users(id),
    title TEXT NOT NULL,
    description TEXT DEFAULT '',
    deadline TEXT,
    file_id TEXT DEFAULT '',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Сдача ДЗ
CREATE TABLE IF NOT EXISTS homework_submissions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    homework_id INTEGER REFERENCES homework(id),
    student_id INTEGER REFERENCES users(id),
    text_answer TEXT DEFAULT '',
    file_id TEXT DEFAULT '',
    submitted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    grade TEXT DEFAULT '',
    teacher_comment TEXT DEFAULT '',
    UNIQUE(homework_id, student_id)
);

-- Учебные материалы
CREATE TABLE IF NOT EXISTS materials (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    course_id INTEGER REFERENCES courses(id),
    title TEXT NOT NULL,
    link TEXT DEFAULT '',
    file_id TEXT DEFAULT '',
    uploaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    uploaded_by INTEGER REFERENCES users(id)
);

-- Платежи
CREATE TABLE IF NOT EXISTS payments (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    student_id INTEGER REFERENCES users(id),
    course_id INTEGER REFERENCES courses(id),
    amount REAL DEFAULT 0,
    month TEXT DEFAULT '',
    receipt_file_id TEXT DEFAULT '',
    status TEXT DEFAULT 'pending',
    confirmed_by INTEGER REFERENCES users(id),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Пробные уроки
CREATE TABLE IF NOT EXISTS trial_lessons (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER REFERENCES users(id),
    course_id INTEGER REFERENCES courses(id),
    preferred_date TEXT DEFAULT '',
    preferred_time TEXT DEFAULT '',
    contact_phone TEXT DEFAULT '',
    status TEXT DEFAULT 'new',
    admin_comment TEXT DEFAULT '',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Новости и мероприятия
CREATE TABLE IF NOT EXISTS news (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL,
    body TEXT DEFAULT '',
    image_file_id TEXT DEFAULT '',
    category TEXT DEFAULT 'news',
    event_date TEXT DEFAULT '',
    published_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    published_by INTEGER REFERENCES users(id),
    posted_to_channel INTEGER DEFAULT 0,
    channel_message_id INTEGER DEFAULT 0
);

-- Прогресс ученика
CREATE TABLE IF NOT EXISTS student_progress (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    student_id INTEGER REFERENCES users(id),
    course_id INTEGER REFERENCES courses(id),
    lessons_completed INTEGER DEFAULT 0,
    progress_percent INTEGER DEFAULT 0,
    teacher_comment TEXT DEFAULT '',
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(student_id, course_id)
);

-- Отзывы
CREATE TABLE IF NOT EXISTS reviews (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    student_id INTEGER REFERENCES users(id),
    course_id INTEGER REFERENCES courses(id),
    rating INTEGER DEFAULT 5,
    text TEXT DEFAULT '',
    is_approved INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- История рассылок
CREATE TABLE IF NOT EXISTS broadcasts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    text TEXT DEFAULT '',
    image_file_id TEXT DEFAULT '',
    target_role TEXT DEFAULT 'all',
    target_filter TEXT DEFAULT 'all',
    sent_count INTEGER DEFAULT 0,
    sent_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    sent_by INTEGER REFERENCES users(id)
);

-- Очередь уведомлений
CREATE TABLE IF NOT EXISTS notifications (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER REFERENCES users(id),
    text TEXT NOT NULL,
    send_at TIMESTAMP NOT NULL,
    is_sent INTEGER DEFAULT 0,
    type TEXT DEFAULT 'custom'
);
