import pandas as pd
import requests
import time
import json
from typing import Dict, List, Tuple
import numpy as np


# ==================== 1. Класс для работы с Ollama ====================

class OllamaEvaluator:
    """Класс для оценки суммаризаций с помощью LLM-as-a-judge"""

    def __init__(self, model_name="gemma3:27b", base_url="http://localhost:11434/api/generate"):
        self.model_name = model_name
        self.base_url = base_url
        self.session = requests.Session()

    def generate(self, prompt: str, temperature: float = 0.1) -> str:
        """Генерация ответа на промпт"""
        payload = {
            "model": self.model_name,
            "prompt": prompt,
            "stream": False,
            "options": {
                "temperature": temperature,
                "top_p": 0.9
            }
        }

        try:
            response = self.session.post(self.base_url, json=payload, timeout=120)
            response.raise_for_status()
            return response.json().get("response", "")
        except Exception as e:
            print(f"Ошибка при генерации: {e}")
            return ""

    def extract_score(self, response: str) -> Tuple[float, str]:
        """
        Извлекает оценку и обоснование из ответа модели.
        Ожидает формат: ОЦЕНКА: X/5 [обоснование]
        """
        try:
            # Ищем оценку в формате "X/5" или "X из 5"
            import re

            # Паттерны для поиска оценки
            patterns = [
                r'ОЦЕНКА:\s*(\d+(?:\.\d+)?)\s*/\s*5',
                r'ОЦЕНКА:\s*(\d+(?:\.\d+)?)\s*из\s*5',
                r'(\d+(?:\.\d+)?)\s*/\s*5',
                r'(\d+(?:\.\d+)?)\s*из\s*5',
                r'Оценка:\s*(\d+(?:\.\d+)?)'
            ]

            score = None
            for pattern in patterns:
                match = re.search(pattern, response, re.IGNORECASE)
                if match:
                    score = float(match.group(1))
                    break

            # Если не нашли оценку, пытаемся извлечь число от 1 до 5
            if score is None:
                numbers = re.findall(r'\b[1-5](?:\.\d+)?\b', response)
                if numbers:
                    score = float(numbers[0])

            # Обоснование - все что после оценки или вся строка
            reason = response
            if score is not None:
                # Пытаемся выделить обоснование после оценки
                reason_match = re.search(r'(?:ОБОСНОВАНИЕ|Обоснование|Reason|Причина)[:\s]*(.+)', response,
                                         re.IGNORECASE | re.DOTALL)
                if reason_match:
                    reason = reason_match.group(1).strip()
                else:
                    # Берем все после оценки
                    parts = re.split(r'ОЦЕНКА|оценка|Score|score', response, maxsplit=1)
                    if len(parts) > 1:
                        reason = parts[1].strip()

            return score if score is not None else 0.0, reason

        except Exception as e:
            print(f"Ошибка при извлечении оценки: {e}")
            return 0.0, response


# ==================== 2. Промпты для оценки ====================

def create_relevance_prompt(original: str, summary: str) -> str:
    """Промпт для оценки релевантности"""
    return f"""Ты эксперт по оценке качества текстов. Оцени релевантность суммаризации исходному тексту.

ИСХОДНЫЙ ТЕКСТ:
{original}

СУММАРИЗАЦИЯ:
{summary}

КРИТЕРИИ ОЦЕНКИ:
1. Все ли ключевые факты из оригинала есть в суммаризации?
2. Нет ли в суммаризации информации, которой нет в оригинале?
3. Точно ли передана основная мысль?

ИНСТРУКЦИЯ:
1. Поставь оценку от 1 до 5, где:
   - 1: Суммаризация не соответствует оригиналу
   - 2: Соответствует частично, много ошибок/пропусков
   - 3: Основная мысль передана, но есть неточности
   - 4: Хорошо передает содержание, мелкие недочеты
   - 5: Идеально передает все ключевые аспекты
2. Объясни свою оценку

ФОРМАТ ОТВЕТА:
ОЦЕНКА: X/5
ОБОСНОВАНИЕ: [твое объяснение]"""


def create_conciseness_prompt(original: str, summary: str) -> str:
    """Промпт для оценки краткости"""
    return f"""Ты эксперт по оценке качества текстов. Оцени краткость и емкость суммаризации.

ИСХОДНЫЙ ТЕКСТ:
{original}

СУММАРИЗАЦИЯ:
{summary}

КРИТЕРИИ ОЦЕНКИ:
1. Суммаризация должна быть 15-25 слов (сейчас: {len(summary.split())} слов)
2. Нет ли избыточных деталей или повторов?
3. Сохранилась ли основная мысль при сокращении?

ИНСТРУКЦИЯ:
1. Поставь оценку от 1 до 5, где:
   - 1: Слишком подробно или слишком кратко (>30 или <10 слов)
   - 2: Значительные проблемы с длиной или избыточностью
   - 3: Приемлемая длина, но можно улучшить
   - 4: Хорошая длина, минимальные недочеты
   - 5: Идеальная длина (15-25 слов), лаконично и информативно
2. Объясни свою оценку

ФОРМАТ ОТВЕТА:
ОЦЕНКА: X/5
ОБОСНОВАНИЕ: [твое объяснение]"""


def create_clarity_prompt(summary: str) -> str:
    """Промпт для оценки ясности"""
    return f"""Ты эксперт по оценке качества текстов. Оцени ясность и понятность суммаризации.

СУММАРИЗАЦИЯ:
{summary}

КРИТЕРИИ ОЦЕНКИ:
1. Легко ли понять основную мысль?
2. Нет ли двусмысленностей или сложных конструкций?
3. Логична ли структура изложения?

ИНСТРУКЦИЯ:
1. Поставь оценку от 1 до 5, где:
   - 1: Непонятно, запутанно, много ошибок
   - 2: Сложно понять, требуется дополнительный контекст
   - 3: В основном понятно, но есть неясные моменты
   - 4: Хорошо понятно, мелкие недочеты
   - 5: Очень ясно, четко и недвусмысленно
2. Объясни свою оценку

ФОРМАТ ОТВЕТА:
ОЦЕНКА: X/5
ОБОСНОВАНИЕ: [твое объяснение]"""


# ==================== 3. Функция для извлечения суммаризации ====================

def extract_summary_from_response(response_text: str) -> str:
    """Извлекает текст суммаризации из ответа модели"""
    import re

    # Пытаемся найти суммаризацию по разным шаблонам
    patterns = [
        r'СУММАРИЗАЦИЯ:\s*(.+?)(?=\n\n|\n[A-Z]|$)',
        r'суммаризация:\s*(.+?)(?=\n\n|\n[A-Z]|$)',
        r'Саммари:\s*(.+?)(?=\n\n|\n[A-Z]|$)',
        r'саммари:\s*(.+?)(?=\n\n|\n[A-Z]|$)',
        r'Summary:\s*(.+?)(?=\n\n|\n[A-Z]|$)',
        r'summary:\s*(.+?)(?=\n\n|\n[A-Z]|$)'
    ]

    for pattern in patterns:
        match = re.search(pattern, response_text, re.IGNORECASE | re.DOTALL)
        if match:
            return match.group(1).strip()

    # Если не нашли по шаблонам, берем весь текст
    return response_text.strip()


# ==================== 4. Основной процесс оценки ====================

def evaluate_summarizations_simple(dataset_path: str, output_path: str, sample_size: int = None):
    """
    Упрощенная функция для оценки суммаризаций

    Args:
        dataset_path: путь к CSV файлу с результатами суммаризации
        output_path: путь для сохранения результатов оценки
        sample_size: количество отзывов для оценки (None - все)
    """

    # Загружаем датасет
    print("Загрузка датасета...")
    df = pd.read_csv(dataset_path)

    # Проверяем наличие необходимых колонок
    required_columns = ['Текст отзыва (API)', 'gemma4b саммари']
    for col in required_columns:
        if col not in df.columns:
            raise ValueError(f"Отсутствует обязательная колонка: {col}")

    # Выбираем подвыборку если нужно
    if sample_size and sample_size < len(df):
        df = df.sample(sample_size, random_state=42).reset_index(drop=True)
        print(f"Выбрано {sample_size} случайных отзывов для оценки")

    # Инициализируем оценщика
    evaluator = OllamaEvaluator(model_name="gemma3:27b")

    # Список для хранения результатов
    evaluation_results = []

    print(f"Начинаем оценку {len(df)} отзывов...")
    print("=" * 80)

    for index, row in df.iterrows():
        original_text = str(row['Текст отзыва (API)'])
        summary_response = str(row['gemma4b саммари'])

        # Извлекаем чистую суммаризацию
        summary_text = extract_summary_from_response(summary_response)

        if not summary_text or pd.isna(summary_text) or summary_text == 'nan':
            print(f"Пропускаем отзыв {index}: пустая суммаризация")
            continue

        print(f"\n[{index + 1}/{len(df)}] ОЦЕНКА СУММАРИЗАЦИИ")
        print(f"Оригинал: {original_text[:100]}...")
        print(f"Суммаризация: {summary_text}")
        print(f"Длина: {len(summary_text.split())} слов")

        try:
            # Оцениваем релевантность
            print("\n1. Оценка релевантности...")
            relevance_prompt = create_relevance_prompt(original_text, summary_text)
            relevance_response = evaluator.generate(relevance_prompt)
            relevance_score, relevance_reason = evaluator.extract_score(relevance_response)

            # Оцениваем краткость
            print("2. Оценка краткости...")
            conciseness_prompt = create_conciseness_prompt(original_text, summary_text)
            conciseness_response = evaluator.generate(conciseness_prompt)
            conciseness_score, conciseness_reason = evaluator.extract_score(conciseness_response)

            # Оцениваем ясность
            print("3. Оценка ясности...")
            clarity_prompt = create_clarity_prompt(summary_text)
            clarity_response = evaluator.generate(clarity_prompt)
            clarity_score, clarity_reason = evaluator.extract_score(clarity_response)

            # Вычисляем общую оценку
            overall_score = (relevance_score + conciseness_score + clarity_score) / 3

            # Сохраняем результаты
            result = {
                'index': index,
                'original_text_length': len(original_text),
                'summary_text': summary_text,
                'summary_length_words': len(summary_text.split()),
                'relevance_score': round(relevance_score, 2),
                'relevance_reason': relevance_reason[:500],  # Ограничиваем длину
                'conciseness_score': round(conciseness_score, 2),
                'conciseness_reason': conciseness_reason[:500],
                'clarity_score': round(clarity_score, 2),
                'clarity_reason': clarity_reason[:500],
                'overall_score': round(overall_score, 2)
            }

            evaluation_results.append(result)

            print(f"\n✓ Оценки получены:")
            print(f"   Релевантность: {relevance_score:.2f}/5")
            print(f"   Краткость: {conciseness_score:.2f}/5")
            print(f"   Ясность: {clarity_score:.2f}/5")
            print(f"   Общая: {overall_score:.2f}/5")

            # Пауза чтобы не перегружать модель
            time.sleep(1)

        except Exception as e:
            print(f"✗ Ошибка при оценке отзыва {index}: {e}")
            import traceback
            traceback.print_exc()
            continue

    # Сохраняем результаты в DataFrame
    if evaluation_results:
        results_df = pd.DataFrame(evaluation_results)

        # Сохраняем в CSV
        results_df.to_csv(output_path, index=False, encoding='utf-8-sig')
        print(f"\n✓ Результаты сохранены в {output_path}")

        # Генерируем отчет
        generate_report(results_df)

        return results_df
    else:
        print("✗ Не удалось оценить ни один отзыв")
        return None


# ==================== 5. Генерация отчета ====================

def generate_report(results_df: pd.DataFrame):
    """Генерирует детальный отчет по результатам оценки"""

    print("\n" + "=" * 80)
    print("ОТЧЕТ ПО ОЦЕНКЕ КАЧЕСТВА СУММАРИЗАЦИИ")
    print("=" * 80)

    # Основные статистики
    print(f"\n📊 ОБЩАЯ СТАТИСТИКА ({len(results_df)} отзывов):")
    print("-" * 40)

    metrics = ['relevance_score', 'conciseness_score', 'clarity_score', 'overall_score']
    metric_names = ['Релевантность', 'Краткость', 'Ясность', 'Общая оценка']

    for metric, name in zip(metrics, metric_names):
        if metric in results_df.columns:
            mean_val = results_df[metric].mean()
            median_val = results_df[metric].median()
            std_val = results_df[metric].std()
            min_val = results_df[metric].min()
            max_val = results_df[metric].max()

            print(f"\n{name}:")
            print(f"  Среднее: {mean_val:.2f}/5")
            print(f"  Медиана: {median_val:.2f}/5")
            print(f"  Std: {std_val:.2f}")
            print(f"  Диапазон: {min_val:.2f} - {max_val:.2f}")

    # Распределение по категориям качества
    print(f"\n📈 РАСПРЕДЕЛЕНИЕ ПО КАТЕГОРИЯМ КАЧЕСТВА:")
    print("-" * 40)

    def categorize_score(score):
        if score >= 4.5:
            return "Отлично (4.5-5.0)"
        elif score >= 4.0:
            return "Хорошо (4.0-4.5)"
        elif score >= 3.0:
            return "Удовлетворительно (3.0-4.0)"
        elif score >= 2.0:
            return "Плохо (2.0-3.0)"
        else:
            return "Очень плохо (0-2.0)"

    results_df['quality_category'] = results_df['overall_score'].apply(categorize_score)
    distribution = results_df['quality_category'].value_counts().sort_index()

    for category, count in distribution.items():
        percentage = (count / len(results_df)) * 100
        print(f"  {category}: {count} отзывов ({percentage:.1f}%)")

    # Лучшие и худшие примеры
    print(f"\n🏆 ЛУЧШИЕ СУММАРИЗАЦИИ (Топ-3):")
    print("-" * 40)

    best_examples = results_df.nlargest(3, 'overall_score')
    for idx, (_, row) in enumerate(best_examples.iterrows(), 1):
        print(f"\n{idx}. Оценка: {row['overall_score']:.2f}/5")
        print(f"   Суммаризация: {row['summary_text'][:150]}...")
        print(f"   Длина: {row['summary_length_words']} слов")

    print(f"\n⚠️ ПРОБЛЕМНЫЕ СУММАРИЗАЦИИ (Топ-3):")
    print("-" * 40)

    worst_examples = results_df.nsmallest(3, 'overall_score')
    for idx, (_, row) in enumerate(worst_examples.iterrows(), 1):
        print(f"\n{idx}. Оценка: {row['overall_score']:.2f}/5")
        print(f"   Суммаризация: {row['summary_text'][:150]}...")
        print(f"   Длина: {row['summary_length_words']} слов")
        print(f"   Проблема: {row['relevance_reason'][:200]}...")

    # Анализ длины
    print(f"\n📏 АНАЛИЗ ДЛИНЫ СУММАРИЗАЦИЙ:")
    print("-" * 40)

    avg_length = results_df['summary_length_words'].mean()
    median_length = results_df['summary_length_words'].median()

    print(f"  Средняя длина: {avg_length:.1f} слов")
    print(f"  Медианная длина: {median_length} слов")
    print(f"  Целевой диапазон: 15-25 слов")

    # Процент суммаризаций в целевом диапазоне
    in_range = results_df[
        (results_df['summary_length_words'] >= 15) &
        (results_df['summary_length_words'] <= 25)
        ]
    percentage_in_range = (len(in_range) / len(results_df)) * 100
    print(f"  В целевом диапазоне: {len(in_range)} ({percentage_in_range:.1f}%)")

    # Рекомендации
    print(f"\n💡 РЕКОМЕНДАЦИИ:")
    print("-" * 40)

    if results_df['relevance_score'].mean() < 3.5:
        print("1. Улучшите релевантность: добавьте в промпт указание сохранять ключевые факты")

    if results_df['conciseness_score'].mean() < 3.5:
        print("2. Улучшите краткость: явно укажите требуемую длину (15-25 слов)")

    if results_df['clarity_score'].mean() < 3.5:
        print("3. Улучшите ясность: попросите модель использовать простые и четкие формулировки")

    if percentage_in_range < 70:
        print("4. Контролируйте длину: многие суммаризации выходят за пределы целевого диапазона")

    print(f"\n🎯 ОБЩИЙ ВЫВОД:")
    print("-" * 40)

    overall_mean = results_df['overall_score'].mean()
    if overall_mean >= 4.0:
        print("✅ Качество суммаризации отличное! Модель хорошо справляется с задачей.")
    elif overall_mean >= 3.5:
        print("☑️ Качество суммаризации хорошее, есть небольшой потенциал для улучшения.")
    elif overall_mean >= 3.0:
        print("⚠️ Качество суммаризации удовлетворительное, требуется доработка промптов.")
    else:
        print("❌ Качество суммаризации низкое, необходим пересмотр подхода.")


# ==================== 6. Запуск оценки ====================

if __name__ == "__main__":

    # Конфигурация
    INPUT_DATASET = 'baseline_dataset_with_gemma4b.csv'
    OUTPUT_RESULTS = 'evaluation_results.csv'

    # Количество отзывов для оценки (None - все)
    SAMPLE_SIZE = 10  # Для начала оценим 10 отзывов

    print("=" * 80)
    print("ОЦЕНКА КАЧЕСТВА СУММАРИЗАЦИИ С ПОМОЩЬЮ LLM-as-a-judge")
    print("Используемая модель: gemma3:27b")
    print("=" * 80)

    try:
        # Проверяем доступность Ollama
        print("Проверка подключения к Ollama...")
        test_response = requests.get("http://localhost:11434/api/tags", timeout=5)
        if test_response.status_code == 200:
            print("✓ Ollama доступна")
        else:
            print("✗ Не удалось подключиться к Ollama")
            print("Убедитесь, что Ollama запущена: ollama serve")
            exit(1)

        # Проверяем наличие модели
        models = test_response.json().get('models', [])
        model_names = [model.get('name', '') for model in models]
        if 'gemma3:27b' not in model_names and 'gemma3:27b' not in [name.split(':')[0] for name in model_names]:
            print("⚠️ Модель gemma3:27b не найдена. Попробую использовать другую модель...")
            if model_names:
                print(f"Доступные модели: {model_names}")

        # Запускаем оценку
        print(f"\nЗапуск оценки...")
        results = evaluate_summarizations_simple(
            dataset_path=INPUT_DATASET,
            output_path=OUTPUT_RESULTS,
            sample_size=SAMPLE_SIZE
        )

        if results is not None:
            # Сохраняем сводный отчет в отдельный файл
            with open('evaluation_report.txt', 'w', encoding='utf-8') as f:
                import sys
                from io import StringIO

                # Перенаправляем вывод в файл
                old_stdout = sys.stdout
                sys.stdout = StringIO()

                generate_report(results)

                report_text = sys.stdout.getvalue()
                sys.stdout = old_stdout

                f.write(report_text)

            print(f"\n✓ Детальный отчет сохранен в evaluation_report.txt")
            print("✓ Оценка завершена успешно!")

    except FileNotFoundError:
        print(f"✗ Ошибка: Файл {INPUT_DATASET} не найден")
        print("Убедитесь, что вы сначала запустили код для суммаризации")
    except Exception as e:
        print(f"✗ Произошла ошибка: {e}")
        import traceback

        traceback.print_exc()