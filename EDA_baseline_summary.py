import requests
import ollama
import pandas as pd


# загружаем наш датасет и выбираем 10 отзывов на тест модели и обкатку работы с deep eval
baseline_dataset_summary = pd.read_csv('D:/pars/baseline_dataset.csv')
baseline_dataset_summary = baseline_dataset_summary[['Текст отзыва (API)']].iloc[:10]

import pandas as pd
import requests

# URL локального API Ollama
url = "http://localhost:11434/api/generate"

# SYSTEM_PROMPT (замените на ваш реальный SYSTEM_PROMPT)
SYSTEM_PROMPT = "Вы — эксперт по анализу банковских отзывов."

# Функция для получения ответа от Ollama
def get_ollama_response(prompt):
    payload = {
        "model": "gemma3:4b",
        "prompt": prompt,
        "stream": False
    }
    response = requests.post(url, json=payload)
    if response.status_code == 200:
        return response.json()["response"]
    else:
        raise Exception(f"Ошибка: {response.status_code}, {response.text}")

# Функция для получения тегов
def get_tags(review_text):
    tag_prompt = f"""<start_of_turn>user
{SYSTEM_PROMPT}
Проведи тегирование банковского отзыва. Создай 10-15 тегов, характеризующих отзыв.
Категории для тегов:
1. Банковский продукт (кредит, ипотека, карта и т.д.)
2. Тип операции (оформление, обслуживание, проблема)
3. Эмоциональная окраска (положительная, отрицательная, нейтральная)
4. Конкретные проблемы (если есть)
5. Каналы обслуживания (отделение, онлайн, мобильное приложение)
Отзыв: "{review_text}"
Формат ответа: ТЕГИ: [тег1], [тег2], [тег3], ...<end_of_turn>
<start_of_turn>model
"""
    return get_ollama_response(tag_prompt)

# Функция для получения суммаризации
def get_summary(review_text):
    summary_prompt = f"""<start_of_turn>user
{SYSTEM_PROMPT}
Суммаризируй банковский отзыв одним емким предложением (15-25 слов).
Выдели основную мысль, проблему или предложение клиента.
Отзыв: "{review_text}"
Формат ответа: СУММАРИЗАЦИЯ: [текст суммаризации]<end_of_turn>
<start_of_turn>model
"""
    return get_ollama_response(summary_prompt)

# Основной цикл обработки отзывов
for index, row in baseline_dataset_summary.iterrows():
    review_text = row['Текст отзыва (API)']

    # Получаем полный ответ, теги и суммаризацию
    try:
        full_response = get_ollama_response(review_text)
        tags = get_tags(review_text)
        summary = get_summary(review_text)

        # Заполняем новые столбцы
        baseline_dataset_summary.at[index, 'gemma4b полный ответ'] = full_response
        baseline_dataset_summary.at[index, 'gemma4b теги'] = tags
        baseline_dataset_summary.at[index, 'gemma4b саммари'] = summary
    except Exception as e:
        print(f"Ошибка при обработке отзыва {index}: {e}")

# Сохраняем результат
baseline_dataset_summary.to_csv('baseline_dataset_with_gemma4b.csv', index=False)
