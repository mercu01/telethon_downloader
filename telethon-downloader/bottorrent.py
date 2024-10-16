#!/usr/bin/env python3

VERSION = "VERSION 3.1.11 - Mercu beta 2.2"
HELP = """
/help		: This Screen
/version	: Version  
/sendfiles	: send files found in the /download/sendFiles folder
/id			: YOUR ID TELEGRAM
/t          : Name Folder,Nombre Castellano [Create torrent]
/sonarr     : Serie to search [Search and create torrent]
"""
UPDATE = """
- DE HASTA 2000MB
- DESCARGA DE IMAGENES COMPRESS/UNCOMPRESS
- DESCARGA DE ARCHIVOS TORRENT EN CARPETA TG_DOWNLOAD_PATH_TORRENTS
- DESCARGA DE VIDEOS/LISTAS YOUTUBE.COM Y YOUTU.BE (SOLO ENVIANDO EL LINK DEL VIDEO/LISTA)
- UPLOAD FILES IN /download/sendFiles CON EL COMANDO /sendfiles
"""

import encodings
import re
import os
import shutil
import sys
import time
import asyncio
import threading
import zipfile
import encodings.latin_1
import rarfile

import logging
import configparser
import traceback

import urllib.request
import requests

# Imports Telethon
from telethon import TelegramClient, events
from telethon.tl import types
from telethon.utils import get_extension, get_peer_id, resolve_id
from telethon.tl.custom import Button


from env import *
from logger import logger
from utils import splash, create_directory, getDownloadPath, getUsers, split_input, config_file
from youtube import youtube_download
from createtorrent import CreateTorrentBatchQThread

from sonarr import Serie, sonarr_get_serie, sonarr_search, sonarr_put_serie_tag_uploaded


session = SESSION


download_path = TG_DOWNLOAD_PATH
download_path_torrent = TG_DOWNLOAD_PATH_TORRENTS # Directorio bajo vigilancia de DSDownload u otro.



AUTHORIZED_USER, usuarios = getUsers()
youtube_list = split_input(YOUTUBE_LINKS_SOPORTED) 



queue = asyncio.Queue()
number_of_parallel_downloads = TG_MAX_PARALLEL
maximum_seconds_per_download = TG_DL_TIMEOUT

# Directorio temporal
tmp_path = PATH_TMP
completed_path = PATH_COMPLETED

temp_completed_path = ''

create_directory(tmp_path)
create_directory(completed_path)


FOLDER_GROUP = ''

async def tg_send_message(msg):
    if AUTHORIZED_USER: await client.send_message(usuarios[0], msg)
    return True

async def tg_send_file(CID, file, force_document, caption='', action='document'):
    #await client.send_file(6537360, file)
    async with client.action(CID, action) as action:
        await client.send_file(CID, file,caption=caption, force_document=force_document, progress_callback=action.progress)
    #await client.send_message(6537360, file)

# Printing download progress
async def callback_download(current, total, file_path, file_name, message, _download_path=''):
    global cache_last_time
    global cache_interval
    cache_current_time = time.time()
     # Check if enough time has passed since the last execution
    if cache_current_time - cache_last_time >= cache_interval:
        value = (current / total) * 100
        format_float = "{:.2f}".format(value)
        try:
            await message.edit(f'Downloading {file_name} ... {format_float}% \ndownload in:\n{_download_path}')
        except Exception as e:
            logger.critical(e)
            logger.info('[EXCEPTION Printing download progress]: %s' % (str(e)))
            pass
        finally:
            current
        cache_last_time = cache_current_time
async def decide_format_compresed_firts_file(final_path, file_name, pattern_part, template_part):
    match = re.search(pattern_part, file_name)
    if match:
        # Get the matched part of the text
        matched_part = match.group(0)
        # Find the digits in the matched part
        matched_digits = re.findall(r"\d+", matched_part)
        digits_len = len(matched_digits[0])
        part_1_rar = ''
        if digits_len==4:
            part_1_rar = template_part.replace("XXXX", "0001")
        elif digits_len==3:
            part_1_rar = template_part.replace("XXXX", "001")
        elif digits_len==2:
            part_1_rar = template_part.replace("XXXX", "01")
        else:
            part_1_rar = template_part.replace("XXXX", "1")
        final_path_part1_compressed = re.sub(pattern_part, part_1_rar, final_path)
        mensaje = f'Is part file! decide: {final_path_part1_compressed}'
        logger.info(mensaje)
        return final_path_part1_compressed
    else:
        mensaje = f'Is complete compressed file! decide: {final_path}'
        logger.info(mensaje)
        return final_path
async def unrar(_path, final_path, file_name, end_time, message, pattern_part, template_part, update):
    try:
        mensaje = 'Is RAR compressed file %s [%s] => [%s]' % (end_time, file_name, final_path)
        logger.info(mensaje)
        path_compressed_file = await decide_format_compresed_firts_file(final_path, file_name, pattern_part, template_part)
        
        cmd = f'cd {_path} && unrar x -o+ \'{os.path.basename(path_compressed_file)}\''
        logger.info(cmd)
        end_time_short = time.strftime('%H:%M', time.localtime())
        mensaje = 'Decompressing... %s' % (end_time_short)
        compressed_file = rarfile.RarFile(path_compressed_file)
        files_compressed = compressed_file.namelist()
        # Print rar files
        for file_compressed in files_compressed:
            mensaje += '\n' + file_compressed
        # Close the archive
        compressed_file.close() 
        logger.info(mensaje)
        await message.edit(mensaje)
        proc = await asyncio.create_subprocess_shell(
            cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE)
        # end_time_short = time.strftime('%H:%M', time.localtime())
        # mensaje = 'Decompressing... %s' % (end_time_short)
        # logger.info(mensaje)
        # await message.edit(mensaje)
        # # Extract the contents of the archive
        # compressed_file.extractall(_path)
        stdout, stderr = await proc.communicate()
        end_time_short = time.strftime('%H:%M', time.localtime())
        
        if proc.returncode == 0:
            mensaje = 'Decompressing OK %s [%s]' % (end_time_short, path_compressed_file)
            mensaje = mensaje + '\n' + stdout.decode()
            logger.info(mensaje)
            await message.edit(mensaje)
            time.sleep(5)
            return True
        else:
            mensaje = 'Decompressing KO %s [%s]' % (end_time_short, path_compressed_file)
            mensaje = mensaje + '\n' + stderr.decode()
            logger.info(mensaje)
            await message.edit(mensaje)
            time.sleep(5)
            return False
        end_time_short = time.strftime('%H:%M', time.localtime())
        mensaje = 'Done UNRAR file: '
        
        await update.reply(mensaje)
        return True
    except Exception as e:
        logger.critical(e)
        logger.info('[EXCEPTION]: %s' % (str(e)))
        logger.info('[%s] EXCEPTION RAR %s' % (file_name, time.strftime('%d/%m/%Y %H:%M:%S', time.localtime())))
        return False
async def unzip(_path, final_path, file_name, end_time, message, pattern_part, template_part, update):
    try:
        mensaje = 'Is ZIP compressed file %s [%s] => [%s]' % (end_time, file_name, final_path)
        logger.info(mensaje)
        path_compressed_file = await decide_format_compresed_firts_file(final_path, file_name, pattern_part, template_part)
        end_time_short = time.strftime('%H:%M', time.localtime())
        mensaje = 'Validate compressed file... %s [%s]' % (end_time_short, path_compressed_file)
        logger.info(mensaje)
        await message.edit(mensaje)
        cmd = f'7zz t {path_compressed_file}'
        logger.info(cmd)
        proc = await asyncio.create_subprocess_shell(
            cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE)

        stdout, stderr = await proc.communicate()

        end_time_short = time.strftime('%H:%M', time.localtime())
        if proc.returncode == 0:
            mensaje = 'VALIDATION OK %s [%s]' % (end_time_short, path_compressed_file)
            mensaje = mensaje + '\n' + stdout.decode()
            logger.info(mensaje)
            await message.edit(mensaje)

            end_time_short = time.strftime('%H:%M', time.localtime())
            mensaje = 'Decompressing... %s' % (end_time_short)
            logger.info(mensaje)
            await message.edit(mensaje)
            # Extract the contents of the archive
            cmd = f'cd {_path} && 7zz x {path_compressed_file}'
            logger.info(cmd)
            proc = await asyncio.create_subprocess_shell(
                cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE)

            stdout, stderr = await proc.communicate()
            end_time_short = time.strftime('%H:%M', time.localtime())
           
            if proc.returncode == 0:
                mensaje = 'Decompressing OK %s [%s]' % (end_time_short, path_compressed_file)
                mensaje = mensaje + '\n' + stdout.decode()
                logger.info(mensaje)
                await message.edit(mensaje)
                time.sleep(5)
                return True
            else:
                mensaje = 'Decompressing KO %s [%s]' % (end_time_short, path_compressed_file)
                mensaje = mensaje + '\n' + stderr.decode()
                logger.info(mensaje)
                await message.edit(mensaje)
                time.sleep(5)
                return False
        else: 
            mensaje = 'VALIDATION KO %s [%s]' % (end_time_short, path_compressed_file)
            mensaje = mensaje + '\n' + stderr.decode()
            logger.info(mensaje)
            await message.edit(mensaje)
            return False
    except Exception as e:
        logger.critical(e)
        logger.info('[EXCEPTION]: %s' % (str(e)))
        logger.info('[%s] EXCEPTION ZIP %s' % (file_name, time.strftime('%d/%m/%Y %H:%M:%S', time.localtime())))
        return False

async def delete_compress_files(_path, file_name, pattern_part):
    logger.info('MAINTENANCE - Delete compress files')
    pattern_delete_path = re.sub(pattern_part, "", file_name)
    logger.info(f'Pattern: {pattern_delete_path}')
    files_complete = os.listdir(_path)                
    for file_complete in files_complete:
        if pattern_delete_path in file_complete and re.search(pattern_part, file_complete) :
            file_path_delete = os.path.join(_path, file_complete)  # Ruta completa del archivo
            logger.info(f'DELETE file: {file_path_delete}')
            os.remove(file_path_delete) 

async def downloadImg(command, CID, image, caption):
    localPath="./local-filename.jpg"
    urllib.request.urlretrieve(image, localPath)
    await tg_send_file(CID, localPath, False, caption, 'photo')

DefaultTrackers = """
http://tracker.opentrackr.org:1337/announce

https://www.peckservers.com:9443/announce

udp://tracker2.dler.com:80/announce

udp://tracker.opentrackr.org:1337/announce

udp://93.158.213.92:1337/announce

udp://208.83.20.20:6969/announce

udp://185.102.219.163:6969/announce

udp://102.223.180.235:6969/announce

udp://193.189.100.188:6969/announce

http://tracker.openbittorrent.com/announce

udp://exodus.desync.com:6969/announce

udp://uploads.gamecoast.net:6969/announce

udp://tracker.theoks.net:6969/announce

udp://tracker.ccp.ovh:6969/announce

udp://tracker.bittor.pw:1337/announce

udp://tracker.4.babico.name.tr:3131/announce

udp://thouvenin.cloud:6969/announce

udp://sanincode.com:6969/announce

udp://p4p.arenabg.com:1337/announce

https://tracker.bt4g.com/announce

http://tracker.files.fm:6969/announce

https://www.peckservers.com:9443/announce

udp://tracker.breizh.pm:6969/announce

udp://93.158.213.92:1337/announce

udp://23.134.88.6:1337/announce

udp://185.243.218.213/announce"""

class Trackers: 
    def __init__(self, message, trackers): 
        self.message = message
        self.list = trackers

async def getTrackerList(update):
    message = await update.reply('Getting trackers online...')
    trackers = DefaultTrackers
    url="https://newtrackon.com/api/stable?include_ipv4_only_trackers=true&include_ipv6_only_trackers=false"
    try:
        response = requests.get(url)
        trackers = response.text
    except Exception as e:
        errorMessage = 'ERROR: %s GETTING TRACKERS ONLINE YT: %s' % (e.__class__.__name__, str(e));
        logger.info(errorMessage)
        message = await update.reply(errorMessage)
    return Trackers(message, trackers) 

async def torrent(update, command, CID, image, serie_id):
    commandPartes = command.split(",")
    # Asignar las partes a variables
    pathSerie = '/media/mercu/myUsb14T/Series/'+commandPartes[0].strip()
    nombreCastellano = commandPartes[1].strip()
    excludeEdit = ["*.mp3","tvshow.nfo"]
    save_dir = "/media/mercu/myUsbRAID/Torrent/Created"
    watch_transmission_dir = "/media/mercu/myUsbRAID/Torrent/WatchTransmission"
    trackers = await getTrackerList(update)
    message = trackers.message
    message = await update.reply('Creating torrents...')
    createdTorrents = await CreateTorrentBatchQThread(
        update,
        path=pathSerie,
        exclude=excludeEdit,
        save_dir=save_dir,
        trackers=trackers.list.strip().split(),
        web_seeds="",
        private=False,
        source="",
        comment=nombreCastellano,
        include_md5=True,
        batchModeCheckBox=True
    )
    message = await update.reply('Sending to transmission')
    for fileNamePath in createdTorrents:
        shutil.copy(os.path.join(save_dir, fileNamePath), os.path.join(watch_transmission_dir, fileNamePath))
    
    message = await update.reply('Add sonarr tag uploaded')
    if serie_id != 0:
        await sonarr_put_serie_tag_uploaded(serie_id)

    await tg_send_message("---Resume torrents---")
    #await update.reply("---Resume torrents---")
    firtsFile = True
    for fileNamePath in createdTorrents:
        if firtsFile == True:
            firtsFile = False
            if image != "":
                await downloadImg(command, CID, image, fileNamePath)
            else:
                await tg_send_message(fileNamePath)
        else:
            await tg_send_message(fileNamePath)
        
        #await update.reply(fileNamePath)
        await tg_send_file(CID,os.path.join(save_dir, fileNamePath), True)

async def worker(name):
    while True:
        # Variables for control calls to progress bar
        global cache_last_time
        cache_last_time = time.time()
        global cache_interval
        cache_interval = TG_MAX_PARALLEL*3  # 2 second X parallel proccess, Telegram limit 1 message every second

        queue_item = await queue.get()
        update = queue_item[0]
        message = queue_item[1]
        FOLDER_TO_GROUP = queue_item[2] if queue_item[2] else ''

        real_id = get_peer_id(update.message.peer_id)
        CID , peer_type = resolve_id(real_id)
        sender = await update.get_sender()
        username = sender.username

        if AUTHORIZED_USER and CID not in usuarios:
            logger.info('USUARIO: %s NO AUTORIZADO', CID)
            continue
        ###
        file_path = tmp_path
        file_name = 'FILENAME'
        if isinstance(update.message.media, types.MessageMediaPhoto):
            file_name = '{}{}'.format(update.message.media.photo.id, get_extension(update.message.media))
        elif any(x in update.message.message for x in youtube_list):
            try:
                url = update.message.message
                
                logger.info(f'INIT DOWNLOADING VIDEO YOUTUBE [{url}] ')
                loop = asyncio.get_event_loop()
                task = loop.create_task(youtube_download(url,update,message))
                download_result = await asyncio.wait_for(task, timeout = YT_DL_TIMEOUT)
                logger.info(f'FINIT DOWNLOADING VIDEO YOUTUBE [{url}] [{download_result}] ')
                queue.task_done()
                continue
            except Exception as e:
                logger.info('ERROR: %s DOWNLOADING YT: %s' % (e.__class__.__name__, str(e)))
                await message.edit('Error!')
                message = await message.edit('ERROR: %s DOWNLOADING YT: %s' % (e.__class__.__name__, str(e)))
                queue.task_done()
                continue
        else:
            attributes = update.message.media.document.attributes
            for attr in attributes:
                if isinstance(attr, types.DocumentAttributeFilename):
                    file_name = attr.file_name
                elif update.message.message:
                    file_name = re.sub(r'[^A-Za-z0-9 -!\[\]\(\)]+', ' ', update.message.message)
                else:
                    file_name = time.strftime('%Y%m%d %H%M%S', time.localtime())
                    file_name = '{}{}'.format(update.message.media.document.id, get_extension(update.message.media))
        file_path = os.path.join(file_path, file_name)
        _download_path, _complete_path = getDownloadPath(file_name,CID)
        logger.info(f"getDownloadPath FILE [{file_name}] to [{_download_path}]")
        await message.edit(f'Downloading {file_name} \ndownload in:\n{_download_path}')
        #time.sleep(1)
        logger.info('Downloading... ')
        mensaje = 'STARTING DOWNLOADING %s [%s] BY [%s]' % (time.strftime('%d/%m/%Y %H:%M:%S', time.localtime()), file_path , (CID))
        logger.info(mensaje)
        try:
            loop = asyncio.get_event_loop()
            if (TG_PROGRESS_DOWNLOAD == True or TG_PROGRESS_DOWNLOAD == 'True' ):
                task = loop.create_task(client.download_media(update.message, file_path, progress_callback=lambda x,y: callback_download(x,y,file_path,file_name,message, _download_path)))
            else:
                task = loop.create_task(client.download_media(update.message, file_path))
            download_result = await asyncio.wait_for(task, timeout = maximum_seconds_per_download)
            end_time = time.strftime('%d/%m/%Y %H:%M:%S', time.localtime())
            end_time_short = time.strftime('%H:%M', time.localtime())
            filename = os.path.split(download_result)[1]
            
            if FOLDER_TO_GROUP:
                final_path = os.path.join(FOLDER_TO_GROUP, filename)
                create_directory(FOLDER_TO_GROUP)
                os.chmod(FOLDER_TO_GROUP, 0o777)
            else:
                _path, final_path = getDownloadPath(filename,CID)
                create_directory(_path)
            ######
            logger.info("RENAME/MOVE [%s] [%s]" % (download_result, final_path) )
            #create_directory(completed_path)
            shutil.move(download_result, final_path)
            os.chmod(final_path, 0o777)
            if TG_UNZIP_TORRENTS:
                if zipfile.is_zipfile(final_path):
                    with zipfile.ZipFile(final_path, 'r') as zipObj:
                        for fileName in zipObj.namelist():
                            if fileName.endswith('.torrent'):
                                zipObj.extract(fileName, download_path_torrent)
                                logger.info("UNZIP TORRENTS [%s] to [%s]" % (fileName, download_path_torrent) )
            # UNRAR
            logger.info('rar')
            pattern_part = r"part\d{1,4}\.rar"
            template_part = r"partXXXX.rar"
            if rarfile.is_rarfile(final_path):
                unrar_result = await unrar(_path, final_path, file_name, end_time, message, pattern_part, template_part, update)
                if unrar_result:
                    await delete_compress_files(_path, file_name, pattern_part)
            # ZIP
            logger.info('zip')
            pattern_part = r"zip\.\d{1,4}"
            pattern_complete = r"\.zip"
            template_part = r"zip.XXXX"
            if re.search(pattern_part, file_name) or re.search(pattern_complete, file_name):
                logger.info('zip1')
                unzip_result = await unzip(_path, final_path, file_name, end_time, message, pattern_part, template_part, update)
                logger.info('zip2')
                if unzip_result:
                    logger.info('zip3')
                    await delete_compress_files(_path, file_name, pattern_part)
                 
            ######
            mensaje = 'DOWNLOAD FINISHED %s [%s] => [%s]' % (end_time, file_name, final_path)
            logger.info(mensaje)
            await message.edit('Downloading finished:\n%s \nIN: %s\nat %s' % (file_name,_path,end_time_short))
        except asyncio.TimeoutError:
            logger.info('[%s] Time exceeded %s' % (file_name, time.strftime('%d/%m/%Y %H:%M:%S', time.localtime())))
            await message.edit('Error!')
            message = await update.reply('ERROR: Time exceeded downloading this file')
        except Exception as e:
            logger.critical(e)
            logger.info('[EXCEPCION]: %s' % (str(e)))
            logger.info('[%s] Excepcion %s' % (file_name, time.strftime('%d/%m/%Y %H:%M:%S', time.localtime())))
            await message.edit('Error!')
            message = await update.reply('ERROR: %s downloading : %s' % (e.__class__.__name__, str(e)))
            
        # Unidad de trabajo terminada.
        queue.task_done()

client = TelegramClient(session, api_id, api_hash, proxy = None, request_retries = 10, flood_sleep_threshold = 120)
# Callback data

ONE = "telethonresponseone_"
TWO = "telethonresponsetwo_"
serie = Serie(0, "", "", "")
#ONE Buttons Results search:
@client.on(events.CallbackQuery(pattern="^"+ONE))
async def callback(event):
    id = event.data.decode(encoding='utf-8').replace(ONE, "")
    await event.edit('Getting serie id: ''{}'''.format(id))
    result = await sonarr_get_serie(id)
    serie.id=result.id;
    serie.path=result.path;
    serie.names=result.names;
    serie.image=result.image;
    if len(serie.names)==1:
        # Fix: Path is better than name, because name contains forbiden characters 
        await createTorrentAfterQuestions(serie.path)
        return True

    buttons = [
        [Button.inline(text = serie.names[i], data = TWO + str(i))] for i in range(1,len(serie.names))
    ]
    await client.send_message(usuarios[0], 'Choose spanish title:', buttons = buttons)
    return True

#TWO Buttons choose spanish title:
@client.on(events.CallbackQuery(pattern="^"+TWO))
async def callback(event):
    serieTitlePosition = event.data.decode(encoding='utf-8').replace(TWO, "")
    spanishTitle = serie.names[int(serieTitlePosition)]
    await event.edit('Chose: ''{}'''.format(spanishTitle))
    await createTorrentAfterQuestions(spanishTitle)
    return True
    
async def createTorrentAfterQuestions(spanishTitle):
    commandValue = serie.path + "," + spanishTitle
    message = await client.send_message(usuarios[0], "/t " + commandValue)
    try:
        real_id = get_peer_id(message.peer_id)
        CID , peer_type = resolve_id(real_id)
        await torrent(message, commandValue, CID, serie.image, serie.id)
    except Exception as e:
        message = await message.reply('ERROR: ' + str(e) + "\n" + str(traceback.print_exc()))
        logger.info('EXCEPTION USER: %s %s', str(e), str(traceback.print_exc()))
    return True

@events.register(events.NewMessage)
async def handler(update):
    global temp_completed_path
    global FOLDER_GROUP
    try:

        real_id = get_peer_id(update.message.peer_id)
        CID , peer_type = resolve_id(real_id)

        if update.message.from_id is not None:
            logger.info("USER ON GROUP => U:[%s]G:[%s]M:[%s]" % (update.message.from_id.user_id,CID,update.message.message))

        if update.message.media is not None and ( not AUTHORIZED_USER or CID in usuarios):
            if FOLDER_GROUP != update.message.date:
                logger.info("FOLDER_GROUP => [%s][%s][%s]" % (FOLDER_GROUP,update.message.date,temp_completed_path))
                temp_completed_path  = ''

        if update.message.media is not None and ( not AUTHORIZED_USER or CID in usuarios):
            file_name = 'NONAME'

            if isinstance(update.message.media, types.MessageMediaPhoto):
                file_name = '{}{}'.format(update.message.media.photo.id, get_extension(update.message.media))
                logger.info("MessageMediaPhoto  [%s]" % file_name)
            elif any(x in update.message.message for x in youtube_list):
                file_name = 'YOUTUBE VIDEO'
            else:	
                attributes = update.message.media.document.attributes
                for attr in attributes:
                    if isinstance(attr, types.DocumentAttributeFilename):
                        file_name = attr.file_name
                    elif update.message.message:
                        file_name = re.sub(r'[^A-Za-z0-9 -!\[\]\(\)]+', ' ', update.message.message)

            mensaje = 'DOWNLOAD IN QUEUE [%s] [%s] => [%s]' % (time.strftime('%d/%m/%Y %H:%M:%S', time.localtime()),file_name,temp_completed_path)
            logger.info(mensaje)
            message = await update.reply('Download in queue...')
            await queue.put([update, message,temp_completed_path])
        elif not AUTHORIZED_USER or CID in usuarios:
            if update.message.message == '/help':
                message = await update.reply(HELP) 
                await queue.put([update, message])
            elif update.message.message == '/version': 
                message = await update.reply(VERSION)
                await queue.put([update, message,temp_completed_path])
            elif update.message.message == '/alive': 
                message = await update.reply('Keep-Alive')
                await queue.put([update, message,temp_completed_path])
            elif update.message.message == '/me' or update.message.message == '/id': 
                message = await update.reply('id: {}'.format(CID) )
                await queue.put([update, message,temp_completed_path])
                logger.info('me :[%s]' % (CID))
            else: 
                time.sleep(2)
                if update.message.message.startswith("/t"):
                    command = update.message.message.replace("/t ", "")
                    torrent(update, command, CID, "", 0)
                elif update.message.message.startswith("/sonarr"):
                    command = update.message.message.replace("/sonarr ", "")
                    series = await sonarr_search(command, client, usuarios)
                    if series.__len__==0:
                        await tg_send_message("Not found")
                        return True
                    buttons = [
                        [Button.inline(text = serie._name, data = str(ONE)+str(serie.id))] for serie in series
                    ]      

                    await client.send_message(usuarios[0], 'Search results:', buttons = buttons)
                elif '/folder' in update.message.message:
                    folder = update.message.message
                    FOLDER_GROUP = update.message.date
                    temp_completed_path  = os.path.join(TG_DOWNLOAD_PATH,'completed',folder.replace('/folder ','')) # SI VIENE EL TEXTO '/folder NAME_FOLDER' ESTE CREARÁ UNA CARPETA Y METERÁ ADENTRO TODOS LOS ARCHIVOS A CONTINUACION 
                    logger.info("DOWNLOAD FILE IN :[%s]",temp_completed_path)
                elif ((update.message.message).startswith('/sendfiles')):
                    msg = await update.reply('Sending files...')
                    create_directory(os.path.join(download_path,'sendFiles'))
                    ignored = {"*._process"}
                    basepath = os.path.join(download_path,'sendFiles')
                    sending = 0
                    for root, subFolder, files in os.walk(basepath):
                        subFolder.sort()
                        files.sort()
                        for item in files:
                            if item.endswith('_process') :
                                #skip directories
                                continue
                            sending +=1
                            fileNamePath = str(os.path.join(root,item))
                            logger.info("SEND FILE :[%s]", fileNamePath)
                            await msg.edit('Sending {}...'.format(item))
                            loop = asyncio.get_event_loop()
                            task = loop.create_task(tg_send_file(CID,fileNamePath,item))
                            download_result = await asyncio.wait_for(task, timeout = maximum_seconds_per_download)
                            #message = await tg_send_file(fileNamePath)
                            shutil.move(fileNamePath, fileNamePath + "_process")
                    await msg.edit('{} files submitted'.format(sending))
                    logger.info("FILES SUBMITTED:[%s]", sending)
                elif ((update.message.message).startswith('#')):
                    folder = update.message.message
                    FOLDER_GROUP = update.message.date
                    temp_completed_path  = os.path.join(TG_DOWNLOAD_PATH,'completed',folder.replace('#','')) # SI VIENE EL TEXTO '/folder NAME_FOLDER' ESTE CREARÁ UNA CARPETA Y METERÁ ADENTRO TODOS LOS ARCHIVOS A CONTINUACION 
                    logger.info("DOWNLOAD FILE IN :[%s]",temp_completed_path)

        elif update.message.message == '/me' or update.message.message == '/id':
            logger.info('UNAUTHORIZED USER: %s ', CID)
            message = await update.reply('UNAUTHORIZED USER: %s \n add this ID to TG_AUTHORIZED_USER_ID' % CID)
    except Exception as e:
        message = await update.reply('ERROR: ' + str(e) + "\n" + str(traceback.print_exc()))
        logger.info('EXCEPTION USER: %s %s', str(e), str(traceback.print_exc()))





if __name__ == '__main__':

    try:

        # Crear cola de procesos concurrentes.
        tasks = []
        for i in range(number_of_parallel_downloads):
            loop = asyncio.get_event_loop()
            task = loop.create_task(worker('worker-{%i}' %i))
            tasks.append(task)

        # Arrancamos bot con token
        client.start(bot_token=str(bot_token))
        client.add_event_handler(handler)
        

        # Pulsa Ctrl+C para detener
        loop.run_until_complete(tg_send_message("Telethon Downloader Started: {}".format(VERSION)+ HELP))
        logger.info("%s" % VERSION)
        config_file()
        logger.info("********** START TELETHON DOWNLOADER **********")

        client.run_until_disconnected()
    finally:
        # Cerrando trabajos.
        
    #f.close()
        for task in tasks:
            task.cancel()
        # Cola cerrada
        # Stop Telethon
        client.disconnect()
        logger.info("********** STOPPED **********")
    
