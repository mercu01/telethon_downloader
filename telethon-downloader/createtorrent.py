#!/usr/bin/env python3

import json
import os
import re
import sys
import fnmatch
# import dottorrent
import math
from base64 import b32encode
from collections import OrderedDict
from datetime import datetime
from hashlib import sha1, md5
from urllib.parse import urlparse
from pathlib import Path
from typing import Union

from bencoder import bencode


# import humanfriendly

# from PyQt5 import QtCore, QtGui, QtWidgets

# from dottorrentGUI import Ui_AboutDialog, Ui_MainWindow, __version__


PROGRAM_NAME = "dottorrent-gui"
# PROGRAM_NAME_VERSION = "{} {}".format(PROGRAM_NAME, __version__)
CREATOR = "mercu"

PIECE_SIZES = [None] + [2 ** i for i in range(14, 27)]

if getattr(sys, 'frozen', False):
    _basedir = sys._MEIPASS
else:
    _basedir = os.path.dirname(__file__)


# class CreateTorrentQThread(QtCore.QThread):

    # progress_update = QtCore.pyqtSignal(str, int, int)
    # onError = QtCore.pyqtSignal(str)

    # def __init__(self, torrent, save_path, path):
    #     super().__init__()
    #     self.torrent = torrent
    #     self.save_path = save_path
    #     self.path = path

    # def run(self):
    #     def progress_callback(*args):
    #         self.progress_update.emit(*args)
    #         return self.isInterruptionRequested()
    #     def callback(*args):
    #         return self.isInterruptionRequested()
    #     for i, p in enumerate(self.path.split(";")):
    #         if (p!=''):
    #             name_parent=os.path.basename(os.path.normpath(p))
    #             titulo=name_parent
                
    #             ruta_sin_nombre = os.path.dirname(self.save_path)
    #             ruta_completa = os.path.join(ruta_sin_nombre, titulo+".torrent")
            
    #             self.torrent.name=titulo
    #             self.progress_update.emit(titulo+".torrent", i, self.path.split(";"))
    #             # try:
    #             #     self.success = self.torrent.generate(callback=progress_callback)
    #             # except Exception as exc:
    #             #     self.onError.emit(str(exc))
    #             #     return
    #             # if self.success:
    #             #     with open(self.save_path, 'wb') as f:
    #             #         self.torrent.save(f)
    #             t = Torrent(
    #                     titulo+".torrent",
    #                     p,
    #                     trackers=self.torrent.trackers,
    #                     web_seeds=self.torrent.web_seeds,
    #                     private=self.torrent.private,
    #                     source=self.torrent.source,
    #                     comment=titulo,
    #                     include_md5=self.torrent.include_md5,
    #                     creation_date=datetime.now(),
    #                     created_by=CREATOR
    #                 )
    #             try:
    #                 self.success = t.generate(callback=callback)
    #             # ignore empty inputs
    #             except EmptyInputException:
    #                 continue
    #             except Exception as exc:
    #                 self.onError.emit(str(exc))
    #                 return
    #             if self.isInterruptionRequested():
    #                 return
    #             if self.success:
    #                 with open(ruta_completa, 'wb') as f:
    #                     t.save(f)

async def CreateTorrentBatchQThread(update, path, exclude, save_dir, trackers, web_seeds,
                 private, source, comment, include_md5, batchModeCheckBox):

# class CreateTorrentBatchQThread(QtCore.QThread):

#     progress_update = QtCore.pyqtSignal(str, int, int)
#     onError = QtCore.pyqtSignal(str)

#     def __init__(self, path, exclude, save_dir, trackers, web_seeds,
#                  private, source, comment, include_md5, batchModeCheckBox):
#         super().__init__()
#         self.path = path
#         self.exclude = exclude
#         self.save_dir = save_dir
#         self.trackers = trackers
#         self.web_seeds = web_seeds
#         self.private = private
#         self.source = source
#         self.comment = comment
#         self.include_md5 = include_md5
#         self.batchModeCheckBox = batchModeCheckBox

#     def run(self):
#         def callback(*args):
#             return self.isInterruptionRequested()
    createdTorrents = []
    for parent_i, parent_p in enumerate(path.split(";")):
        if (parent_p!=''):
            if(batchModeCheckBox):
                entries = os.listdir(parent_p)
            else:
                entries=[]
                entries.append(parent_p)
                parte_principal, ultimo_directorio = os.path.split(parent_p)
                parent_p=parte_principal
            filtered_entries = [p for p in entries if not any(fnmatch.fnmatch(p, ex) for ex in exclude)]
            name_parent=os.path.basename(os.path.normpath(parent_p));
            for i, p in enumerate(filtered_entries):
                p = os.path.join(parent_p, p)
                if not is_hidden_file(p):
                    numero = re.findall(r'\d+', os.path.split(p)[1])[0]
                    numero_formateado = numero.zfill(2)
                    
                    prioridades = [
                        ("SDTV", 10),
                        ("DVD", 20),
                        ("HDTV-720p", 30),
                        ("WEBDL-720p", 40),
                        ("Bluray-720p", 50),
                        ("Bluray-1080p", 60),
                        ("WEBDL-480p", 70),
                        ("HDTV-1080p", 80),
                        ("Raw-HD", 90),
                        ("WEBRip-480p", 100),
                        ("Bluray-480p",110),
                        ("WEBRip-720p", 120),
                        ("WEBRip-1080p", 120),
                        ("WEBDL-1080p", 140),
                        ("HDTV-2160p", 150),
                        ("WEBRip-2160p", 160),
                        ("WEBDL-2160p", 170),
                        ("Bluray-2160p", 180),
                        ("Bluray-1080p Remux", 190),
                        ("Bluray-2160p Remux", 200),
                    ]
                    calidad_prioridad = -1
                    archivo_calidad = "Unknown"
                    for archivo in os.listdir(p):
                        for calidad, prioridad in prioridades:
                            if calidad in archivo and prioridad > calidad_prioridad:
                                archivo_calidad = calidad
                                calidad_prioridad = prioridad
                        
                    if comment!="":
                        titulo=comment
                    else:
                        titulo=name_parent
                    # nameFolder = titulo + ' S' + numero_formateado + ' - Temporada ' + numero + ' ['+archivo_calidad+'][Castellano] ' + name_parent  + ' Season ' + numero + ' - Spanish' 
                    # sfn = titulo + ' S' + numero_formateado + ' - Temporada ' + numero + ' ['+archivo_calidad+'][Castellano] ' + name_parent + ' - Spanish' + '.torrent'
                    nameFolder = titulo + ' S' + numero_formateado + ' - Temporada ' + numero + ' ['+archivo_calidad+'][Castellano] ' + name_parent  + ' - Season ' + numero + ' - Spanish' 
                    sfn = nameFolder+ '.torrent'
                    destinoAccesoDirecto="/media/mercu/myUsb14T/symlinks"
                    # Create symlink - FOLDER
                    if not os.path.exists(destinoAccesoDirecto + '/' +  nameFolder):
                        await update.reply("Creating, symlink")
                        relative_symlink(p, destinoAccesoDirecto + '/' +  nameFolder)
                    else:
                        await update.reply("Omitting, symlink exist in:" +  destinoAccesoDirecto + '/' +  nameFolder)
                    if not os.path.exists(os.path.join(save_dir, sfn)):
                        await update.reply("Creating, torrent " + sfn + " " + str(i+1) + "/" + str(len(filtered_entries)))
                        t = Torrent(
                            nameFolder,
                            p,
                            exclude=exclude,
                            trackers=trackers,
                            web_seeds=web_seeds,
                            private=private,
                            source=source,
                            comment=nameFolder,
                            include_md5=include_md5,
                            creation_date=datetime.now(),
                            created_by=CREATOR
                        )
                        try:
                            success = t.generate()
                        # ignore empty inputs
                        except EmptyInputException:
                            await update.reply("EmptyInputException")
                            continue
                        except Exception as exc:
                            await update.reply("Peta en generate: " + str(exc))
                            return
                        if success:
                            await update.reply("Creation torrent success")
                            createdTorrents.append(sfn)
                            with open(os.path.join(save_dir, sfn), 'wb') as f:
                                t.save(f)
                    else:
                        await update.reply("Omitting, torrent exist in:" + os.path.join(save_dir, sfn) + " " + str(i+1) + "/" + str(len(filtered_entries)))
                        createdTorrents.append(sfn)
    return createdTorrents
class EmptyInputException(Exception):
    def __init__(self, *args, **kwargs):
        super().__init__('Input path must be non-empty')

MIN_PIECE_SIZE = 2 ** 14
MAX_PIECE_SIZE = 2 ** 26
if sys.version_info >= (3, 5) and os.name == 'nt':
    import stat

    def is_hidden_file(path):
        fn = path.split(os.sep)[-1]
        return fn.startswith('.') or \
            bool(os.stat(path).st_file_attributes &
                 stat.FILE_ATTRIBUTE_HIDDEN)
else:
    def is_hidden_file(path):
        fn = path.split(os.sep)[-1]
        return fn.startswith('.')

def relative_symlink(target: Union[Path, str], destination: Union[Path, str]):
    """Create a symlink pointing to ``target`` from ``location``.
    Args:
        target: The target of the symlink (the file/directory that is pointed to)
        destination: The location of the symlink itself.
    """
    target = Path(target)
    destination = Path(destination)
    target_dir = destination.parent
    target_dir.mkdir(exist_ok=True, parents=True)
    relative_source = os.path.relpath(target, target_dir)
    dir_fd = os.open(str(target_dir.absolute()), os.O_RDONLY)
    print(f"{relative_source} -> {destination.name} in {target_dir}")
    try:
        os.symlink(relative_source, destination.name, dir_fd=dir_fd)
    finally:
        os.close(dir_fd)
def print_err(v):
    print(v, file=sys.stderr)
class InvalidURLException(Exception):
    def __init__(self, message="URL no válida"):
        self.message = "InvalidURLException "+message
        super().__init__(self.message)
class InvalidInputException(Exception):
    def __init__(self, message):
        self.message = "InvalidInputException "+message
        super().__init__(self.message)
class InvalidPieceSizeException(Exception):
    def __init__(self, message):
        self.message = "InvalidPieceSizeException "+message
        super().__init__(self.message)
class EmptyInputException(Exception):
    def __init__(self, message="input vacio"):
        self.message = "EmptyInputException "+message
        super().__init__(self.message)
class TorrentNotGeneratedException(Exception):
    def __init__(self, message="Torrent no generado"):
        self.message = "TorrentNotGeneratedException "+message
        super().__init__(self.message)

class Torrent(object):

    def __init__(self, name, path, trackers=None, web_seeds=None,
                 piece_size=None, private=False, source=None,
                 creation_date=None, comment=None, created_by=None,
                 include_md5=False, exclude=None):
        """
        :param name: name torrent
        :param path: path to a file or directory from which to create the torrent
        :param trackers: list/iterable of tracker URLs
        :param web_seeds: list/iterable of HTTP/FTP seed URLs
        :param piece_size: Piece size in bytes. Must be >= 16 KB and a power of 2.
            If None, ``get_info()`` will be used to automatically select a piece size.
        :param private: The private flag. If True, DHT/PEX will be disabled.
        :param source: An optional source string for the torrent.
        :param exclude: A list of filename patterns that should be excluded from the torrent.
        :param creation_date: An optional datetime object representing the torrent creation date.
        :param comment: An optional comment string for the torrent.
        :param created_by: name/version of the program used to create the .torrent.
            If None, defaults to the value of ``DEFAULT_CREATOR``.
        :param include_md5: If True, also computes and stores MD5 hashes for each file.
        """
        self.name = name
        self.path = os.path.normpath(path)
        self.trackers = trackers
        self.web_seeds = web_seeds
        self.piece_size = piece_size
        self.private = private
        self.source = source
        self.exclude = [] if exclude is None else exclude
        self.creation_date = creation_date
        self.comment = comment
        self.created_by = created_by
        self.include_md5 = include_md5

        self._data = None

    @property
    def trackers(self):
        return self._trackers

    @trackers.setter
    def trackers(self, value):
        tl = []
        if value:
            for t in value:
                pr = urlparse(t)
                if pr.scheme and pr.netloc:
                    tl.append(t)
                else:
                    raise InvalidURLException("trackers setter:"+t)
        self._trackers = tl

    @property
    def web_seeds(self):
        return self._web_seeds

    @web_seeds.setter
    def web_seeds(self, value):
        tl = []
        if value:
            for t in value:
                pr = urlparse(t)
                if pr.scheme and pr.netloc:
                    tl.append(t)
                else:
                    raise InvalidURLException("web_seeds setter:"+t)
        self._web_seeds = tl

    @property
    def piece_size(self):
        return self._piece_size

    @piece_size.setter
    def piece_size(self, value):
        if value:
            value = int(value)
            if value > 0 and (value & (value-1) == 0):
                if value < MIN_PIECE_SIZE:
                    raise InvalidPieceSizeException(
                        "Piece size should be at least 16 KiB")
                if value > MAX_PIECE_SIZE:
                    print_err("Warning: piece size is greater than 64 MiB")
                self._piece_size = value
            else:
                raise InvalidPieceSizeException(
                    "Piece size must be a power of 2 bytes")
        else:
            self._piece_size = None

    def get_info(self):
        """
        Scans the input path and automatically determines the optimal
        piece size based on ~1500 pieces (up to MAX_PIECE_SIZE) along
        with other basic info, including total size (in bytes), the
        total number of files, piece size (in bytes), and resulting
        number of pieces. If ``piece_size`` has already been set, the
        custom value will be used instead.

        :return: ``(total_size, total_files, piece_size, num_pieces)``
        """
        if os.path.isfile(self.path):
            total_size = os.path.getsize(self.path)
            total_files = 1
        elif os.path.exists(self.path):
            total_size = 0
            total_files = 0
            for x in os.walk(self.path):
                for fn in x[2]:
                    if any(fnmatch.fnmatch(fn, ext) for ext in self.exclude):
                        continue
                    fpath = os.path.normpath(os.path.join(x[0], fn))
                    fsize = os.path.getsize(fpath)
                    if fsize and not is_hidden_file(fpath):
                        total_size += fsize
                        total_files += 1
        else:
            raise InvalidInputException("a Input de entrada invalido")
        if not (total_files and total_size):
            raise EmptyInputException()
        if self.piece_size:
            ps = self.piece_size
        else:
            ps = 1 << max(0, math.ceil(math.log(total_size / 1500, 2)))
            if ps < MIN_PIECE_SIZE:
                ps = MIN_PIECE_SIZE
            if ps > MAX_PIECE_SIZE:
                ps = MAX_PIECE_SIZE
        return (total_size, total_files, ps, math.ceil(total_size / ps))

    def generate(self):
        """
        Computes and stores piece data. Returns ``True`` on success, ``False``
        otherwise.

        :param callback: progress/cancellation callable with method
            signature ``(filename, pieces_completed, pieces_total)``.
            Useful for reporting progress if dottorrent is used in a
            GUI/threaded context, and if torrent generation needs to be cancelled.
            The callable's return value should evaluate to ``True`` to trigger
            cancellation.
        """
        files = []
        single_file = os.path.isfile(self.path)
        if single_file:
            files.append((self.path, os.path.getsize(self.path), {}))
        elif os.path.exists(self.path):
            for x in os.walk(self.path):
                for fn in x[2]:
                    if any(fnmatch.fnmatch(fn, ext) for ext in self.exclude):
                        continue
                    fpath = os.path.normpath(os.path.join(x[0], fn))
                    fsize = os.path.getsize(fpath)
                    if fsize and not is_hidden_file(fpath):
                        files.append((fpath, fsize, {}))
        else:
            raise InvalidInputException("b Input de entrada invalido")
        total_size = sum([x[1] for x in files])
        if not (len(files) and total_size):
            raise EmptyInputException()
        # set piece size if not already set
        if self.piece_size is None:
            self.piece_size = self.get_info()[2]
        if files:
            self._pieces = bytearray()
            i = 0
            num_pieces = math.ceil(total_size / self.piece_size)
            pc = 0
            buf = bytearray()
            while i < len(files):
                fe = files[i]
                f = open(fe[0], 'rb')
                if self.include_md5:
                    md5_hasher = md5()
                else:
                    md5_hasher = None
                for chunk in iter(lambda: f.read(self.piece_size), b''):
                    buf += chunk
                    if len(buf) >= self.piece_size \
                            or i == len(files)-1:
                        piece = buf[:self.piece_size]
                        self._pieces += sha1(piece).digest()
                        del buf[:self.piece_size]
                        pc += 1
                    if self.include_md5:
                        md5_hasher.update(chunk)
                if self.include_md5:
                    fe[2]['md5sum'] = md5_hasher.hexdigest()
                f.close()
                i += 1
            # Add pieces from any remaining data
            while len(buf):
                piece = buf[:self.piece_size]
                self._pieces += sha1(piece).digest()
                del buf[:self.piece_size]
                pc += 1

        # Create the torrent data structure
        data = OrderedDict()
        if len(self.trackers) > 0:
            data['announce'] = self.trackers[0].encode()
            if len(self.trackers) > 1:
                data['announce-list'] = [[x.encode()] for x in self.trackers]
        if self.comment:
            data['comment'] = self.comment.encode()
        if self.created_by:
            data['created by'] = self.created_by.encode()
        else:
            data['created by'] = DEFAULT_CREATOR.encode()
        if self.creation_date:
            data['creation date'] = int(self.creation_date.timestamp())
        if self.web_seeds:
            data['url-list'] = [x.encode() for x in self.web_seeds]
        data['info'] = OrderedDict()
        if single_file:
            data['info']['length'] = files[0][1]
            if self.include_md5:
                data['info']['md5sum'] = files[0][2]['md5sum']
            data['info']['name'] = files[0][0].split(os.sep)[-1].encode()
        else:
            data['info']['files'] = []
            path_sp = self.path.split(os.sep)
            for x in files:
                fx = OrderedDict()
                fx['length'] = x[1]
                if self.include_md5:
                    fx['md5sum'] = x[2]['md5sum']
                fx['path'] = [y.encode()
                              for y in x[0].split(os.sep)[len(path_sp):]]
                data['info']['files'].append(fx)
            if (self.name!=""):
                data['info']['name'] = self.name.encode()
            else:
                data['info']['name'] = path_sp[-1].encode()
        data['info']['pieces'] = bytes(self._pieces)
        data['info']['piece length'] = self.piece_size
        data['info']['private'] = int(self.private)
        if self.source:
            data['info']['source'] = self.source.encode()

        self._data = data
        return True

    @property
    def data(self):
        """
        Returns the data dictionary for the torrent.

        .. note:: ``generate()`` must be called first.
        """
    
        if self._data:
            return self._data
        else:
            raise TorrentNotGeneratedException()

    @property
    def info_hash_base32(self):
        """
        Returns the base32 info hash of the torrent. Useful for generating
        magnet links.

        .. note:: ``generate()`` must be called first.
        """
        if getattr(self, '_data', None):
            return b32encode(sha1(bencode(self._data['info'])).digest())
        else:
            raise TorrentNotGeneratedException()

    @property
    def info_hash(self):
        """
        :return: The SHA-1 info hash of the torrent. Useful for generating
            magnet links.

        .. note:: ``generate()`` must be called first.
        """
        if getattr(self, '_data', None):
            return sha1(bencode(self._data['info'])).hexdigest()
        else:
            raise TorrentNotGeneratedException()

    def dump(self):
        """
        :return: The bencoded torrent data as a byte string.

        .. note:: ``generate()`` must be called first.
        """
        if getattr(self, '_data', None):

            return bencode(self._data)
        else:
            raise TorrentNotGeneratedException()

    def save(self, fp):
        """
        Saves the torrent to ``fp``, a file(-like) object
        opened in binary writing (``wb``) mode.

        .. note:: ``generate()`` must be called first.
        """
        fp.write(self.dump())

# class DottorrentGUI(Ui_MainWindow):

#     def setupUi(self, MainWindow):
#         super().setupUi(MainWindow)

#         self.torrent = None
#         self.MainWindow = MainWindow

#         self.actionImportProfile.triggered.connect(self.import_profile)
#         self.actionExportProfile.triggered.connect(self.export_profile)
#         self.actionAbout.triggered.connect(self.showAboutDialog)
#         self.actionQuit.triggered.connect(self.MainWindow.close)

#         self.fileRadioButton.toggled.connect(self.inputModeToggle)
#         self.fileRadioButton.setChecked(True)
#         self.directoryRadioButton.toggled.connect(self.inputModeToggle)
#         self.browseButton.clicked.connect(self.browseInput)
#         self.batchModeCheckBox.stateChanged.connect(self.batchModeChanged)

#         self.inputEdit.dragEnterEvent = self.inputDragEnterEvent
#         self.inputEdit.dropEvent = self.inputDropEvent
#         self.pasteButton.clicked.connect(self.pasteInput)

#         self.pieceCountLabel.hide()
#         self.pieceSizeComboBox.addItem('Auto')
#         for x in PIECE_SIZES[1:]:
#             self.pieceSizeComboBox.addItem(
#                 humanfriendly.format_size(x, binary=True))

#         self.pieceSizeComboBox.currentIndexChanged.connect(
#             self.pieceSizeChanged)

#         self.privateTorrentCheckBox.stateChanged.connect(
#             self.privateTorrentChanged)

#         self.commentEdit.textEdited.connect(
#             self.commentEdited)

#         self.sourceEdit.textEdited.connect(
#             self.sourceEdited)

#         self.md5CheckBox.stateChanged.connect(
#             self.md5Changed)

#         self.progressBar.hide()
#         self.createButton.setEnabled(False)
#         self.createButton.clicked.connect(self.createButtonClicked)
#         self.cancelButton.hide()
#         self.cancelButton.clicked.connect(self.cancel_creation)
#         self.resetButton.clicked.connect(self.reset)

#         self._statusBarMsg('Ready')

#     def getSettings(self):
#         portable_fn = PROGRAM_NAME + '.ini'
#         portable_fn = os.path.join(_basedir, portable_fn)
#         if os.path.exists(portable_fn):
#             return QtCore.QSettings(
#                 portable_fn,
#                 QtCore.QSettings.IniFormat
#             )
#         return QtCore.QSettings(
#             QtCore.QSettings.IniFormat,
#             QtCore.QSettings.UserScope,
#             PROGRAM_NAME,
#             PROGRAM_NAME
#         )

#     def loadSettings(self):
#         settings = self.getSettings()
#         if settings.value('input/mode') == 'directory':
#             self.directoryRadioButton.setChecked(True)
#         batch_mode = bool(int(settings.value('input/batch_mode') or 0))
#         self.batchModeCheckBox.setChecked(batch_mode)
#         exclude = settings.value('input/exclude')
#         if exclude:
#             self.excludeEdit.setPlainText(exclude)
#         trackers = settings.value('seeding/trackers')
#         if trackers:
#             self.trackerEdit.setPlainText(trackers)
#         web_seeds = settings.value('seeding/web_seeds')
#         if web_seeds:
#             self.webSeedEdit.setPlainText(web_seeds)
#         private = bool(int(settings.value('options/private') or 0))
#         self.privateTorrentCheckBox.setChecked(private)
#         source = settings.value('options/source')
#         if source:
#             self.sourceEdit.setText(source)
#         compute_md5 = bool(int(settings.value('options/compute_md5') or 0))
#         if compute_md5:
#             self.md5CheckBox.setChecked(compute_md5)
#         mainwindow_size = settings.value("geometry/size")
#         if mainwindow_size:
#             self.MainWindow.resize(mainwindow_size)
#         mainwindow_position = settings.value("geometry/position")
#         if mainwindow_position:
#             self.MainWindow.move(mainwindow_position)
#         self.last_input_dir = settings.value('history/last_input_dir') or None
#         self.last_output_dir = settings.value(
#             'history/last_output_dir') or None

#     def saveSettings(self):
#         settings = self.getSettings()
#         settings.setValue('input/mode', self.inputMode)
#         settings.setValue('input/batch_mode', int(self.batchModeCheckBox.isChecked()))
#         settings.setValue('input/exclude', self.excludeEdit.toPlainText())
#         settings.setValue('seeding/trackers', self.trackerEdit.toPlainText())
#         settings.setValue('seeding/web_seeds', self.webSeedEdit.toPlainText())
#         settings.setValue('options/private',
#                           int(self.privateTorrentCheckBox.isChecked()))
#         settings.setValue('options/source', self.sourceEdit.text())
#         settings.setValue('options/compute_md5', int(self.md5CheckBox.isChecked()))
#         settings.setValue('geometry/size', self.MainWindow.size())
#         settings.setValue('geometry/position', self.MainWindow.pos())
#         if self.last_input_dir:
#             settings.setValue('history/last_input_dir', self.last_input_dir)
#         if self.last_output_dir:
#             settings.setValue('history/last_output_dir', self.last_output_dir)

#     def _statusBarMsg(self, msg):
#         self.MainWindow.statusBar().showMessage(msg)

#     def _showError(self, msg):
#         errdlg = QtWidgets.QErrorMessage()
#         errdlg.setWindowTitle('Error')
#         errdlg.showMessage(msg)
#         errdlg.exec_()

#     def showAboutDialog(self):
#         qdlg = QtWidgets.QDialog()
#         # ad = Ui_AboutDialog()
#         ad.setupUi(qdlg)
#         ad.programVersionLabel.setText("version {}".format(__version__))
#         ad.dtVersionLabel.setText("(dottorrent {})".format(
#             dottorrent.__version__))
#         qdlg.exec_()

#     def inputModeToggle(self):
#         if self.fileRadioButton.isChecked():
#             self.inputMode = 'file'
#             self.batchModeCheckBox.setEnabled(False)
#             self.batchModeCheckBox.hide()
#         else:
#             self.inputMode = 'directory'
#             self.batchModeCheckBox.setEnabled(True)
#             self.batchModeCheckBox.show()
#         self.inputEdit.setText('')

#     def browseInput(self):
#         qfd = QtWidgets.QFileDialog(self.MainWindow)
#         if self.last_input_dir and os.path.exists(self.last_input_dir):
#             qfd.setDirectory(self.last_input_dir)
#         if self.inputMode == 'file':
#             qfd.setWindowTitle('Select file')
#             qfd.setFileMode(QtWidgets.QFileDialog.ExistingFile)
#             qfd.setOption(QtWidgets.QFileDialog.DontUseNativeDialog, True)
#             file_view = qfd.findChild(QtWidgets.QListView, 'listView')
#             if file_view:
#                 file_view.setSelectionMode(QtWidgets.QAbstractItemView.MultiSelection)
#             f_tree_view = qfd.findChild(QtWidgets.QTreeView)
#             if f_tree_view:
#                 f_tree_view.setSelectionMode(QtWidgets.QAbstractItemView.MultiSelection)

#             if qfd.exec(): 
#                 str1 = ""
#                 for ele in  qfd.selectedFiles():
#                     str1 += ele + ";"
#                 self.inputEdit.setText(str1)
#                 self.last_input_dir = os.path.split(qfd.selectedFiles()[0])[0]
#                 self.initializeTorrent()
#         else:
#             #qfd.setWindowTitle('Select directory')
#             # qfd.setFileMode(QtWidgets.QFileDialog.Directory)
#             qfd.setFileMode(QtWidgets.QFileDialog.DirectoryOnly)
#             qfd.setOption(QtWidgets.QFileDialog.DontUseNativeDialog, True)
#             file_view = qfd.findChild(QtWidgets.QListView, 'listView')

#             # to make it possible to select multiple directories:
#             if file_view:
#                 file_view.setSelectionMode(QtWidgets.QAbstractItemView.MultiSelection)
#             f_tree_view = qfd.findChild(QtWidgets.QTreeView)
#             if f_tree_view:
#                 f_tree_view.setSelectionMode(QtWidgets.QAbstractItemView.MultiSelection)

#             if qfd.exec(): 
#                 str1 = ""
#                 for ele in  qfd.selectedFiles():
#                     str1 += ele + ";"
#                 self.inputEdit.setText(str1)
#                 self.last_input_dir = os.path.split(qfd.selectedFiles()[0])[0]
#                 self.initializeTorrent()

#     def injectInputPath(self, path):
#         if os.path.exists(path):
#             if os.path.isfile(path):
#                 self.fileRadioButton.setChecked(True)
#                 self.inputMode = 'file'
#                 self.batchModeCheckBox.setCheckState(QtCore.Qt.Unchecked)
#                 self.batchModeCheckBox.setEnabled(False)
#                 self.batchModeCheckBox.hide()
#             else:
#                 self.directoryRadioButton.setChecked(True)
#                 self.inputMode = 'directory'
#                 self.batchModeCheckBox.setEnabled(True)
#                 self.batchModeCheckBox.show()
#             self.inputEdit.setText(path)
#             self.last_input_dir = os.path.split(path)[0]
#             self.initializeTorrent()

#     def inputDragEnterEvent(self, event):
#         if event.mimeData().hasUrls():
#             urls = event.mimeData().urls()
#             if len(urls) == 1 and urls[0].isLocalFile():
#                 event.accept()
#                 return
#         event.ignore()

#     def inputDropEvent(self, event):
#         path = event.mimeData().urls()[0].toLocalFile()
#         self.injectInputPath(path)

#     def pasteInput(self):
#         mimeData = self.clipboard().mimeData()
#         if mimeData.hasText():
#             path = mimeData.text().strip("'\"")
#             self.injectInputPath(path)

#     def batchModeChanged(self, state):
#         if state == QtCore.Qt.Checked:
#             self.pieceSizeComboBox.setCurrentIndex(0)
#             self.pieceSizeComboBox.setEnabled(False)
#             self.pieceCountLabel.hide()
#         else:
#             self.pieceSizeComboBox.setEnabled(True)
#             if self.torrent:
#                 self.pieceCountLabel.show()

#     def initializeTorrent(self):
#         self.torrent = Torrent("",self.inputEdit.text().split(";")[0])
#         try:
#             t_info = self.torrent.get_info()
#         except Exception as e:
#             self.torrent = None
#             self._showError(str(e))
#             return
#         ptail = os.path.split(self.torrent.path)[1]
#         if self.inputMode == 'file':
#             self._statusBarMsg(
#                 "{}: {}".format(ptail, humanfriendly.format_size(
#                     t_info[0], binary=True)))
#         else:
#             self._statusBarMsg(
#                 "{}: {} files, {}".format(
#                     ptail, t_info[1], humanfriendly.format_size(
#                         t_info[0], binary=True)))
#         self.pieceSizeComboBox.setCurrentIndex(0)
#         self.updatePieceCountLabel(t_info[2], t_info[3])
#         self.pieceCountLabel.show()
#         self.createButton.setEnabled(True)

#     def commentEdited(self, comment):
#         if getattr(self, 'torrent', None):
#             self.torrent.comment = comment

#     def sourceEdited(self, source):
#         if getattr(self, 'torrent', None):
#             self.torrent.source = source

#     def pieceSizeChanged(self, index):
#         if getattr(self, 'torrent', None):
#             self.torrent.piece_size = PIECE_SIZES[index]
#             t_info = self.torrent.get_info()
#             self.updatePieceCountLabel(t_info[2], t_info[3])

#     def updatePieceCountLabel(self, ps, pc):
#         ps = humanfriendly.format_size(ps, binary=True)
#         self.pieceCountLabel.setText("{} pieces @ {} each".format(pc, ps))

#     def privateTorrentChanged(self, state):
#         if getattr(self, 'torrent', None):
#             self.torrent.private = (state == QtCore.Qt.Checked)

#     def md5Changed(self, state):
#         if getattr(self, 'torrent', None):
#             self.torrent.include_md5 = (state == QtCore.Qt.Checked)

#     def createButtonClicked(self):
#         self.torrent.exclude = self.excludeEdit.toPlainText().strip().splitlines()
#         # Validate trackers and web seed URLs
#         trackers = self.trackerEdit.toPlainText().strip().split()
#         web_seeds = self.webSeedEdit.toPlainText().strip().split()
#         try:
#             self.torrent.trackers = trackers
#             self.torrent.web_seeds = web_seeds
#         except Exception as e:
#             self._showError(str(e))
#             return
#         self.torrent.private = self.privateTorrentCheckBox.isChecked()
#         self.torrent.comment = self.commentEdit.text() or None
#         self.torrent.source = self.sourceEdit.text() or None
#         self.torrent.include_md5 = self.md5CheckBox.isChecked()
#         self.torrent.batchModeCheckBox = self.batchModeCheckBox.isChecked()
#         if self.inputMode == 'directory':
#             self.createTorrentBatch()
#         else:
#             self.createTorrent()

#     def createTorrent(self):
#         if os.path.isfile(self.inputEdit.text().split(";")[0]):
#             save_fn = os.path.splitext(
#                 os.path.split(self.inputEdit.text().split(";")[0])[1])[0] + '.torrent'
#         else:
#             save_fn = self.inputEdit.text().split(";")[0].split(os.sep)[-1] + '.torrent'
#         if self.last_output_dir and os.path.exists(self.last_output_dir):
#             save_fn = os.path.join(self.last_output_dir, save_fn)
#         fn = QtWidgets.QFileDialog.getSaveFileName(
#             self.MainWindow, 'Save torrent', save_fn,
#             filter=('Torrent file (*.torrent)'))[0]
#         if fn:
#             self.last_output_dir = os.path.split(fn)[0]
#             self.creation_thread = CreateTorrentQThread(
#                 self.torrent,
#                 fn,                
#                 path=self.inputEdit.text())
#             self.creation_thread.started.connect(
#                 self.creation_started)
#             self.creation_thread.progress_update.connect(
#                 self._progress_update)
#             self.creation_thread.finished.connect(
#                 self.creation_finished)
#             self.creation_thread.onError.connect(
#                 self._showError)
#             self.creation_thread.start()

#     def createTorrentBatch(self):
#         save_dir = QtWidgets.QFileDialog.getExistingDirectory(
#             self.MainWindow, 'Select output directory', self.last_output_dir)
#         if save_dir:
#             self.last_output_dir = save_dir
#             trackers = self.trackerEdit.toPlainText().strip().split()
#             web_seeds = self.webSeedEdit.toPlainText().strip().split()
#             self.creation_thread = CreateTorrentBatchQThread(
#                 path=self.inputEdit.text(),
#                 exclude=self.excludeEdit.toPlainText().strip().splitlines(),
#                 save_dir=save_dir,
#                 trackers=trackers,
#                 web_seeds=web_seeds,
#                 private=self.privateTorrentCheckBox.isChecked(),
#                 source=self.sourceEdit.text(),
#                 comment=self.commentEdit.text(),
#                 include_md5=self.md5CheckBox.isChecked(),
#                 batchModeCheckBox=self.batchModeCheckBox.isChecked()
#             )
#             self.creation_thread.started.connect(
#                 self.creation_started)
#             self.creation_thread.progress_update.connect(
#                 self._progress_update_batch)
#             self.creation_thread.finished.connect(
#                 self.creation_finished)
#             self.creation_thread.onError.connect(
#                 self._showError)
#             self.creation_thread.start()

#     def cancel_creation(self):
#         self.creation_thread.requestInterruption()

#     def _progress_update(self, fn, pc, pt):
#         fn = os.path.split(fn)[1]
#         msg = "{} ({}/{})".format(fn, pc, pt)
#         self.updateProgress(msg, int(round(100 * pc / pt)))

#     def _progress_update_batch(self, fn, tc, tt):
#         msg = "({}/{}) {}".format(tc, tt, fn)
#         self.updateProgress(msg, int(round(100 * tc / tt)))

#     def updateProgress(self, statusMsg, pv):
#         self._statusBarMsg(statusMsg)
#         self.progressBar.setValue(pv)

#     def creation_started(self):
#         self.inputGroupBox.setEnabled(False)
#         self.seedingGroupBox.setEnabled(False)
#         self.optionGroupBox.setEnabled(False)
#         self.progressBar.show()
#         self.createButton.hide()
#         self.cancelButton.show()
#         self.resetButton.setEnabled(False)

#     def creation_finished(self):
#         self.inputGroupBox.setEnabled(True)
#         self.seedingGroupBox.setEnabled(True)
#         self.optionGroupBox.setEnabled(True)
#         self.progressBar.hide()
#         self.createButton.show()
#         self.cancelButton.hide()
#         self.resetButton.setEnabled(True)
#         if self.creation_thread.success:
#             self._statusBarMsg('Finished')
#         else:
#             self._statusBarMsg('Canceled')
#         self.creation_thread = None

#     def export_profile(self):

#         fn = QtWidgets.QFileDialog.getSaveFileName(
#             self.MainWindow, 'Save profile', self.last_output_dir,
#             filter=('JSON configuration file (*.json)'))[0]
#         if fn:
#             exclude = self.excludeEdit.toPlainText().strip().splitlines()
#             trackers = self.trackerEdit.toPlainText().strip().split()
#             web_seeds = self.webSeedEdit.toPlainText().strip().split()
#             private = self.privateTorrentCheckBox.isChecked()
#             compute_md5 = self.md5CheckBox.isChecked()
#             source = self.sourceEdit.text()
#             data = {
#                 'exclude': exclude,
#                 'trackers': trackers,
#                 'web_seeds': web_seeds,
#                 'private': private,
#                 'compute_md5': compute_md5,
#                 'source': source
#             }
#             with open(fn, 'w') as f:
#                 json.dump(data, f, indent=4, sort_keys=True)
#             self._statusBarMsg("Profile saved to " + fn)

#     def import_profile(self):
#         fn = QtWidgets.QFileDialog.getOpenFileName(
#             self.MainWindow, 'Open profile', self.last_input_dir,
#             filter=('JSON configuration file (*.json)'))[0]
#         if fn:
#             with open(fn) as f:
#                 data = json.load(f)
#             exclude = data.get('exclude', [])
#             trackers = data.get('trackers', [])
#             web_seeds = data.get('web_seeds', [])
#             private = data.get('private', False)
#             compute_md5 = data.get('compute_md5', False)
#             source = data.get('source', '')
#             try:
#                 self.excludeEdit.setPlainText(os.linesep.join(exclude))
#                 self.trackerEdit.setPlainText(os.linesep.join(trackers))
#                 self.webSeedEdit.setPlainText(os.linesep.join(web_seeds))
#                 self.privateTorrentCheckBox.setChecked(private)
#                 self.md5CheckBox.setChecked(compute_md5)
#                 self.sourceEdit.setText(source)
#             except Exception as e:
#                 self._showError(str(e))
#                 return
#             self._statusBarMsg("Profile {} loaded".format(
#                 os.path.split(fn)[1]))

#     def reset(self):
#         self._statusBarMsg('')
#         self.createButton.setEnabled(False)
#         self.fileRadioButton.setChecked(True)
#         self.batchModeCheckBox.setChecked(False)
#         self.inputEdit.setText(None)
#         self.excludeEdit.setPlainText(None)
#         self.trackerEdit.setPlainText(None)
#         self.webSeedEdit.setPlainText(None)
#         self.pieceSizeComboBox.setCurrentIndex(0)
#         self.pieceCountLabel.hide()
#         self.commentEdit.setText(None)
#         self.privateTorrentCheckBox.setChecked(False)
#         self.md5CheckBox.setChecked(False)
#         self.sourceEdit.setText(None)
#         self.torrent = None
#         self._statusBarMsg('Ready')


# def main():
#     app = QtWidgets.QApplication(sys.argv)
#     MainWindow = QtWidgets.QMainWindow()
#     ui = DottorrentGUI()
#     ui.setupUi(MainWindow)

#     MainWindow.setWindowTitle(PROGRAM_NAME_VERSION)

#     ui.loadSettings()
#     ui.clipboard = app.clipboard
#     app.aboutToQuit.connect(lambda: ui.saveSettings())
#     MainWindow.show()
#     sys.exit(app.exec_())


# if __name__ == "__main__":
#     main()
