# **************************************************************************
# *
# * Authors: Yunior C. Fonseca Reyna    (cfonseca@cnb.csic.es)
# *
# *
# * Unidad de  Bioinformatica of Centro Nacional de Biotecnologia , CSIC
# *
# * This program is free software; you can redistribute it and/or modify
# * it under the terms of the GNU General Public License as published by
# * the Free Software Foundation; either version 3 of the License, or
# * (at your option) any later version.
# *
# * This program is distributed in the hope that it will be useful,
# * but WITHOUT ANY WARRANTY; without even the implied warranty of
# * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# * GNU General Public License for more details.
# *
# * You should have received a copy of the GNU General Public License
# * along with this program; if not, write to the Free Software
# * Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA
# * 02111-1307  USA
# *
# *  All comments concerning this program package may be sent to the
# *  e-mail address 'scipion@cnb.csic.es'
# *
# **************************************************************************
from glob import glob
import json
import os
import time
from os.path import join, dirname, basename, exists, getmtime
import logging
from pathlib import Path
from typing import Optional, Set, Tuple

from pwem import (EXEC_STATUS_DIR, STREAM_JOURNAL, STREAM_SCHEMA_VERSION,
                  STREAM_REC_HEADER, STREAM_REC_ITEM, STREAM_REC_CLOSE,
                  STREAM_HEARTBEAT)
from pyworkflow.protocol import Protocol
from pyworkflow.utils import makePath

logger = logging.getLogger(__name__)
import pyworkflow.utils as pwutils
import pwem


def loadSetFromDb(dbName, dbPrefix=''):
    from pwem import Domain
    from pyworkflow.mapper.sqlite import SqliteFlatDb
    db = SqliteFlatDb(dbName=dbName, tablePrefix=dbPrefix)
    setClassName = db.getProperty('self')  # get the set class name
    setObj = Domain.getObjects()[setClassName](filename=dbName, prefix=dbPrefix)
    return setObj


def runProgram(program, params):
    """ Runs an em program setting its environment matching a prefix"""
    env = None

    # Allow passing absolute paths
    programName = basename(program)

    from pwem import Domain
    # Avoid detecting xmipp installation script to be run as xmipp, since
    # it will run devel installation with production xmippEnv.json environment:
    # Example: want to compile devel with java 8, but production was compiled with java 11.
    # So java 11 makes it into the PATH taking priority
    if programName.startswith('xmipp_'):
        print("Xmipp command detected")
        xmipp3 = Domain.getPlugin('xmipp3').Plugin
        env = xmipp3.getEnviron()
    if programName.startswith('relion'):
        print("relion command detected")
        relion = Domain.getPlugin("relion").Plugin
        env = relion.getEnviron()
    elif (programName.startswith('e2') or
          programName.startswith('sx')):
        print("eman/sparx command detected")
        eman2 = Domain.importFromPlugin('eman2', 'Plugin')
        env = eman2.getEnviron()
        program = eman2.getProgram(programName)
    elif programName.startswith('b'):
        print("Bsoft command detected")
        bsoft = Domain.importFromPlugin('bsoft', 'Plugin')
        env = bsoft.getEnviron()

    pwutils.runJob(None, program, params, env=env)


def getPWEMPath(*paths):
    return join(dirname(pwem.__file__), *paths)


def getTemplatePath(*paths):
    return join(getPWEMPath('templates'), *paths)


def getCmdPath(*paths):
    return join(getPWEMPath('cmd'), *paths)


def convertPixToLength(samplingRate, length):
    return samplingRate * length


def splitRange(minValue, maxValue, splitNum=10, roundTo=2):
    """
    returns a list of "splitNum" items with values ranging from minValue to maxValue, equally divided
    :param minValue: value to start from
    :param maxValue: value to stop
    :param splitNum: number of splits, limits included
    :param roundTo: default to 2, rounding decimal value
    :return: list with the split
    """
    inter = (maxValue - minValue) / (splitNum - 1)
    rangeList = []
    for step in range(0, splitNum):
        rangeList.append(round(minValue + step * inter, roundTo))
    return rangeList


PROBLEMATIC_SHELL_CHARS = ";<>?\"()|*\\'&"


def cleanFileName(fn, warn=True):
    """ Cleans any character that later on might cause shell parsing errors like "(", ")", " "
    and warns about it if warn is true.

    :param fn: file to be cleaned
    :param warn: Optional (True). Logs """

    cleaned = False

    for bannedChar in PROBLEMATIC_SHELL_CHARS:
        if bannedChar in fn:
            if warn:
                logger.info("Warning!. Problematic character (%s) found in file %s. "
                            "Any of these characters will be removed: %s" % (bannedChar, fn, PROBLEMATIC_SHELL_CHARS))
            fn = fn.replace(bannedChar, '')
            cleaned = True

    return fn, cleaned


def round_to_nearest(number, base):
    """ Rounds number to the nearest integer: E.g: pass base=5 to round to the nearest
     number multiple of 5

    :param number: number to be rounded
    :param base: integer to limit the rounding to
    """

    return base * round(number/base)


def getMatchingFiles(path, sort=False):
    filePaths = glob(path)
    if sort:
        filePaths.sort()
    return filePaths


def fnMatching(itemId, filesDict, objType='Micrograph'):
    """
    Check if in an object (micrograph, ctf, etc...) its files are matched
   :param itemId: Is micName, baseName, tsId,...(is not objId)
   :param filesDict: The keys are the base name of the file to import without the extension,
                     and the values can be a path (e.g. path of the ctf files when importing ctf)
                     or an object (e.g. micrographs when importing coordinates).
   :param objType: This parameter is informative to complete the log messages to know what is being imported.
   :return: A tuple with the key and the value of filesDict that matches itemId
   """
    longestItem = None
    longestItemId = None
    finalMessage = None

    if itemId in filesDict:
        longestItem = filesDict[itemId]
        longestItemId = itemId
        finalMessage = "%s %s exact match" % (objType, itemId)
    else:
        longestMatch = 0
        matchLen = 0
        # ItemId is not objId. Is micName or tsId
        for fileBaseName, item in filesDict.items():
            if itemId.startswith(fileBaseName):
                # BVP_1234_aligned(objFile) startswith BVP_1234(micName, baseName, tsId,...)
                message = "%s %s starts with %s" % (objType, itemId, fileBaseName)
                matchLen = len(fileBaseName)
            elif fileBaseName in itemId:
                # BVP_1234(micName or baseName) in BVP_1234_info(objFile)
                message = "%s %s contains %s" % (objType, itemId, fileBaseName)
                matchLen = len(fileBaseName)

            if len(itemId) > matchLen:
                if fileBaseName.startswith(itemId):
                    # BVP_1234_aligned(fileBaseName) startswith BVP_1234(itemId)
                    # MicBase start with coordBase
                    message = "%s %s is the beginning of %s" % (objType, itemId, fileBaseName)
                    matchLen = len(itemId)
                elif itemId in fileBaseName:
                    # BVP_1234(itemId) in BVP_1234_aligned(fileBaseName)
                    # micBase contains coordBase
                    message = "%s %s contained in %s" % (objType, itemId, fileBaseName)
                    matchLen = len(itemId)

            if matchLen > longestMatch:
                finalMessage = message
                longestMatch = matchLen
                longestItem = item
                longestItemId = fileBaseName
                matchLen = 0

    if finalMessage is not None:
        logger.debug(finalMessage + ': ' + str(longestItem))
    else:
        finalMessage = '%s %s does not match ' % (objType, itemId)
        logger.debug(finalMessage)

    return longestItemId, longestItem


# -------------------------- Streaming utilities -------------------------------
def getExecStatusDir(prot: Protocol) -> str:
    return prot._getPath(EXEC_STATUS_DIR)


def genExecStatusDir(prot: Protocol) -> None:
    makePath(getExecStatusDir(prot))


# ---- Append-only stream journal (replaces '*.ready' + 'DONE' + YAML sidecar) --
def getStreamJournalFn(prot: Protocol) -> str:
    return join(getExecStatusDir(prot), STREAM_JOURNAL)


def _appendStreamRecord(journalFn: str, record: dict) -> None:
    """Append one JSON record as a single newline-terminated line.

    A single ``write`` + ``flush`` (+ ``fsync``) of one complete line is the
    network-filesystem-safe write primitive this design relies on: readers parse
    only complete '\\n'-terminated lines, so a partially written trailing line is
    ignored until it is finished. This is what removes the truncated-read race of
    the old (non-atomic) YAML sidecar.
    """
    line = json.dumps(record, sort_keys=False) + '\n'
    with open(journalFn, 'a') as f:
        f.write(line)
        f.flush()
        os.fsync(f.fileno())


def initStreamJournal(prot: Protocol, imgSet) -> None:
    """Append a header record carrying the set class name plus its full
    'Properties' table (``getObjDict()`` -- exactly what ``Set.write()`` persists).
    These properties are global to the set, so a downstream consumer can rebuild
    an in-memory set/item from them without opening the producer's set DB.

    On a continued run a fresh header is appended; readers take the LAST header
    seen, so edited acquisition/sampling parameters are reflected.
    """
    record = {
        'type': STREAM_REC_HEADER,
        'schema': STREAM_SCHEMA_VERSION,
        'set': imgSet.getClassName(),
        'properties': imgSet.getObjDict(),
    }
    _appendStreamRecord(getStreamJournalFn(prot), record)


def appendStreamItem(prot: Protocol, imgId: str, meta: Optional[dict] = None) -> None:
    """Append one item record signaling that ``imgId`` is ready/processed.

    ``meta`` (optional) is a small JSON-serializable dict of per-item metadata
    inlined into the record. A consumer can then rebuild the item fully from the
    journal (one sequential read it already performs for discovery) without
    opening the producer's SQLite set -- avoiding both a DB read and a per-item
    sidecar file. Keep it small and flat (this is appended once per item)."""
    record = {'type': STREAM_REC_ITEM, 'id': imgId}
    if meta is not None:
        record['meta'] = meta
    _appendStreamRecord(getStreamJournalFn(prot), record)


def closeStreamJournal(prot: Protocol) -> None:
    """Append the terminal record marking the stream as closed."""
    _appendStreamRecord(getStreamJournalFn(prot), {'type': STREAM_REC_CLOSE})


def touchHeartbeat(prot: Protocol) -> None:
    """Refresh the producer liveness heartbeat (its mtime). Consumers use the
    file's age to detect a producer that died without closing the stream."""
    Path(join(getExecStatusDir(prot), STREAM_HEARTBEAT)).touch()


def getHeartbeatAge(statusDir: str) -> Optional[float]:
    """Seconds since the producer's heartbeat was last refreshed, or None if the
    heartbeat file does not exist yet."""
    hbFn = join(statusDir, STREAM_HEARTBEAT)
    if not exists(hbFn):
        return None
    return time.time() - getmtime(hbFn)


def readStreamJournal(statusDir: str,
                      fromOffset: int = 0) -> Tuple[Set[str], Optional[dict], bool, int, dict]:
    """Incrementally read a stream journal.

    Reads only the bytes after ``fromOffset``, parses only complete
    newline-terminated lines, and advances the returned offset past the last
    complete line (a partial trailing line is left for the next call). Returns
    ``(items, header, closed, newOffset, itemMeta)`` where ``items`` is the set of
    item ids seen in THIS chunk, ``header`` is the last header record in this
    chunk (or None), ``closed`` is True if a close record was seen, and
    ``itemMeta`` maps item id -> inlined metadata dict for the items that carry it.
    """
    journalFn = join(statusDir, STREAM_JOURNAL)
    items: Set[str] = set()
    itemMeta: dict = {}
    header = None
    closed = False
    if not exists(journalFn):
        return items, header, closed, fromOffset, itemMeta

    with open(journalFn, 'rb') as f:
        f.seek(fromOffset)
        chunk = f.read()

    # Consume only up to the last newline; the remainder is an incomplete line
    # still being written by the producer.
    lastNl = chunk.rfind(b'\n')
    if lastNl == -1:
        return items, header, closed, fromOffset, itemMeta
    newOffset = fromOffset + lastNl + 1

    for raw in chunk[:lastNl + 1].splitlines():
        if not raw.strip():
            continue
        try:
            record = json.loads(raw.decode('utf-8'))
        except (ValueError, UnicodeDecodeError):
            # Defensive: skip a single corrupt line rather than abort the stream.
            logger.warning("Skipping unparseable stream journal line in %s" % statusDir)
            continue
        rType = record.get('type')
        if rType == STREAM_REC_ITEM:
            itemId = record.get('id')
            items.add(itemId)
            meta = record.get('meta')
            if meta is not None:
                itemMeta[itemId] = meta
        elif rType == STREAM_REC_HEADER:
            header = record
        elif rType == STREAM_REC_CLOSE:
            closed = True

    return items, header, closed, newOffset, itemMeta
