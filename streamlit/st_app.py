import streamlit as st
import requests
import pandas as pd
import time

API_URL='http://app:8080'

# Вспомогательная функция для API запросов
def make_api_request(endpoint, method='GET', data=None, params=None):
    try:
        if method == 'GET':
            response = requests.get(f'{API_URL}{endpoint}', params=params)
        elif method == 'POST':
            response = requests.post(f'{API_URL}{endpoint}', json=data)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        st.error(f'Error: {str(e)}')
        return None


# сессия для авторизации
if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False
    st.session_state.email = None
    st.session_state.is_admin = False

# Главное меню
def main():
    st.title('ML service study project')
    if not st.session_state.logged_in:
        menu = ['Login', 'Register']
    else:
        menu = ['Home', 'Add Balance', 'Iris prediction', 'List of events', 'Logout']
    choice = st.sidebar.selectbox('Menu', menu)

    if choice == 'Login':
        login()
    elif choice == 'Register':
        register()
    elif choice == 'Home':
        home()
    elif choice == 'List of events':
        list_of_events()
    elif choice == 'Logout':
        logout()


# Страница входа в приложение
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


# Страница регистрации
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


# Домашняя страница пользователя
def home():
    st.header('Welcome! Please, use Menu to: \n- Add Balance \n- Make Predictions \n- View list of app events')
    st.write(f'Logged in as: {st.session_state.email}')
    balance = make_api_request('/api/balance/balance', method='GET', params={'email': st.session_state.email})
    if balance:
        st.write(f'Current Balance: ${round(balance["balance"], 2)}')


# Страница пополнения баланса
def add_balance():
    st.header('Add Balance')
    amount = st.number_input('Amount', min_value=1.00, step=0.5, value=10.0)
    target_email = None
    if st.session_state.is_admin:
        target_email = st.text_input('Target Email (optional, for admins only)')
    if st.button('Add Balance'):
        data = {'email': st.session_state.email, 'amount': amount}
        if target_email:
            data['target_email'] = target_email
        response = make_api_request('/api/balance/balance', method='POST', data=data)
        if response:
            result_message = f'{response["message"]} New Balance: ${round(response["new_balance"], 2)}.'
            st.success(result_message)
            time.sleep(2)
            st.rerun()


# Страница взаимодействия с ml моделью
def prediction():
    st.header('Iris Prediction')
    sepal_length = st.number_input('sepal_length', min_value=4.3, max_value=7.9, step=0.1)
    sepal_width = st.number_input('sepal_width', min_value=2.0, max_value=4.4, step=0.1)
    petal_length = st.number_input('petal_length', min_value=1.0, max_value=6.9, step=0.1)
    petal_width = st.number_input('petal_width', min_value=0.1, max_value=2.5, step=0.1)

    if st.button('Predict'):
        features_data = {
            'sepal_length': float(sepal_length),
            'sepal_width': float(sepal_width),
            'petal_length': float(petal_length),
            'petal_width': float(petal_width),
        }
        request_data = {
            'email': st.session_state.email,
            'data': features_data,
            'model_name': 'iris'
        }
        response = make_api_request('/api/ml/prediction', method='POST', data=request_data)

        if response:
            st.success(response['message'])

            prediction_data = None

            if 'predicted_class' in response:
                prediction_data = response
            elif 'result' in response and isinstance(response['result'], dict) and 'predicted_class' in response[
                'result']:
                prediction_data = response['result']
            else:
                response_result = make_api_request('/api/ml/result', method='GET',
                                                   params={'task_id': response["task_id"]})
                if response_result and 'predicted_class' in response_result:
                    prediction_data = response_result
                elif response_result and 'result' in response_result and 'predicted_class' in response_result['result']:
                    prediction_data = response_result['result']

            if prediction_data:
                st.header('Prediction Results')

                col1, col2 = st.columns(2)
                with col1:
                    st.metric("Predicted Class", prediction_data['predicted_class'])
                with col2:
                    st.metric("Confidence", f"{prediction_data['predicted_class_prob']:.2%}")

                if 'probabilities' in prediction_data:
                    st.subheader('Class Probabilities')
                    for class_name, probability in prediction_data['probabilities'].items():
                        st.write(f"**{class_name.capitalize()}**: {probability:.2%}")
                        st.progress(float(probability))

                with st.expander("Transaction Details"):
                    st.write(f"Task ID: {response.get('task_id', 'N/A')}")
                    st.write(f"User ID: {response.get('user_id', 'N/A')}")
                    st.write(f"Email: {response.get('email', 'N/A')}")
                    st.write(f"New Balance: ${response.get('new_balance', 'N/A')}")

            else:
                st.error('Could not extract prediction data from response')
                st.write("Response keys:", response.keys())
                if 'task_id' in response:
                    st.write(f"Task ID: {response['task_id']} - try checking results later")

        else:
            st.error('Prediction request failed')


# streamlit pyarrow conversion issue
def normalize_data(data):
    if data is None:
        return 'N/A'
    elif isinstance(data, list):
        return ", ".join(str(element) for element in data)
    else:
        return str(data)


# Страница событий пользователя
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

    params = {'email': st.session_state.email}

    if st.session_state.is_admin:
        if view_mode == "All users":
            params['all_users'] = 'true'
        elif view_mode == "Specific user" and target_email:
            params['target_email'] = target_email

    events = make_api_request('/api/events/events', method='GET', params=params)

    if st.session_state.is_admin:
        if view_mode == "All users":
            st.info("📋 Viewing events for ALL users")
        elif view_mode == "Specific user" and target_email:
            st.info(f"👤 Viewing events for user: {target_email}")
        else:
            st.info("👤 Viewing your events")

    if events and 'events' in events and events['events']:
        df = pd.DataFrame(events['events'])

        if st.session_state.is_admin and 'view_mode' in events:
            if events['view_mode'] == 'all_users':
                st.success(f"Found {len(df)} events from all users")
            elif events['view_mode'] == 'specific_user':
                st.success(f"Found {len(df)} events for user: {events.get('target_email', 'N/A')}")
        else:
            st.write(f"Total events found: {len(df)}")

        if 'ml_input' in df.columns:
            df['ml_input'] = df['ml_input'].apply(normalize_data)

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
        # Отладочная информация для админов
        if st.session_state.is_admin and events:
            st.write("Response structure:", events.keys())


# Logout пользователя
def logout():
    st.session_state.logged_in = False
    st.session_state.email = None
    st.session_state.is_admin = False
    st.success('Logged out successfully!')
    time.sleep(1)
    st.rerun()


if __name__ == '__main__':
    main()
