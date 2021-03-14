import streamlit as st
import matplotlib.pyplot as plt
import pandas as pd
import pandas_profiling

from funcs import *

title = '物件検索（東京）'
st.set_page_config(page_title=title, layout='wide')
st.title(title)

st.sidebar.write('検索条件')
prefecture = '東京' # NOTE: まだここだけ
area = st.sidebar.selectbox('地域', areas)
sort = st.sidebar.selectbox('並び替え', sort_metrics)
rent_from = st.sidebar.selectbox('家賃下限（万円）', rent_values)
rent_to = st.sidebar.selectbox('家賃上限（万円）', rent_values)
layout_types = st.sidebar.multiselect('間取り（複数選択可）', layout_type_values)
payment_types = st.sidebar.multiselect('料金設定（複数選択可）', payment_type_values)
building_types = st.sidebar.multiselect('建物の種類（複数選択可）', building_type_values)
construction_types = st.sidebar.multiselect('建物構造（複数選択可）', construction_type_values)
minutes_to_station = st.sidebar.selectbox('駅徒歩（分）', minutes_values)
area_from = st.sidebar.selectbox('専有面積下限（平方メートル）', area_values)
area_to = st.sidebar.selectbox('専有面積上限（平方メートル）', area_values)
age = st.sidebar.selectbox('築年数', age_values)
options = st.sidebar.multiselect('その他オプション（複数選択可）', option_values)

n_lists = st.sidebar.selectbox('表示件数', [40, 80, 120, 160, 200])

if st.sidebar.button('検索'):
    with st.spinner('検索中...'):
        df = rooms_info_accross_services(prefecture=prefecture,
                                         area=area,
                                         sort=sort,
                                         rent_from=rent_from,
                                         rent_to=rent_to,
                                         layout_types=layout_types,
                                         payment_types=payment_types,
                                         building_types=building_types,
                                         construction_types=construction_types,
                                         minutes_to_station=minutes_to_station,
                                         area_from=area_from,
                                         area_to=area_to,
                                         age=age,
                                         options=options,
                                         n_lists=int(n_lists/2) # NOTE: suumoとhomes
                                        )
    map_ = export_map_html(df, area, area)
    st.components.v1.html(folium.Figure().add_child(map_).render(), height=500)
    st.write(df[['name_link', 'img_tag', 'info_in_table']].to_html(header=None, escape=False), unsafe_allow_html=True)
