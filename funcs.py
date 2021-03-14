import requests
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.support.select import Select
from selenium.webdriver.chrome.options import Options

import geocoder
import folium

from ipywidgets import interact, Dropdown, SelectionSlider, SelectMultiple

from tqdm.notebook import tqdm
import pandas as pd
import time
import random
import codecs
import re


areas = ['千代田区', '中央区', '港区', '新宿区', '文京区', '渋谷区', '台東区', '墨田区', '江東区', '荒川区', '足立区', '葛飾区', '江戸川区', '品川区', '目黒区', '大田区', '世田谷区', '中野区', '杉並区', '練馬区', '豊島区', '北区', '板橋区', '八王子市', '立川市', '武蔵野市', '三鷹市', '青梅市', '府中市', '昭島市', '調布市', '町田市', '小金井市', '小平市', '日野市', '東村山市', '国分寺市', '国立市', '福生市', '狛江市', '東大和市', '清瀬市', '東久留米市', '武蔵村山市', '多摩市', '稲城市', '羽村市', 'あきる野市', '西東京市', '西多摩郡']
sort_metrics = ['賃料が安い順', '賃料が高い順', '築年数が新しい順', '広い順', '新着順']

rent_values = ['3.0', '3.5', '4.0', '4.5', '5.0', '5.5', '6.0', '6.5', '7.0', '7.5', '8.0', '8.5', '9.0', '9.5', '10.0', '11.0', '12.0', '13.0', '14.0', '15.0', '16.0', '17.0', '18.0', '19.0', '20.0', '30.0', '50.0', '100.0']
area_values = ['20', '30', '40', '50', '60', '70', '80', '90', '100']
minutes_values = ['1', '5', '7', '10', '15', '20']
age_values = ['新築', '3', '5', '10', '15', '20', '25', '30']

layout_type_values = ['ワンルーム', '1K', '1DK', '1LDK', '2K', '2DK', '2LDK', '3K', '3DK', '3LDK', '4K', '4DK', '4LDK']
payment_type_values = ['管理費・共益費込み', '礼金なし', '敷金なし']          
building_type_values = ['マンション', 'アパート', '一戸建て・その他']
construction_type_values = ['鉄筋系', '鉄骨系', '木造', 'ブロック・その他']
option_values = ['バス・トイレ別', '2階以上', '室内洗濯機置場', 'エアコン付', '駐車場あり']
# [l.append('すべての選択を解除する') for l in [layout_type_values, payment_type_values, building_type_values, construction_type_values, option_values]] # NOTE: streamlitでは不要

# 初期値
rent_from, rent_to = '3.0', '3.0'
minutes_to_station = '0'
area_from, area_to = '20', '20'
age = '新築'
layout_types, payment_types, building_types, construction_types, options = [], [], [], [], []


def scrape(url):
    response = requests.get(url)
    response.encoding = response.apparent_encoding
    html = response.text
    soup = BeautifulSoup(html, 'html.parser')
    return soup

def get_driver(url, headless=True):
    if headless:
        options = Options()
        options.add_argument('--headless')
        driver = webdriver.Chrome('./chromedriver', chrome_options=options)
    else:
        driver =  webdriver.Chrome('./chromedriver')
    driver.get(url)    
    return driver

def scrape_with_chrome(driver, select_options={}, check_options={}, text_options={}):
    for id_, is_checked in check_options.items():
        if not is_checked: continue
        try:
            elem = driver.find_element_by_id(id_)
        except:
            elem = driver.find_element_by_name(id_)
        elem.click()
        
    for id_, val in select_options.items():
        try:
            elem = driver.find_element_by_id(id_)
        except:
            elem = driver.find_element_by_name(id_)
        select = Select(elem)
        select.select_by_value(val)        
        
    for id_, val in text_options.items():
        try:
            elem = driver.find_element_by_id(id_)
        except:
            elem = driver.find_element_by_class_name(id_)
        elem.send_keys(val)
        
    html = driver.page_source
    return BeautifulSoup(html, 'html.parser')


def get_suumo_url(prefecture = '東京都',
                  area = '千代田区',
                  sort = 
                  'おすすめ順',
                  #'賃料が安い順',
                  #'賃料が高い順',
                  #'築年数が新しい順',
                  #'広い順',
                  #'新着順',                  
                  rent_from = '8.0', # 家賃下限（万円）
                  rent_to = '15.0', # 家賃上限
                  layout_types = [ # 間取り
                      #'ワンルーム'
                      '1K',
                  ],
                  payment_types = [
                      '管理費・共益費込み',
                      '礼金なし',
                      #'敷金なし'
                  ],
                  building_types = [ # 建物の種類
                      'マンション',
                      #'アパート', 
                      #'一戸建て・その他'
                  ],
                  construction_types = [ # 建築構造
                      '鉄筋系',
                      #'鉄骨系',
                      #'木造',
                      #'ブロック・その他'
                  ],
                  minutes_to_station = '20', # 駅徒歩（分）
                  area_from = '20', # 専有面積下限（平方メートル）
                  area_to = '30', # 専有面積上限
                  age = '20', # 築年数
                  options = [
                      'バス・トイレ別',
                      '2階以上',
                      '室内洗濯機置場',
                      #'エアコン付',
                      #'駐車場あり'
                  ],
                  n_lists = 100
                 ):
    sort_enc = {
        'おすすめ順': '25',
        '賃料が安い順': '00',
        '賃料が高い順': '01',
        '築年数が新しい順': '04',
        '広い順': '11',
        '新着順': '09'
    }
    area_enc = { '千代田区': '13101',
                 '中央区': '13102',
                 '港区': '13103',
                 '新宿区': '13104',
                 '文京区': '13105',
                 '渋谷区': '13113',
                 '台東区': '13106',
                 '墨田区': '13107',
                 '江東区': '13108',
                 '荒川区': '13118',
                 '足立区': '13121',
                 '葛飾区': '13122',
                 '江戸川区': '13123',
                 '品川区': '13109',
                 '目黒区': '13110',
                 '大田区': '13111',
                 '世田谷区': '13112',
                 '中野区': '13114',
                 '杉並区': '13115',
                 '練馬区': '13120',
                 '豊島区': '13116',
                 '北区': '13117',
                 '板橋区': '13119',
                 '八王子市': '13201',
                 '立川市': '13202',
                 '武蔵野市': '13203',
                 '三鷹市': '13204',
                 '青梅市': '13205',
                 '府中市': '13206',
                 '昭島市': '13207',
                 '調布市': '13208',
                 '町田市': '13209',
                 '小金井市': '13210',
                 '小平市': '13211',
                 '日野市': '13212',
                 '東村山市': '13213',
                 '国分寺市': '13214',
                 '国立市': '13215',
                 '福生市': '13218',
                 '狛江市': '13219',
                 '東大和市': '13220',
                 '清瀬市': '13221',
                 '東久留米市': '13222',
                 '武蔵村山市': '13223',
                 '多摩市': '13224',
                 '稲城市': '13225',
                 '羽村市': '13227',
                 'あきる野市': '13228',
                 '西東京市': '13229',
                 '西多摩郡': '13300',
                 #'大島支庁': None,
                 #'大島町': None,
                 #'利島村': None,
                 #'新島村': None,
                 #'神津島村': None,
                 #'三宅支庁': None,
                 #'三宅島三宅村': None,
                 #'御蔵島村': None,
                 #'八丈支庁': None,
                 #'八丈島八丈町': None,
                 #'青ヶ島村': None,
                 #'小笠原支庁': None,
                 #'小笠原村': None
               }
    layout_enc = {'ワンルーム': '01', # TODO: この辺の変数を別のファイルに
                  '1K': '02',
                  '1DK': '03',
                  '1LDK': '04',
                  '2K': '05',
                  '2DK': '06',
                  '2LDK': '07',
                  '3K': '08',
                  '3DK': '09',
                  '3LDK': '10',
                  '4K': '11',
                  '4DK': '12',
                  '4LDK': '13',
                  '5K以上': '14'}
    options_enc = {'駐車場あり': '0400901',
                   'バス・トイレ別': '0400301',
                   '2階以上': '0400101',
                   '室内洗濯機置場': '0400501',
                   'エアコン付': '0400601'} 
    
    ta = 13 # TODO: 東京都のみ
    sc = area_enc[area]
    po1 = sort_enc[sort]
    cb = rent_from
    ct = rent_to if rent_to != '0' else '9999999'
    md = ''.join([f'&md={layout_enc[layout]}' for layout in layout_types])
    co = [f'&co={i}' for i, type_ in enumerate(['管理費・共益費込み', None, '礼金なし', '敷金なし'], 1) if type_ in payment_types]
    co = ''.join(co)
    ts = [f'&ts={i}' for i, type_ in enumerate(['マンション', 'アパート', '一戸建て・その他'], 1) if type_ in building_types]
    ts = ''.join(ts)
    kz = [f'&kz={i}' for i, type_ in enumerate(['鉄筋系', '鉄骨系', '木造', 'ブロック・その他'], 1) if type_ in construction_types]
    kz = ''.join(kz)
    et = minutes_to_station if minutes_to_station != '0' else '9999999'
    mb = area_from
    mt = area_to if area_to != '0' else '9999999'
    cn = age if age not in ['新築', '指定しない'] else {'新築': '0', '指定しない': '9999999'}[age]
    tc = ''.join([f'&tc={options_enc[option]}' for option in options])
    
    return f'https://suumo.jp/jj/chintai/ichiran/FR301FC005/?ar=030&bs=040&po1={po1}&pc={n_lists}&ta={ta}&sc={sc}&cb={cb}&ct={ct}{md}{co}{ts}{kz}&et={et}&cn={cn}&mb={mb}&mt={mt}{tc}'

def _ja_to_int(text):
    if text[0] == "-": return 0
    unit = "万円"
    text = text.replace(',', '')
    if unit in text:
        man_yen = float(text.split(unit)[0])
        return int(man_yen * 10000)
    return int(text.split("円")[0])

def suumo_info(soup):
    name = soup.h2.text.strip()
    url = 'https://suumo.jp/' + soup.h2.a.get('href')
    # img_url = soup.select_one("#js-bukkenList-casset0").li.img['rel']
    try: img_url = soup.img['rel']
    except: img_url = 'https://suumo.jp/library/img/img_colno.png'
        
    rent_str = soup.select_one(".detailbox-property--col1").select_one(".detailbox-property-point").text
    rent = _ja_to_int(rent_str)
    management_fee_str = soup.select_one(".detailbox-property--col1").select('div')[1].text.split("管理費 ")[-1]
    management_fee = _ja_to_int(management_fee_str)
    deposit_str = soup.select_one(".detailbox-property--col2").select('div')[0].text.split('敷')[-1]
    deposit = _ja_to_int(deposit_str)
    key_money_str = soup.select_one(".detailbox-property--col2").select('div')[1].text.split('礼')[-1]
    key_money = _ja_to_int(key_money_str)
    key_money_str = soup.select_one(".detailbox-property--col2").select('div')[1].text.split('礼')[-1]

    layout, area, direction = [tag.text for tag in soup.select(".detailbox-property--col3")[0].select('div')]
    area = float(area.split("m2")[0])

    building_type, age = [tag.text for tag in soup.select(".detailbox-property--col3")[1].select('div')]
    age = age.split("築")[-1].split("年")[0]
    age = int(age) if age != "" else None

    address = soup.select(".detailbox-property-col")[-1].text.strip()

    detail = soup.select_one(".detailnote-box").text

    return {"name": name,
            "url": url,
            "name_link": f'<a href="{url}" target="_blank">{name}</a>',
            "img_url": img_url,
            "img_tag": f'<img src="{img_url}" height=150>',
            "rent": rent,
            "rent_str": rent_str,
            "management_fee": management_fee,
            "management_fee_str": management_fee_str,
            "rent_and_management_fee": rent + management_fee,
            "deposit": deposit,
            "deposit_str": deposit_str,
            "key_money_str": key_money_str,
            "key_money": key_money,
            "layout": layout,
            "area": area,
            # "direction": direction,
            "address": address,
            "detail": detail.replace('\n', ''),
            "building_type": building_type,
            "age": age,            
            "info_in_table": _info_in_table(rent_str, management_fee_str, deposit_str, key_money_str, layout, area, address, building_type, age)            
           }

def _parse_homes_area_ids(url='https://www.homes.co.jp/chintai/tokyo/city/'):
    soup = scrape(url)    
    d = {}
    for tag in soup.select_one('.mod-tokyoCityList.area.fitting').select('li'):
        try: d[tag.a.text] = tag.a.get('href')
        except: pass
    return d    

def get_homes_url(prefecture = '東京都',
                  area = '千代田区',
                  sort = 
                  'おすすめ順',
                  #'賃料が安い順',
                  #'賃料が高い順',
                  #'築年数が新しい順',
                  #'広い順',
                  #'新着順',
                  rent_from = '8.0', # 家賃下限（万円）
                  rent_to = '15.0', # 家賃上限
                  layout_types = [ # 間取り
                      #'1R'
                      '1K',
                  ],
                  payment_types = [
                      #'管理費・共益費込み',
                      #'礼金なし',
                      #'敷金なし'
                  ],                  
                  building_types = [ # 建物の種類
                      'マンション',
                      #'アパート', 
                      #'一戸建て・その他'
                  ],
                  construction_types = [
                      '鉄筋系',
                      #'鉄骨系',
                      #'木造',
                      #'ブロック・その他'                      
                  ],
                  minutes_to_station = '20', # 駅徒歩（分）
                  area_from = '20', # 専有面積下限（平方メートル）
                  area_to = '30', # 専有面積上限
                  age = '20', # 築年数
                  options = [
                      #'バス・トイレ別',
                      #'2階以上',
                      #'室内洗濯機置場',
                      #'エアコン付',
                      #'駐車場あり'
                  ]
                 ):
    
    sort_enc = {
        'おすすめ順': 'recommend',
        '賃料が安い順': 'fee',
        '賃料が高い順': '-fee',
        '築年数が新しい順': 'period',
        '広い順': 'area_house',
        '新着順': 'newdate'        
    }
    area_enc = { '千代田区': 'https://www.homes.co.jp/chintai/tokyo/chiyoda-city/list/',
                 '中央区': 'https://www.homes.co.jp/chintai/tokyo/chuo-city/list/',
                 '港区': 'https://www.homes.co.jp/chintai/tokyo/minato-city/list/',
                 '新宿区': 'https://www.homes.co.jp/chintai/tokyo/shinjuku-city/list/',
                 '文京区': 'https://www.homes.co.jp/chintai/tokyo/bunkyo-city/list/',
                 '渋谷区': 'https://www.homes.co.jp/chintai/tokyo/shibuya-city/list/',
                 '台東区': 'https://www.homes.co.jp/chintai/tokyo/taito-city/list/',
                 '墨田区': 'https://www.homes.co.jp/chintai/tokyo/sumida-city/list/',
                 '江東区': 'https://www.homes.co.jp/chintai/tokyo/koto-city/list/',
                 '荒川区': 'https://www.homes.co.jp/chintai/tokyo/arakawa-city/list/',
                 '足立区': 'https://www.homes.co.jp/chintai/tokyo/adachi-city/list/',
                 '葛飾区': 'https://www.homes.co.jp/chintai/tokyo/katsushika-city/list/',
                 '江戸川区': 'https://www.homes.co.jp/chintai/tokyo/edogawa-city/list/',
                 '品川区': 'https://www.homes.co.jp/chintai/tokyo/shinagawa-city/list/',
                 '目黒区': 'https://www.homes.co.jp/chintai/tokyo/meguro-city/list/',
                 '大田区': 'https://www.homes.co.jp/chintai/tokyo/ota-city/list/',
                 '世田谷区': 'https://www.homes.co.jp/chintai/tokyo/setagaya-city/list/',
                 '中野区': 'https://www.homes.co.jp/chintai/tokyo/nakano-city/list/',
                 '杉並区': 'https://www.homes.co.jp/chintai/tokyo/suginami-city/list/',
                 '練馬区': 'https://www.homes.co.jp/chintai/tokyo/nerima-city/list/',
                 '豊島区': 'https://www.homes.co.jp/chintai/tokyo/toshima-city/list/',
                 '北区': 'https://www.homes.co.jp/chintai/tokyo/kita-city/list/',
                 '板橋区': 'https://www.homes.co.jp/chintai/tokyo/itabashi-city/list/',
                 '八王子市': 'https://www.homes.co.jp/chintai/tokyo/hachioji-city/list/',
                 '立川市': 'https://www.homes.co.jp/chintai/tokyo/tachikawa-city/list/',
                 '武蔵野市': 'https://www.homes.co.jp/chintai/tokyo/musashino-city/list/',
                 '三鷹市': 'https://www.homes.co.jp/chintai/tokyo/mitaka-city/list/',
                 '青梅市': 'https://www.homes.co.jp/chintai/tokyo/ome-city/list/',
                 '府中市': 'https://www.homes.co.jp/chintai/tokyo/fuchu-city/list/',
                 '昭島市': 'https://www.homes.co.jp/chintai/tokyo/akishima-city/list/',
                 '調布市': 'https://www.homes.co.jp/chintai/tokyo/chofu-city/list/',
                 '町田市': 'https://www.homes.co.jp/chintai/tokyo/machida-city/list/',
                 '小金井市': 'https://www.homes.co.jp/chintai/tokyo/koganei-city/list/',
                 '小平市': 'https://www.homes.co.jp/chintai/tokyo/kodaira-city/list/',
                 '日野市': 'https://www.homes.co.jp/chintai/tokyo/hino-city/list/',
                 '東村山市': 'https://www.homes.co.jp/chintai/tokyo/higashimurayama-city/list/',
                 '国分寺市': 'https://www.homes.co.jp/chintai/tokyo/kokubunji-city/list/',
                 '国立市': 'https://www.homes.co.jp/chintai/tokyo/kunitachi-city/list/',
                 '福生市': 'https://www.homes.co.jp/chintai/tokyo/fussa-city/list/',
                 '狛江市': 'https://www.homes.co.jp/chintai/tokyo/komae-city/list/',
                 '東大和市': 'https://www.homes.co.jp/chintai/tokyo/higashiyamato-city/list/',
                 '清瀬市': 'https://www.homes.co.jp/chintai/tokyo/kiyose-city/list/',
                 '東久留米市': 'https://www.homes.co.jp/chintai/tokyo/higashikurume-city/list/',
                 '武蔵村山市': 'https://www.homes.co.jp/chintai/tokyo/musashimurayama-city/list/',
                 '多摩市': 'https://www.homes.co.jp/chintai/tokyo/tama-city/list/',
                 '稲城市': 'https://www.homes.co.jp/chintai/tokyo/inagi-city/list/',
                 '羽村市': 'https://www.homes.co.jp/chintai/tokyo/hamura-city/list/',
                 'あきる野市': 'https://www.homes.co.jp/chintai/tokyo/akiruno-city/list/',
                 '西東京市': 'https://www.homes.co.jp/chintai/tokyo/nishitokyo-city/list/',
                 '西多摩郡瑞穂町': 'https://www.homes.co.jp/chintai/tokyo/nishitama_mizuho-city/list/',
                 '西多摩郡日の出町': 'https://www.homes.co.jp/chintai/tokyo/nishitama_hinode-city/list/'
    }
    
    url = area_enc[area]

    rent_from = rent_from if (float(rent_from) < 10 or float(rent_from) == 100) else rent_from.replace('.0', '')
    rent_to = rent_to if (float(rent_to) < 10 or float(rent_to) == 100) else rent_to.replace('.0', '')     
    if age == '指定しない':
        age = '0' 
    elif age == '新築':
        age = '1'

    select_options = {
        # 賃料
        'cond_monthmoneyroom': rent_from, 
        'cond_monthmoneyroomh': rent_to, 
        # 専有面積
        'cond_housearea': area_from, 
        'cond_houseareah': area_to,
        # 駅徒歩
        'cond_walkminutesh': minutes_to_station,
        # 築年数
        'cond_houseageh': age,
        # 並び替え
        'cond_sortby': sort_enc[sort]
    }

    check_options = {
        # 共益費/管理費を含む, 礼金なし, 敷金なし
        'cond_kanrihi': '管理費・共益費込み' in payment_types, 
        'cond_reikin': '礼金なし' in payment_types,
        'cond_shikikin': '敷金なし' in payment_types,
        # 間取り（ワンルーム, 1K, 1DK, 1LDK, 2K, 2DK, 2LDK, 3K, 3DK, 3LDK, 4K, 4DK, 4LDK以上）
        'cond_madori_11': 'ワンルーム' in layout_types,
        'cond_madori_12': '1K' in layout_types,
        'cond_madori_13': '1DK' in layout_types,
        'cond_madori_15': '1LDK' in layout_types,                 
        'cond_madori_22': '2K' in layout_types,
        'cond_madori_23': '2DK' in layout_types,
        'cond_madori_25': '2LDK' in layout_types,
        'cond_madori_32': '3K' in layout_types,
        'cond_madori_33': '3DK' in layout_types,
        'cond_madori_35': '3LDK' in layout_types,
        'cond_madori_42': '4K' in layout_types,
        'cond_madori_43': '4DK' in layout_types,
        'cond_madori_45-': '4LDK以上' in layout_types,
        # 建物構造（鉄筋系, 木造系, 鉄骨系, ブロック・その他）
        'cond_housekouzougroup_rebar': '鉄筋系' in construction_types, 
        'cond_housekouzougroup_wooden': '木造系' in construction_types,
        'cond_housekouzougroup_steelframe': '鉄骨系' in construction_types,
        'cond_housekouzougroup_blockother': 'ブロック・その他' in construction_types,
        # バス・トイレ別
        'cond_mcf_220301': 'バス・トイレ別' in options,
        # 2階以上
        'cond_mcf_340102': '2階以上' in options,
        # 室内洗濯機置場
        'cond_mcf_290901': '室内洗濯機置場' in options,
        # エアコン付
        'cond_mcf_240104': 'エアコン付' in options,
        # 駐車場あり
        'cond_mcf_320801': '駐車場あり' in options,    
    }
    
    return url, select_options, check_options

def _homes_deposit_and_key_int(text, rent):
    if text == '無': return 0
    if '万円' in text: return float(text.replace('万円', '')) * 10000
    unit = 'ヶ月'
    return int(rent * float(text.split(unit)[0]))

def homes_info(soup):
    # TODO: PR物件を飛ばす
    name = soup.h2.text
    url = soup.a.get('href')
    img_url = soup.img['data-original']
    rent_str = soup.select_one('.priceLabel').text
    rent = _ja_to_int(rent_str)
    management_fee_str = soup.select_one('td.price').text.split('/')[1].split('円')[0] + '円' # 最初の1部屋
    management_fee = _ja_to_int(management_fee_str)
    
    deposit_str, key_money_str = str(soup.select_one('td.price')).split('<br/>')[-1].split('/')[:2]
    deposit, key_money = _homes_deposit_and_key_int(deposit_str, rent), _homes_deposit_and_key_int(key_money_str, rent)
    
    l = str(soup.select_one('td.layout')).split('<br/>')
    layout, area = l[0].split('>')[-1], float(l[-1].split('<')[0].split('m')[0])
    address = soup.td.text
    age_str = str(soup.select_one('.bukkenSpec').select('td')).split('/')[0].split('>')[-1]
    detail = soup.select_one('.memberNameBox').text
    
    return {"name": name,
            "url": url,
            "name_link": f'<a href="{url}" target="_blank">{name}</a>',
            "img_url": img_url,
            "img_tag": f'<img src="{img_url}" height=150>',
            "rent": rent,
            "rent_str": rent_str,
            "management_fee": management_fee,
            "management_fee_str": management_fee_str,
            "rent_and_management_fee": rent + management_fee,
            "deposit": deposit,
            "deposit_str": deposit_str,
            "key_money_str": key_money_str,
            "key_money": key_money,            
            "layout": layout,
            "area": area,      
            "address": address,
            "detail": detail,
            "building_type": "",
            "age": "",
            "info_in_table": _info_in_table(rent_str, management_fee_str, deposit_str, key_money_str, layout, area, address, '', age)
           }


def _info_in_table(rent, management_fee, deposit, key_money, layout, area, address, building_type, age):
    if age != '新築': age = f'築{age}年' 
    return f'''
    <ul>
    <li>賃料: {rent} 管理費: {management_fee}</li>
    <li>敷金: {deposit} 礼金: {key_money}</li>
    <li>{layout} {area}㎡</li>
    <li>{age} {building_type}</li>
    <li>{address}</li>
    </ul>
    '''.replace('\n', '')

# suumoとhomesの両方
def rooms_info_accross_services(prefecture = '東京都',
                  area = '千代田区',
                  sort = 
                  'おすすめ順',
                  #'賃料が安い順',
                  #'賃料が高い順',
                  #'築年数が新しい順',
                  #'広い順',
                  #'新着順',                                
                  rent_from = '8.0', # 家賃下限（万円）
                  rent_to = '15.0', # 家賃上限
                  layout_types = [ # 間取り
                      #'1R'
                      '1K',
                  ],
                  payment_types = [
                      #'管理費・共益費込み',
                      #'礼金なし',
                      #'敷金なし'
                  ],                  
                  building_types = [ # 建物の種類
                      'マンション',
                      #'アパート', 
                      #'一戸建て・その他'
                  ],
                  construction_types = [
                      '鉄筋系',
                      #'鉄骨系',
                      #'木造',
                      #'ブロック・その他'                      
                  ],
                  minutes_to_station = '20', # 駅徒歩（分）
                  area_from = '20', # 専有面積下限（平方メートル）
                  area_to = '30', # 専有面積上限
                  age = '20', # 築年数
                  options = [
                      #'バス・トイレ別',
                      #'2階以上',
                      #'室内洗濯機置場',
                      #'エアコン付',
                      #'駐車場あり'
                  ],
                  n_lists = 100,
                 ):
    print('物件情報を収集中')

    # suumo
    url = get_suumo_url(prefecture, area, sort, rent_from, rent_to, layout_types, payment_types, building_types, construction_types, minutes_to_station, area_from, area_to, age, options, n_lists)
    soup = scrape(url)
    suumo_rooms_info = [suumo_info(property_) for property_ in tqdm(soup.select('.property'))]
    
    # homes
    url, select_options, check_options = get_homes_url(prefecture, area, sort, rent_from, rent_to, layout_types, payment_types, building_types, construction_types, minutes_to_station, area_from, area_to, age, options)
    driver = get_driver(url, headless=True)
    soup = scrape_with_chrome(driver, select_options, check_options)
    homes_rooms_info = [homes_info(property_) for property_ in tqdm(soup.select(".moduleInner.prg-building"))]
    print(n_lists)
    for i in range(int((n_lists - 20) / 20)):
        try: driver.find_element_by_class_name('nextPage').click()
        except: break
        soup = BeautifulSoup(driver.page_source, 'html.parser')
        homes_rooms_info += [homes_info(property_) for property_ in tqdm(soup.select(".moduleInner.prg-building"))]
    driver.close()
    rooms_info = suumo_rooms_info + homes_rooms_info

    df = pd.DataFrame(columns=list(rooms_info[0].keys())) # headerの順序を明示的に固定
    for room_info in rooms_info:
        df = df.append(room_info, ignore_index=True)
        
    if sort == '賃料が安い順':
        df = df.sort_values('rent')
    elif sort == '賃料が高い順':
        df = df.sort_values('rent', ascending=False)
    elif sort == '築年数が新しい順':
        df = df.sort_values('age')
    elif sort == '広い順':
        df = df.sort_values('area', ascending=True)
        
    print('物件情報が収集完了')
    return df.reset_index(drop=True)


class Map():
    def __init__(self, loc_name, zoom_start=14):
        self.loc_name = loc_name
        self.zoom_start = zoom_start
        
    def init_map(self):
        location = geocoder.osm(self.loc_name, timeout=5.0)
        self.map_ = folium.Map(location=location.latlng, width='100%', zoom_start=self.zoom_start)
        
    def add_marker_to_map(self, location, text, index, base_url, img_url=None, width=30):
        marker = self.get_marker(location, text, index, base_url, img_url, width)
        if marker:
            marker.add_to(self.map_)
            return marker

    def get_marker(self, location, text, index, base_url, img_url=None, width=50):
        if img_url != None:
            html = f'<img src={img_url} width={width}><a href={base_url} target="_blank">{text}</a>'
        else:
            html = f'<a href={base_url} target="_blank">{text}</a>'
        popup = folium.map.Popup(html, show=False, max_width=150)
        icon = folium.features.DivIcon(html=f'<div style="color:black;background-color:#19bd7c;border:solid 3px #afccc1;width:20px;height:20px;line-height:20px;border-radius:50%;text-align:center;">{index}</div>')
        return folium.Marker(location=location, popup=popup, icon=icon)
    
def _normalize_address(address, area):
    address = address.split(area)[-1].split('丁目')[0]
    
    to_kanji = {'1': '一',
                '１': '一',
                '2': '二',
                '２': '二',
                '3': '三',
                '３': '三',
                '4': '四',
                '４': '四',
                '5': '五',
                '５': '五',
                '6': '六',
                '６': '六',
                '7': '七',
                '７': '七',
                '8': '八',
                '８': '八',
                '9': '九',
                '９': '九'
               }
    for chr_from, chr_to in to_kanji.items():
        address = address.replace(chr_from, chr_to)
    return address

def create_html_table(df):
    df = df.dropna(axis=1, how='any')
    pd.set_option('colheader_justify', 'center')

    html_string = '''
    <html>
      <head>
      <title>物件情報</title>
      </head>
      <link rel="stylesheet" type="text/css"/>
      <body>
        {table}
      </body>
    </html>.
    '''
    return html_string.format(table=df.to_html(index=True))

def export_map_html(df, area, fname, show_table=False):
    print('物件の地図を作成中')
    map_obj = Map(area)
    map_obj.init_map()

    location_soup = scrape(f'http://geoapi.heartrails.com/api/xml?method=getTowns&city={area}')
    locations = {}
    for tag in location_soup.select('location'):
        town = tag.town.text.split('丁目')[0]
        locations[town] = [float(tag.y.text), float(tag.x.text)]

    for i, row in df.iterrows():
        address, index, name, rent, url, img_url = row.address, row.name, row['name'], row.rent_str, row.url, row.img_url
        address = _normalize_address(address, area)
        if address not in locations.keys(): continue

        location = locations[address]
        x_blur, y_blur = random.uniform(-1, 1) / 1000, random.uniform(-1, 1) / 1000 # NOTE: 丁目までではアイコンが重なるため
        location = [location[0] + x_blur, location[1] + y_blur]

        text = f'{index}：{name} {rent}'
        map_obj.add_marker_to_map(location, text, i, url, img_url)

    fname = f'{fname}.html'
    map_obj.map_.save(fname)
    
    if show_table:
        html_table = create_html_table(df.loc[:, ['name_link', 'img_tag', 'rent_str', 'management_fee_str', 'layout', 'area', 'address', 'building_type', 'age','detail']])
        html_table = html_table.replace('&lt;', '<').replace('&gt;', '>')
        with open(fname, mode='a', encoding='utf-8') as f:
            f.write(html_table)
            
        print(f'終了（ファイル名：{fname}）')
    return map_obj.map_

# Jupyter Notebookウィジェット
def assign_value(change):
    var = change['owner'].description    
    change['new'] = [] if change['new'] == 'すべての選択を解除する' else change['new']
    change['new'] = list(change['new']) if type(change['new']) is tuple  else change['new']
    globals().update({f'{var}': change['new']})
    
def show_conditions():
    global areas, sort_metrics, layout_type_values, payment_type_values, building_type_values, construction_type_values, option_values, rent_values, area_values, minutes_values, age_values
    print('・地域')
    form = Dropdown(options=areas, description='area', value=None)
    form.observe(assign_value, names='value')
    display(form)

    print('・並び替え')
    form = Dropdown(options=sort_metrics, description='sort', value=None)
    form.observe(assign_value, names='value')
    display(form)

    print('・家賃下限（万円）')
    form = SelectionSlider(options=rent_values, description='rent_from', value=None)
    form.observe(assign_value, names='value')
    display(form)

    print('・家賃上限（万円）')
    form = SelectionSlider(options=rent_values, description='rent_to', value=None)
    form.observe(assign_value, names='value')
    display(form)

    print('・間取り（複数選択可）')
    form = SelectMultiple(options=layout_type_values, description='layout_types', value=())
    form.observe(assign_value, names='value')
    display(form)

    print('・料金設定（複数選択可）')
    form = SelectMultiple(options=payment_type_values, description='payment_types', value=())
    form.observe(assign_value, names='value')
    display(form)

    print('・建物の種類（複数選択可）')
    form = SelectMultiple(options=building_type_values, description='building_types', value=())
    form.observe(assign_value, names='value')
    display(form)

    print('・建物構造（複数選択可）')
    form = SelectMultiple(options=construction_type_values, description='construction_types', value=())
    form.observe(assign_value, names='value')
    display(form)

    print('・駅徒歩（分）')
    form = SelectionSlider(options=minutes_values, description='minutes_to_station', value=None)
    form.observe(assign_value, names='value')
    display(form)      

    print('・専有面積下限（平方メートル）')
    form = SelectionSlider(options=area_values, description='area_from', value=None)
    form.observe(assign_value, names='value')
    display(form)

    print('・専有面積上限（平方メートル）')
    form = SelectionSlider(options=area_values, description='area_to', value=None)
    form.observe(assign_value, names='value')
    display(form)

    print('・築年数')
    form = SelectionSlider(options=age_values, description='age', value=None)
    form.observe(assign_value, names='value')
    display(form)

    print('・その他オプション（複数選択可）')
    form = SelectMultiple(options=option_values, description='options', value=())
    form.observe(assign_value, names='value')
    display(form) 