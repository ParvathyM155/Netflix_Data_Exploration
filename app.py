"""
Netflix Content Analysis — Streamlit Dashboard
===============================================
Run with:  streamlit run app.py

Displays an interactive dashboard over the Netflix dataset with
sidebar filters, KPI cards, charts, and a recommendation engine.
"""

import warnings
from pathlib import Path

import pandas as pd
import plotly.express as px
import streamlit as st
from wordcloud import WordCloud
import matplotlib.pyplot as plt
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

warnings.filterwarnings('ignore')

# ── Page configuration ────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Netflix Data Analysis",
    page_icon="🎬",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown("""
<style>
  [data-testid="stMetricValue"] { font-size: 2rem !important; color: #E50914; }
  .block-container { padding-top: 2rem; }
</style>
""", unsafe_allow_html=True)


# ── Data loading and cleaning ─────────────────────────────────────────────────
@st.cache_data(show_spinner="Loading dataset…")
def load_and_clean(path: Path) -> pd.DataFrame:
    """Load the Netflix dataset and apply all cleaning steps."""
    df = (
        pd.read_excel(path)
        if path.suffix in ('.xlsx', '.xls')
        else pd.read_csv(path)
    )
    df.columns = [c.strip().title().replace(' ', '_') for c in df.columns]

    for col in ['Director', 'Cast', 'Country', 'Rating']:
        if col in df.columns:
            df[col] = df[col].fillna('Unknown')

    date_col = next(
        (c for c in ['Date_Added', 'Release_Date'] if c in df.columns),
        None
    )
    if date_col:
        df[date_col]      = pd.to_datetime(df[date_col], errors='coerce')
        df['Year_Added']  = df[date_col].dt.year
        df['Month_Added'] = df[date_col].dt.month

    genre_col = next(
        (c for c in ['Listed_In', 'Type'] if c in df.columns),
        None
    )
    if genre_col:
        df['Main_Genre'] = (
            df[genre_col].astype(str).str.split(',').str[0].str.strip()
        )

    if 'Country' in df.columns:
        df['Main_Country'] = (
            df['Country'].astype(str).str.split(',').str[0].str.strip()
        )

    return df.drop_duplicates()


# ── Dataset path ──────────────────────────────────────────────────────────────
DATA_PATH = Path('data/Netflix_Dataset.xlsx')

if not DATA_PATH.exists():
    st.error(
        "⚠️  Dataset not found.\n\n"
        "Download `Netflix_Dataset.xlsx` from Kaggle and place it at "
        "`data/Netflix_Dataset.xlsx`, then restart the app."
    )
    st.stop()

df = load_and_clean(DATA_PATH)

# ── Sidebar filters ───────────────────────────────────────────────────────────
with st.sidebar:
    st.image(
        "https://upload.wikimedia.org/wikipedia/commons/0/08/Netflix_2015_logo.svg",
        width=120
    )
    st.markdown("### Filters")

    categories = ['All'] + sorted(df['Category'].dropna().unique().tolist()) \
        if 'Category' in df.columns else ['All']
    sel_cat = st.selectbox("Content Type", categories)

    if 'Year_Added' in df.columns:
        years = sorted(df['Year_Added'].dropna().astype(int).unique())
        sel_years = st.select_slider(
            "Year Range",
            options=years,
            value=(min(years), max(years))
        )
    else:
        sel_years = None

# ── Apply filters ─────────────────────────────────────────────────────────────
fdf = df.copy()
if 'Category' in df.columns and sel_cat != 'All':
    fdf = fdf[fdf['Category'] == sel_cat]
if sel_years and 'Year_Added' in df.columns:
    fdf = fdf[fdf['Year_Added'].between(*sel_years)]

# ── Header ────────────────────────────────────────────────────────────────────
st.title("🎬 Netflix Content Analysis")
st.caption("Interactive Dashboard")
st.divider()

# ── KPI cards ─────────────────────────────────────────────────────────────────
col1, col2, col3, col4, col5 = st.columns(5)
col1.metric("Total Titles",   f"{len(fdf):,}")
col2.metric("Movies",
    int((fdf['Category'] == 'Movie').sum())   if 'Category' in fdf.columns else '—')
col3.metric("TV Shows",
    int((fdf['Category'] == 'TV Show').sum()) if 'Category' in fdf.columns else '—')
col4.metric("Countries",
    fdf['Main_Country'].nunique()             if 'Main_Country' in fdf.columns else '—')
col5.metric("Top Rating",
    fdf['Rating'].value_counts().idxmax()
    if 'Rating' in fdf.columns and not fdf['Rating'].empty else '—')

st.divider()

# ── Row 1 charts ──────────────────────────────────────────────────────────────
c1, c2 = st.columns(2)

with c1:
    st.subheader("Movies vs TV Shows")
    if 'Category' in fdf.columns:
        vc = fdf['Category'].value_counts().reset_index()
        vc.columns = ['Category', 'Count']
        fig = px.bar(
            vc, x='Category', y='Count', color='Category',
            color_discrete_sequence=['#E50914', '#831010'],
            text='Count', template='plotly_dark'
        )
        fig.update_traces(textposition='outside')
        st.plotly_chart(fig, use_container_width=True)

with c2:
    st.subheader("Yearly Content Trend")
    if 'Year_Added' in fdf.columns:
        yearly = (
            fdf['Year_Added'].dropna().astype(int)
            .value_counts().sort_index().reset_index()
        )
        yearly.columns = ['Year', 'Count']
        fig2 = px.area(
            yearly, x='Year', y='Count',
            template='plotly_dark',
            color_discrete_sequence=['#E50914']
        )
        st.plotly_chart(fig2, use_container_width=True)

# ── Row 2 charts ──────────────────────────────────────────────────────────────
c3, c4 = st.columns(2)

with c3:
    st.subheader("Top 10 Countries")
    if 'Main_Country' in fdf.columns:
        tc = fdf['Main_Country'].value_counts().head(10).reset_index()
        tc.columns = ['Country', 'Count']
        fig3 = px.bar(
            tc, x='Count', y='Country', orientation='h',
            template='plotly_dark', color='Count',
            color_continuous_scale='reds'
        )
        fig3.update_layout(yaxis={'categoryorder': 'total ascending'})
        st.plotly_chart(fig3, use_container_width=True)

with c4:
    st.subheader("Rating Distribution")
    if 'Rating' in fdf.columns:
        rat = fdf['Rating'].value_counts().reset_index()
        rat.columns = ['Rating', 'Count']
        fig4 = px.bar(
            rat, x='Count', y='Rating', orientation='h',
            template='plotly_dark', color='Count',
            color_continuous_scale='reds'
        )
        fig4.update_layout(yaxis={'categoryorder': 'total ascending'})
        st.plotly_chart(fig4, use_container_width=True)

# ── World map ─────────────────────────────────────────────────────────────────
st.subheader("🌍 Global Content Distribution")
if 'Country' in fdf.columns:
    cc = fdf['Country'].value_counts().reset_index()
    cc.columns = ['Country', 'Count']
    fig_map = px.choropleth(
        cc, locations='Country', locationmode='country names',
        color='Count', hover_name='Country',
        color_continuous_scale='reds', template='plotly_dark',
        title='Netflix Content by Country'
    )
    st.plotly_chart(fig_map, use_container_width=True)

# ── Word cloud ────────────────────────────────────────────────────────────────
st.subheader("☁️ Title Word Cloud")
if 'Title' in fdf.columns:
    text = ' '.join(fdf['Title'].dropna().astype(str))
    wc = WordCloud(
        width=900, height=300,
        background_color='#0e1117',
        colormap='Reds', max_words=200
    ).generate(text)
    fig_wc, ax = plt.subplots(figsize=(14, 4))
    ax.imshow(wc, interpolation='bilinear')
    ax.axis('off')
    fig_wc.patch.set_facecolor('#0e1117')
    st.pyplot(fig_wc)

st.divider()

# ── Recommendation engine ─────────────────────────────────────────────────────
st.subheader("🤖 Content Recommendation Engine")
st.caption("Finds similar titles using TF-IDF on description, genre, and cast.")

rec_df = df.dropna(subset=['Title']).reset_index(drop=True)
rec_df['Title'] = rec_df['Title'].astype(str)


def _get_col(dataframe: pd.DataFrame, candidates: list) -> pd.Series:
    """Return the first matching column, or an empty-string Series."""
    for col in candidates:
        if col in dataframe.columns:
            return dataframe[col].fillna('').astype(str)
    return pd.Series([''] * len(dataframe))


rec_df['Tags'] = (
    _get_col(rec_df, ['Description'])               + ' ' +
    _get_col(rec_df, ['Listed_In', 'Main_Genre'])    + ' ' +
    _get_col(rec_df, ['Cast', 'Director'])
)


@st.cache_resource(show_spinner="Building similarity matrix…")
def build_sim_matrix(tags: pd.Series):
    """Compute TF-IDF cosine similarity matrix."""
    tfidf  = TfidfVectorizer(stop_words='english', max_features=5000)
    matrix = tfidf.fit_transform(tags)
    return cosine_similarity(matrix)


sim = build_sim_matrix(rec_df['Tags'])

col_search, col_n = st.columns([3, 1])
title_input = col_search.selectbox("Select a title", sorted(rec_df['Title'].tolist()))
n_recs = col_n.slider("Results", 3, 10, 5)

if st.button("Get Recommendations", type="primary"):
    matches = rec_df.index[rec_df['Title'].str.lower() == title_input.lower()]
    if len(matches) == 0:
        st.warning(f'Title "{title_input}" not found.')
    else:
        idx    = matches[0]
        scores = sorted(
            enumerate(sim[idx]), key=lambda x: x[1], reverse=True
        )[1:n_recs + 1]
        cols = [
            c for c in ['Title', 'Category', 'Main_Genre', 'Listed_In']
            if c in rec_df.columns
        ]
        result = rec_df.iloc[[i for i, _ in scores]][cols].reset_index(drop=True)
        result.index += 1
        st.success(f"Top {n_recs} titles similar to **{title_input}**:")
        st.dataframe(result, use_container_width=True)

# ── Footer ────────────────────────────────────────────────────────────────────
st.divider()
st.caption("🎬 Netflix Content Analysis")
