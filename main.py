import requests
import os
import time
import datetime
import numpy as np
from config import api_token, bot_token
from static import write_values

import django
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "bets_bot.settings")
django.setup()

from selenium import webdriver
from selenium.webdriver.firefox.options import Options

from admin_panel.models import Params, Event, Division, Group
# Импортируем модели

'''
TODO:
•
'''

bk_num = 1

operators = {'+': (1, lambda x, y: x + y), '-': (1, lambda x, y: x - y),
             '*': (2, lambda x, y: x * y), '/': (2, lambda x, y: x / y)}

settings_data = Params.objects.all()[0]

slovar = {'а':'a','б':'b','в':'v','г':'g','д':'d','е':'e','ё':'e',
      'ж':'zh','з':'z','и':'i','й':'i','к':'k','л':'l','м':'m','н':'n',
      'о':'o','п':'p','р':'r','с':'s','т':'t','у':'u','ф':'f','х':'h',
      'ц':'c','ч':'cz','ш':'sh','щ':'scz','ъ':'','ы':'y','ь':'','э':'a',
      'ю':'u','я':'ja', 'А':'A','Б':'B','В':'V','Г':'G','Д':'D','Е':'E','Ё':'E',
      'Ж':'ZH','З':'Z','И':'I','Й':'I','К':'K','Л':'L','М':'M','Н':'N',
      'О':'O','П':'P','Р':'R','С':'S','Т':'T','У':'U','Ф':'F','Х':'H',
      'Ц':'C','Ч':'CZ','Ш':'SH','Щ':'SCH','Ъ':'','Ы':'y','Ь':'','Э':'A',
      'Ю':'U','Я':'YA'}

def get_it_inline(home_team, away_team):
    """ Задача функии забирать данные по индивидуальному тоталу за 10 минут до игры
        Но Идея сбрать с парсинга, мне не нравиться. Ведь можно забирать по апи ODDS
    """
    options = Options()
    #set headless mode
    options.add_argument("--headless")
    #options = options
    browser = webdriver.Firefox(options = options)
    browser.get('https://www.fonbet.ru/bets/handball')
    poster_page = browser.page_source
    print('Проверяю в фонбет по линии get_it_inline')
    print('На этом месте скрипт подвисает при matches 0, процессор на сервере загудел на полную')
    for i in range(3):
        try:
            m = None
            time.sleep(10)
            matches = browser.find_elements_by_xpath('//tr[@class="table__row"]')
            print('matches', len(matches))

            for match in matches:
                index = matches.index(match)
                try:
                    title = match.find_elements_by_xpath('//a[@class="table__match-title-text"]/h3')[index].text.upper()
                except Exception:
                    continue

                print(title)
                print(home_team)
                print(away_team)

                translit_title = title

                for key in slovar:
                    translit_title = translit_title.replace(key, slovar[key])

                if title.find(home_team.upper()) != -1 or title.find(away_team.upper()) != -1 or translit_title.find(home_team.upper()) != -1 or translit_title.find(away_team.upper()) != -1:
                    m = match
                    break
                elif len(home_team.split(' ')) > 1 or len(away_team.split(' ')) > 1:
                    print("g is ok 1")
                    for home_team_daetail in home_team.split(' '):
                        if title.find(home_team_daetail.upper()) != -1 or translit_title.find(home_team_daetail.upper()) != -1:
                            m = match
                            print("g is ok 2")
                            break

                    for away_team_daetail in away_team.split(' '):
                        if title.find(away_team_daetail.upper()) != -1 or translit_title.find(away_team_daetail.upper()) != -1:
                            m = match
                            print("g is ok 3")
                            break

            url = m.find_elements_by_xpath('//a[@class="table__match-title-text"]')[index].get_attribute('href')
            browser.get(url)
            time.sleep(10)

            headers = [h.text for h in browser.find_elements_by_xpath('//div[contains(@class, "event-view-tables-wrap")]/div/div[1]/div/div[3]')]
            ##print(headers)
            index = headers.index('Индивидуальные тоталы голов')

            home_team_total = browser.find_element_by_xpath(f'//div[contains(@class, "event-view-tables-wrap")]/div[{index + 1}]/div[2]/div[1]/div[1]/div[2]/div[1]/div/div').text.replace('Тотал ', '')
            away_team_total = browser.find_element_by_xpath(f'//div[contains(@class, "event-view-tables-wrap")]/div[{index + 1}]/div[2]/div[2]/div[1]/div[2]/div[1]/div/div').text.replace('Тотал ', '')

            totals = [home_team_total, away_team_total]

            print(totals)
            if len(totals) < 2:
                totals = ['-', '-']

            browser.close()

            return totals
        except:
            pass
    browser.close()

def get_kf_live(home_team, away_team):
    """ Функция парсит фонбет и сравнивает команды по названиям
        с загруженными по апи.
        Также название с фонбет переводиться команда на англ и тоже сравнивается
    """
    options = Options()
    #set headless mode
    options.add_argument("--headless")
    time.sleep(5)
    print('started web')
    browser = webdriver.Firefox(options = options)
    browser.get('https://www.fonbet.ru/live/handball/')
    poster_page = browser.page_source
    m = None
    titles = []
    swap: bool = False
    index = -1

    for i in range(3):
        time.sleep(10)

        matches = browser.find_elements_by_xpath('//tr[@class="table__row"]')
        print(len(matches), ' - лайв игр в фонбет')
        titles = []
        for match in matches:
            index = matches.index(match)
            #print(index, 'индекс')
            title = None
            title_home = title_away = ""
            trans_title_home = trans_title_away = ""
            try:
                title = match.find_elements_by_xpath('//a[@class="table__match-title-text"]/div')[index].text.upper()
                titles.append(title)
                title_home, title_away = title.split(" — ")
            except Exception:
                continue
            #print(title, '    -     название в фонбет')
            #print(home_team, '        -       название с апи хозяева')
            #print(away_team, '        -       название с апи гости')

            translit_title = title

            for key in slovar:
                translit_title = translit_title.replace(key, slovar[key])

            translit_title = translit_title.upper()

            try:
                trans_title_home, trans_title_away = translit_title.split(" — ")
            except Exception as e:
                pass

            #print(translit_title, '    -      перевод с фонбет на анг')

            #print(home_team.split(' '), ' - home_team.split(' ')')
            #print(away_team.split(' '))

            if title.find(home_team.upper()) != -1 or title.find(away_team.upper()) != -1 or translit_title.find(home_team.upper()) != -1 or translit_title.find(away_team.upper()) != -1:
                if title_home.find(away_team.upper()) != -1 or title_away.find(
                        home_team.upper()) != -1 or trans_title_home.find(
                        away_team.upper()) != -1 or trans_title_away.find(home_team.upper()) != -1:
                    swap = True
                m = match
                break

            elif len(home_team.split(' ')) > 1 or len(away_team.split(' ')) > 1:
                found = False
                print("Совпадение НЕ найдено")
                for home_team_daetail in home_team.split(' '):
                    if title.find(home_team_daetail.upper()) != -1 or translit_title.find(home_team_daetail.upper()) != -1:
                        if title_away.find(home_team_daetail.upper()) != -1 or trans_title_away.find(
                                home_team_daetail.upper()) != -1:
                            swap = True
                        m = match
                        found = True
                        print('Совпадение по хозяевам')

                        break

                for away_team_daetail in away_team.split(' '):
                    if title.find(away_team_daetail.upper()) != -1 or translit_title.find(away_team_daetail.upper()) != -1:
                        if title_home.find(away_team_daetail.upper()) != -1 or trans_title_home.find(
                                away_team_daetail.upper()) != -1:
                            swap = True
                        m = match
                        found = True
                        print('Совпадение по гостям')

                        break

                if found == True:
                    break
        if m:
            break
    else:
        browser.close()
        print(f'*На сайте*: {", ".join(titles)}\n*По апи*:{", ".join([home_team, away_team])}')
        return None

    url = m.find_elements_by_xpath('//a[@class="table__match-title-text"]')[index].get_attribute('href')
    browser.get(url)

    time.sleep(5)

    for i in range(3):
        headers = [h.text for h in browser.find_elements_by_xpath('//div[contains(@class, "event-view-tables-wrap")]/div/div[1]/div/div[3]')]
        if 'Индивидуальные тоталы голов' in headers:
            break
        time.sleep(10)
    else:
        browser.close()
        return None

    print(headers, 'headers')
    index = headers.index('Индивидуальные тоталы голов')

    home_team_total = browser.find_element_by_xpath(f'//div[contains(@class, "event-view-tables-wrap")]/div[{index + 1}]/div[2]/div[1]/div[1]/div[2]/div[1]/div/div').text.replace('Тотал ', '')
    home_team_more_odd = browser.find_element_by_xpath(f'//div[contains(@class, "event-view-tables-wrap")]/div[{index + 1}]/div[2]/div[1]/div[1]/div[2]/div[2]/div/div/div').text
    home_team_less_odd = browser.find_element_by_xpath(f'//div[contains(@class, "event-view-tables-wrap")]/div[{index + 1}]/div[2]/div[1]/div[1]/div[2]/div[3]/div/div/div').text

    away_team_total = browser.find_element_by_xpath(f'//div[contains(@class, "event-view-tables-wrap")]/div[{index + 1}]/div[2]/div[2]/div[1]/div[2]/div[1]/div/div').text.replace('Тотал ', '')
    away_team_more_odd = browser.find_element_by_xpath(f'//div[contains(@class, "event-view-tables-wrap")]/div[{index + 1}]/div[2]/div[2]/div[1]/div[2]/div[2]/div/div/div').text
    away_team_less_odd = browser.find_element_by_xpath(f'//div[contains(@class, "event-view-tables-wrap")]/div[{index + 1}]/div[2]/div[2]/div[1]/div[2]/div[3]/div/div/div').text

    #tables_away = browser.find_elements_by_xpath(f'//div[contains(@class, "event-view-tables-wrap")]/div[{index + 1}]/div[2]/div[2]/div[1]/div[2]')

    #home_team_total = tables_home[0].text
    #home_team_more_odd = tables_home[1].text
    #home_team_less_odd = tables_home[2].text

    #away_team_total = tables_away[0].text
    #away_team_more_odd = tables_away[1].text
    #away_team_less_odd = tables_away[2].text

    if swap:
        home_team_total, home_team_more_odd, home_team_less_odd, away_team_total, away_team_more_odd, away_team_less_odd = away_team_total, away_team_more_odd, away_team_less_odd, home_team_total, home_team_more_odd, home_team_less_odd

    odds = [[home_team_total, home_team_more_odd, home_team_less_odd], [away_team_total, away_team_more_odd, away_team_less_odd]]
    print(odds)
    #time.sleep(500)

    browser.close()
    return odds

def day_static(group, events, day):
    """ Функция должна иметь счетчик прибольности из расчета:
        Каждый новый месяц счетчит обнуляем до 100%
        в конце каждого дня отправляем сообщение в телеграмм канал
        message = (
            Итог дня: статистика за вчера + домашний или гостевой коэфиент выйгранных ставок - 10% за каждую проигранную ставку = результат %'

    """
    yesterday_static, chat_id = group.yesterday_static, group.chat_id
    kfs = []
    result, percent = 0, 0

    if day == 1:
        group.yesterday_static = 100
        group.save()

    for event in events:
        if event.isWin == True:
            if event.odd_team == 'home':
                result += ((event.home_kf - 1)*10)
            elif event.odd_team == 'away':
                result += ((event.away_kf - 1)*10)
        else:
            result -= 10

    if yesterday_static == 0:
        yesterday_static = result

    percent = int((result + yesterday_static))

    message = (
        f'*Итог дня:* {yesterday_static}+{result}={percent} %'
    )
    print(message, ' - Итог дня')
    message_id = send_message(message, chat_id)

    group.yesterday_static = result
    group.save()

def send_message(message, chat_id, markdown = True):
    message_str = f'https://api.telegram.org/bot{bot_token}/sendMessage?chat_id={chat_id}&text={message}'
    if markdown is not False:
        message_str += '&parse_mode=Markdown'
    response = requests.get(message_str)
    json = response.json()
    message_id = json['result']['message_id']

    return message_id

def add_to_message(message_id, chat_id, text, prev_text, markdown = True):
    message = prev_text + text
    message_str = f'https://api.telegram.org/bot{bot_token}/editMessageText?chat_id={chat_id}&text={message}&message_id={message_id}'
    if markdown is not False:
        message_str += '&parse_mode=Markdown'
    response = requests.get(message_str)

def get_events():
    """ Функция собирает по Апи данные о предстоящих играх и создает новые евенты:
        Кто играет, когда играет, ссылка на евент
    """
    sport_id = 78
    url = 'https://api.betsapi.com/v2/events/upcoming'
    params = {'token': api_token,
              'sport_id': sport_id,
              'day': 'TODAY',
              'LNG_ID': 73}

    try:
        response = requests.get(url, params = params)
        response = response.json()
        events = response["results"]
        #print(events)
    except Exception as e:
        return [True]

    for event in events:
        event_id = int(event["id"])
        event_league = event["league"]["name"]
        home_team = event["home"]["name"]
        away_team = event["away"]["name"]
        time_status = 0
        url_element = home_team.replace(' ', '-') + "-v-" + away_team.replace(' ', '-')
        event_url = f'https://ru.betsapi.com/r/{event_id}/{url_element}'
        event_start_time = event["time"]

        odded_events = Event.objects.all().filter(event_id = event_id)
        if len(odded_events) > 0:
            continue

        leagues = Division.objects.all().filter(title = event_league)
        odd_events = Event.objects.all().filter(event_id = event_id)

        if len(leagues) > 0 and len(odd_events) == 0:
            new_event = Event(event_id = event_id,
                      event_url = event_url,
                      event_league = event_league,
                      event_start_time = event_start_time,
                      time_status = time_status,
                      home_team = home_team,
                      away_team = away_team
            )

            new_event.save()

    return [True]

def get_event_data(event_id, event_url, home_team, away_team):
    """ Функция дополняет созданный евент:
    Результаты последних 10 игр (ИТ)
    Результат последних 3 игр очных вчтреч.
    И сортирует от большего к меньшему.
    """
    home_history, away_history, ftf_history = None, None, None

    it_home, it_away = None, None
    it10min_home, it10min_away = None, None
    it_away_ids, it_home_ids = None, None
    team_position = None
    result, ftf_home_history, ftf_away_history = None, None, None

    results = []

    settings = {'token': api_token,
                'event_id': event_id,
                'LNG_ID': 73}

    event_view_settings = {'token': api_token,
                           'event_id': event_id,
                           'odds_market': 3
    }

    history = requests.get('https://api.betsapi.com/v1/event/history', params = settings)
    history = history.json()

    try:
        history = history["results"]
    except Exception as e:
        history = {"home": [], "away": [], "h2h": []}

    for history_item in history["home"][:10]:
        scores = history_item["ss"]

        if history_item['home']['name'] == home_team:
            result = scores.split("-")[0]
        else:
            result = scores.split("-")[1]

        results.append(result)

    results.sort()
    results.reverse()
    if len(results) > 0:
        home_history = ', '.join(results)

    results = []

    for history_item in history["away"][:10]:
        scores = history_item["ss"]

        if history_item['home']['name'] == away_team:
            result = scores.split("-")[0]
        else:
            result = scores.split("-")[1]

        results.append(result)

    results.sort()
    results.reverse()
    if len(results) > 0:
        away_history = ', '.join(results)

    results = []

    for history_item in history["h2h"][:3]:
        scores = history_item["ss"]

        if history_item['home']['name'] == home_team:
            result = scores.split("-")[0]
        else:
            result = scores.split("-")[1]

        results.append(result)

    results.sort()
    results.reverse()
    if len(results) > 0:
        ftf_home_history = ', '.join(results)

    results = []

    for history_item in history["h2h"][:3]:
        scores = history_item["ss"]

        if history_item['home']['name'] == away_team:
            result = scores.split("-")[0]
        else:
            result = scores.split("-")[1]

        results.append(result)

    results.sort()
    results.reverse()
    if len(results) > 0:
        ftf_away_history = ', '.join(results)

    event = Event.objects.all().filter(event_id = event_id)[0]

    event.it_home = home_history
    event.it_away = away_history
    event.ftf_home_history = ftf_home_history
    event.ftf_away_history = ftf_away_history
    event.update_status = 0
    event.save()

    return (
        home_history, away_history,
        ftf_home_history, ftf_away_history
    )

def check_updates(event, group):
    """ А эта функиция делает слишком много. Попробую описать
        Задача стоит в обновлении данный, Сейчас обновляются
        ИТ 10 игр и ИТ 3 очных встреч,
        делаются подсчет калькулятора F1 , F2 , F3
        проверяется time status, при статусе ==1 вызывается get_kf_live и делается сравнение названий
        если совпадения названий найдено, то сверяется Результаты калькулятора с онлайн,
        И если и здесь проходят по условиям, то уходит сигнал в телеграмм канал.
        А потом еще при тайм статусе ==3 считывается результат игры,
        смотриться выйгрышь был или проигрышь и досылается сигнал в телеграмм с Конечным итогом
    """
    event_id, event_league = event.event_id, event.event_league
    home_team, away_team = event.home_team, event.away_team
    update_status = event.update_status
    more_or_less = group.more_or_less
    event_url = event.event_url
    #bk_num in range(1, 5, 1)

    params_kf, params_time_period, settings_data = None, None, None

    settings_data = Params.objects.all()[0]
    params_time_period = range(settings_data.game_time_from, settings_data.game_time_to)
    params_kf = np.arange(settings_data.kf_live_from, settings_data.kf_live_to, 0.1)

    F2, F3, chat_id = group.F2, group.F3, group.chat_id

    calc_f1_home, calc_f2_home, calc_f3_home = -1, -1, -1
    calc_f1_away, calc_f2_away, calc_f3_away = -1, -1, -1
    home_score, away_score = 0, 0
    it10min_home, it10min_away = None, None
    monitoring_period, m_l = None, None

    F1_using, F2_using, F3_using = group.F1_using, group.F2_using, group.F3_using


    #time_step = settings_data.time_step
    time_periods = []

    '''
    for per in range(0, 61, time_step):
        index = range(0, 61, time_step).index(per)
        min_period = str(per) + '-'

        if per == 60:
            break
        elif len(range(0, 61, time_step)) == index + 1:
            min_period += '60'
        else:
            min_period += str(range(0, 61, time_step)[index + 1])

        time_periods.append(min_period)

    #print(F1)
    '''

    it_home_str, it_away_str = event.it_home, event.it_away
    ftf_home_history_str, ftf_away_history_str = event.ftf_home_history, event.ftf_away_history

    #print(home_team, ' - ', away_team)

    it_home = []
    it_away = []
    ftf_home_history = []
    ftf_away_history = []

    if it_home_str is not None:
        it_home = [int(it) for it in it_home_str.split(', ')]
    if it_away_str is not None:
        it_away = [int(it) for it in it_away_str.split(', ')]
    if ftf_home_history_str is not None:
        ftf_home_history = [int(it) for it in ftf_home_history_str.split(', ')]
    if ftf_away_history_str is not None:
        ftf_away_history = [int(it) for it in ftf_away_history_str.split(', ')]
    print(it_home, " -  ИТ 10 игр хозяева", home_team)
    print(ftf_home_history, "           -        ИТ очных встреч хозяева ", home_team)
    #print(it_away, " - ИТ очных встреч гости")
    #print(ftf_away_history, " - ИТ 10 игр гости")

    t1, t2, t3, t4, t5, t6, t7, t8, t9, t10, t11 = [it_home[-1] if it_home else 0 for i in range(11)]
    b1, b2, b3, b4, b5, b6, b7, b8, b9, b10, b11 = [ftf_home_history[-1] if ftf_home_history else 0 for i in range(11)]


    for i, it in enumerate(it_home):
        globals()[f't{i + 1}'] = it

    for i, it in enumerate(ftf_home_history):
        globals()[f'b{i + 1}'] = it

    try:
        calc_f2_home = eval(F2, globals(), globals())
        #print(calc_f2_home,  '    -          результат очных calc_f2 ', home_team)
    except Exception as e:
        print(e)

    try:
        calc_f3_home = eval(F3, globals(), globals())
        print(calc_f2_home, 'и', calc_f3_home, '    -          результат calc_f2 и и очных calc_f3 ', home_team)
    except Exception as e:
        print(e)

    # HOME
    print(it_away, " -  ИТ 10 игр гости", away_team)
    print(ftf_away_history, "           -        ИТ очных встреч гости", away_team)

    for it in it_away:
        num = it_away.index(it) + 1
        globals()[f't{num}'] = it

    for it in ftf_away_history:
        num = ftf_away_history.index(it) + 1
        globals()[f'b{num}'] = it

    try:
        calc_f2_away = eval(F2, globals(), globals())
        #print(calc_f2_away, '  -        результат calc_f2_гости', away_team)
    except Exception as e:
        print(e)

    try:
        calc_f3_away = eval(F3, globals(), globals())
        print(calc_f2_away, 'и', calc_f3_away, '  -        результат calc_f2 ипроперка очных calc_f3_гости', away_team)
    except Exception as e:
        print(e)

    # AWAY

    response = requests.get(f'https://app.bsportsfan.com/event/view?id={event_id}')
    json = response.json()
    #print(int(json['event']['time_status']))

    if json['success'] == 0:
        db_events = Event.objects.all().filter(event_url = event_url)
        if len(db_events) > 0:
            db_events[0].time_status = 4
            db_events[0].save()
        return False

    print(int(json['event']['time_status']), " -  time status")
    #print('status')

    if int(json['event']['time_status']) == 0:
        time_now = datetime.datetime.today()
        start_time = datetime.datetime.fromtimestamp(int(json['event']['time']))
        minutes_before = int((start_time-time_now).seconds/60)
        days_before = (start_time-time_now).days
        #print(minutes_before)
        print(home_team,'-', away_team, ':',days_before, ' - дней до игры;', '       ', minutes_before, ' - минут до игры')
        if minutes_before == 5 and days_before == 0:
            # Получаем ИТ за 5 минут
            totals = get_it_inline(home_team, away_team)
            if totals:
                it10min_home = totals[0]
                it10min_away = totals[1]

                event.it10min_home = it10min_home
                event.it10min_away = it10min_away
                event.save()
        return True

    elif int(json['event']['time_status']) == 1 and update_status != 1:
        minutes = int(json['event']['timer']['tm'])
        seconds = int(json['event']['timer']['ts'])

        """
        monitoring_period = None
        for per in time_periods:
            per_ranges = per.split("-")
            print(per_ranges)
            print(minutes)
            if minutes in range(int(per_ranges[0]), int(per_ranges[1]) + 1):
                monitoring_period = per
                break

        if monitoring_period == None:
            return False
        """

        event.monitoring_time = monitoring_period
        event.save()

        if json['event'].get('scores', None) is not None:
            if json['event']['scores'].get('1', None) is not None:
                home_score = int(json['event']['scores']['1']['home'])
                away_score = int(json['event']['scores']['1']['away'])
        elif json['event'].get('ss', None) is not None:
            home_score = int(json['event']['ss'].split('-')[0])
            away_score = int(json['event']['ss'].split('-')[1])

        #goals_num = home_score + away_score
        goalmin_coefficient = group.goalmin_coefficient

        #calc_f1 = goals_num/minutes*goalmin_coefficient

        if minutes != 0:
            calc_f1_home = home_score/minutes*goalmin_coefficient
            calc_f1_away = away_score/minutes*goalmin_coefficient
        event.goalmin_score_home = calc_f1_home
        event.goalmin_score_away = calc_f1_away
        event.save()

        kfs = get_kf_live(home_team, away_team)
        if kfs:
            home_it_odds, away_it_odds = kfs[0], kfs[1]

            event.home_total = home_it_odds[0]
            event.away_total = away_it_odds[0]

            print(more_or_less, ' - больше или меньше')

            if more_or_less == 'more':
                event.home_kf = home_it_odds[1]
                event.away_kf = away_it_odds[1]
                m_l = 'Б'

            elif more_or_less == 'less':
                event.home_kf = home_it_odds[2]
                event.away_kf = away_it_odds[2]
                m_l = 'М'

            event.save()
            #print(event.home_kf, ' - домашний КФ')
            #print(event.away_kf, ' - гостевой КФ')
            print(event.home_total, ' - домашний тотал сейчас')
            print(calc_f2_home, '  - должен быть calc_f2_хозяева', home_team)
            print(event.away_total, ' - гостевой тотал сейчас')
            print(calc_f2_away, '  - должен быть calc_f2_гости', away_team)
            print(minutes, ' - минуты')

            if minutes in params_time_period:
                print('Проверка на вхождение в период мониторинга')
                #if calc_f2_home < calc_f3_home and ((calc_f2_home > calc_f1_home and more_or_less == 'less') or (calc_f2_home < calc_f1_home and more_or_less == 'more')) and (event.home_kf in params_kf):
                if F1_using == 'home not' or 'Не используется' or 'not' or eval(f'{calc_f1_home} {F1_using} {calc_f2_home}'):
                    # F1 and F2
                    event.home_total = float(event.home_total)
                    event.away_total = float(event.away_total)
                    print('Проверка F1 home', F1_using)
                    if F2_using == 'not' or (more_or_less == 'more' and event.home_total <= calc_f2_home) or (more_or_less == 'less' and floatevent.home_total >= calc_f2_home):
                        #if F2_using != 'Не используется' or (more_or_less == 'more' and event.home_total < calc_f2_home) or (more_or_less == 'less' and event.home_total > calc_f2_home):
                        # F2 и ИТ
                        print('Проверка F2 home', F2_using)
                        if F3_using == 'not' or len(ftf_home_history) < 3 or eval(f'{calc_f3_home} {F3_using} {calc_f2_home}'):
                            # F3 and F2
                            print('Проверка F3 home', F3_using)
                            event.update_status = 1
                            event.time_status = 1
                            event.save()

                            message = (
                                f'БК № {bk_num}\n'
                                f'*{event_league}*\n'
                                f'{home_team} - {away_team}\n'
                                f'*Текущий счет:* {home_score}:{away_score}\n'
                                f'*Время в игре:* {minutes}:{seconds}\n'
                                f'*Текущий КФ:* {event.home_kf}\n'
                                f'*Ставка:* ИТ1 - {home_team}\n'
                                f'*Значение:* {event.home_total}{m_l}\n'
                            )

                            message = message.replace('None', '-')

                            event.message_text = message
                            event.odd_team = 'home'
                            event.odd_minutes = f'{minutes}'

                            message_id = send_message(message, chat_id)
                            event.message_id = message_id
                            event.save()

                            #if bk_num in range(1, 5, 1):
                                #bk_num += 1
                            #else:
                                #bk_num = 1

                    # HERE



                if F1_using == 'home not' or 'Не используется' or 'not' or eval(f'{calc_f1_away} {F1_using} {calc_f2_away}'):
                    print('Проверка F1 away', F1_using)
                #elif calc_f2_away < calc_f3_away and ((calc_f2_away > calc_f1_away and more_or_less == 'less') or (calc_f2_away > calc_f1_away and more_or_less == 'more')) and (event.away_kf in params_kf):
                #if (more_or_less == 'more' and event.away_total < calc_f2_away) or (more_or_less == 'less' and event.away_total > calc_f2_away):
                    if F2_using == 'Не используется' or (more_or_less == 'more' and event.away_total <= calc_f2_away) or (more_or_less == 'less' and event.away_total >= calc_f2_away):
                        print('Проверка F2 away', F2_using)
                        if F3_using == 'Не используется' or len(ftf_away_history) < 3 or eval(f'{calc_f3_away} {F3_using} {calc_f2_away}'):
                            print('Проверка F3 away', F3_using)
                            event.update_status = 1
                            event.time_status = 1
                            event.save()

                            message = (
                                f'БК № {bk_num}\n'
                                f'*{event_league}*\n'
                                f'{home_team} - {away_team}\n'
                                f'*Текущий счет:* {home_score}:{away_score}\n'
                                f'*Время в игре:* {minutes}:{seconds}\n'
                                f'*Текущий КФ:* {event.away_kf}\n'
                                f'*Ставка:* ИТ2 - {away_team}\n'
                                f'*Значение:* {event.away_total}{m_l}\n'
                            )

                            message = message.replace('None', '-')

                            event.message_text = message
                            event.odd_team = 'away'
                            event.odd_minutes = f'{minutes}'

                            message_id = send_message(message, chat_id)
                            event.message_id = message_id
                            event.save()

                            #if bk_num in (1, 2):
                                #bk_num += 1
                            #else:
                                #bk_num = 1


    elif int(json['event']['time_status']) == 3:
        event.time_status = 3
        event.save()

        '''if json['event'].get('scores', None) is not None:
            if json['event']['scores'].get('1', None) is not None:
                print(json['event']['scores'])
                home_score = float(json['event']['scores']['4']['home'])
                away_score = float(json['event']['scores']['4']['away'])'''
        print(json['event']['ss'], 'счет')
        home_score = float(json['event']['ss'].split('-')[0])
        away_score = float(json['event']['ss'].split('-')[1])

        home_total, away_total, odd_team = event.home_total, event.away_total, event.odd_team
        home_kf, away_kf = event.home_kf, event.away_kf
        isWin = False
        final_analysis, profit = 0.0, 0
        done_odd, line_total, kf, total = None, None, None, None

        event.result = f'{int(home_score)}-{int(away_score)}'
        event.save()

        print(740, home_total, ' - Итог хозяев ')
        print(odd_team, ' - odd_team ')
        print(home_score, ' - home_score ')
        print(more_or_less, ' - more_or_less ')

        if odd_team is not None:
            if odd_team == 'home':
                kf = event.home_kf
                total = event.home_total
                line_total = event.it10min_home
                final_analysis = home_score - home_total
                if more_or_less == 'more':
                    done_odd = 'ИТБ 1'
                    if home_score > home_total:
                        print('Nice')
                        isWin = True
                elif more_or_less == 'less':
                    done_odd = 'ИТМ 1'
                    if home_score < home_total:
                        isWin = True

                if isWin == False:
                    profit = -10
                    add_to_message(event.message_id, chat_id, f'*Конечный итог:* {int(home_score)}-{int(away_score)} \u274c', event.message_text)
                else:
                    add_to_message(event.message_id, chat_id, f'*Конечный итог:* {int(home_score)}-{int(away_score)} \u2705', event.message_text)
                    percent = int(float("%.1f" % home_kf) % 1 * 10)
                    print(percent)
                    profit = f'{percent}'


            elif odd_team == 'away':
                kf = event.away_kf
                total = event.away_total
                line_total = event.it10min_away
                done_odd = 'ИТБ 2'
                final_analysis = away_score - away_total
                if more_or_less == 'more':
                    if away_score > away_total:
                        isWin = True
                elif more_or_less == 'less':
                    done_odd = 'ИТМ 2'
                    if away_score < away_total:
                        isWin = True

                if isWin == False:
                    profit = -10
                    add_to_message(event.message_id, chat_id, f'*Конечный итог:* {int(home_score)}-{int(away_score)} \u274c', event.message_text)
                else:
                    add_to_message(event.message_id, chat_id, f'*Конечный итог:* {int(home_score)}-{int(away_score)} \u2705', event.message_text)
                    percent = int(float("%.1f" % away_kf) % 1 * 10)
                    print(percent)
                    profit = f'{percent}'

            event.isWin = isWin
            print(profit)
            event.save()

            data = [f'{datetime.datetime.fromtimestamp(event.event_start_time).strftime("%d-%m-%y %H:%M:%S")}',
                    f'{event_league}',
                    f'{home_team} - {away_team}',
                    f'{line_total}',
                    f'{done_odd}',
                    f'{total}',
                    f'{kf}',
                    f'{event.odd_minutes}',
                    f'{event.result.split("-")[0]}',
                    f'{event.result.split("-")[1]}',
                    f'{final_analysis}',
                    f'{int(profit)}',
                    ''
            ]
            print(data)
            write_values(data, group.id)

            # Дозапись данных в Excel и TG TODO

    elif int(json['event']['time_status']) == 4:
        event.time_status = 4
        event.save()

# HERE!!!!!!!!!!!!

print("готово")
#get_events()
#get_event_data(2284216, 'https://ru.betsapi.com/r/2284216/BNTU-2-Minsk-v-Vitebchanka-Women', 'BNTU-2 Minsk', 'Vitebchanka Women')

#event = Event.objects.all().filter(event_id = 2284216)[0]
#group = Group.objects.all().filter(chat_id = -1001271456208)[0]
#check_updates(event, group)
#get_event_data(2259126, 'https://ru.betsapi.com/r/2259126/HC-Gomel-v-%D0%91%D1%80%D0%B5%D1%81%D1%82', 'HC Gomel', 'Брест')
#check_updates(event, group)


#get_kf_live('HC Gomel', 'Брест')

#get_event_data(1816753, 'https://ru.betsapi.com/r/1816753/Dijon-Metropole-v-Гранд-Безансон', 'Dijon Metropole', 'Гранд Безансон')
#event = Event.objects.all().filter(event_id = 1816753)[0]
#group = Group.objects.all().filter(chat_id = -1001271456208)[0]
#get_it_inline('Цеглед', 'Гьонгьоси')
#get_it_inline('РГУОР- Сб. 2002', 'БГК-2')

if __name__ == "__main__":
    while True:
        get_events()
        # За 25 минут <=
        close_events = Event.objects.all().filter(update_status = None).exclude(time_status = 4).filter(event_start_time__lte = (time.time()+1500))

        for close_event in close_events:
            get_event_data(close_event.event_id, close_event.event_url, close_event.home_team, close_event.away_team)
            time.sleep(1)

        update_events = Event.objects.all().exclude(update_status = 0).filter(time_status = 1)
        update_events_before = Event.objects.all().filter(update_status = 0).filter(time_status = 0).filter(event_start_time__lte = (time.time()+700))
        print(len(update_events), ' - игр онлайн по АПИ;', "     ",len(update_events_before), ' - игр предстоит' )
        #print('update_events')
        #print(len(update_events_before), '  - игр предстоит' )
        #print('update_events_before')
        time.sleep(30)
        groups = Group.objects.all()

        for update_event in update_events:
            for group in groups:
                try:
                    check_updates(update_event, group)
                    print(check_updates)
                    time.sleep(5)
                except Exception:
                    print('Exception: check_updates: events')

        for update_event in update_events_before:
            for group in groups:
                try:
                    check_updates(update_event, group)
                    print(check_updates)
                    time.sleep(5)
                except Exception:
                    print('Exception: check_updates: events_before прошлый раз выскочила при поиске совпадений 1индекс')


        #time.sleep(2000)

        old_events = Event.objects.all().filter(event_start_time__lte = (time.time()-21600)).filter(time_status = 0)
        print(len(old_events))

        for old_event in old_events:
            old_event.time_status = 3
            old_event.save()

        now_time = datetime.datetime.now()
        print(now_time)
        if now_time.hour == 23 and now_time.minute == 55 or now_time.minute == 56 or now_time.minute == 57 or now_time.minute == 58:
            for group in groups:
                today_events = [t for t in Event.objects.all().filter(time_status = 3).exclude(odd_team = None).filter(group_odd = group) if datetime.datetime.fromtimestamp(t.event_start_time).day == now_time.day]
                print(len(today_events))
                if len(today_events) > 0:
                    day_static(group, today_events, now_time.day)

        time.sleep(10)
