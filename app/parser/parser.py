import requests
import json
import time
import pandas as pd
from bs4 import BeautifulSoup
from datetime import datetime
import random
import os

from sqlmodel import Session, select
from database.database import get_database_engine
from models.raw_parser_reviews import MortgageReview
from services.crud import parser_crud as ReviewService
from services.crud import parser_job_crud as JobService
import json
from datetime import datetime
import random
import time


def create_session():
    """Создает сессию с правильными заголовками"""
    session = requests.Session()

    session.headers.update({
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
        'Accept-Language': 'ru-RU,ru;q=0.9,en-US;q=0.8,en;q=0.7',
        'Accept-Encoding': 'gzip, deflate, br',
        'Cache-Control': 'no-cache',
        'Connection': 'keep-alive',
        'Upgrade-Insecure-Requests': '1',
        'Sec-Fetch-Dest': 'document',
        'Sec-Fetch-Mode': 'navigate',
        'Sec-Fetch-Site': 'none',
        'Sec-Fetch-User': '?1',
    })

    return session


def load_progress(filename):
    """Загружает прогресс парсинга из файла"""
    progress_file = f"{filename}_progress.json"
    if os.path.exists(progress_file):
        try:
            with open(progress_file, 'r', encoding='utf-8') as f:
                progress = json.load(f)
            print(f"📁 Загружен прогресс: страница {progress['current_page']}, отзыв {progress['current_review']}")
            return progress
        except:
            print("❌ Ошибка загрузки прогресс, начинаем заново")
    return None


def save_progress(filename, current_page, current_review, total_pages, processed_ids):
    """Сохраняет прогресс парсинга в файл"""
    progress_file = f"{filename}_progress.json"
    progress = {
        'current_page': current_page,
        'current_review': current_review,
        'total_pages': total_pages,
        'processed_ids': list(processed_ids),
        'timestamp': datetime.now().isoformat()
    }
    try:
        with open(progress_file, 'w', encoding='utf-8') as f:
            json.dump(progress, f, ensure_ascii=False, indent=2)
        print(f"💾 Прогресс сохранен: страница {current_page}, отзыв {current_review}")
    except Exception as e:
        print(f"❌ Ошибка сохранения прогресса: {e}")


def load_existing_data(filename):
    """Загружает существующие данные из Excel файла"""
    if os.path.exists(filename):
        try:
            df = pd.read_excel(filename)
            existing_ids = set(df['ID'].dropna().astype(int).tolist())
            print(f"📁 Загружено {len(existing_ids)} существующих записей из {filename}")
            return existing_ids
        except Exception as e:
            print(f"❌ Ошибка загрузки существующих данных: {e}")
    return set()


def load_all_existing_ids(filename, save_to_db, resume=True):
    """Загружает все существующие ID из всех источников"""
    all_ids = set()

    # 1. Из прогресс-файла
    if resume and filename:
        progress_file = f"{filename}_progress.json"
        if os.path.exists(progress_file):
            try:
                with open(progress_file, 'r', encoding='utf-8') as f:
                    progress = json.load(f)
                all_ids.update(set(progress.get('processed_ids', [])))
                print(f"📁 Загружено {len(progress.get('processed_ids', []))} ID из прогресс-файла")
            except:
                pass

    # 2. Из Excel
    if filename and os.path.exists(filename):
        try:
            df = pd.read_excel(filename)
            excel_ids = set(df['ID'].dropna().astype(int).tolist())
            all_ids.update(excel_ids)
            print(f"📊 Загружено {len(excel_ids)} ID из Excel")
        except Exception as e:
            print(f"⚠️  Ошибка загрузки Excel: {e}")

    # 3. Из БД
    if save_to_db:
        try:
            engine = get_database_engine()
            with Session(engine) as session:
                statement = select(MortgageReview.id)
                db_ids = session.exec(statement).all()
                all_ids.update(db_ids)
                print(f"💾 Загружено {len(db_ids)} ID из базы данных")
        except Exception as e:
            print(f"⚠️  Ошибка загрузки БД: {e}")

    print(f"🎯 Всего уникальных ID для проверки дубликатов: {len(all_ids)}")
    return all_ids


def check_review_in_database(review_id, session):
    """Проверяет, существует ли отзыв в БД (реальная проверка)"""
    try:
        statement = select(MortgageReview).where(MortgageReview.id == review_id)
        result = session.exec(statement).first()
        return result is not None
    except Exception as e:
        print(f"❌ Ошибка проверки в БД: {e}")
        return False


def append_to_excel(reviews_data, filename, page_number):
    """Добавляет данные в существующий Excel файл или создает новый с проверкой дубликатов"""
    try:
        # Загружаем существующие данные
        if os.path.exists(filename):
            existing_df = pd.read_excel(filename)
            existing_ids = set(existing_df['ID'].dropna().astype(int).tolist())

            # Фильтруем новые данные
            new_reviews = [r for r in reviews_data if r.get('id') not in existing_ids]

            if not new_reviews:
                print("ℹ️  Нет новых данных для добавления")
                return filename

            # Создаем DataFrame из новых данных
            new_df = create_dataframe(new_reviews, page_number)

            # Объединяем с существующими данными
            combined_df = pd.concat([existing_df, new_df], ignore_index=True)

            # Сохраняем объединенный файл
            save_dataframe_to_excel(combined_df, filename)
            print(f"✅ Добавлено {len(new_reviews)} новых записей в {filename}")

        else:
            # Создаем новый файл
            df = create_dataframe(reviews_data, page_number)
            save_dataframe_to_excel(df, filename)
            print(f"✅ Создан новый файл с {len(reviews_data)} записями: {filename}")

        return filename

    except Exception as e:
        print(f"❌ Ошибка при добавлении в Excel: {e}")
        # Создаем резервную копию
        backup_name = f"backup_append_error_{datetime.now().strftime('%H%M%S')}.xlsx"
        try:
            df = create_dataframe(reviews_data, page_number)
            save_dataframe_to_excel(df, backup_name)
            print(f"💾 Создана резервная копия: {backup_name}")
        except:
            print("❌ Не удалось создать резервную копию")
        return None


def create_dataframe(reviews_data, page_number):
    """Создает DataFrame из данных отзывов с новыми столбцами"""
    df_data = []
    current_date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    for review in reviews_data:
        # Форматируем комментарии для Excel
        comments_formatted = ""
        if 'comments_detailed' in review:
            comments_formatted = format_comments_for_excel(review['comments_detailed'])

        # Извлекаем оценки по критериям
        criteria_scores = review.get('criteria_scores', {})

        # Форматируем поле "Учитывается в рейтинге"
        is_countable = review.get('is_countable', '')
        is_countable_display = 'Да' if is_countable else 'Нет' if is_countable is not None else ''

        # Определяем статус отзыва
        status = determine_review_status(review)

        row = {
            # Данные из первой части (API)
            'ID': review.get('id', ''),
            'Заголовок': review.get('title', ''),
            'Пользователь (API)': review.get('user_name', ''),
            'Оценка': review.get('grade', ''),
            'Дата создания (API)': review.get('date_create', ''),
            'Количество комментариев': review.get('comment_count', ''),
            'Учитывается в рейтинге': is_countable_display,
            'Статус отзыва': status,
            'Текст отзыва (API)': review.get('text', ''),
            'Название банка': review.get('bank_name', ''),
            'ID банка': review.get('bank_id', ''),
            'Регион банка': review.get('bank_region', ''),
            'Ответ банка (API)': review.get('bank_answer_text', ''),
            'ID сотрудника': review.get('agent_id', ''),

            # Данные со второй страницы
            'Пользователь (страница)': review.get('user_name_detailed', ''),
            'Город пользователя': review.get('user_city', ''),
            'Полный текст отзыва': review.get('full_text', ''),
            'Комментарии': comments_formatted,
            'Дата отзыва (страница)': review.get('date_detailed', ''),
            'Рейтинг (страница)': review.get('rating_detailed', ''),
            'Ответ банка (детально)': review.get('bank_answer_detailed', ''),

            # Оценки по критериям
            'Прозрачные условия': criteria_scores.get('Прозрачные условия', ''),
            'Вежливые сотрудники': criteria_scores.get('Вежливые сотрудники', ''),
            'Доступность и поддержка': criteria_scores.get('Доступность и поддержка', ''),
            'Удобство приложения, сайта': criteria_scores.get('Удобство приложения, сайта', ''),

            # Ссылки
            'Ссылка на список': review.get('link_part1', ''),
            'Ссылка на страницу': review.get('link_part2', ''),

            # НОВЫЕ СТОЛБЦЫ
            'Дата выгрузки': current_date,
            'Страница выгрузки': page_number,

            'Ошибка': review.get('error', ''),
        }
        df_data.append(row)

    return pd.DataFrame(df_data)


def determine_review_status(review):
    """Определяет статус отзыва на основе данных - ОБНОВЛЕННАЯ ЛОГИКА"""
    # Если есть ошибка при парсинге
    if review.get('error'):
        return 'Ошибка парсинга'

    # Если отзыв не учитывается в рейтинге
    if review.get('is_countable') is False:
        return 'Не зачтено'

    # Если отзыв учитывается в рейтинге
    if review.get('is_countable') is True:
        return 'Зачтено'

    # Если статус "Проверяется" или другие возможные статусы
    if review.get('is_countable') is None:
        return 'Проверяется'

    # Дополнительная проверка по наличию ответа банка
    if review.get('bank_answer_text') or review.get('bank_answer_detailed'):
        return 'Зачтено'

    # Статус по умолчанию
    return 'Проверяется'


def save_dataframe_to_excel(df, filename):
    """Сохраняет DataFrame в Excel файл с форматированием"""
    try:
        with pd.ExcelWriter(filename, engine='xlsxwriter') as writer:
            df.to_excel(writer, sheet_name='Отзывы по ипотеке', index=False)

            workbook = writer.book
            worksheet = writer.sheets['Отзывы по ипотеке']

            # Настраиваем ширину колонок
            column_widths = {
                'A': 10,  # ID
                'B': 40,  # Заголовок
                'C': 25,  # Пользователь (API)
                'D': 8,  # Оценка
                'E': 20,  # Дата создания (API)
                'F': 10,  # Количество комментариев
                'G': 8,  # Учитывается в рейтинге
                'H': 12,  # Статус отзыва
                'I': 50,  # Текст отзыва (API)
                'J': 25,  # Название банка
                'K': 10,  # ID банка
                'L': 15,  # Регион банка
                'M': 50,  # Ответ банка (API)
                'N': 12,  # ID сотрудника
                'O': 25,  # Пользователь (страница)
                'P': 20,  # Город пользователя
                'Q': 80,  # Полный текст отзыва
                'R': 80,  # Комментарии
                'S': 20,  # Дата отзыва (страница)
                'T': 15,  # Рейтинг (страница)
                'U': 50,  # Ответ банка (детально)
                'V': 15,  # Прозрачные условия
                'W': 15,  # Вежливые сотрудники
                'X': 15,  # Доступность и поддержка
                'Y': 15,  # Удобство приложения, сайта
                'Z': 60,  # Ссылка на список
                'AA': 60,  # Ссылка на страницу
                'AB': 20,  # Дата выгрузки (НОВЫЙ)
                'AC': 15,  # Страница выгрузки (НОВЫЙ)
                'AD': 30,  # Ошибка
            }

            for col, width in column_widths.items():
                worksheet.set_column(f'{col}:{col}', width)

            # Добавляем автофильтр
            worksheet.autofilter(0, 0, len(df), len(df.columns) - 1)

            # Форматирование заголовков
            header_format = workbook.add_format({
                'bold': True,
                'text_wrap': True,
                'valign': 'top',
                'fg_color': '#D7E4BC',
                'border': 1
            })

            for col_num, value in enumerate(df.columns.values):
                worksheet.write(0, col_num, value, header_format)

        return True

    except Exception as e:
        print(f"❌ Ошибка при сохранении Excel: {e}")
        return False


def parse_single_review(review_id, max_retries=3):
    """Парсит страницу отдельного отзыва и извлекает нужные данные"""

    url = f"https://www.banki.ru/services/responses/bank/response/{review_id}/"

    print(f"    🌐 Переходим на: {url}")

    session = create_session()

    for attempt in range(max_retries):
        try:
            print(f"    📥 Попытка {attempt + 1}/{max_retries}...")

            headers = {
                'Referer': 'https://www.banki.ru/services/responses/list/product/hypothec/',
            }

            response = session.get(url, headers=headers, timeout=15)

            print(f"    📊 Статус: {response.status_code}")

            if response.status_code != 200:
                print(f"    ❌ HTTP ошибка: {response.status_code}")
                if attempt < max_retries - 1:
                    time.sleep(5 * (attempt + 1))
                    continue
                return {'link_part2': url, 'error': f'HTTP {response.status_code}'}

            soup = BeautifulSoup(response.text, 'html.parser')

            # Проверяем заголовок страницы
            page_title = soup.title.string if soup.title else 'No title'
            print(f"    📄 Заголовок: {page_title}")

            if '404' in page_title or 'не найдена' in page_title.lower():
                print(f"    ❌ Страница не найдена")
                return {'link_part2': url, 'error': 'Page not found'}

            review_details = {
                'link_part2': url,
            }

            # 1. ИМЯ ПОЛЬЗОВАТЕЛЯ со страницы
            user_name_selectors = [
                '[data-gtm-click*="click_author_user_rating_banks_response_page"] .l17191939 span',
                '.l17191939 span',
                '.text-header-3',
                'h1'
            ]

            user_name = None
            for selector in user_name_selectors:
                element = soup.select_one(selector)
                if element and element.get_text().strip():
                    user_name = element.get_text().strip()
                    print(f"    ✅ Имя пользователя: {user_name}")
                    review_details['user_name_detailed'] = user_name
                    break

            # 2. ГОРОД ПОЛЬЗОВАТЕЛЯ
            city_selectors = [
                '.l3a372298',
                '[class*="region"]',
                '[class*="city"]',
                '.text-size-6'
            ]

            for selector in city_selectors:
                element = soup.select_one(selector)
                if element and element.get_text().strip():
                    city = element.get_text().strip()
                    if (city and len(city) > 1 and
                            not any(word in city.lower() for word in ['отзыв', 'оценка', '202']) and
                            not city.replace('.', '').isdigit()):
                        review_details['user_city'] = city
                        print(f"    ✅ Город пользователя: {city}")
                        break

            # 3. ПОЛНЫЙ ТЕКСТ ОТЗЫВА
            text_selectors = [
                '.lb1789875',
                '.markdown-inside',
                '[data-module-options*="text"]',
                '.response-text',
                '.article-text'
            ]

            for selector in text_selectors:
                elements = soup.select(selector)
                for element in elements:
                    full_text = clean_html_text(element.get_text())
                    if (len(full_text) > 50 and
                            any(word in full_text.lower() for word in
                                ['хочу', 'выразить', 'благодарность', 'спасибо', 'ипотек'])):
                        review_details['full_text'] = full_text
                        print(f"    ✅ Полный текст: {len(full_text)} символов")
                        break
                if 'full_text' in review_details:
                    break

            # 4. ДАТА ОТЗЫВА на странице
            date_selectors = [
                '.l10fac986',
                '.l46c44745',
                '.text-size-6',
                '[class*="date"]',
                '[class*="time"]'
            ]

            for selector in date_selectors:
                elements = soup.select(selector)
                for element in elements:
                    date_text = element.get_text().strip()
                    if (date_text and
                            any(char.isdigit() for char in date_text) and
                            ('.' in date_text or ':' in date_text)):
                        review_details['date_detailed'] = date_text
                        print(f"    ✅ Дата отзыва: {date_text}")
                        break
                if 'date_detailed' in review_details:
                    break

            # 5. РЕЙТИНГ на странице
            rating_selectors = [
                '.rating-grade',
                '[class*="rating"]',
                '.text-size-4'
            ]

            for selector in rating_selectors:
                elements = soup.select(selector)
                for element in elements:
                    rating_text = element.get_text().strip()
                    if rating_text and rating_text.isdigit() and 1 <= int(rating_text) <= 5:
                        review_details['rating_detailed'] = rating_text
                        print(f"    ✅ Рейтинг: {rating_text}")
                        break
                if 'rating_detailed' in review_details:
                    break

            # 6. ОЦЕНКИ ПО КРИТЕРИЯМ
            print(f"    📈 Парсим оценки по критериям...")

            criteria_block = soup.select_one('.ld97a7dcf')
            if criteria_block:
                criteria_data = {}

                criteria_rows = criteria_block.select('.ldab753e4')

                current_criterion = None
                for i, row in enumerate(criteria_rows):
                    text_element = row.select_one('.text-size-6')
                    if text_element:
                        criterion_name = text_element.get_text().strip()
                        current_criterion = criterion_name
                        print(f"      📊 Критерий: {criterion_name}")
                    else:
                        if current_criterion:
                            filled_bars = row.select('.l61f54b7b')
                            empty_bars = row.select('.le102b2d3')

                            total_bars = len(filled_bars) + len(empty_bars)
                            if total_bars > 0:
                                score = len(filled_bars)
                                criteria_data[current_criterion] = score
                                print(f"      ✅ Оценка '{current_criterion}': {score}/{total_bars}")

                            current_criterion = None

                if criteria_data:
                    review_details['criteria_scores'] = criteria_data
                    print(f"    ✅ Собрано оценок по критериям: {len(criteria_data)}")

            # 7. ID СОТРУДНИКА (из ответа банка)
            print(f"    👨‍💼 Ищем ID сотрудника...")

            # Ищем ответ банка на странице
            bank_answer_selectors = [
                '.lcc571035',
                '[class*="answer"]',
                '[class*="bank"]',
                '.response-answer'
            ]

            for selector in bank_answer_selectors:
                bank_answer_section = soup.select_one(selector)
                if bank_answer_section:
                    answer_text = bank_answer_section.get_text()
                    if any(word in answer_text.lower() for word in
                           ['сотрудник', 'менеджер', 'специалист', 'анна', 'мария']):
                        review_details['bank_answer_detailed'] = clean_html_text(answer_text)
                        print(f"    ✅ Найден ответ банка с упоминанием сотрудника")
                        break

            # 8. КОММЕНТАРИИ на странице
            comments_data = []
            comments_selectors = [
                '#comments',
                '[data-module-options*="comments"]',
                '.lcc571035',
                '.response-comments'
            ]

            for selector in comments_selectors:
                comments_section = soup.select_one(selector)
                if comments_section:
                    comment_item_selectors = [
                        '.lcc571035',
                        '.lc91c72cc',
                        '.comment-item'
                    ]

                    for item_selector in comment_item_selectors:
                        comment_elems = comments_section.select(item_selector)
                        for comment_elem in comment_elems:
                            comment_info = {}

                            # Автор комментария
                            author_selectors = [
                                '.l5b3cd260',
                                '.text-header-5',
                                '[class*="author"]'
                            ]

                            for author_selector in author_selectors:
                                author_elem = comment_elem.select_one(author_selector)
                                if author_elem:
                                    comment_info['author'] = author_elem.get_text().strip()
                                    break

                            # Дата комментария
                            date_selectors = [
                                '.l46c44745',
                                '.text-size-6',
                                '[class*="date"]'
                            ]

                            for date_selector in date_selectors:
                                date_elem = comment_elem.select_one(date_selector)
                                if date_elem:
                                    comment_info['date'] = date_elem.get_text().strip()
                                    break

                            # Текст комментария
                            text_selectors = [
                                '.lb1789875',
                                '.text-size-4',
                                '[class*="text"]'
                            ]

                            for text_selector in text_selectors:
                                text_elem = comment_elem.select_one(text_selector)
                                if text_elem:
                                    comment_text = clean_html_text(text_elem.get_text())
                                    if len(comment_text) > 10:
                                        comment_info['text'] = comment_text
                                        break

                            if comment_info.get('text'):
                                comments_data.append(comment_info)

                    if comments_data:
                        print(f"    ✅ Найдено комментариев: {len(comments_data)}")
                        review_details['comments_detailed'] = comments_data
                    break

            print(f"    📊 Собрано данных: {len(review_details) - 1} полей")

            return review_details

        except requests.exceptions.Timeout:
            print(f"    ⏰ Таймаут")
            if attempt < max_retries - 1:
                time.sleep(5 * (attempt + 1))
                continue
        except Exception as e:
            print(f"    ❌ Ошибка: {str(e)}")
            if attempt < max_retries - 1:
                time.sleep(3 * (attempt + 1))
                continue

    return {'link_part2': url, 'error': 'All retries failed'}


def get_mortgage_reviews(page=1, review_type='all', max_retries=3):
    """Получает список отзывов с использованием сессии"""
    url = "https://www.banki.ru/services/responses/list/ajax/"

    params = {
        'product': 'hypothec',
        'page': page,
        'type': 'all',
    }

    session = create_session()

    headers = {
        'Accept': 'application/json, text/javascript, */*; q=0.01',
        'X-Requested-With': 'XMLHttpRequest',
        'Referer': f'https://www.banki.ru/services/responses/list/product/hypothec/?page={page}&type={review_type}',
    }

    for attempt in range(max_retries):
        try:
            response = session.get(url, params=params, headers=headers, timeout=15)

            if response.status_code == 200:
                return response.json()
            else:
                print(f"❌ Ошибка {response.status_code} для страницы {page}")
                if attempt < max_retries - 1:
                    time.sleep(5 * (attempt + 1))
                    continue

        except Exception as e:
            print(f"⚠️ Ошибка: {e}")
            if attempt < max_retries - 1:
                time.sleep(3 * (attempt + 1))
                continue

    return None


def clean_html_text(text):
    """Очищает текст от HTML тегов"""
    if text and '<' in text and '>' in text:
        soup = BeautifulSoup(text, 'html.parser')
        return soup.get_text().strip()
    return text


def parse_review_details(review):
    """Извлекает все доступные данные из отзыва (первая часть)"""

    review_data = {
        'id': review.get('id'),
        'title': review.get('title'),
        'user_name': review.get('userName'),
        'text': clean_html_text(review.get('text')),
        'grade': review.get('grade'),
        'comment_count': review.get('commentCount'),
        'is_countable': review.get('isCountable'),  # Учитывается в рейтинге
        'date_create': review.get('dateCreate'),
        'has_documents': review.get('hasDocuments'),
        'link_part1': f"https://www.banki.ru/services/responses/list/product/hypothec/?response_id={review.get('id')}"
    }

    company = review.get('company', {})
    if company:
        review_data['bank_name'] = company.get('name')
        review_data['bank_id'] = company.get('id')  # ID банка
        review_data['bank_region'] = company.get('region')  # Регион банка
        review_data['bank_address'] = company.get('address')
        review_data['bank_code'] = company.get('code')

    agent_answer = review.get('agentAnswerText')
    if agent_answer:
        review_data['bank_answer_text'] = clean_html_text(agent_answer)
        review_data['agent_id'] = review.get('agentId')  # ID сотрудника

    return review_data


def format_comments_for_excel(comments_data):
    """Форматирует комментарии для Excel"""
    if not comments_data:
        return ""

    formatted_comments = []
    for i, comment in enumerate(comments_data, 1):
        author = comment.get('author', 'Неизвестно')
        date = comment.get('date', '')
        text = comment.get('text', '')

        comment_str = f"{i}. {author}"
        if date:
            comment_str += f" ({date})"
        if text:
            comment_str += f": {text}"

        formatted_comments.append(comment_str)

    return " | ".join(formatted_comments)


def save_review_to_database(review_data, page_number, session=None):
    """Сохраняет отзыв в базу данных"""
    try:
        if not session:
            engine = get_database_engine()
            session = Session(engine)

        # Определяем статус отзыва
        status = determine_review_status(review_data)

        # Парсим даты
        created_at_api = parse_date(review_data.get('date_create'))
        created_at_page = parse_date(review_data.get('date_detailed'))

        # Подготавливаем данные для модели
        model_data = {
            'id': review_data.get('id'),
            'title': review_data.get('title'),
            'user_name_api': review_data.get('user_name'),
            'user_name_page': review_data.get('user_name_detailed'),
            'user_city': review_data.get('user_city'),
            'grade_api': review_data.get('grade'),
            'grade_page': review_data.get('rating_detailed'),
            'text_api': review_data.get('text'),
            'full_text': review_data.get('full_text'),
            'created_at_api': created_at_api,
            'created_at_page': created_at_page,
            'comment_count': review_data.get('comment_count'),
            'is_countable': review_data.get('is_countable'),
            'status': status,
            'bank_id': review_data.get('bank_id'),
            'bank_name': review_data.get('bank_name'),
            'bank_region': review_data.get('bank_region'),
            'bank_answer_api': review_data.get('bank_answer_text'),
            'bank_answer_detailed': review_data.get('bank_answer_detailed'),
            'agent_id': review_data.get('agent_id'),
            'criteria_scores': json.dumps(review_data.get('criteria_scores', {})) if review_data.get(
                'criteria_scores') else None,
            'comments': json.dumps(review_data.get('comments_detailed', [])) if review_data.get(
                'comments_detailed') else None,
            'link_list': review_data.get('link_part1'),
            'link_page': review_data.get('link_part2'),
            'page_number': page_number,
            'error': review_data.get('error'),
        }

        # Создаем модель
        review_model = MortgageReview(**model_data)

        # Сохраняем в БД
        ReviewService.upsert_review(review_model, session)
        session.commit()

        return True

    except Exception as e:
        print(f"❌ Ошибка сохранения в БД: {e}")
        import traceback
        traceback.print_exc()
        session.rollback()
        return False


def parse_date(date_str):
    """Парсит дату из строки"""
    if not date_str:
        return None

    try:
        # Убираем лишние символы
        date_str = date_str.replace('T', ' ').replace('Z', '')

        # Пробуем разные форматы
        formats = [
            '%Y-%m-%d %H:%M:%S.%f',
            '%Y-%m-%d %H:%M:%S',
            '%d.%m.%Y %H:%M',
            '%d.%m.%Y %H:%M:%S',
            '%d.%m.%Y'
        ]

        for fmt in formats:
            try:
                return datetime.strptime(date_str, fmt)
            except ValueError:
                continue

        return None
    except Exception:
        return None


def full_parse_cycle(
        start_page=1,
        end_page=None,
        filename=None,
        delay=2,
        max_retries=3,
        resume=True,
        save_to_db=True,
        job_id=None
):
    """Полный цикл парсинга с поддержкой возобновления и сохранением в БД"""

    if not filename:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"mortgage_reviews_{timestamp}.xlsx"

    print("🚀 Запуск парсинга отзывов по ипотеке...")
    print(f"💾 Сохранение в БД: {'ВКЛЮЧЕНО' if save_to_db else 'ВЫКЛЮЧЕНО'}")
    print(f"💾 Сохранение в Excel: {filename}")
    print(f"🎯 Цель: страницы {start_page}-{end_page or 'до конца'}")

    # Создаем сессию для БД если нужно сохранять туда
    db_session = None
    if save_to_db:
        engine = get_database_engine()
        db_session = Session(engine)

        # Создаем задачу парсинга
        if job_id is None:
            job = JobService.create_job(db_session)
            job_id = job.id
            print(f"📋 Создана задача парсинга ID: {job_id}")

    # ⭐⭐⭐ ЗАГРУЖАЕМ ВСЕ СУЩЕСТВУЮЩИЕ ID ИЗ ВСЕХ ИСТОЧНИКОВ ⭐⭐⭐
    processed_ids = load_all_existing_ids(filename, save_to_db, resume)

    current_page = start_page
    current_review = 0

    # Если возобновляем, загружаем позицию с последней страницы
    if resume:
        progress = load_progress(filename)
        if progress:
            current_page = progress['current_page']
            current_review = progress['current_review']
            if end_page is None and progress.get('total_pages'):
                end_page = progress['total_pages']

    all_reviews = []
    page = current_page
    review_counter = 0
    duplicates_skipped = 0

    try:
        while True:
            # Проверяем условие окончания
            if end_page and page > end_page:
                print(f"✅ Достигнута конечная страница {end_page}")
                break

            print(f"\n{'=' * 60}")
            print(f"📄 Страница {page}/{end_page or '?'}")
            print(f"📊 Пропущено дубликатов на данный момент: {duplicates_skipped}")
            print(f"{'=' * 60}")

            # Обновляем статус задачи
            if save_to_db and job_id:
                JobService.update_job(
                    job_id,
                    db_session,
                    current_page=page,
                    total_pages=end_page,
                    message=f"Парсинг страницы {page}, пропущено дубликатов: {duplicates_skipped}"
                )
                db_session.commit()

            # Задержка между страницами
            page_delay = random.uniform(1, 3)
            print(f"⏳ Задержка между страницами: {page_delay:.1f} секунд")
            time.sleep(page_delay)

            data = get_mortgage_reviews(page=page, max_retries=max_retries)

            if not data or 'data' not in data:
                print(f"❌ Не удалось получить данные со страницы {page}")
                if end_page is None:
                    print("✅ Достигнут конец списка отзывов")
                    break
                else:
                    page += 1
                    continue

            reviews = data['data']
            print(f"📝 Найдено отзывов на странице: {len(reviews)}")

            # Если это первая страница и мы не знаем общее количество страниц
            if end_page is None and page == start_page:
                total_pages = data.get('pagination', {}).get('pageCount', 0)
                if total_pages > 0:
                    end_page = total_pages
                    print(f"📚 Всего страниц: {total_pages}")

            for i, review in enumerate(reviews, 1):
                review_id = review.get('id')

                # ⭐⭐⭐ ПЕРВАЯ ПРОВЕРКА: В ПАМЯТИ (быстрая) ⭐⭐⭐
                if review_id in processed_ids:
                    duplicates_skipped += 1
                    print(f"  ⏭️  Пропускаем ДУБЛИКАТ в памяти {i}/{len(reviews)} (ID: {review_id})")
                    continue

                # ⭐⭐⭐ ВТОРАЯ ПРОВЕРКА: В БД (двойная проверка) ⭐⭐⭐
                if save_to_db and db_session:
                    if check_review_in_database(review_id, db_session):
                        duplicates_skipped += 1
                        processed_ids.add(review_id)  # Добавляем в кэш для будущих проверок
                        print(f"  ⏭️  Пропускаем ДУБЛИКАТ в БД {i}/{len(reviews)} (ID: {review_id})")
                        continue

                # Если возобновляем с середины страницы
                if page == current_page and i <= current_review:
                    print(f"  ⏭️  Пропускаем отзыв {i}/{len(reviews)} (ID: {review_id}) - уже обработан по прогрессу")
                    continue

                print(f"\n  🔍 Отзыв {i}/{len(reviews)} (ID: {review_id})")

                # Первая часть
                review_data = parse_review_details(review)

                # Вторая часть
                print(f"     🌐 Парсим страницу отзыва...")
                detailed_data = parse_single_review(review_data['id'], max_retries=2)

                review_data.update(detailed_data)

                # СОХРАНЕНИЕ В БД
                if save_to_db:
                    try:
                        save_review_to_database(review_data, page, db_session)
                        print(f"     💾 Сохранено в БД: ID {review_id}")
                    except Exception as e:
                        print(f"     ❌ Ошибка сохранения в БД: {e}")

                # Сохранение для Excel
                all_reviews.append(review_data)
                processed_ids.add(review_id)  # Добавляем ID в обработанные
                review_counter += 1

                # Обновляем счетчик в задаче
                if save_to_db and job_id:
                    JobService.update_job(
                        job_id,
                        db_session,
                        processed_reviews=len(processed_ids) - duplicates_skipped
                    )
                    db_session.commit()

                print(f"     ✅ Готово")

                # Сохраняем прогресс
                save_progress(filename, page, i, end_page, processed_ids)

                # АВТОСОХРАНЕНИЕ КАЖДЫЕ 25 ОТЗЫВОВ
                if review_counter >= 25:
                    print(f"💾 Автосохранение {len(all_reviews)} отзывов в Excel...")
                    append_to_excel(all_reviews, filename, page)
                    all_reviews = []
                    review_counter = 0

                # ЗАДЕРЖКА МЕЖДУ ОТЗЫВАМИ
                if i < len(reviews) or page < (end_page or page):
                    current_delay = delay + random.uniform(0.5, 1.5)
                    print(f"⏳ Задержка до следующего отзыва: {current_delay:.1f} секунд")
                    time.sleep(current_delay)

            # Сохраняем оставшиеся данные после обработки страницы
            if all_reviews:
                print(f"💾 Сохранение {len(all_reviews)} отзывов в Excel...")
                append_to_excel(all_reviews, filename, page)
                all_reviews = []

            page += 1
            current_review = 0

            # Сохраняем прогресс перехода на новую страницу
            save_progress(filename, page, 0, end_page, processed_ids)

        # Финальное сохранение в Excel
        if all_reviews:
            print(f"💾 Финальное сохранение {len(all_reviews)} отзывов в Excel...")
            append_to_excel(all_reviews, filename, page - 1)

        # Обновляем статус задачи
        total_processed = len(processed_ids) - duplicates_skipped
        if save_to_db and job_id:
            JobService.finish_job(
                job_id,
                db_session,
                status="finished",
                message=f"Парсинг завершен. Обработано {total_processed} отзывов, пропущено {duplicates_skipped} дубликатов"
            )
            db_session.commit()

        print(f"\n🎉 ПАРСИНГ ЗАВЕРШЕН!")
        print(f"📊 Статистика:")
        print(f"   • Найдено уникальных ID: {len(processed_ids)}")
        print(f"   • Пропущено дубликатов: {duplicates_skipped}")
        print(f"   • Обработано новых отзывов: {total_processed}")
        print(f"💾 Данные сохранены:")
        print(f"   • В БД: {'ДА' if save_to_db else 'НЕТ'}")
        print(f"   • В Excel: {filename}")

        return list(processed_ids)

    except Exception as e:
        print(f"\n❌ ОШИБКА ВО ВРЕМЯ ПАРСИНГА: {e}")
        import traceback
        traceback.print_exc()

        # Обновляем статус задачи при ошибке
        if save_to_db and job_id:
            try:
                JobService.finish_job(
                    job_id,
                    db_session,
                    status="failed",
                    message=f"Ошибка: {str(e)}"
                )
                db_session.commit()
            except:
                pass

        raise

    finally:
        # Закрываем сессию
        if db_session:
            db_session.close()

        # Удаляем файл прогресса
        progress_file = f"{filename}_progress.json"
        if os.path.exists(progress_file):
            os.remove(progress_file)
            print("🧹 Файл прогресса удален")


def run_parser_job(
        start_page: int = 1,
        end_page: int | None = None,
        delay: int = 2,
        excel_filename: str | None = None,
        save_to_db: bool = True,
        job_id: int | None = None
):
    """Запуск парсинга через задачу - использует full_parse_cycle"""

    try:
        print(f"🚀 Запуск парсинга через задачу...")
        print(f"📄 Страницы: {start_page}-{end_page or 'конец'}")
        print(f"💾 Сохранение в БД: {'Да' if save_to_db else 'Нет'}")

        # Просто вызываем full_parse_cycle с нужными параметрами
        processed_ids = full_parse_cycle(
            start_page=start_page,
            end_page=end_page,
            filename=excel_filename,
            delay=delay,
            resume=True,
            save_to_db=save_to_db,
            job_id=job_id
        )

        return {
            "success": True,
            "processed_ids": len(processed_ids) if processed_ids else 0
        }

    except Exception as e:
        print(f"❌ Ошибка в run_parser_job: {e}")
        import traceback
        traceback.print_exc()
        raise


def _parse_date(value: str | None):
    """Парсит дату из строки (для обратной совместимости)"""
    return parse_date(value)

# Примеры запуска (закомментированы)
# if __name__ == "__main__":
#     # Тестовый запуск одной страницы
#     full_parse_cycle(
#         start_page=1,
#         end_page=1,
#         filename="test.xlsx",
#         save_to_db=True,
#         delay=1
#     )