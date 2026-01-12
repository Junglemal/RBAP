import streamlit as st
import requests
import pandas as pd
import time
import json
from datetime import datetime

API_URL = 'http://app:8080'  # Используйте 'http://localhost:8080' если запускаете локально


# Вспомогательная функция для API запросов
def make_api_request(endpoint, method='GET', data=None, params=None):
    try:
        url = f'{API_URL}{endpoint}'
        if method == 'GET':
            response = requests.get(url, params=params)
        elif method == 'POST':
            response = requests.post(url, json=data)
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
# ФУНКЦИИ ДЛЯ РАБОТЫ С ПАРСЕРОМ (исправленные пути)
# =========================

def get_parser_jobs(limit=100, offset=0):
    """Получить список задач парсинга"""
    endpoint = '/api/parser/parser/jobs'  # ⭐ ИСПРАВЛЕНО
    params = {'limit': limit, 'offset': offset}
    return make_api_request(endpoint, method='GET', params=params)


def get_parser_job_by_id(job_id):
    """Получить задачу парсинга по ID"""
    endpoint = f'/api/parser/parser/jobs/{job_id}'  # ⭐ ИСПРАВЛЕНО
    return make_api_request(endpoint, method='GET')


def get_all_reviews(limit=100, offset=0):
    """Получить все отзывы"""
    endpoint = '/api/parser/parser/reviews'  # ⭐ ИСПРАВЛЕНО
    params = {'limit': limit, 'offset': offset}
    return make_api_request(endpoint, method='GET', params=params)


def get_review_by_id(review_id):
    """Получить отзыв по ID"""
    endpoint = f'/api/parser/parser/reviews/{review_id}'  # ⭐ ИСПРАВЛЕНО
    return make_api_request(endpoint, method='GET')


def get_reviews_by_bank(bank_id, limit=100, offset=0):
    """Получить отзывы по банку"""
    endpoint = f'/api/parser/parser/reviews/bank/{bank_id}'  # ⭐ ИСПРАВЛЕНО
    params = {'limit': limit, 'offset': offset}
    return make_api_request(endpoint, method='GET', params=params)


def search_reviews(bank_name=None, status=None, min_grade=None, max_grade=None, limit=100, offset=0):
    """Поиск отзывов"""
    endpoint = '/api/parser/parser/reviews/search'  # ⭐ ИСПРАВЛЕНО
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
    endpoint = '/api/parser/parser/stats/summary'  # ⭐ ИСПРАВЛЕНО
    return make_api_request(endpoint, method='GET')


def get_bank_stats():
    """Получить статистику по банкам"""
    endpoint = '/api/parser/parser/stats/banks'  # ⭐ ИСПРАВЛЕНО
    return make_api_request(endpoint, method='GET')


def run_parser(data):
    """Запустить парсер"""
    endpoint = '/api/parser/parser/run'  # ⭐ ИСПРАВЛЕНО
    return make_api_request(endpoint, method='POST', data=data)


def run_test_parser(page=1, save_to_db=True):
    """Запустить тестовый парсер"""
    endpoint = '/api/parser/parser/run/test'  # ⭐ ИСПРАВЛЕНО
    data = {
        'page': page,
        'save_to_db': save_to_db
    }
    return make_api_request(endpoint, method='POST', data=data)


def delete_review_by_id(review_id):
    """Удалить отзыв по ID"""
    endpoint = f'/api/parser/parser/reviews/{review_id}'  # ⭐ ИСПРАВЛЕНО
    return make_api_request(endpoint, method='DELETE')


def delete_reviews_by_status(status_name):
    """Удалить отзывы по статусу"""
    endpoint = f'/api/parser/parser/reviews/status/{status_name}'  # ⭐ ИСПРАВЛЕНО
    return make_api_request(endpoint, method='DELETE')


def update_job_status(job_id, status=None, current_page=None, total_pages=None,
                      processed_reviews=None, message=None):
    """Обновить статус задачи парсинга"""
    endpoint = f'/api/parser/parser/jobs/{job_id}/update'  # ⭐ ИСПРАВЛЕНО
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
    endpoint = '/api/parser/parser/health'  # ⭐ ИСПРАВЛЕНО
    return make_api_request(endpoint, method='GET')


# =========================
# ФУНКЦИИ ПОЛЬЗОВАТЕЛЯ (оставляем как было)
# =========================

def get_user_balance():
    """Получить баланс пользователя"""
    if not st.session_state.logged_in:
        return None
    endpoint = '/api/balance/balance'
    params = {'email': st.session_state.email}
    return make_api_request(endpoint, method='GET', params=params)


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


# =========================
# ГЛАВНОЕ МЕНЮ
# =========================

def main():
    st.title('ML service study project')

    if not st.session_state.logged_in:
        menu = ['Login', 'Register']
    else:
        if st.session_state.is_admin:
            menu = ['Home', 'Parser Dashboard', 'Parser Control',
                    'Add Balance', 'Iris prediction', 'List of events',
                    'Logout']
        else:
            menu = ['Home', 'Add Balance', 'Iris prediction',
                    'List of events', 'Logout']

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
    elif choice == 'List of events':
        list_of_events()
    elif choice == 'Logout':
        logout()


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
        "🏦 By Bank",
        "🔄 Jobs",
        "🗑️ Delete"
    ])

    with tab1:
        st.header("All Reviews")

        col1, col2 = st.columns(2)
        with col1:
            limit = st.number_input("Limit", min_value=1, max_value=1000, value=100, step=50)
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
                        col1, col2, col3 = st.columns(3)
                        with col1:
                            st.metric("Total", len(df))
                        with col2:
                            unique_banks = df['bank_name'].nunique() if 'bank_name' in df.columns else 0
                            st.metric("Unique Banks", unique_banks)
                        with col3:
                            if 'grade_api' in df.columns:
                                avg_grade = df['grade_api'].mean()
                                st.metric("Avg Grade", f"{avg_grade:.1f}")
                else:
                    st.warning("No reviews found or failed to load")

    with tab2:
        st.header("Search Reviews")

        col1, col2 = st.columns(2)
        with col1:
            search_bank = st.text_input("Bank Name (contains)")
            search_status = st.selectbox(
                "Status",
                ["", "Зачтено", "Не зачтено", "Проверяется", "Ошибка парсинга"]
            )
        with col2:
            min_grade = st.number_input("Min Grade", min_value=1, max_value=5, value=1, step=1)
            max_grade = st.number_input("Max Grade", min_value=1, max_value=5, value=5, step=1)
            limit_search = st.number_input("Search Limit", min_value=1, max_value=500, value=100, step=50)

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
                    st.dataframe(df, use_container_width=True, height=400)
                else:
                    st.info("No reviews found matching criteria")

    with tab3:
        st.header("Reviews by Bank")

        bank_id = st.number_input("Bank ID", min_value=1, value=1, step=1)
        limit_bank = st.number_input("Bank Reviews Limit", min_value=1, max_value=500, value=100, step=50)

        if st.button("Load Bank Reviews", use_container_width=True):
            with st.spinner("Loading bank reviews..."):
                reviews = get_reviews_by_bank(bank_id, limit=limit_bank)
                if reviews:
                    st.success(f"✅ Found {len(reviews)} reviews for bank ID {bank_id}")
                    df = pd.DataFrame(reviews)
                    st.dataframe(df, use_container_width=True, height=400)
                else:
                    st.info(f"No reviews found for bank ID {bank_id}")

    with tab4:
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

    with tab5:
        st.header("Delete Operations")

        col1, col2 = st.columns(2)

        with col1:
            st.subheader("Delete by ID")
            delete_id = st.number_input("Review ID to delete", min_value=1, value=1, step=1)

            if st.button("🗑️ Delete Review", type="secondary", use_container_width=True):
                if st.session_state.get(f"confirm_delete_{delete_id}", False):
                    result = delete_review_by_id(delete_id)
                    if result:
                        st.success(f"✅ Review {delete_id} deleted successfully")
                        st.session_state[f"confirm_delete_{delete_id}"] = False
                else:
                    st.warning(f"⚠️ Are you sure you want to delete review {delete_id}?")
                    if st.button(f"Confirm Delete Review {delete_id}"):
                        st.session_state[f"confirm_delete_{delete_id}"] = True
                        st.rerun()

        with col2:
            st.subheader("Delete by Status")
            delete_status = st.selectbox(
                "Status to delete",
                ["Зачтено", "Не зачтено", "Проверяется", "Ошибка парсинга"]
            )

            if st.button("🗑️ Delete All by Status", type="secondary", use_container_width=True):
                if st.session_state.get(f"confirm_delete_status_{delete_status}", False):
                    result = delete_reviews_by_status(delete_status)
                    if result:
                        deleted_count = result.get('deleted_count', 0)
                        st.success(f"✅ Deleted {deleted_count} reviews with status '{delete_status}'")
                        st.session_state[f"confirm_delete_status_{delete_status}"] = False
                else:
                    st.warning(f"⚠️ Are you sure you want to delete ALL reviews with status '{delete_status}'?")
                    if st.button(f"Confirm Delete All '{delete_status}'"):
                        st.session_state[f"confirm_delete_status_{delete_status}"] = True
                        st.rerun()


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
    email = st.text_input('Email')
    password = st.text_input('Password', type='password')
    if st.button('Register'):
        data = {'email': email, 'password': password}
        response = make_api_request('/api/users/signup', method='POST', data=data)
        if response:
            st.success('Registered successfully! Please, use Menu to log in.')
            time.sleep(2)
            st.rerun()
        else:
            st.error('Registration failed. Please try again.')


def home():
    st.header('Welcome! Please, use Menu to: \n- Add Balance \n- Make Predictions \n- View list of app events')
    if st.session_state.logged_in:
        st.write(f'Logged in as: {st.session_state.email}')
        balance_response = get_user_balance()
        if balance_response and 'balance' in balance_response:
            st.write(f'Current Balance: ${round(balance_response["balance"], 2)}')

        # Показать краткую статистику парсера для админов
        if st.session_state.is_admin:
            st.divider()
            st.subheader("📊 Parser Quick Stats")

            health = check_parser_health()
            if health and health['status'] == 'healthy':
                stats = get_parser_stats()
                if stats:
                    col1, col2, col3 = st.columns(3)
                    with col1:
                        st.metric("Total Reviews", stats.get('total_reviews', 0))
                    with col2:
                        if stats.get('status_distribution'):
                            total = sum(stats['status_distribution'].values())
                            st.metric("Processed Reviews", total)
                    with col3:
                        jobs = get_parser_jobs(limit=5)
                        if jobs:
                            running_jobs = sum(1 for job in jobs if job.get('status') == 'running')
                            st.metric("Running Jobs", running_jobs)

                    # Быстрая ссылка на парсер
                    if st.button("Go to Parser Dashboard"):
                        st.session_state.current_page = "Parser Dashboard"
                        st.rerun()
            else:
                st.info("Parser API is not available")


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