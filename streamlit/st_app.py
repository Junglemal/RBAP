import streamlit as st
import requests
import pandas as pd
import numpy as np
import time
import json
from datetime import datetime, date, timedelta
from typing import Optional, List, Dict, Any
import io

API_URL = 'http://app:8080'  # 'http://localhost:8080'

try:
    import plotly.express as px
    import plotly.graph_objects as go
    from plotly.subplots import make_subplots

    PLOTLY_AVAILABLE = True
except ImportError:
    PLOTLY_AVAILABLE = False
    st.warning("Plotly не установлен. Визуализация статистики будет ограничена.")


# Вспомогательная функция для API запросов
def make_api_request(endpoint, method='GET', data=None, params=None):
    try:
        url = f'{API_URL}{endpoint}'
        if method == 'GET':
            response = requests.get(url, params=params)
        elif method == 'POST':
            if params:
                response = requests.post(url, params=params)
            elif data:
                response = requests.post(url, json=data)
            else:
                response = requests.post(url)
        elif method == 'DELETE':
            response = requests.delete(url, params=params)
        elif method == 'PUT':
            response = requests.put(url, json=data)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        st.error(f'Error: {str(e)}')
        return None


# =========================
# ФУНКЦИИ ДЛЯ РАБОТЫ С ПАРСЕРОМ
# =========================

def get_parser_jobs(limit=100, offset=0):
    """Получить список задач парсинга"""
    endpoint = '/api/parser/jobs'
    params = {'limit': limit, 'offset': offset}
    return make_api_request(endpoint, method='GET', params=params)


def get_parser_job_by_id(job_id):
    """Получить задачу парсинга по ID"""
    endpoint = f'/api/parser/jobs/{job_id}'
    return make_api_request(endpoint, method='GET')


def get_all_reviews(limit=100, offset=0):
    """Получить все отзывы"""
    endpoint = '/api/parser/reviews'
    params = {'limit': limit, 'offset': offset}
    return make_api_request(endpoint, method='GET', params=params)


def get_review_by_id(review_id):
    """Получить отзыв по ID"""
    endpoint = f'/api/parser/reviews/{review_id}'
    return make_api_request(endpoint, method='GET')


def get_reviews_by_bank(bank_id, limit=100, offset=0):
    """Получить отзывы по банку"""
    endpoint = f'/api/parser/reviews/bank/{bank_id}'
    params = {'limit': limit, 'offset': offset}
    return make_api_request(endpoint, method='GET', params=params)


def search_reviews(bank_name=None, status=None, min_grade=None, max_grade=None, limit=100, offset=0):
    """Поиск отзывов"""
    endpoint = '/api/parser/reviews/search'
    params = {
        'limit': limit,
        'offset': offset
    }
    if bank_name:
        params['bank_name'] = bank_name
    if status:
        params['status'] = status
    if min_grade is not None:
        params['min_grade'] = min_grade
    if max_grade is not None:
        params['max_grade'] = max_grade

    return make_api_request(endpoint, method='GET', params=params)


def get_parser_stats():
    """Получить статистику парсинга"""
    endpoint = '/api/parser/stats/summary'
    return make_api_request(endpoint, method='GET')


def get_bank_stats():
    """Получить статистику по банкам"""
    endpoint = '/api/parser/stats/banks'
    return make_api_request(endpoint, method='GET')


def run_parser(data):
    """Запустить парсер"""
    endpoint = '/api/parser/run'
    return make_api_request(endpoint, method='POST', data=data)


def run_test_parser(page=1, save_to_db=True):
    """Запустить тестовый парсер"""
    endpoint = '/api/parser/run/test'
    data = {
        'page': page,
        'save_to_db': save_to_db
    }
    return make_api_request(endpoint, method='POST', data=data)


def delete_review_by_id(review_id):
    """Удалить отзыв по ID"""
    endpoint = f'/api/parser/reviews/{review_id}'
    return make_api_request(endpoint, method='DELETE')


def delete_reviews_by_status(status_name):
    """Удалить отзывы по статусу"""
    endpoint = f'/api/parser/reviews/status/{status_name}'
    return make_api_request(endpoint, method='DELETE')


def update_job_status(job_id, status=None, current_page=None, total_pages=None,
                      processed_reviews=None, message=None):
    """Обновить статус задачи парсинга"""
    endpoint = f'/api/parser/jobs/{job_id}/update'
    data = {}
    if status is not None:
        data['status'] = status
    if current_page is not None:
        data['current_page'] = current_page
    if total_pages is not None:
        data['total_pages'] = total_pages
    if processed_reviews is not None:
        data['processed_reviews'] = processed_reviews
    if message is not None:
        data['message'] = message

    return make_api_request(endpoint, method='PUT', data=data)


def check_parser_health():
    """Проверить здоровье парсера"""
    endpoint = '/api/parser/health'
    return make_api_request(endpoint, method='GET')


def get_unique_bank_names():
    """Получить уникальные названия банков"""
    try:
        reviews = get_all_reviews(limit=5000)
        if reviews:
            df = pd.DataFrame(reviews)
            if 'bank_name' in df.columns:
                return sorted(df['bank_name'].dropna().unique().tolist())
    except:
        pass
    return []


# =========================
# ФУНКЦИИ ДЛЯ РАБОТЫ С ML ЗАДАЧАМИ
# =========================

def send_ml_task(message: str, user_id: int, review_id: Optional[int] = None,
                 user_city: Optional[str] = None, bank_id: Optional[int] = None,
                 bank_name: Optional[str] = None):
    """Отправить единичную ML задачу"""
    endpoint = '/api/ml/send_task'
    params = {
        'message': message,
        'user_id': user_id
    }
    if review_id is not None:
        params['review_id'] = review_id
    if user_city is not None:
        params['user_city'] = user_city
    if bank_id is not None:
        params['bank_id'] = bank_id
    if bank_name is not None:
        params['bank_name'] = bank_name

    return make_api_request(endpoint, method='POST', params=params)


def send_ml_batch_task(user_id: int, bank_id: Optional[int] = None,
                       limit: int = 10, date_from: Optional[datetime] = None,
                       date_to: Optional[datetime] = None):
    """Отправить пакетную ML задачу"""
    endpoint = '/api/ml/send_task_batch'
    params = {
        'user_id': user_id,
        'limit': limit
    }
    if bank_id:
        params['bank_id'] = bank_id
    if date_from:
        params['date_from'] = date_from.isoformat()
    if date_to:
        params['date_to'] = date_to.isoformat()

    return make_api_request(endpoint, method='POST', params=params)


def get_ml_tasks():
    """Получить все ML задачи"""
    endpoint = '/api/ml/tasks'
    return make_api_request(endpoint, method='GET')


def get_ml_task(task_id: int):
    """Получить ML задачу по ID"""
    endpoint = f'/api/ml/tasks/{task_id}'
    return make_api_request(endpoint, method='GET')


def get_ml_batch_stats(bank_id: Optional[int] = None,
                       date_from: Optional[datetime] = None,
                       date_to: Optional[datetime] = None):
    """Получить статистику для batch обработки"""
    endpoint = '/api/ml/batch_stats'
    params = {}
    if bank_id:
        params['bank_id'] = bank_id
    if date_from:
        params['date_from'] = date_from.isoformat()
    if date_to:
        params['date_to'] = date_to.isoformat()

    return make_api_request(endpoint, method='GET', params=params)


def send_ml_task_result(task_id: int, result: str):
    """Отправить результат ML задачи"""
    endpoint = '/api/ml/send_task_result'
    data = {
        'task_id': task_id,
        'result': result
    }
    return make_api_request(endpoint, method='POST', data=data)


# =========================
# ФУНКЦИЯ ДЛЯ ПАРСИНГА JSON РЕЗУЛЬТАТОВ ML
# =========================

def parse_ml_result_json(result_text: str) -> Dict[str, Any]:
    """Парсит JSON результат ML задачи и извлекает структурированные данные"""
    try:
        if not result_text or pd.isna(result_text):
            return {}

        # Пытаемся распарсить JSON
        result_data = json.loads(result_text)

        parsed_data = {}

        # Извлекаем summary
        parsed_data['summary'] = result_data.get('summary', '')

        # Извлекаем sentiment
        sentiment = result_data.get('sentiment', {})
        parsed_data['sentiment_overall'] = sentiment.get('overall', '')
        parsed_data['sentiment_intensity'] = sentiment.get('intensity', '')
        parsed_data['sentiment_key_emotion'] = sentiment.get('key_emotion', '')

        # Извлекаем themes
        themes = result_data.get('themes', {})
        parsed_data['theme_primary'] = themes.get('primary', {}).get('theme', '') if isinstance(themes.get('primary'),
                                                                                                dict) else ''
        parsed_data['theme_primary_significance'] = themes.get('primary', {}).get('significance', '') if isinstance(
            themes.get('primary'), dict) else ''

        # Извлекаем secondary themes (может быть несколько)
        secondary_themes = []
        for key, value in themes.items():
            if 'secondary' in key and isinstance(value, dict):
                secondary_themes.append(f"{value.get('theme', '')} ({value.get('significance', '')})")

        parsed_data['theme_secondary'] = '; '.join(secondary_themes) if secondary_themes else ''

        # Извлекаем analysis
        analysis = result_data.get('analysis', {})
        objectivity = analysis.get('objectivity', {})
        parsed_data['objectivity_score'] = objectivity.get('score', '') if isinstance(objectivity, dict) else ''
        parsed_data['objectivity_reason'] = objectivity.get('reason', '') if isinstance(objectivity, dict) else ''

        # Извлекаем strengths
        strengths = analysis.get('strengths', [])
        parsed_data['analysis_strengths'] = '; '.join(strengths) if isinstance(strengths, list) else ''

        # Извлекаем weaknesses
        weaknesses = analysis.get('weaknesses', [])
        parsed_data['analysis_weaknesses'] = '; '.join(weaknesses) if isinstance(weaknesses, list) else ''

        # Извлекаем omissions
        omissions = analysis.get('omissions', [])
        parsed_data['analysis_omissions'] = '; '.join(omissions) if isinstance(omissions, list) else ''

        # Извлекаем service_stage
        service_stage = result_data.get('service_stage', [])
        parsed_data['service_stage'] = '; '.join(service_stage) if isinstance(service_stage, list) else ''

        # Извлекаем tags
        tags = result_data.get('tags', {})
        parsed_data['tags_process'] = '; '.join(tags.get('process', [])) if isinstance(tags.get('process'),
                                                                                       list) else ''
        parsed_data['tags_service'] = '; '.join(tags.get('service', [])) if isinstance(tags.get('service'),
                                                                                       list) else ''
        parsed_data['tags_product'] = '; '.join(tags.get('product', [])) if isinstance(tags.get('product'),
                                                                                       list) else ''

        # Извлекаем entities
        entities = result_data.get('entities', {})
        parsed_data['entities_branch'] = '; '.join(entities.get('branch', [])) if isinstance(entities.get('branch'),
                                                                                             list) else ''
        parsed_data['entities_employees'] = '; '.join(entities.get('employees', [])) if isinstance(
            entities.get('employees'), list) else ''

        return parsed_data

    except json.JSONDecodeError:
        # Если не JSON, возвращаем как есть
        return {'raw_result': str(result_text)}
    except Exception as e:
        st.warning(f"Ошибка парсинга результата: {str(e)}")
        return {'raw_result': str(result_text), 'parse_error': str(e)}


# =========================
# ФУНКЦИИ ПОЛЬЗОВАТЕЛЯ
# =========================

def get_user_events(view_mode="my_events", target_email=None):
    """Получить события пользователя"""
    if not st.session_state.logged_in:
        return None

    params = {'email': st.session_state.email}

    if st.session_state.is_admin:
        if view_mode == "all_users":
            params['all_users'] = 'true'
        elif view_mode == "specific_user" and target_email:
            params['target_email'] = target_email

    endpoint = '/api/events/events'
    return make_api_request(endpoint, method='GET', params=params)


# =========================
# ИНИЦИАЛИЗАЦИЯ СЕССИИ
# =========================

if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False
    st.session_state.email = None
    st.session_state.is_admin = False

if 'ml_export_filters' not in st.session_state:
    st.session_state.ml_export_filters = {
        'statuses': [],
        'operation_types': [],
        'date_from': None,
        'date_to': None,
        'user_id': None,
        'review_id': None,
        'bank_id': None,
        'bank_name': '',
        'user_city': ''
    }


# =========================
# ГЛАВНОЕ МЕНЮ
# =========================

def main():
    st.title('Сервис по анализу отзывов')

    if not st.session_state.logged_in:
        menu = ['Login', 'Register']
    else:
        if st.session_state.is_admin:
            menu = ['Home', 'Parser Dashboard', 'Parser Control',
                    'ML Tasks', 'Экспорт ML задач', 'Экспорт парсера', 'List of events', 'Logout']
        else:
            menu = ['Home', 'ML Tasks', 'Экспорт ML задач', 'List of events', 'Logout']

    choice = st.sidebar.selectbox('Menu', menu)

    if choice == 'Login':
        login()
    elif choice == 'Register':
        register()
    elif choice == 'Home':
        home()
    elif choice == 'Parser Dashboard':
        parser_dashboard()
    elif choice == 'Parser Control':
        parser_control()
    elif choice == 'ML Tasks':
        ml_tasks()
    elif choice == 'Экспорт ML задач':
        export_ml_tasks_page()
    elif choice == 'Экспорт парсера':
        export_parser_page()
    elif choice == 'List of events':
        list_of_events()
    elif choice == 'Logout':
        logout()


# =========================
# СТРАНИЦА HOME
# =========================

def home():
    st.header(
        'Welcome! Please, use Menu to: \n- Inspect parser data \n- Inspect review summarization \n- View list of app events')

    if st.session_state.logged_in:
        st.write(f'Logged in as: {st.session_state.email}')

        # Показать краткую статистику
        st.divider()
        st.subheader("🚀 Quick Actions")

        col1, col2, col3 = st.columns(3)

        with col1:
            if st.button("🤖 Go to ML Tasks", use_container_width=True):
                st.session_state.menu_choice = "ML Tasks"
                st.rerun()

        with col2:
            if st.session_state.is_admin and st.button("📊 Go to Parser Dashboard", use_container_width=True):
                st.session_state.menu_choice = "Parser Dashboard"
                st.rerun()

        with col3:
            if st.button("📤 Export ML Tasks", use_container_width=True):
                st.session_state.menu_choice = "Экспорт ML задач"
                st.rerun()

        # Для админов - общая статистика
        if st.session_state.is_admin:
            st.divider()
            st.subheader("📊 System Overview")

            # Статистика парсера
            try:
                parser_stats = get_parser_stats()
                if parser_stats:
                    col1, col2, col3, col4 = st.columns(4)

                    with col1:
                        st.metric("Total Reviews", parser_stats.get('total_reviews', 0))

                    with col2:
                        if parser_stats.get('status_distribution'):
                            total = sum(parser_stats['status_distribution'].values())
                            st.metric("Processed Reviews", total)

                    # Получаем даты отзывов
                    reviews = get_all_reviews(limit=50)
                    if reviews:
                        df = pd.DataFrame(reviews)
                        if 'created_at_api' in df.columns:
                            df['created_at_api'] = pd.to_datetime(df['created_at_api'], errors='coerce')
                            min_date = df['created_at_api'].min()
                            max_date = df['created_at_api'].max()

                            with col3:
                                if pd.notna(min_date):
                                    st.metric("Earliest Review", min_date.strftime('%Y-%m-%d'))

                            with col4:
                                if pd.notna(max_date):
                                    st.metric("Latest Review", max_date.strftime('%Y-%m-%d'))
            except Exception as e:
                st.error(f"Error loading parser stats: {str(e)}")

            # Статистика ML
            try:
                ml_stats = get_ml_batch_stats()
                if ml_stats:
                    stats = ml_stats.get('statistics', {})
                    col1, col2, col3, col4 = st.columns(4)

                    with col1:
                        st.metric("ML: Total Reviews", stats.get('total_reviews', 0))

                    with col2:
                        st.metric("ML: Processed", stats.get('processed_reviews', 0))

                    with col3:
                        st.metric("ML: Pending", stats.get('pending_reviews', 0))

                    # Получаем даты ML задач
                    ml_tasks_data = get_ml_tasks()
                    if ml_tasks_data:
                        df_ml = pd.DataFrame(ml_tasks_data)
                        if 'created_at_api' in df_ml.columns:
                            df_ml['created_at_api'] = pd.to_datetime(df_ml['created_at_api'], errors='coerce')
                            ml_min_date = df_ml['created_at_api'].min()
                            ml_max_date = df_ml['created_at_api'].max()

                            # Показываем в отдельной строке
                            st.divider()
                            st.subheader("📅 ML Processing Dates")
                            col5, col6 = st.columns(2)

                            with col5:
                                if pd.notna(ml_min_date):
                                    st.metric("Earliest ML Task", ml_min_date.strftime('%Y-%m-%d'))

                            with col6:
                                if pd.notna(ml_max_date):
                                    st.metric("Latest ML Task", ml_max_date.strftime('%Y-%m-%d'))
            except Exception as e:
                st.error(f"Error loading ML stats: {str(e)}")


# =========================
# ПАНЕЛЬ УПРАВЛЕНИЯ ПАРСЕРОМ (данные)
# =========================

def parser_dashboard():
    """Панель управления данными парсера"""
    if not st.session_state.is_admin:
        st.warning("⚠️ This page is available only for administrators")
        return

    st.title('📈 Parser Dashboard')

    # Вкладки
    tab1, tab2, tab3, tab4, tab5 = st.tabs([
        "📋 All Reviews",
        "🔍 Search",
        "🔄 Jobs",
        "🗑️ Delete",
        "📤 Export CSV"
    ])

    with tab1:
        st.header("All Reviews")

        col1, col2 = st.columns(2)
        with col1:
            limit = st.number_input("Limit", min_value=1, max_value=10000, value=1000, step=100)
        with col2:
            offset = st.number_input("Offset", min_value=0, value=0, step=100)

        if st.button("Load Reviews", use_container_width=True):
            with st.spinner("Loading reviews..."):
                reviews = get_all_reviews(limit=limit, offset=offset)
                if reviews:
                    st.success(f"✅ Loaded {len(reviews)} reviews")

                    # Преобразуем в DataFrame
                    df = pd.DataFrame(reviews)

                    # Отображаем таблицу
                    st.dataframe(df, use_container_width=True, height=400)

                    # Статистика
                    if not df.empty:
                        st.subheader("📊 Quick Statistics")
                        col1, col2, col3, col4 = st.columns(4)
                        with col1:
                            st.metric("Total", len(df))
                        with col2:
                            unique_banks = df['bank_name'].nunique() if 'bank_name' in df.columns else 0
                            st.metric("Unique Banks", unique_banks)
                        with col3:
                            if 'grade_api' in df.columns:
                                avg_grade = df['grade_api'].mean()
                                st.metric("Avg Grade", f"{avg_grade:.1f}")
                        with col4:
                            if 'created_at_api' in df.columns:
                                df['created_at_api'] = pd.to_datetime(df['created_at_api'], errors='coerce')
                                min_date = df['created_at_api'].min()
                                max_date = df['created_at_api'].max()
                                if pd.notna(min_date) and pd.notna(max_date):
                                    st.metric("Date Range", f"{min_date.date()} to {max_date.date()}")

                        # Статистика по месяцам
                        if 'created_at_api' in df.columns and not df['created_at_api'].isna().all():
                            st.subheader("📅 Reviews by Month")
                            df['month'] = df['created_at_api'].dt.to_period('M')
                            monthly_counts = df['month'].value_counts().sort_index()
                            monthly_df = pd.DataFrame(
                                {'Month': monthly_counts.index.astype(str), 'Count': monthly_counts.values})

                            col_chart, col_table = st.columns([2, 1])

                            with col_chart:
                                if PLOTLY_AVAILABLE and not monthly_df.empty:
                                    fig = px.bar(monthly_df, x='Month', y='Count',
                                                 title='Отзывы по месяцам',
                                                 color='Count',
                                                 color_continuous_scale='Viridis')
                                    st.plotly_chart(fig, use_container_width=True)

                            with col_table:
                                st.dataframe(monthly_df, use_container_width=True)
                else:
                    st.warning("No reviews found or failed to load")

    with tab2:
        st.header("Search Reviews")

        # Получаем уникальные названия банков
        bank_names = get_unique_bank_names()

        col1, col2, col3 = st.columns(3)

        with col1:
            if bank_names:
                search_bank = st.selectbox("Bank Name", options=[""] + bank_names)
            else:
                search_bank = st.text_input("Bank Name")

            search_status = st.selectbox(
                "Status",
                ["", "Зачтено", "Не зачтено", "Проверяется", "Ошибка парсинга"]
            )

        with col2:
            min_grade = st.number_input("Min Grade", min_value=1, max_value=5, value=1, step=1)
            max_grade = st.number_input("Max Grade", min_value=1, max_value=5, value=5, step=1)
            limit_search = st.number_input("Search Limit", min_value=1, max_value=1000, value=100, step=50)

        with col3:
            st.write("**Date Filter (created_at_api):**")
            search_date_from = st.date_input("From Date", value=None, key='search_date_from')
            search_date_to = st.date_input("To Date", value=None, key='search_date_to')

        if st.button("🔍 Search", type="primary", use_container_width=True):
            with st.spinner("Searching..."):
                reviews = search_reviews(
                    bank_name=search_bank if search_bank else None,
                    status=search_status if search_status else None,
                    min_grade=min_grade,
                    max_grade=max_grade,
                    limit=limit_search
                )

                if reviews:
                    st.success(f"✅ Found {len(reviews)} reviews")
                    df = pd.DataFrame(reviews)

                    # Применяем фильтр по дате created_at_api на стороне клиента
                    if search_date_from or search_date_to:
                        if 'created_at_api' in df.columns:
                            df['created_at_api'] = pd.to_datetime(df['created_at_api'], errors='coerce')
                            if search_date_from:
                                date_from_dt = pd.Timestamp(search_date_from)
                                df = df[df['created_at_api'] >= date_from_dt]
                            if search_date_to:
                                date_to_dt = pd.Timestamp(search_date_to) + pd.Timedelta(days=1)
                                df = df[df['created_at_api'] <= date_to_dt]
                            st.info(f"After date filter (created_at_api): {len(df)} reviews")

                    st.dataframe(df, use_container_width=True, height=400)
                else:
                    st.info("No reviews found matching criteria")

    with tab3:
        st.header("Parser Jobs")

        if st.button("🔄 Refresh Jobs", use_container_width=True):
            with st.spinner("Loading jobs..."):
                jobs = get_parser_jobs(limit=50)
                if jobs:
                    st.success(f"✅ Loaded {len(jobs)} parser jobs")

                    # Преобразуем в DataFrame
                    jobs_df = pd.DataFrame(jobs)

                    # Преобразуем даты
                    for date_col in ['started_at', 'finished_at']:
                        if date_col in jobs_df.columns:
                            try:
                                jobs_df[date_col] = pd.to_datetime(jobs_df[date_col])
                            except:
                                pass

                    # Сортируем по дате
                    if 'started_at' in jobs_df.columns:
                        jobs_df = jobs_df.sort_values('started_at', ascending=False)

                    # Отображаем
                    st.dataframe(jobs_df, use_container_width=True, height=400)

                    # Статистика по статусам
                    if 'status' in jobs_df.columns:
                        st.subheader("📊 Jobs Status Distribution")
                        status_counts = jobs_df['status'].value_counts()
                        col1, col2, col3 = st.columns(3)
                        cols = [col1, col2, col3]
                        for i, (status, count) in enumerate(status_counts.items()):
                            with cols[i % 3]:
                                st.metric(status, count)
                else:
                    st.info("No parser jobs found")

    with tab4:
        st.header("Delete Operations")

        col1, col2 = st.columns(2)

        with col1:
            st.subheader("Delete by ID")
            delete_id = st.number_input("Review ID to delete", min_value=1, value=1, step=1)

            if st.button("🗑️ Delete Review", type="secondary", use_container_width=True):
                result = delete_review_by_id(delete_id)
                if result:
                    st.success(f"✅ Review {delete_id} deleted successfully")
                else:
                    st.error(f"❌ Failed to delete review {delete_id}")

        with col2:
            st.subheader("Delete by Status")
            delete_status = st.selectbox(
                "Status to delete",
                ["Зачтено", "Не зачтено", "Проверяется", "Ошибка парсинга"]
            )

            if st.button("🗑️ Delete All by Status", type="secondary", use_container_width=True):
                result = delete_reviews_by_status(delete_status)
                if result:
                    deleted_count = result.get('deleted_count', 0)
                    st.success(f"✅ Deleted {deleted_count} reviews with status '{delete_status}'")
                else:
                    st.error(f"❌ Failed to delete reviews with status '{delete_status}'")

    with tab5:
        st.header("Export Parser Data to CSV")

        # Получаем уникальные названия банков
        bank_names = get_unique_bank_names()

        # Фильтры
        col1, col2 = st.columns(2)

        with col1:
            export_bank = st.selectbox("Bank Name", options=[""] + bank_names, key='export_parser_bank')
            export_status = st.selectbox(
                "Status",
                ["", "Зачтено", "Не зачтено", "Проверяется", "Ошибка парсинга"],
                key='export_parser_status'
            )

        with col2:
            export_min_grade = st.number_input("Min Grade", min_value=1, max_value=5, value=1, step=1,
                                               key='export_min_grade')
            export_max_grade = st.number_input("Max Grade", min_value=1, max_value=5, value=5, step=1,
                                               key='export_max_grade')
            export_limit = st.number_input("Limit", min_value=1, max_value=10000, value=1000, step=100,
                                           key='export_limit')

        col3, col4 = st.columns(2)
        with col3:
            export_date_from = st.date_input("From Date (created_at_api)", value=None, key='export_date_from')
        with col4:
            export_date_to = st.date_input("To Date (created_at_api)", value=None, key='export_date_to')

        if st.button("📥 Export to CSV", type="primary", use_container_width=True):
            with st.spinner("Exporting data..."):
                # Получаем данные
                reviews = search_reviews(
                    bank_name=export_bank if export_bank else None,
                    status=export_status if export_status else None,
                    min_grade=export_min_grade,
                    max_grade=export_max_grade,
                    limit=export_limit
                )

                if reviews:
                    df = pd.DataFrame(reviews)

                    # Применяем фильтр по дате created_at_api
                    if export_date_from or export_date_to:
                        if 'created_at_api' in df.columns:
                            df['created_at_api'] = pd.to_datetime(df['created_at_api'], errors='coerce')
                            if export_date_from:
                                date_from_dt = pd.Timestamp(export_date_from)
                                df = df[df['created_at_api'] >= date_from_dt]
                            if export_date_to:
                                date_to_dt = pd.Timestamp(export_date_to) + pd.Timedelta(days=1)
                                df = df[df['created_at_api'] <= date_to_dt]

                    # Конвертируем в CSV
                    csv_data = df.to_csv(index=False, encoding='utf-8-sig')

                    # Скачивание
                    st.download_button(
                        label="📥 Download CSV",
                        data=csv_data,
                        file_name=f"parser_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                        mime="text/csv",
                        type="primary",
                        use_container_width=True
                    )

                    st.success(f"✅ Exported {len(df)} records")
                else:
                    st.warning("No data to export")


# =========================
# СТРАНИЦА ЗАПУСКА ПАРСЕРА (только для админов)
# =========================

def parser_control():
    """Страница управления парсером"""
    if not st.session_state.is_admin:
        st.warning("⚠️ This page is available only for administrators")
        return

    st.title('📊 Parser Control Panel')

    # Проверка здоровья API
    with st.expander("🔧 System Health", expanded=True):
        health = check_parser_health()
        if health:
            if health['status'] == 'healthy':
                st.success(f"✅ API Status: {health['status']}")
                st.info(f"📊 Reviews in DB: {health.get('reviews_count', 0)}")
                st.info(f"🔄 Parser Jobs: {health.get('jobs_count', 0)}")
            else:
                st.error(f"❌ API Status: {health['status']}")
                st.error(f"Error: {health.get('error', 'Unknown error')}")
        else:
            st.warning("⚠️ Could not fetch health status")

    # Разделы
    tab1, tab2, tab3 = st.tabs(["🚀 Run Parser", "⚙️ Test Parser", "📈 Statistics"])

    with tab1:
        st.header("Run Parser")

        col1, col2 = st.columns(2)

        with col1:
            start_page = st.number_input("Start Page", min_value=1, value=1, step=1)
            end_page = st.number_input("End Page (0 for all)", min_value=0, value=10, step=1)
            if end_page == 0:
                end_page = None

        with col2:
            delay = st.slider("Delay between requests (seconds)", 1, 10, 2)
            resume = st.checkbox("Resume from last position", value=True)

        col3, col4 = st.columns(2)

        with col3:
            save_to_db = st.checkbox("Save to Database", value=True)

        with col4:
            filename = st.text_input("Excel filename (optional)",
                                     value="mortgage_reviews.xlsx")
            if not filename:
                filename = None

        if st.button("🚀 Start Parsing", type="primary", use_container_width=True):
            with st.spinner("Starting parser..."):
                data = {
                    'start_page': start_page,
                    'end_page': end_page,
                    'delay': delay,
                    'resume': resume,
                    'save_to_db': save_to_db,
                    'filename': filename
                }

                result = run_parser(data)
                if result:
                    st.success("✅ Parser started successfully!")
                    st.info(f"Job ID: {result.get('job_id')}")

                    # Показать детали
                    with st.expander("Job Details"):
                        st.json(result)
                else:
                    st.error("❌ Failed to start parser")

    with tab2:
        st.header("Test Parser")

        col1, col2 = st.columns(2)

        with col1:
            test_page = st.number_input("Test Page", min_value=1, value=1, step=1)

        with col2:
            test_save_to_db = st.checkbox("Save test to DB", value=True)

        if st.button("🧪 Run Test", type="secondary", use_container_width=True):
            with st.spinner("Running test parser..."):
                result = run_test_parser(page=test_page, save_to_db=test_save_to_db)
                if result:
                    st.success("✅ Test parser started successfully!")
                    st.info(f"Job ID: {result.get('job_id')}")
                else:
                    st.error("❌ Failed to start test parser")

    with tab3:
        st.header("Parser Statistics")

        if st.button("🔄 Refresh Statistics", use_container_width=True):
            stats = get_parser_stats()
            bank_stats = get_bank_stats()

            if stats:
                col1, col2, col3 = st.columns(3)

                with col1:
                    st.metric("Total Reviews", stats.get('total_reviews', 0))

                with col2:
                    if stats.get('last_job', {}).get('status'):
                        st.metric("Last Job Status", stats['last_job']['status'])

                with col3:
                    if stats.get('status_distribution'):
                        total = sum(stats['status_distribution'].values())
                        st.metric("Total Statuses", total)

                # Распределение по статусам
                st.subheader("📊 Status Distribution")
                if stats.get('status_distribution'):
                    status_df = pd.DataFrame(
                        list(stats['status_distribution'].items()),
                        columns=['Status', 'Count']
                    )
                    st.dataframe(status_df, use_container_width=True)
                else:
                    st.info("No status distribution data available")

                # Статистика по банкам
                if bank_stats:
                    st.subheader("🏦 Bank Statistics")
                    banks_df = pd.DataFrame(bank_stats.get('banks', []))
                    if not banks_df.empty:
                        st.dataframe(banks_df, use_container_width=True)
                        st.metric("Total Banks", bank_stats.get('total_banks', 0))
                else:
                    st.info("No bank statistics available")
            else:
                st.error("❌ Failed to fetch statistics")


# =========================
# СТРАНИЦА ML TASKS
# =========================

def ml_tasks():
    """Страница для работы с ML задачами"""
    if not st.session_state.logged_in:
        st.warning("⚠️ Please login first")
        return

    st.title('🤖 ML Tasks - Анализ отзывов с помощью ИИ')

    # Вкладки
    tab1, tab2, tab3, tab4 = st.tabs([
        "📝 Единичный запрос",
        "📊 Пакетная обработка",
        "📋 История задач",
        "📈 Статистика"
    ])

    with tab1:
        st.header("Единичный запрос к LLM")

        col1, col2 = st.columns(2)

        with col1:
            user_id = st.number_input("User ID",
                                      min_value=1,
                                      value=1,
                                      help="ID пользователя, инициирующего запрос")
            review_id = st.number_input("Review ID (опционально)",
                                        min_value=1,
                                        value=None,
                                        help="ID отзыва из базы данных")
            user_city = st.text_input("Город пользователя (опционально)")

        with col2:
            bank_id = st.number_input("Bank ID (опционально)",
                                      min_value=1,
                                      value=None)
            bank_name = st.text_input("Название банка (опционально)")

        # Поле для промпта
        message = st.text_area(
            "Введите текст для анализа или вопрос к LLM:",
            height=150,
            placeholder="Например: Проанализируй этот отзыв и выдели основные проблемы..."
        )

        if st.button("🚀 Отправить задачу", type="primary", use_container_width=True):
            if not message.strip():
                st.error("Пожалуйста, введите текст для анализа")
                return

            with st.spinner("Отправка задачи..."):
                result = send_ml_task(
                    message=message,
                    user_id=user_id,
                    review_id=review_id,
                    user_city=user_city,
                    bank_id=bank_id,
                    bank_name=bank_name
                )

                if result:
                    st.success("✅ Задача успешно отправлена!")

                    # Показать детали задачи
                    with st.expander("Детали задачи", expanded=True):
                        col_a, col_b, col_c = st.columns(3)
                        with col_a:
                            st.metric("ID задачи", result.get('task_id'))
                        with col_b:
                            st.metric("Тип операции", result.get('operation_type'))
                        with col_c:
                            if result.get('review_id'):
                                st.metric("ID отзыва", result.get('review_id'))

                        st.info(f"**Статус:** Задача поставлена в очередь")
                        st.info(f"**Сообщение:** {result.get('message')}")
                else:
                    st.error("❌ Ошибка при отправке задачи")

    with tab2:
        st.header("Пакетная обработка отзывов")
        st.info("Обработка нескольких отзывов из базы данных за один раз")

        # Форма для batch обработки
        col1, col2 = st.columns(2)

        with col1:
            batch_user_id = st.number_input("User ID для batch",
                                            min_value=1,
                                            value=1,
                                            key='batch_user_id')
            batch_bank_id = st.number_input("Фильтр по Bank ID (опционально)",
                                            min_value=1,
                                            value=None,
                                            key='batch_bank_id')
            batch_limit = st.slider("Количество отзывов",
                                    min_value=1,
                                    max_value=100,
                                    value=10,
                                    help="Максимум 100 отзывов за один запрос")

        with col2:
            st.write("**Фильтр по дате (created_at_api):**")
            col_date1, col_date2 = st.columns(2)
            with col_date1:
                date_from = st.date_input("С даты",
                                          value=None,
                                          key='date_from')
            with col_date2:
                date_to = st.date_input("По дату",
                                        value=None,
                                        key='date_to')

        if st.button("📦 Запустить пакетную обработку", type="primary", use_container_width=True):
            with st.spinner("Запуск пакетной обработки..."):
                # Конвертируем даты в datetime
                date_from_dt = datetime.combine(date_from, datetime.min.time()) if date_from else None
                date_to_dt = datetime.combine(date_to, datetime.max.time()) if date_to else None

                result = send_ml_batch_task(
                    user_id=batch_user_id,
                    bank_id=batch_bank_id,
                    limit=batch_limit,
                    date_from=date_from_dt,
                    date_to=date_to_dt
                )

                if result:
                    st.success(f"✅ Успешно создано {result.get('processed_count', 0)} задач!")

                    # Детальная информация
                    with st.expander("Детали пакетной обработки", expanded=True):
                        # Статистика
                        st.subheader("📊 Статистика")
                        stats = result.get('statistics', {})
                        col_stat1, col_stat2, col_stat3 = st.columns(3)
                        with col_stat1:
                            st.metric("Уникальных банков", stats.get('unique_banks_count', 0))
                        with col_stat2:
                            if stats.get('oldest_review'):
                                st.metric("Самый старый отзыв",
                                          pd.to_datetime(stats['oldest_review']).strftime('%d.%m.%Y'))
                        with col_stat3:
                            if stats.get('newest_review'):
                                st.metric("Самый новый отзыв",
                                          pd.to_datetime(stats['newest_review']).strftime('%d.%m.%Y'))

                        # Список задач
                        st.subheader("📋 Созданные задачи")
                        tasks = result.get('tasks', [])
                        if tasks:
                            tasks_df = pd.DataFrame(tasks)
                            st.dataframe(tasks_df, use_container_width=True, height=300)
                        else:
                            st.info("Нет созданных задач")
                else:
                    st.error("❌ Ошибка при запуске пакетной обработки")

    with tab3:
        st.header("История ML задач")

        # Инициализируем session_state для фильтров
        if 'ml_filters' not in st.session_state:
            st.session_state.ml_filters = {
                'status': [],
                'operation_type': [],
                'bank_name': []
            }

        # Инициализируем session_state для данных задач
        if 'ml_tasks_data' not in st.session_state:
            st.session_state.ml_tasks_data = None

        # Кнопка обновления
        if st.button("🔄 Обновить список задач", use_container_width=True):
            with st.spinner("Загрузка задач..."):
                tasks = get_ml_tasks()
                if tasks:
                    st.success(f"✅ Загружено {len(tasks)} задач")
                    st.session_state.ml_tasks_data = tasks
                else:
                    st.info("Нет доступных ML задач")
                    st.session_state.ml_tasks_data = []

        # Если данные уже загружены, показываем их
        if st.session_state.ml_tasks_data is not None:
            tasks = st.session_state.ml_tasks_data

            # Преобразуем в DataFrame
            tasks_df = pd.DataFrame([task for task in tasks])

            if not tasks_df.empty:
                # Преобразуем даты
                for date_col in ['created_at', 'updated_at', 'created_at_api']:
                    if date_col in tasks_df.columns:
                        try:
                            tasks_df[date_col] = pd.to_datetime(tasks_df[date_col])
                        except:
                            pass

                # Сортируем по дате создания
                if 'created_at' in tasks_df.columns:
                    tasks_df = tasks_df.sort_values('created_at', ascending=False)

                # Фильтры с сохранением состояния
                st.subheader("Фильтры")
                col_filter1, col_filter2, col_filter3 = st.columns(3)

                with col_filter1:
                    # Получаем уникальные статусы
                    status_options = tasks_df['status'].unique() if 'status' in tasks_df.columns else []
                    # Используем session_state для сохранения выбранных значений
                    status_filter = st.multiselect(
                        "Статус",
                        options=status_options,
                        default=st.session_state.ml_filters['status'],
                        key='status_filter'
                    )
                    st.session_state.ml_filters['status'] = status_filter

                with col_filter2:
                    # Получаем уникальные типы операций
                    operation_options = tasks_df[
                        'operation_type'].unique() if 'operation_type' in tasks_df.columns else []
                    operation_filter = st.multiselect(
                        "Тип операции",
                        options=operation_options,
                        default=st.session_state.ml_filters['operation_type'],
                        key='operation_filter'
                    )
                    st.session_state.ml_filters['operation_type'] = operation_filter

                with col_filter3:
                    # Получаем уникальные названия банков
                    bank_options = tasks_df['bank_name'].unique() if 'bank_name' in tasks_df.columns else []
                    bank_filter = st.multiselect(
                        "Банк",
                        options=bank_options,
                        default=st.session_state.ml_filters['bank_name'],
                        key='bank_filter'
                    )
                    st.session_state.ml_filters['bank_name'] = bank_filter

                # Применяем фильтры
                filtered_df = tasks_df.copy()

                if status_filter:
                    filtered_df = filtered_df[filtered_df['status'].isin(status_filter)]
                if operation_filter:
                    filtered_df = filtered_df[filtered_df['operation_type'].isin(operation_filter)]
                if bank_filter:
                    filtered_df = filtered_df[filtered_df['bank_name'].isin(bank_filter)]

                # Отображаем статистику
                st.subheader("📊 Статистика")
                col_stat1, col_stat2, col_stat3, col_stat4 = st.columns(4)

                with col_stat1:
                    st.metric("Всего задач", len(tasks_df))
                with col_stat2:
                    st.metric("После фильтров", len(filtered_df))
                with col_stat3:
                    if 'status' in filtered_df.columns:
                        completed = len(filtered_df[filtered_df['status'] == 'COMPLETED'])
                        st.metric("Завершено", completed)
                with col_stat4:
                    if 'status' in filtered_df.columns:
                        failed = len(filtered_df[filtered_df['status'] == 'FAILED'])
                        st.metric("Ошибок", failed)

                # Отображаем таблицу
                st.subheader("📋 Список задач")

                # Показываем таблицу с возможностью развернуть детали
                for idx, row in filtered_df.iterrows():
                    task_id = row['id'] if 'id' in row and pd.notna(row['id']) else idx

                    with st.expander(f"Задача #{task_id} - {row.get('status', 'N/A')} - {row.get('created_at', '')}",
                                     expanded=False):
                        # Основная информация в колонках
                        col1, col2, col3 = st.columns(3)

                        with col1:
                            st.metric("ID", task_id)
                            if 'user_id' in row:
                                st.write(f"User ID: {row['user_id']}")
                            if 'review_id' in row and pd.notna(row['review_id']):
                                st.write(f"Review ID: {row['review_id']}")

                        with col2:
                            if 'status' in row:
                                status = row['status']
                                if status == 'COMPLETED':
                                    st.success(f"Статус: {status}")
                                elif status == 'FAILED':
                                    st.error(f"Статус: {status}")
                                else:
                                    st.info(f"Статус: {status}")

                            if 'operation_type' in row:
                                st.write(f"Тип: {row['operation_type']}")

                        with col3:
                            if 'bank_name' in row and pd.notna(row['bank_name']):
                                st.write(f"Банк: {row['bank_name']}")
                            if 'created_at' in row:
                                created_time = row['created_at']
                                if isinstance(created_time, pd.Timestamp):
                                    created_time = created_time.strftime('%Y-%m-%d %H:%M:%S')
                                st.write(f"Создана: {created_time}")

                        # Детали - вопрос
                        if 'question' in row and pd.notna(row['question']):
                            st.subheader("Вопрос:")
                            question_text = str(row['question'])
                            # Убираем ограничение по символам, показываем полный текст
                            st.text_area(
                                label=f"Вопрос задачи {task_id}",
                                value=question_text,
                                height=min(300, max(100, len(question_text) // 4)),  # Адаптивная высота
                                disabled=True,
                                key=f"question_{task_id}"  # Уникальный ключ
                            )

                        # Детали - результат
                        if 'result' in row and pd.notna(row['result']):
                            st.subheader("Результат:")
                            result_text = str(row['result'])

                            # Пытаемся распарсить JSON для красивого отображения
                            try:
                                result_json = json.loads(result_text)
                                with st.expander("📊 Структурированный результат"):
                                    st.json(result_json)
                            except:
                                pass

                            # Убираем ограничение по символам, показываем полный текст
                            st.text_area(
                                label=f"Результат задачи {task_id}",
                                value=result_text,
                                height=min(400, max(150, len(result_text) // 4)),  # Адаптивная высота
                                disabled=True,
                                key=f"result_{task_id}"  # Уникальный ключ
                            )

                # Кнопка для сброса фильтров
                if st.button("🧹 Сбросить фильтры", type="secondary"):
                    st.session_state.ml_filters = {
                        'status': [],
                        'operation_type': [],
                        'bank_name': []
                    }
                    st.rerun()
            else:
                st.info("Нет данных для отображения")

        # Детальный просмотр задачи по ID
        st.divider()
        st.subheader("🔍 Поиск задачи по ID")

        col_search1, col_search2 = st.columns([3, 1])

        with col_search1:
            selected_task_id = st.number_input(
                "Введите ID задачи для детального просмотра",
                min_value=1,
                value=1,
                key="detail_task_id"
            )

        with col_search2:
            st.write("")  # Пустое место для выравнивания
            st.write("")  # Пустое место для выравнивания
            if st.button("🔎 Показать детали", key="show_details_btn", use_container_width=True):
                with st.spinner("Поиск задачи..."):
                    task_details = get_ml_task(selected_task_id)
                    if task_details:
                        st.success(f"✅ Задача #{selected_task_id} найдена")

                        # Создаем expander для деталей
                        with st.expander(f"Детали задачи #{selected_task_id}", expanded=True):
                            # Отображаем основные поля в виде метрик
                            col_a, col_b, col_c = st.columns(3)

                            with col_a:
                                if 'id' in task_details:
                                    st.metric("ID задачи", task_details['id'])
                                if 'user_id' in task_details:
                                    st.write(f"User ID: {task_details['user_id']}")

                            with col_b:
                                if 'status' in task_details:
                                    status = task_details['status']
                                    if status == 'COMPLETED':
                                        st.success(f"Статус: {status}")
                                    elif status == 'FAILED':
                                        st.error(f"Статус: {status}")
                                    else:
                                        st.info(f"Статус: {status}")

                            with col_c:
                                if 'operation_type' in task_details:
                                    st.write(f"Тип операции: {task_details['operation_type']}")
                                if 'created_at' in task_details:
                                    try:
                                        created = pd.to_datetime(task_details['created_at'])
                                        st.write(f"Создана: {created.strftime('%Y-%m-%d %H:%M:%S')}")
                                    except:
                                        st.write(f"Создана: {task_details['created_at']}")

                            # Отображаем дополнительные поля
                            if 'review_id' in task_details and task_details['review_id']:
                                st.write(f"Review ID: {task_details['review_id']}")

                            if 'bank_name' in task_details and task_details['bank_name']:
                                st.write(f"Банк: {task_details['bank_name']}")

                            # Показываем вопрос
                            if 'question' in task_details and task_details['question']:
                                st.subheader("Вопрос:")
                                question_text = str(task_details['question'])
                                st.text_area(
                                    label=f"Вопрос задачи {selected_task_id}",
                                    value=question_text,
                                    height=300,
                                    disabled=True,
                                    key=f"detail_question_{selected_task_id}"
                                )

                            # Показываем результат
                            if 'result' in task_details and task_details['result']:
                                st.subheader("Результат:")
                                result_text = str(task_details['result'])

                                # Пытаемся распарсить JSON для красивого отображения
                                try:
                                    result_json = json.loads(result_text)
                                    with st.expander("📊 Структурированный результат"):
                                        st.json(result_json)
                                except:
                                    pass

                                st.text_area(
                                    label=f"Результат задачи {selected_task_id}",
                                    value=result_text,
                                    height=400,
                                    disabled=True,
                                    key=f"detail_result_{selected_task_id}"
                                )

                            # Показываем полный JSON
                            with st.expander("📄 Полный JSON ответ"):
                                st.json(task_details)
                    else:
                        st.error(f"❌ Задача #{selected_task_id} не найдена")

    with tab4:
        st.header("Статистика batch обработки")

        # Фильтры для статистики
        col1, col2 = st.columns(2)

        with col1:
            stats_bank_id = st.number_input("Bank ID для статистики (опционально)",
                                            min_value=1,
                                            value=None,
                                            key='stats_bank_id')

        with col2:
            st.write("**Период (created_at_api):**")
            col_date1, col_date2 = st.columns(2)
            with col_date1:
                stats_date_from = st.date_input("С даты",
                                                value=None,
                                                key='stats_date_from')
            with col_date2:
                stats_date_to = st.date_input("По дату",
                                              value=None,
                                              key='stats_date_to')

        if st.button("📊 Загрузить статистику", type="primary", use_container_width=True):
            with st.spinner("Загрузка статистики..."):
                # Конвертируем даты
                stats_date_from_dt = datetime.combine(stats_date_from, datetime.min.time()) if stats_date_from else None
                stats_date_to_dt = datetime.combine(stats_date_to, datetime.max.time()) if stats_date_to else None

                stats = get_ml_batch_stats(
                    bank_id=stats_bank_id,
                    date_from=stats_date_from_dt,
                    date_to=stats_date_to_dt
                )

                if stats:
                    st.success("✅ Статистика загружена")

                    # Общая статистика
                    statistics = stats.get('statistics', {})
                    st.subheader("📈 Общая статистика")

                    col_stat1, col_stat2, col_stat3, col_stat4 = st.columns(4)
                    with col_stat1:
                        st.metric("Всего отзывов", statistics.get('total_reviews', 0))
                    with col_stat2:
                        st.metric("Обработано", statistics.get('processed_reviews', 0))
                    with col_stat3:
                        st.metric("Ожидают обработки", statistics.get('pending_reviews', 0))
                    with col_stat4:
                        st.metric("Процент обработки",
                                  f"{statistics.get('processing_percentage', 0)}%")

                    # Получаем задачи ML для дополнительной статистики
                    ml_tasks_data = get_ml_tasks()
                    if ml_tasks_data:
                        df_ml = pd.DataFrame(ml_tasks_data)

                        # Минимальная и максимальная даты ML задач (по created_at_api)
                        if 'created_at_api' in df_ml.columns:
                            df_ml['created_at_api'] = pd.to_datetime(df_ml['created_at_api'], errors='coerce')
                            ml_min_date = df_ml['created_at_api'].min()
                            ml_max_date = df_ml['created_at_api'].max()

                            st.subheader("📅 Даты ML обработки (created_at_api)")
                            col_date_min, col_date_max = st.columns(2)
                            with col_date_min:
                                if pd.notna(ml_min_date):
                                    st.metric("Самая ранняя дата", ml_min_date.strftime('%Y-%m-%d'))
                            with col_date_max:
                                if pd.notna(ml_max_date):
                                    st.metric("Самая поздняя дата", ml_max_date.strftime('%Y-%m-%d'))

                            # График по месяцам для batch задач
                            batch_tasks = df_ml[df_ml['operation_type'] == 'BATCH'].copy()
                            if not batch_tasks.empty and 'created_at_api' in batch_tasks.columns:
                                st.subheader("📈 Распределение batch задач по месяцам")
                                batch_tasks['month'] = batch_tasks['created_at_api'].dt.to_period('M')
                                monthly_counts = batch_tasks['month'].value_counts().sort_index()
                                monthly_df = pd.DataFrame({'Month': monthly_counts.index.astype(str),
                                                           'Count': monthly_counts.values})

                                if PLOTLY_AVAILABLE and not monthly_df.empty:
                                    fig = px.bar(monthly_df, x='Month', y='Count',
                                                 title='Batch задачи по месяцам (created_at_api)',
                                                 color='Count',
                                                 color_continuous_scale='Blues')
                                    st.plotly_chart(fig, use_container_width=True)
                                else:
                                    st.dataframe(monthly_df, use_container_width=True)

                    # Статистика по банкам
                    banks = stats.get('banks', [])
                    if banks:
                        st.subheader("🏦 Статистика по банкам")
                        banks_df = pd.DataFrame(banks)

                        # Визуализация
                        col_chart1, col_chart2 = st.columns(2)

                        with col_chart1:
                            # Круговая диаграмма по банкам
                            if not banks_df.empty:
                                fig1 = px.pie(
                                    banks_df,
                                    values='total_reviews',
                                    names='bank_name',
                                    title='Распределение отзывов по банкам',
                                    hole=0.3
                                )
                                st.plotly_chart(fig1, use_container_width=True)

                        with col_chart2:
                            # Столбчатая диаграмма
                            if not banks_df.empty:
                                fig2 = px.bar(
                                    banks_df,
                                    x='bank_name',
                                    y=['total_reviews', 'pending_reviews'],
                                    title='Отзывы по банкам',
                                    barmode='group',
                                    labels={'value': 'Количество', 'variable': 'Тип'}
                                )
                                st.plotly_chart(fig2, use_container_width=True)

                        # Таблица с деталями
                        st.dataframe(banks_df, use_container_width=True)
                    else:
                        st.info("Нет данных по банкам")
                else:
                    st.error("❌ Ошибка при загрузке статистики")


# =========================
# ФУНКЦИЯ ЭКСПОРТА ML ЗАДАЧ
# =========================

def export_ml_tasks_page():
    """Страница для экспорта ML задач в CSV"""
    if not st.session_state.logged_in:
        st.warning("⚠️ Please login first")
        return

    st.title('📤 Экспорт ML задач в CSV')
    st.markdown("Фильтрация и экспорт задач из таблицы MLTask")

    # Проверяем доступность данных
    with st.expander("ℹ️ Информация", expanded=True):
        st.info("""
        Эта страница позволяет фильтровать задачи ML и экспортировать их в CSV файл.
        Для начала работы загрузите задачи или используйте уже загруженные данные.
        """)

    # Инициализация данных
    if 'ml_tasks_data' not in st.session_state:
        st.session_state.ml_tasks_data = None

    # Кнопка загрузки данных
    col1, col2 = st.columns([3, 1])
    with col1:
        if st.button("🔄 Загрузить все задачи", type="primary", use_container_width=True):
            with st.spinner("Загрузка задач..."):
                tasks = get_ml_tasks()
                if tasks:
                    st.session_state.ml_tasks_data = tasks
                    st.success(f"✅ Загружено {len(tasks)} задач")
                else:
                    st.error("❌ Не удалось загрузить задачи")

    with col2:
        if st.button("🧹 Очистить кэш", type="secondary", use_container_width=True):
            st.session_state.ml_tasks_data = None
            st.success("Кэш очищен")

    # Если данные не загружены, показываем только кнопку загрузки
    if not st.session_state.ml_tasks_data:
        st.warning("Данные не загружены. Нажмите кнопку выше для загрузки.")
        return

    tasks = st.session_state.ml_tasks_data
    df = pd.DataFrame(tasks)

    # Преобразуем даты
    for date_col in ['created_at', 'updated_at', 'created_at_api']:
        if date_col in df.columns:
            df[date_col] = pd.to_datetime(df[date_col], errors='coerce')

    # Боковая панель с фильтрами
    with st.sidebar:
        st.header("⚙️ Фильтры")

        # Фильтр по статусам
        st.subheader("Статусы")
        status_options = list(df['status'].unique()) if 'status' in df.columns else []
        selected_statuses = st.multiselect(
            "Выберите статусы:",
            options=status_options,
            default=st.session_state.ml_export_filters.get('statuses', status_options)
        )

        # Фильтр по типам операций
        st.subheader("Типы операций")
        operation_options = list(df['operation_type'].unique()) if 'operation_type' in df.columns else []
        selected_operations = st.multiselect(
            "Выберите типы операций:",
            options=operation_options,
            default=st.session_state.ml_export_filters.get('operation_types', operation_options)
        )

        # Фильтр по датам (created_at_api)
        st.subheader("Дата создания отзыва (created_at_api)")
        col1, col2 = st.columns(2)
        with col1:
            date_from = st.date_input(
                "От:",
                value=st.session_state.ml_export_filters.get('date_from'),
                key='export_date_from'
            )
        with col2:
            date_to = st.date_input(
                "До:",
                value=st.session_state.ml_export_filters.get('date_to'),
                key='export_date_to'
            )

        # Фильтры по ID
        st.subheader("Фильтры по ID")
        user_id_filter = st.number_input(
            "User ID:",
            min_value=0,
            value=st.session_state.ml_export_filters.get('user_id') or None,
            step=1,
            placeholder="Все"
        )

        review_id_filter = st.number_input(
            "Review ID:",
            min_value=0,
            value=st.session_state.ml_export_filters.get('review_id') or None,
            step=1,
            placeholder="Все"
        )

        bank_id_filter = st.number_input(
            "Bank ID:",
            min_value=0,
            value=st.session_state.ml_export_filters.get('bank_id') or None,
            step=1,
            placeholder="Все"
        )

        # Текстовые фильтры
        st.subheader("Текстовые фильтры")
        bank_name_filter = st.text_input(
            "Название банка:",
            value=st.session_state.ml_export_filters.get('bank_name', ''),
            placeholder="Часть названия"
        )
        user_city_filter = st.text_input(
            "Город пользователя:",
            value=st.session_state.ml_export_filters.get('user_city', ''),
            placeholder="Часть названия города"
        )

        # Кнопки управления фильтрами
        st.subheader("Управление")
        col_btn1, col_btn2 = st.columns(2)
        with col_btn1:
            apply_filters = st.button("✅ Применить", type="primary", use_container_width=True)
        with col_btn2:
            reset_filters = st.button("🧹 Сбросить", type="secondary", use_container_width=True)

        if reset_filters:
            st.session_state.ml_export_filters = {
                'statuses': status_options,
                'operation_types': operation_options,
                'date_from': None,
                'date_to': None,
                'user_id': None,
                'review_id': None,
                'bank_id': None,
                'bank_name': '',
                'user_city': ''
            }
            st.rerun()

        # Сохраняем фильтры
        if apply_filters:
            st.session_state.ml_export_filters = {
                'statuses': selected_statuses,
                'operation_types': selected_operations,
                'date_from': date_from,
                'date_to': date_to,
                'user_id': user_id_filter if user_id_filter else None,
                'review_id': review_id_filter if review_id_filter else None,
                'bank_id': bank_id_filter if bank_id_filter else None,
                'bank_name': bank_name_filter,
                'user_city': user_city_filter
            }
            st.rerun()

    # Применяем фильтры
    filtered_df = df.copy()

    # Статусы
    if st.session_state.ml_export_filters['statuses']:
        filtered_df = filtered_df[filtered_df['status'].isin(st.session_state.ml_export_filters['statuses'])]

    # Типы операций
    if st.session_state.ml_export_filters['operation_types']:
        filtered_df = filtered_df[
            filtered_df['operation_type'].isin(st.session_state.ml_export_filters['operation_types'])]

    # Дата создания отзыва (created_at_api)
    if st.session_state.ml_export_filters['date_from'] and 'created_at_api' in filtered_df.columns:
        date_from_dt = datetime.combine(st.session_state.ml_export_filters['date_from'], datetime.min.time())
        filtered_df = filtered_df[filtered_df['created_at_api'] >= date_from_dt]

    if st.session_state.ml_export_filters['date_to'] and 'created_at_api' in filtered_df.columns:
        date_to_dt = datetime.combine(st.session_state.ml_export_filters['date_to'], datetime.max.time())
        filtered_df = filtered_df[filtered_df['created_at_api'] <= date_to_dt]

    # User ID
    if st.session_state.ml_export_filters['user_id']:
        filtered_df = filtered_df[filtered_df['user_id'] == st.session_state.ml_export_filters['user_id']]

    # Review ID
    if st.session_state.ml_export_filters['review_id'] and 'review_id' in filtered_df.columns:
        filtered_df = filtered_df[filtered_df['review_id'] == st.session_state.ml_export_filters['review_id']]

    # Bank ID
    if st.session_state.ml_export_filters['bank_id'] and 'bank_id' in filtered_df.columns:
        filtered_df = filtered_df[filtered_df['bank_id'] == st.session_state.ml_export_filters['bank_id']]

    # Bank Name
    if st.session_state.ml_export_filters['bank_name'] and 'bank_name' in filtered_df.columns:
        filtered_df = filtered_df[
            filtered_df['bank_name'].astype(str).str.contains(
                st.session_state.ml_export_filters['bank_name'],
                case=False,
                na=False
            )
        ]

    # User City
    if st.session_state.ml_export_filters['user_city'] and 'user_city' in filtered_df.columns:
        filtered_df = filtered_df[
            filtered_df['user_city'].astype(str).str.contains(
                st.session_state.ml_export_filters['user_city'],
                case=False,
                na=False
            )
        ]

    # Отображаем статистику
    st.subheader("📊 Статистика фильтрации")

    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.metric("Всего задач", len(df))

    with col2:
        st.metric("После фильтров", len(filtered_df))

    with col3:
        if not filtered_df.empty and 'status' in filtered_df.columns:
            completed = len(filtered_df[filtered_df['status'] == 'COMPLETED'])
            st.metric("Завершено", completed)

    with col4:
        if not filtered_df.empty and 'created_at_api' in filtered_df.columns:
            date_range = filtered_df['created_at_api']
            if not date_range.empty:
                min_date = date_range.min().strftime('%d.%m.%Y')
                st.metric("Самая старая", min_date)

    # Предпросмотр данных
    st.subheader("👁️ Предпросмотр данных")

    if not filtered_df.empty:
        # Создаем копию для отображения
        display_df = filtered_df.copy()

        # Форматируем даты для отображения
        for date_col in ['created_at', 'updated_at', 'created_at_api']:
            if date_col in display_df.columns:
                display_df[date_col] = display_df[date_col].dt.strftime('%Y-%m-%d %H:%M:%S')

        # Обрезаем длинные тексты для предпросмотра
        if 'question' in display_df.columns:
            display_df['question_preview'] = display_df['question'].apply(
                lambda x: (str(x)[:150] + '...') if pd.notna(x) and len(str(x)) > 150 else str(x) if pd.notna(x) else ''
            )

        if 'result' in display_df.columns:
            display_df['result_preview'] = display_df['result'].apply(
                lambda x: (str(x)[:150] + '...') if pd.notna(x) and len(str(x)) > 150 else str(x) if pd.notna(x) else ''
            )

        # Выбираем колонки для отображения
        display_columns = []
        if 'id' in display_df.columns:
            display_columns.append('id')
        if 'status' in display_df.columns:
            display_columns.append('status')
        if 'operation_type' in display_df.columns:
            display_columns.append('operation_type')
        if 'user_id' in display_df.columns:
            display_columns.append('user_id')
        if 'bank_name' in display_df.columns:
            display_columns.append('bank_name')
        if 'question_preview' in display_df.columns:
            display_columns.append('question_preview')
        if 'result_preview' in display_df.columns:
            display_columns.append('result_preview')
        if 'created_at_api' in display_df.columns:
            display_columns.append('created_at_api')

        st.dataframe(display_df[display_columns], use_container_width=True, height=400)
    else:
        st.warning("Нет данных, соответствующих выбранным фильтрам.")

    # Раздел экспорта
    st.divider()
    st.subheader("📥 Экспорт в CSV")

    if not filtered_df.empty:
        # Настройки экспорта
        col_export1, col_export2, col_export3 = st.columns(3)

        with col_export1:
            export_filename = st.text_input(
                "Имя файла:",
                value=f"mltasks_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
            )

        with col_export2:
            include_full_text = st.checkbox("Включить полный текст вопроса и результата", value=True)

        with col_export3:
            parse_json_result = st.checkbox("Распарсить JSON результат в отдельные колонки", value=True)

        # Подготовка данных для экспорта
        export_df = filtered_df.copy()

        # Форматируем даты для экспорта
        for date_col in ['created_at', 'updated_at', 'created_at_api']:
            if date_col in export_df.columns:
                export_df[date_col] = export_df[date_col].dt.strftime('%Y-%m-%d %H:%M:%S')

        # Укорачиваем текст для CSV, если не включена опция полного текста
        if not include_full_text:
            if 'question' in export_df.columns:
                export_df['question'] = export_df['question'].apply(
                    lambda x: (str(x)[:500] + '...') if pd.notna(x) and len(str(x)) > 500 else str(x) if pd.notna(
                        x) else ''
                )
            if 'result' in export_df.columns:
                export_df['result'] = export_df['result'].apply(
                    lambda x: (str(x)[:500] + '...') if pd.notna(x) and len(str(x)) > 500 else str(x) if pd.notna(
                        x) else ''
                )

        # Парсинг JSON результатов в отдельные колонки
        if parse_json_result and 'result' in export_df.columns:
            st.info("Парсинг JSON результатов...")

            # Создаем список для распарсенных данных
            parsed_results = []

            for idx, row in export_df.iterrows():
                result_text = row['result'] if pd.notna(row['result']) else ''
                parsed_data = parse_ml_result_json(result_text)
                parsed_results.append(parsed_data)

            # Создаем DataFrame из распарсенных данных
            if parsed_results:
                parsed_df = pd.DataFrame(parsed_results)

                # Объединяем с основным DataFrame
                # Сначала сохраняем оригинальный result
                export_df['result_original'] = export_df['result']

                # Удаляем оригинальную колонку result, если пользователь хочет только распарсенные данные
                export_df = export_df.drop(columns=['result'])

                # Объединяем с распарсенными данными
                export_df = pd.concat([export_df, parsed_df], axis=1)

                st.success(
                    f"✅ Распарсено {len(parsed_df)} JSON результатов. Добавлено {len(parsed_df.columns)} новых колонок.")

        # Конвертируем DataFrame в CSV
        csv_data = export_df.to_csv(index=False, encoding='utf-8-sig')

        # Кнопка скачивания
        st.download_button(
            label="📥 Скачать CSV",
            data=csv_data,
            file_name=export_filename,
            mime="text/csv",
            type="primary",
            use_container_width=True
        )

        # Дополнительная информация
        st.info(f"📊 Файл будет содержать {len(export_df)} записей и {len(export_df.columns)} колонок.")

        # Быстрые действия
        st.subheader("⚡ Быстрые действия")

        quick_cols = st.columns(4)

        with quick_cols[0]:
            if st.button("Только новые", use_container_width=True):
                st.session_state.ml_export_filters['statuses'] = ['NEW']
                st.rerun()

        with quick_cols[1]:
            if st.button("Только выполненные", use_container_width=True):
                st.session_state.ml_export_filters['statuses'] = ['COMPLETED']
                st.rerun()

        with quick_cols[2]:
            if st.button("За сегодня", use_container_width=True):
                today = date.today()
                st.session_state.ml_export_filters['date_from'] = today
                st.session_state.ml_export_filters['date_to'] = today
                st.rerun()

        with quick_cols[3]:
            if st.button("Только batch", use_container_width=True):
                st.session_state.ml_export_filters['operation_types'] = ['BATCH']
                st.rerun()
    else:
        st.warning("Нет данных для экспорта. Измените фильтры или загрузите задачи.")


# =========================
# ФУНКЦИЯ ЭКСПОРТА ПАРСЕРА
# =========================

def export_parser_page():
    """Страница для экспорта данных парсера"""
    if not st.session_state.logged_in:
        st.warning("⚠️ Please login first")
        return

    st.title('📤 Экспорт данных парсера')

    # Получаем уникальные названия банков
    bank_names = get_unique_bank_names()

    # Фильтры
    col1, col2 = st.columns(2)

    with col1:
        export_bank = st.selectbox("Bank Name", options=[""] + bank_names, key='export_parser_page_bank')
        export_status = st.selectbox(
            "Status",
            ["", "Зачтено", "Не зачтено", "Проверяется", "Ошибка парсинга"],
            key='export_parser_page_status'
        )

    with col2:
        export_min_grade = st.number_input("Min Grade", min_value=1, max_value=5, value=1, step=1,
                                           key='export_parser_min_grade')
        export_max_grade = st.number_input("Max Grade", min_value=1, max_value=5, value=5, step=1,
                                           key='export_parser_max_grade')
        export_limit = st.number_input("Limit", min_value=1, max_value=10000, value=1000, step=100,
                                       key='export_parser_limit')

    col3, col4 = st.columns(2)
    with col3:
        export_date_from = st.date_input("From Date (created_at_api)", value=None, key='export_parser_date_from')
    with col4:
        export_date_to = st.date_input("To Date (created_at_api)", value=None, key='export_parser_date_to')

    if st.button("📥 Export to CSV", type="primary", use_container_width=True):
        with st.spinner("Exporting data..."):
            # Получаем данные
            reviews = search_reviews(
                bank_name=export_bank if export_bank else None,
                status=export_status if export_status else None,
                min_grade=export_min_grade,
                max_grade=export_max_grade,
                limit=export_limit
            )

            if reviews:
                df = pd.DataFrame(reviews)

                # Применяем фильтр по дате created_at_api
                if export_date_from or export_date_to:
                    if 'created_at_api' in df.columns:
                        df['created_at_api'] = pd.to_datetime(df['created_at_api'], errors='coerce')
                        if export_date_from:
                            date_from_dt = pd.Timestamp(export_date_from)
                            df = df[df['created_at_api'] >= date_from_dt]
                        if export_date_to:
                            date_to_dt = pd.Timestamp(export_date_to) + pd.Timedelta(days=1)
                            df = df[df['created_at_api'] <= date_to_dt]

                # Конвертируем в CSV
                csv_data = df.to_csv(index=False, encoding='utf-8-sig')

                # Скачивание
                st.download_button(
                    label="📥 Download CSV",
                    data=csv_data,
                    file_name=f"parser_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                    mime="text/csv",
                    type="primary",
                    use_container_width=True
                )

                st.success(f"✅ Exported {len(df)} records")
            else:
                st.warning("No data to export")


# =========================
# СУЩЕСТВУЮЩИЕ ФУНКЦИИ (без изменений)
# =========================

def login():
    st.header('Login')
    email = st.text_input('Email')
    password = st.text_input('Password', type='password')
    if st.button('Login'):
        data = {'email': email, 'password': password}
        response = make_api_request('/api/users/signin', method='POST', data=data)
        if response:
            st.session_state.logged_in = True
            st.session_state.email = email
            st.session_state.is_admin = response.get('is_admin', False)
            st.success('Logged in successfully!')
            time.sleep(1)
            st.rerun()
        else:
            st.error('Login failed. Please check your credentials.')


def register():
    st.header('Register')
    name = st.text_input('Name')
    bank_position = st.text_input('Bank Position')
    bank_unit = st.text_input('Bank Unit')
    email = st.text_input('Email')
    password = st.text_input('Password', type='password')

    if st.button('Register'):
        data = {
            'name': name,
            'bank_position': bank_position,
            'bank_unit': bank_unit,
            'email': email,
            'password': password
        }

        response = make_api_request('/api/users/signup', method='POST', data=data)
        if response:
            st.success('Registered successfully! Please, use Menu to log in.')
            time.sleep(2)
            st.rerun()
        else:
            st.error('Registration failed. Please try again.')


def list_of_events():
    st.header('List of events')

    # Для админов добавляем опции просмотра
    view_mode = "my_events"
    target_email = None

    if st.session_state.is_admin:
        st.subheader('Admin Mode')
        view_mode = st.radio(
            "View events:",
            ["My events", "All users", "Specific user"],
            horizontal=True
        )

        if view_mode == "Specific user":
            target_email = st.text_input('Enter user email:')
        elif view_mode == "All users":
            target_email = None

    if st.button("Load Events", use_container_width=True):
        events_response = get_user_events(view_mode, target_email)

        if st.session_state.is_admin:
            if view_mode == "All users":
                st.info("📋 Viewing events for ALL users")
            elif view_mode == "Specific user" and target_email:
                st.info(f"👤 Viewing events for user: {target_email}")
            else:
                st.info("👤 Viewing your events")

        if events_response and 'events' in events_response and events_response['events']:
            df = pd.DataFrame(events_response['events'])

            if st.session_state.is_admin and 'view_mode' in events_response:
                if events_response['view_mode'] == 'all_users':
                    st.success(f"Found {len(df)} events from all users")
                elif events_response['view_mode'] == 'specific_user':
                    st.success(f"Found {len(df)} events for user: {events_response.get('target_email', 'N/A')}")
            else:
                st.write(f"Total events found: {len(df)}")

            if 'ml_input' in df.columns:
                df['ml_input'] = df['ml_input'].apply(lambda x: normalize_data(x))

            if 'created_at' in df.columns:
                df['created_at'] = pd.to_datetime(df['created_at']).dt.strftime('%Y-%m-%d %H:%M:%S')

            column_order = [
                'id', 'event_id', 'user_id', 'is_admin',
                'balance_operation', 'balance_operation_amount', 'created_at',
                'ml_input', 'ml_output_result'
            ]

            existing_columns = [col for col in column_order if col in df.columns]

            other_columns = [col for col in df.columns if col not in existing_columns]
            final_columns = existing_columns + other_columns

            sort_column = 'created_at' if 'created_at' in df.columns else 'id'

            # Отображаем таблицу
            st.dataframe(
                df.sort_values(sort_column, ascending=False),
                hide_index=True,
                column_order=final_columns
            )

            # Дополнительная статистика для админов
            if st.session_state.is_admin and len(df) > 0:
                st.subheader("📊 Statistics")

                # Статистика по пользователям
                if 'user_id' in df.columns:
                    unique_users = df['user_id'].nunique()
                    st.write(f"Unique users: {unique_users}")

        else:
            st.write('No events found.')
            if st.session_state.is_admin and events_response:
                st.write("Response structure:", events_response.keys())


def logout():
    st.session_state.logged_in = False
    st.session_state.email = None
    st.session_state.is_admin = False
    st.success('Logged out successfully!')
    time.sleep(1)
    st.rerun()


# Вспомогательная функция
def normalize_data(data):
    """Нормализация данных"""
    try:
        if isinstance(data, str):
            return json.loads(data)
        return data
    except:
        return data


if __name__ == '__main__':
    main()
