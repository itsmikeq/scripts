#!/usr/bin/env python
from threading import Thread
import subprocess, os, sys, getopt, multiprocessing, time, threading

from Queue import Queue
import os,re,subprocess, logging, traceback
import StringIO
# Globals
num_threads = multiprocessing.cpu_count()
os.environ["RSYNC_SSH"]="ssh"
queue = Queue()
rsync = "/usr/bin/rsync -aHS --delete"
global source
global destination
global logfile
global exclude
global include 
include = ""
exclude = []

logger = logging.getLogger(__name__)


try:
  opts, args = getopt.getopt(sys.argv[1:], "vhs:d:l:e:r:i:", ["verbose","help", "source=", 
    "destination=","logfile=", "exclude=[]", "rsync=", "include="])
except getopt.GetoptError, err:
  # print help information and exit:
  print str(err) # will print something like "option -a not recognized"
  usage()
  sys.exit(2)
output = None
verbose = False

class MultiProcessingLogHandler(logging.Handler):
    def __init__(self, handler, queue, child=False):
        logging.Handler.__init__(self)

        self._handler = handler
        self.queue = queue

        # we only want one of the loggers to be pulling from the queue.
        # If there is a way to do this without needing to be passed this
        # information, that would be great!
        if child == False:
            self.shutdown = False
            self.polltime = 1
            t = threading.Thread(target=self.receive)
            t.daemon = True
            t.start()

    def setFormatter(self, fmt):
        logging.Handler.setFormatter(self, fmt)
        self._handler.setFormatter(fmt)

    def receive(self):
        #print "receive on"
        while (self.shutdown == False) or (self.queue.empty() == False):
            # so we block for a short period of time so that we can
            # check for the shutdown cases.
            try:
                record = self.queue.get(True, self.polltime)
                self._handler.emit(record)
            except Queue.Empty, e:
                pass

    def send(self, s):
        # send just puts it in the queue for the server to retrieve
        self.queue.put(s)

    def _format_record(self, record):
        ei = record.exc_info
        if ei:
            dummy = self.format(record) # just to get traceback text into record.exc_text
            record.exc_info = None  # to avoid Unpickleable error

        return record

    def emit(self, record):
        try:
            s = self._format_record(record)
            self.send(s)
        except (KeyboardInterrupt, SystemExit):
            raise
        except:
            self.handleError(record)

    def close(self):
        time.sleep(self.polltime+1) # give some time for messages to enter the queue.
        self.shutdown = True
        time.sleep(self.polltime+1) # give some time for the server to time out and see the shutdown

    def __del__(self):
        self.close() # hopefully this aids in orderly shutdown when things are going poorly.


def set_logging(logfile):
  # logging.formatter='%(asctime)-15s %(processName)s %(user)-8s %(message)s'
  logger.propagate = True
  global hdlr
  formatter = logging.Formatter("%(levelname)s: %(asctime)s - %(name)s - %(process)s - %(message)s")
  hdlr = logging.FileHandler(logfile)
  hdlr.setFormatter(formatter)
  logger.addHandler(hdlr) 
  logger.setLevel(logging.DEBUG)
  return hdlr


def usage():
  print '''
  Do some help stuff here
  '''

def find_git_dirs(root_path=os.curdir):
  logger.info("Looking for %s dirs in %s" % (include,root_path))
  print "Looking for %s dirs in %s" % (include,root_path)
  if include in ("",None):
    return root_path
  git_dirs = []
  for path, dirs, files in os.walk(os.path.abspath(root_path)):
    if re.match("^.*"+include+"$",str(path)):
      print "Adding %s" % (str(path))
      git_dirs.append(str(path))
      continue
    for dir in dirs:
      print "Looking through directory: %s/%s" % (path,dir)
      if re.match("^.*"+include+"$",dir):
        print "Adding %s/%s" % (path,dir)
        git_dirs.append(str(path+'/'+dir))
  return git_dirs
def initPool(queue, level):
    """
    This causes the logging module to be initialized with the necessary info
    in pool threads to work correctly.
    """
    logging.getLogger('').addHandler(MultiProcessingLogHandler(logging.StreamHandler(), queue, child=True))
    logging.getLogger('').setLevel(level)

def sync_directory(i,queue):
  """syncsDirectory"""
  while queue.empty != True:
    dir = queue.get()
    print "Running on %s" % dir
    if dir in exclude:
      queue.task_done()
    else:
      hdlr.acquire()
      logger.info("Beginning "+ dir +" copy to " + destination)
      command = rsync + " " + dir + " " + destination
      logger.info("Running " + command)
      ret = subprocess.call(command,
                shell=True,
                stdout=open(logfile + "stdout.log", 'a'),
                stderr=subprocess.STDOUT)
      #print "running dir on", dir
      queue.task_done()
      logger.info("Finishing"+ dir )
    queuesize = queue.qsize()
    logger.info(str(queuesize) + " remaining")
    print queuesize, "remaining"
    try:
      hdlr.release()
    except:
      pass

if __name__ == "__main__":
  for o, a in opts:
    if o in ("-v", "--verbose"):
      verbose = True
    elif o in ("-h", "--help"):
      usage()
      sys.exit()
    elif o in ("-s", "--source"):
      # Basepath to look for .git directories
      source = a
      print "Source path is %s" % source
    elif o in ("-d", "--destination"):
      # Destination base path
      destination = a
      print "Destination path is %s" % destination
    elif o in ("-l", "--logfile"):
      logfile = a
      print "Log file is %s" % logfile
    elif o in ("-e", "--exclude"):
      # exclude list "e1 e1 e3" or file name
      try: 
        exclude = a.split()
      except:
        exclude = []
      print "Excludes are %s" % exclude      
    elif o in ("-r", "--rsync"):
      # exclude list "e1 e1 e3" or file name
      if a != "":
        rsync = a
    elif o in ("-i", "--include"):
      # exclude list "e1 e1 e3" or file name
      if a != "":
        include = a
    else:
      assert False, "unhandled option"
  stream = StringIO.StringIO()
  logQueue = multiprocessing.Queue(100)
  handler= MultiProcessingLogHandler(logging.StreamHandler(stream), logQueue)
  logging.getLogger('').addHandler(handler)
  logging.getLogger
  set_logging(logfile)

  for i in range(num_threads):
    '''
    Start the threads
    '''
    worker = Thread(target=sync_directory, args=(i,queue))
    worker.setDaemon(True)
    worker.start()
  print "Looking for .git dirs in source: %s" % source
  directories = find_git_dirs(source)
  if directories in (None,"") or source in (None,""):
    logger.info("Did not find any git dirs in %s" % source)
    print "Did not find any git dirs in %s" % source
    sys.exit(0)
  print "Found git dirs: " + str(directories)
  for dir in directories:
    '''
    Fill the queue
    '''
    queue.put(dir)
  print "*** Main thread waiting ***"
  queue.join()
  print "*** Main thread done ***"
