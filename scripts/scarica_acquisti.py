import subprocess
import requests
from requests.packages.urllib3.exceptions import InsecureRequestWarning
requests.packages.urllib3.disable_warnings(InsecureRequestWarning)
import re
import time
from datetime import timedelta, datetime, tzinfo, timezone
import sys
import pytz
import json
import os
import shutil
from clint.textui import colored, puts
from tqdm import *

from parametri_db import carica_parametri

    
def unixTime():
    dt = datetime.now(tz=pytz.utc)
    return str(int(dt.timestamp() * 1000))

try:
    # Leggi i parametri dal database (tabella parametri, riga id=1)
    params = carica_parametri()

    CF = params['codicefiscale']
    PIN = params['pin']
    Password = params['password']
    Dal = params['dal']
    Al = params['al']
    pivadiretta = params['pivadiretta']
    tipo = int(params['tipo'])
    VenOAcq = params['venoacq']
    # profilo è sempre 1 (delega diretta), non più configurabile
    profilo = 1
    
    s = requests.Session()
    s.headers.update({'User-Agent': 'Mozilla/5.0 (Windows NT 6.1; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/72.0.3626.119 Safari/537.36'})
    s.headers.update({'Connection': 'keep-alive'})

    cookie_obj1 = requests.cookies.create_cookie(domain='ivaservizi.agenziaentrate.gov.it',name='LFR_SESSION_STATE_20159',value='expired')
    s.cookies.set_cookie(cookie_obj1)
    cookie_obj2 = requests.cookies.create_cookie(domain='ivaservizi.agenziaentrate.gov.it',name='LFR_SESSION_STATE_10811916',value=unixTime())
    s.cookies.set_cookie(cookie_obj2)
    r = s.get('https://ivaservizi.agenziaentrate.gov.it/portale/web/guest', verify=False)

    if r.status_code == 200:
        puts(colored.yellow('Collegamento alla homepage. Avvio.'))
    else:
        puts(colored.red('Collegamento alla homepage non riuscito: uscita.'))
        sys.exit()
    cookieJar = s.cookies

    print('Effettuo il login')
    payload = {'_58_saveLastPath': 'false', '_58_redirect' : '', '_58_doActionAfterLogin': 'false', '_58_login': CF , '_58_pin': PIN, '_58_password': Password}    
    r = s.post('https://ivaservizi.agenziaentrate.gov.it/portale/home?p_p_id=58&p_p_lifecycle=1&p_p_state=normal&p_p_mode=view&p_p_col_id=column-1&p_p_col_pos=3&p_p_col_count=4&_58_struts_action=%2Flogin%2Flogin', data=payload)
    cookieJar = s.cookies

    liferay = re.findall(r"Liferay.authToken = '.*';", r.text)[0]
    p_auth = liferay.replace("Liferay.authToken = '","")
    p_auth = p_auth.replace("';", "")

    r = s.get('https://ivaservizi.agenziaentrate.gov.it/dp/api?v=' + unixTime())
# controlla fase di login 
    if r.status_code == 200:
        puts(colored.yellow('Login riuscito. Con credenzilali ENTRATEL'))
    else:
        puts(colored.red('Login non riuscito: uscita.')) 
        sys.exit()

    
    cookieJar = s.cookies

    print('Seleziono il tipo di incarico')
    if profilo == 1:
    # Delega Diretta
                payload = {'cf_inserito': CF};
                r = s.post('https://ivaservizi.agenziaentrate.gov.it/portale/scelta-utenza-lavoro?p_auth='+ p_auth + '&p_p_id=SceltaUtenzaLavoro_WAR_SceltaUtenzaLavoroportlet&p_p_lifecycle=1&p_p_state=normal&p_p_mode=view&p_p_col_id=column-1&p_p_col_count=1&_SceltaUtenzaLavoro_WAR_SceltaUtenzaLavoroportlet_javax.portlet.action=delegaDirettaAction', data=payload);
                payload = {'cf_inserito': CF, 'sceltapiva' : pivadiretta};    
                r = s.post('https://ivaservizi.agenziaentrate.gov.it/portale/scelta-utenza-lavoro?p_auth='+ p_auth + '&p_p_id=SceltaUtenzaLavoro_WAR_SceltaUtenzaLavoroportlet&p_p_lifecycle=1&p_p_state=normal&p_p_mode=view&p_p_col_id=column-1&p_p_col_count=1&_SceltaUtenzaLavoro_WAR_SceltaUtenzaLavoroportlet_javax.portlet.action=delegaDirettaAction', data=payload);
    
    else:
                printi('PORCO CANE QUALCOSA E ANDATA STORTA!')

    print('Aderisco al servizio')
    r = s.get('https://ivaservizi.agenziaentrate.gov.it/ser/api/fatture/v1/ul/me/adesione/stato/')
    
# ADERISCO AL SERVIZIO - NA CAMURRIA!
    if r.status_code == 200:
        puts(colored.yellow('Adesione riuscita ai servizi AdE.'))
    else:
        puts(colored.red('Adesione ai servizi AdE non riuscita: uscita.')) 
        sys.exit()
    
    cookieJar = s.cookies 

    headers_token = {'x-xss-protection': '1; mode=block',
               'strict-transport-security': 'max-age=16070400; includeSubDomains',
               'x-content-type-options': 'nosniff',
               'x-frame-options': 'deny'}
    r = s.get('https://ivaservizi.agenziaentrate.gov.it/cons/cons-services/sc/tokenB2BCookie/get?v='+unixTime() , headers = headers_token )
    if r.status_code == 200:
        puts(colored.yellow('B2B Cookie ottenuto'))
    else:
        puts(colored.red('B2B Cookie non ottenuto: uscita.')) 
        sys.exit()
    cookieJar = s.cookies
    tokens = r.headers

    xb2bcookie = r.headers.get('x-b2bcookie')
    xtoken = r.headers.get('x-token')

    s.headers.update({'Host': 'ivaservizi.agenziaentrate.gov.it'})
    s.headers.update({'Referer': 'https://ivaservizi.agenziaentrate.gov.it/cons/cons-web/?v=' + unixTime()})
    s.headers.update({'Accept': 'application/json, text/plain, */*'})
    s.headers.update({'Accept-Encoding': 'gzip, deflate, br'})
    s.headers.update({'Accept-Language': 'it-IT,it;q=0.9,en-US;q=0.8,en;q=0.7,fr;q=0.6'})
    s.headers.update({'DNT': '1'})
    s.headers.update({'X-XSS-Protection': '1; mode=block'})
    s.headers.update({'Strict-Transport-Security': 'max-age=16070400; includeSubDomains'})
    s.headers.update({'X-Content-Type-Options': 'nosniff'})
    s.headers.update({'X-Frame-Options': 'deny'})
    s.headers.update({'x-b2bcookie': xb2bcookie})
    s.headers.update({'x-token': xtoken})

    headers = {'Host': 'ivaservizi.agenziaentrate.gov.it',
               'referer': 'https://ivaservizi.agenziaentrate.gov.it/cons/cons-web/?v=' + unixTime(),
               'accept': 'application/json, text/plain, */*',
               'accept-encoding': 'gzip, deflate, br',
               'accept-language': 'it-IT,it;q=0.9,en-US;q=0.8,en;q=0.7,fr;q=0.6',
               'DNT': '1',
               'x-xss-protection': '1; mode=block',
               'strict-transport-security': 'max-age=16070400; includeSubDomains',
               'x-content-type-options': 'nosniff',
               'x-frame-options': 'deny',
               'x-b2bcookie': xb2bcookie,
               'x-token': xtoken,
               'User-Agent': 'Mozilla/5.0 (Windows NT 6.1; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/72.0.3626.119 Safari/537.36'}
    print('Accetto le condizioni')
    r = s.get('https://ivaservizi.agenziaentrate.gov.it/cons/cons-services/rs/disclaimer/accetta?v='+unixTime() , headers = headers_token )
    cookieJar = s.cookies


    if VenOAcq != "V":
        #===============================================================================================
        # FATTURE MESSE A DISPOSIZIONE
        #===============================================================================================
        print('Scarico il json delle fatture ricevute e messe a disposizione per la partita IVA ' + CF)
        r = s.get('https://ivaservizi.agenziaentrate.gov.it/cons/cons-services/rs/fe/mc/dal/'+Dal+'/al/'+Al+'?v=' + unixTime(), headers = headers)
        if r.status_code == 200:
            puts(colored.yellow('Lista ottenuta FATTURE A DISPOSIZIONE. Potrebbe essere vuota!'))
        else:
            puts(colored.red('Lista FATTURE A DISPOSIZIONE non ottenuta: uscita.')) 
            sys.exit()


        with open('fe_ricevute_disposizione_' + CF + '.json', 'wb') as f:
            f.write(r.content)
            print('Inizio a scaricare le fatture ricevute e messe a disposizione!')
        path = r'FatturePassive_' + CF
        if not os.path.exists(path):
            os.makedirs(path)
        with open('fe_ricevute_disposizione_'+ CF +'.json') as data_file:    
            data = json.load(data_file)
            #print('Inizio a scaricare ' + str(data['totaleFatture']) + ' fatture dal ' + data['dataRicercaDa'] + ' al ' + data['dataRicercaA'] + ' per un massimo di ' + str(data['limiteBloccoTotaleFatture']) + ' fatture scaricabili.')#
            numero_fatture_disposizione = 0
            numero_notifiche_disposizione = 0
            for fattura in data['fatture']:
                fatturaFile = fattura['tipoInvio']+fattura['idFattura']
                r = s.get('https://ivaservizi.agenziaentrate.gov.it/cons/cons-services/rs/fatture/file/'+fatturaFile+'?tipoFile=FILE_FATTURA&download=1&v='+unixTime() , headers = headers_token )
                if r.status_code == 200:
                    numero_fatture = numero_fatture + 1
                    d = r.headers['content-disposition']
                    fname = re.findall("filename=(.+)", d)
                    print('Downloading ' + fname[0])
                    print('Totale fatture messe a disposizione scaricate: ', numero_fatture_disposizione)
                    with open(path + '/' + fname[0], 'wb') as f:
                        f.write(r.content)              
        print('Totale fatture messe a disposizione scaricate: ', numero_fatture_disposizione)

        #===============================================================================================
        # FATTURE PASSIVE RICEVUTE
        #===============================================================================================
        if tipo == 1:
        # r = s.get('https://ivaservizi.agenziaentrate.gov.it/ser/api/monitoraggio/v1/monitoraggio/fatture/?v='+unixTime()+'&idFiscCedente=&idFiscDestinatario=&idFiscEmittente=&idFiscTrasmittente=&idSdi=&perPage=10&start=1&statoFile=&tipoFattura=EMESSA')
             print('Scarico il json delle fatture ricevute per data ricezione per la partita IVA ' + CF)
             r = s.get('https://ivaservizi.agenziaentrate.gov.it/cons/cons-services/rs/fe/ricevute/dal/'+Dal+'/al/'+Al+'/ricerca/ricezione?v=' + unixTime(), headers = headers)
        else:     
             print('Scarico il json delle fatture ricevute per data di emissione per la partita IVA ' + CF)
             r = s.get('https://ivaservizi.agenziaentrate.gov.it/cons/cons-services/rs/fe/ricevute/dal/'+Dal+'/al/'+Al+'/ricerca/emissione?v=' + unixTime(), headers = headers)

        with open('fe_ricevute_'+ CF +'.json', 'wb') as f:
            f.write(r.content)
            
        print('Inizio a scaricare le fatture PASSIVE ricevute')
        path = r'FatturePassive_' + CF
        pathp7m = path + '_p7m'
        if not os.path.exists(path):
            os.makedirs(path)
        if not os.path.exists(path):
            os.makedirs(pathp7m)

        with open('fe_ricevute_'+ CF +'.json') as data_file:    
            data = json.load(data_file)
            numero_fatture_ricevute = 0
            numero_notifiche_ricevute = 0
            print('Inizio a scaricare ' + str(data['totaleFatture']) + ' fatture PASSIVE ricevute dal ' + data['dataRicercaDa'] + ' al ' + data['dataRicercaA'] + ' per un massimo di ' + str(data['limiteBloccoTotaleFatture']) + ' fatture scaricabili.')
            for fattura in data['fatture']:
                fatturaFile = fattura['tipoInvio']+fattura['idFattura']
                with s.get('https://ivaservizi.agenziaentrate.gov.it/cons/cons-services/rs/fatture/file/'+fatturaFile+'?tipoFile=FILE_FATTURA&download=1&v='+unixTime(), headers = headers_token , stream = True) as r:
                    if r.status_code == 200:
                        numero_fatture_ricevute = numero_fatture_ricevute + 1
                        r.raise_for_status()
                        total_size = int(r.headers.get('content-length', 0))
                        d = r.headers['content-disposition']
                        fname = re.findall("filename=(.+)", d)
                        with open(path + '/' + fname[0], 'wb') as f:
                            f.write(r.content)
                            fmetadato = re.findall("filename=(.+)", d)
                            with open(path + '/' + fname[0], 'wb') as f:
                                pbar = tqdm(total=total_size, unit='B', unit_divisor=1024, unit_scale=True, ascii=True)
                                pbar.set_description('Scarico la fattura: ' + fname[0])
                                for chunk in r.iter_content(chunk_size=1024):
                                    if chunk:  
                                        f.write(chunk)
                                        pbar.update(len(chunk))
                                pbar.close()
                               
           # decrypt_p7m_files(path, pathp7m)# decodifica fattura p7m e copia in dir p7m
            print('Totale fatture PASSIVE RICEVUTE scaricate: ', numero_fatture_ricevute , ' e notifiche ' , numero_notifiche_ricevute)


    #=============# FATTURE TRANSFRONTALIERE RICEVUTE=======#
        print('Scarico il json delle fatture  Transfrontaliere Ricevute per la Partita IVA ' + CF)
        r = s.get('https://ivaservizi.agenziaentrate.gov.it/cons/cons-services/rs/ft/ricevute/dal/'+Dal+'/al/'+Al+'?v=' + unixTime(), headers = headers)

        with open('fe_ricevutetr_'+ CF +'.json', 'wb') as f:
            f.write(r.content)
            
        print('Inizio a scaricare le fatture transfrontaliere ricevute')
        path = r'FatturePassive_' + CF
        if not os.path.exists(path):
            os.makedirs(path)
        with open('fe_ricevutetr_'+ CF +'.json') as data_file:    
            data = json.load(data_file)
            numero_fatture = 0
            numero_notifiche = 0
            for fattura in data['fatture']:
                fatturaFile = fattura['tipoInvio']+fattura['idFattura']
                r = s.get('https://ivaservizi.agenziaentrate.gov.it/cons/cons-services/rs/fatture/file/'+fatturaFile+'?tipoFile=FILE_FATTURA&download=1&v='+unixTime() , headers = headers_token )
                if r.status_code == 200:
                    numero_fatture = numero_fatture + 1
                    d = r.headers['content-disposition']
                    fname = re.findall("filename=(.+)", d)
                    print('Downloading ' + fname[0])
                    print('Totale Transfrontaliere fatture scaricate: ', numero_fatture)
                    with open(path + '/' + fname[0], 'wb') as f:
                        f.write(r.content)
                        fmetadato = re.findall("filename=(.+)", d)
                r = s.get('https://ivaservizi.agenziaentrate.gov.it/cons/cons-services/rs/fatture/file/'+fatturaFile+'?tipoFile=FILE_METADATI&download=1&v='+unixTime() , headers = headers_token )          
        print('Totale fatture Ricevute TRAN ricevute scaricate: ', numero_fatture)
        print('Totale notifiche scaricate fatture TRAN ricevute: ', numero_notifiche)

        print('Per il cliente: ', CF)
        print('Totale fatture TRANSFRONTALIERE RICEVUTE scaricate: ', numero_fatture)


    # Esegui lo script Rinomina.py alla fine (senza copia in Stampa per questo tipo di download)
    sys.path.append('scripts')
    subprocess.run(['python', 'scripts/rinomina.py', '--no-stampa'], check=True)

except KeyboardInterrupt:
    print("Programma interrotto manualmente!")
except Exception as e:
    print(f"Errore: {str(e)}")
finally:
    sys.exit()