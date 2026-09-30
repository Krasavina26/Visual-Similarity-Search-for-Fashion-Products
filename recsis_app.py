import streamlit as st
import pandas as pd
import json
from PIL import Image
from pathlib import Path
from collections import defaultdict


# Конфигурация путей
class PathConfig:
    BASE_DIR = Path(r"C:\Users\222881\Downloads")
    ARCHIVE_DIR = BASE_DIR / "archive" / "fashion-dataset"
    IMAGES = ARCHIVE_DIR / "fashion-dataset" / "images"
    STYLES = ARCHIVE_DIR / "styles.csv"
    COSINE_SIM = BASE_DIR / "top_similar_images.json"


def load_image_from_path(img_path, target_size=(224, 224)):
    try:
        img = Image.open(img_path)
        return img.resize(target_size)
    except Exception as e:
        st.error(f"Ошибка загрузки изображения: {e}")
        return None


@st.cache_data
def load_data():
    config = PathConfig()

    df = pd.read_csv(config.STYLES, on_bad_lines='warn')
    df['image_id'] = df['id'].astype(str) + '.jpg'

    with open(config.COSINE_SIM, 'r') as f:
        raw_data = json.load(f)

    similarity_dict = defaultdict(dict)
    for main_id, similar_ids in raw_data.items():
        similarity_dict[main_id] = {img_id: 0.9 - 0.1 * i for i, img_id in enumerate(similar_ids)}


    existing_files = {img.name for img in config.IMAGES.glob("*.jpg")}
    valid_ids = set(similarity_dict.keys()) & existing_files

    df_filtered = df[df['image_id'].isin(valid_ids)]
    styles_dict = df_filtered.set_index('image_id').to_dict('index')

    image_paths = {img.name: str(img) for img in config.IMAGES.glob("*.jpg") if img.name in valid_ids}

    # Диагностика
    # st.write("### Отладочная информация")
    # st.write(f"Загружено товаров: {len(df_filtered)}")
    # st.write(f"Пример ключей из JSON: {list(similarity_dict.keys())[:3]}")
    # st.write(
     #   f"Пример рекомендаций: {list(similarity_dict['15970.jpg'].items())[:3] if '15970.jpg' in similarity_dict else 'N/A'}")
    # st.write(f"Общих ID: {len(valid_ids)}")

    return df_filtered, similarity_dict, image_paths, styles_dict


def show_recommendations(selected_id, similarity_dict, image_paths, styles_dict):
    image_id = f"{selected_id}.jpg"

    st.write(f"### Информация для ID: {image_id}")
    st.write(f"Наличие в словаре: {image_id in similarity_dict}")
    st.write(f"Наличие изображения: {image_id in image_paths}")

    if image_id not in similarity_dict:
        st.error("Товар не найден в рекомендациях. Проверьте:")
        st.write("- Соответствие ID между CSV и JSON")
        st.write("- Наличие изображения в папке")
        return

    # Получение рекомендаций
    recommendations = similarity_dict[image_id]
    top_recommendations = sorted(recommendations.items(), key=lambda x: -x[1])[:4]

    # Отображение
    cols = st.columns(5)
    with cols[0]:
        img = load_image_from_path(image_paths[image_id])
        if img:
            st.image(img, use_container_width=True, caption="Выбранный товар")
            st.caption(f"ID: {styles_dict[image_id]['id']}")
            st.caption(f"{styles_dict[image_id]['articleType']} ({styles_dict[image_id]['baseColour']})")

    for i, (rec_id, score) in enumerate(top_recommendations):
        with cols[i + 1]:
            if rec_id in image_paths and rec_id in styles_dict:
                img = load_image_from_path(image_paths[rec_id])
                if img:
                    st.image(img, use_container_width=True, caption=f"Сходство: {score:.2f}")
                    st.caption(f"ID: {styles_dict[rec_id]['id']}")
                    st.caption(f"{styles_dict[rec_id]['articleType']} ({styles_dict[rec_id]['baseColour']})")
            else:
                st.error(f"Отсутствует: {rec_id}")


# Инициализация приложения
st.set_page_config(page_title="Рекомендации", layout="wide")
st.title('Рекомендательная система')

try:
    df, similarity_dict, image_paths, styles_dict = load_data()

    # Фильтры
    with st.sidebar:
        st.header('Фильтры')
        gender = st.selectbox('Пол', ['Все'] + sorted(df['gender'].dropna().unique()))
        category = st.selectbox('Категория', ['Все'] + sorted(df['articleType'].dropna().unique()))

    # Фильтрация
    filtered_df = df.copy()
    if gender != 'Все':
        filtered_df = filtered_df[filtered_df['gender'] == gender]
    if category != 'Все':
        filtered_df = filtered_df[filtered_df['articleType'] == category]

    # Отображение товаров
    st.subheader("Товары")
    cols = st.columns(4)
    for idx, (_, row) in enumerate(filtered_df.head(30).iterrows()):
        with cols[idx % 4]:
            if row['image_id'] in image_paths:
                img = load_image_from_path(image_paths[row['image_id']])
                if img:
                    if st.button(f"ID: {row['id']}", key=row['id']):
                        st.session_state.selected_id = row['id']
                    st.image(img, use_container_width=True)
                    st.caption(f"{row['articleType']} ({row['baseColour']})")

    # Рекомендации
    if 'selected_id' in st.session_state:
        show_recommendations(
            st.session_state.selected_id,
            similarity_dict,
            image_paths,
            styles_dict
        )

except Exception as e:
    st.error(f"Ошибка: {str(e)}")
