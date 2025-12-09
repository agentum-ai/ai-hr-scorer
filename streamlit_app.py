import streamlit as st
from parse_hh import get_html, extract_vacancy_data, extract_resume_data
from gigachat import GigaChat
from gigachat.models import Chat, Messages, MessagesRole
import os

# ДОЛЖЕН быть первым вызовом Streamlit
st.set_page_config(page_title="AI-HR Scorer (GigaChat)", layout="wide")


@st.cache_resource
def get_client() -> GigaChat:
    """Инициализация клиента GigaChat через официальный SDK."""
    auth_key = os.getenv("GIGACHAT_AUTH_KEY") or st.secrets.get("GIGACHAT_AUTH_KEY")
    if not auth_key:
        st.error("Не найден GIGACHAT_AUTH_KEY (ни в переменных окружения, ни в .streamlit/secrets.toml)")
        st.stop()

    # scope подбери под свой тип доступа: GIGACHAT_API_PERS или GIGACHAT_API_CORP
    client = GigaChat(
        credentials=auth_key,
        scope="GIGACHAT_API_PERS",
        verify_ssl_certs=False,  # локально проще отключить строгую проверку SSL
    )
    return client


client = get_client()

SYSTEM_PROMPT = """
Проскорь кандидата, насколько он подходит для данной вакансии (оценка 1-10).

1. Короткий анализ (2-3 предложения): ключевые навыки, опыт, пробелы.
2. Оценка качества резюме (1-5): насколько понятно, с какими задачами сталкивался кандидат и как их решал.
3. Финальная оценка (1-10): учитывай и опыт, и качество резюме.
4. Рекомендация: "Пригласить/Рассмотреть/Отклонить".

Формат ответа:
**Анализ:** ...
**Качество резюме:** X/5
**Оценка:** X/10
**Рекомендация:** ...
""".strip()


def request_gpt(system_prompt: str, user_prompt: str) -> str:
    """Запрос к GigaChat через официальный SDK."""
    try:
        payload = Chat(
            messages=[
                Messages(
                    role=MessagesRole.SYSTEM,
                    content=system_prompt,
                ),
                Messages(
                    role=MessagesRole.USER,
                    content=user_prompt,
                ),
            ]
        )
        resp = client.chat(payload)
        return resp.choices[0].message.content
    except Exception as e:
        return f"Ошибка при обращении к GigaChat: {e}"


# ===== UI =====

st.title("🤖 AI-HR Scorer — прескоринг резюме (GigaChat)")

col1, col2 = st.columns(2)

with col1:
    st.subheader("📋 Вакансия")
    job_url = st.text_input(
        "🔗 Ссылка на вакансию hh.ru (опционально)",
        placeholder="https://hh.ru/vacancy/123456",
    )
    job_text = st.text_area(
        "📝 Или текст вакансии",
        placeholder="Вставьте описание вакансии вручную, если не хотите парсить по ссылке",
        height=180,
    )

with col2:
    st.subheader("📄 Резюме")
    cv_url = st.text_input(
        "🔗 Ссылка на резюме hh.ru (опционально)",
        placeholder="https://hh.ru/resume/abcdef",
    )
    cv_text = st.text_area(
        "📝 Или текст резюме",
        placeholder="Вставьте текст резюме, если нет ссылки на hh.ru",
        height=180,
    )

col_btn1, col_btn2 = st.columns(2)

with col_btn1:
    if st.button("📥 Спарсить вакансию по ссылке"):
        if not job_url:
            st.warning("Сначала вставьте ссылку на вакансию.")
        else:
            with st.spinner("Парсим вакансию с hh.ru..."):
                try:
                    job_html = get_html(job_url).text
                    parsed_job = extract_vacancy_data(job_html)
                    job_text = parsed_job
                    st.success("Вакансия успешно спарсена. Текст подставлен в поле.")
                    st.text_area("📝 Или текст вакансии", value=job_text, height=180)
                except Exception as e:
                    st.error(f"Ошибка парсинга вакансии: {e}")

with col_btn2:
    if st.button("📥 Спарсить резюме по ссылке"):
        if not cv_url:
            st.warning("Сначала вставьте ссылку на резюме.")
        else:
            with st.spinner("Парсим резюме с hh.ru..."):
                try:
                    cv_html = get_html(cv_url).text
                    parsed_cv = extract_resume_data(cv_html)
                    cv_text = parsed_cv
                    st.success("Резюме успешно спарсено. Текст подставлен в поле.")
                    st.text_area("📝 Или текст резюме", value=cv_text, height=180)
                except Exception as e:
                    st.error(
                        "Не удалось спарсить резюме (часто требуется авторизация на hh.ru). "
                        f"Вставьте текст резюме вручную. Детали: {e}"
                    )

st.markdown("---")

if st.button("🚀 Проанализировать соответствие резюме вакансии", type="primary"):
    job_final = (job_text or "").strip()
    cv_final = (cv_text or "").strip()

    if not job_final and not job_url:
        st.error("Не задана вакансия: либо вставьте текст, либо укажите ссылку и нажмите парсинг.")
    elif not cv_final and not cv_url:
        st.error("Не задано резюме: либо вставьте текст, либо укажите ссылку и нажмите парсинг.")
    else:
        with st.spinner("Оцениваем резюме с помощью GigaChat..."):
            try:
                if job_url and not job_final:
                    job_html = get_html(job_url).text
                    job_final = extract_vacancy_data(job_html)

                if cv_url and not cv_final:
                    try:
                        cv_html = get_html(cv_url).text
                        cv_final = extract_resume_data(cv_html)
                    except Exception as e:
                        st.warning(
                            "Не удалось спарсить резюме по ссылке (часто нужна авторизация). "
                            f"Используем текст из поля, если он есть. Детали: {e}"
                        )

                if not job_final or not cv_final:
                    st.error("Нет текста вакансии или резюме. Вставьте их вручную.")
                else:
                    user_prompt = f"# ВАКАНСИЯ\n{job_final}\n\n# РЕЗЮМЕ\n{cv_final}"
                    response = request_gpt(SYSTEM_PROMPT, user_prompt)

                    st.subheader("📊 Результат анализа")
                    st.markdown(response)
            except Exception as e:
                st.error(f"Произошла ошибка при обращении к модели: {e}")

with st.expander("ℹ️ Как пользоваться"):
    st.markdown(
        """
        1. Вставьте ссылку на вакансию и/или резюме с hh.ru и нажмите кнопки парсинга **или** вставьте тексты вручную.  
        2. Нажмите кнопку **«🚀 Проанализировать соответствие резюме вакансии»**.  
        3. Модель GigaChat вернёт анализ, оценку качества резюме и итоговый скоринг 1–10.
        """
    )

st.caption("⚡ Backend: GigaChat API (официальный SDK) · UI: Streamlit")
