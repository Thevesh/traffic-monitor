import pandas as pd
import json
from datetime import datetime
import requests as r

import matplotlib.pyplot as plt
import matplotlib.ticker as tkr
from matplotlib.lines import Line2D

from constants import TOKEN_API_GOOGLE, TELEGRAM_CHANNEL_RAYA
SPACE = '     '


def get_data():
    BASE_URL = 'https://maps.googleapis.com/maps/api/directions/json'
    TIME_NOW = f'{datetime.now():%Y-%m-%d-%H-%M}-00'

    df = pd.read_csv('dep/stops.csv')

    for i in range(1,13):
        tf = df[df['chain'] == i].copy().drop('chain',axis=1)
        for j in range(len(tf)-1): 
            ROUTE = f"{tf['route'].iloc[j]}"
            ORIGIN = f"{tf['lat'].iloc[j]}%2C{tf['lon'].iloc[j]}"
            DESTINATION = f"{tf['lat'].iloc[j+1]}%2C{tf['lon'].iloc[j+1]}"

            URL = f'{BASE_URL}?departure_time=now&origin={ORIGIN}&destination={DESTINATION}&key={TOKEN_API_GOOGLE}'

            data = json.loads(r.get(URL).text)
            FILE = f'output/json_raya/{ROUTE}_{TIME_NOW}.json'
            with open(FILE, 'w', encoding='utf8') as f: f.write(json.dumps(data, indent=4, ensure_ascii=False))

    return TIME_NOW


def update_db(TIME_NOW=None):
    df = pd.read_csv('dep/stops.csv')
    res = pd.DataFrame(columns=['timestamp','route','duration'])

    for i in range(1,13):
        tf = df[df['chain'] == i].copy().drop('chain',axis=1)
        for j in range(len(tf)-1): 
            ROUTE = f"{tf['route'].iloc[j]}"
            try:
                data = json.load(open(f'output/json_raya/{ROUTE}_{TIME_NOW}.json','r'))
                DURATION = data['routes'][0]['legs'][0]['duration_in_traffic']['value']
                res.loc[len(res)] = [TIME_NOW,ROUTE,DURATION]
            except:
                res.loc[len(res)] = [TIME_NOW,ROUTE,-1]

    res.timestamp = pd.to_datetime(res.timestamp,format='%Y-%m-%d-%H-%M-%S')
    N_ISSUES = len(res[res.duration == -1])

    res_old = pd.read_parquet('output/raya.parquet')
    res = pd.concat([res_old,res],axis=0,ignore_index=True).drop_duplicates(subset=['route','timestamp'],keep='last')
    res = res.sort_values(['route','timestamp']).reset_index(drop=True)
    res.to_parquet('output/raya.parquet',index=False,compression='brotli')

    return N_ISSUES


def make_chart():
    map_chain = {
        1: 'Johor Bahru <--> Klang Valley',
        2: 'Johor Bahru <--> Klang Valley', # revertse
        3: 'Kota Bharu <--> Klang Valley', # revertse
        4: 'Kota Bharu <--> Klang Valley',
        5: 'Perlis <--> Klang Valley', # reverse
        6: 'Perlis <--> Klang Valley'
    }

    df = pd.read_parquet('output/raya.parquet')
    rf = pd.read_csv('dep/stops.csv')[['route','chain']]
    df = pd.merge(df,rf,on=['route'],how='left')
    df = df[df.chain < 7]
    df = df[~df.route.str.contains('gerik')].groupby(['timestamp','chain']).sum(numeric_only=True).reset_index()

    df.duration = df.duration / 3600
    df['route'] = df.chain.map(map_chain)
    df['direction'] = 'Into KV'
    df.loc[df.chain.isin([2,3,5]), 'direction'] = 'Out of KV'
    df = df.pivot(index=['route','timestamp'],columns='direction',values='duration').reset_index().sort_values(by=['route','timestamp']).reset_index(drop=True)
    LATEST = str(df.timestamp.iloc[-1])
    df = df.set_index('timestamp')

    plt.rcParams.update({'font.size': 10,
                        'font.family': 'sans-serif',
                        'grid.linestyle': 'dashed'})
    plt.rcParams["figure.figsize"] = [5,11]
    plt.rcParams["figure.autolayout"] = True
    fig, ax = plt.subplots(3,1,sharex=False)
    ax = ax.ravel()

    i = 0
    for o in ['Johor Bahru','Kota Bharu','Perlis']:
        df[df.route.str.contains(o)].plot(y='Into KV', ax=ax[i], color='red')
        df[df.route.str.contains(o)].plot(y='Out of KV', ax=ax[i], color='blue')
        ax[i].set_title(f"""\n{o} <---> Klang Valley""",linespacing=1.8)
        i += 1

    for i in [0,1,2]:
        for b in ['top','right']: ax[i].spines[b].set_visible(False)
        ax[i].get_yaxis().set_major_formatter(tkr.FuncFormatter(lambda x, p: format(x, ',.1f')))
        ax[i].yaxis.grid(True)
        ax[i].set_axisbelow(True)
        ax[i].set_ylabel('')
        ax[i].set_xlabel('')
        ax[i].get_legend().remove()

    line_blue = Line2D([0], [0], label='Out of KV',color='blue')
    line_red = Line2D([0], [0], label='Into KV',color='red')
    fig.legend(ncol=2, handles=[line_red,line_blue], bbox_to_anchor=(0.52, 0.93), loc='upper center')
    plt.suptitle(f'{SPACE}Travel Times across Peninsular (hrs)\n{SPACE}Last Updated: {LATEST[:-3]}\n',linespacing=1.8)
    plt.savefig('output/timeseries_raya.png',dpi=400)
    plt.close()


def send_update(TIME_NOW=None,N_ISSUES=None,TG=TELEGRAM_CHANNEL_RAYA):
    EMOJI = '✅ ✅' if N_ISSUES == 0 else '🥲 🥲'
    message = f'Raya traffic update:\n{TIME_NOW}\n\nCron has run.\n\n{EMOJI} {N_ISSUES} record(s) with null values'
    img_path = 'output/timeseries_raya.png'
    doc_path = ''

    url = f'https://api.telegram.org/bot{TG[0]}/send'

    param_msg = {'chat_id': TG[1], 'text': message}
    param_photo = {'chat_id': TG[1]}
    param_doc = {'chat_id': TG[1]}

    if len(img_path) > 0:
        with open(img_path, 'rb') as image_file:
            param_photo['caption'] = message
            response = r.post(f'{url}Photo', data=param_photo, files={'photo': image_file})
    elif len(doc_path) > 0:
        with open(doc_path, 'rb') as file:
            param_doc['caption'] = message
            response = r.post(f'{url}Document', data=param_doc, files={'document': file})
    else: 
        response = r.post(f'{url}Message', data=param_msg)

    print(f'{response.status_code}')


if __name__ == "__main__":
    print('')
    print(datetime.now())
    print('')
    TIME_NOW = get_data()
    print('')
    N_ISSUES = update_db(TIME_NOW=TIME_NOW)
    print('')
    make_chart()
    print('')
    send_update(TIME_NOW=TIME_NOW,N_ISSUES=N_ISSUES)
    print('')
