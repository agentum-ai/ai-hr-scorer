# CV Scoring App

ИИ-ассистент для прескоринга кандидатов на вакансии.

## Запуск локально

1. `pip install -r requirements.txt`
2. Создайте `.streamlit/secrets.toml` с OPENAI_API_KEY
3. `streamlit run streamlit_app.py`

## Деплой

1. Push в GitHub (без secrets.toml!)
2. Streamlit Cloud → New App → GitHub repo
3. В Secrets добавьте OPENAI_API_KEY
