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



def set_logging(logfile):
  # logging.formatter='%(asctime)-15s %(processName)s %(user)-8s %(message)s'
  logger.propagate = True
  # stream = StringIO.StringIO()
  global hdlr
  formatter = logging.Formatter("%(levelname)s: %(asctime)s - %(name)s - %(process)s - %(message)s")
  hdlr = logging.FileHandler(logfile)
  # logQueue = multiprocessing.Queue(num_threads)
  # handler = MultiProcessingLogHandler(logging.StreamHandler(stream), logQueue)
  hdlr.setFormatter(formatter)
  logger.addHandler(hdlr)
  global loglevel
  loglevel = logging.DEBUG 
  logger.setLevel(loglevel)
  # logging.getLogger('').addHandler(handler)
  logging.getLogger('').addHandler(hdlr)

  return hdlr


def usage():
  print '''
  Do some help stuff here
  '''

def find_git_dirs(root_path=os.curdir):
  git_dirs = []
  if include in ("",None):
    for path in os.listdir(os.path.abspath(root_path)):
      if path not in git_dirs:
        logger.info("Adding %s" % (str(path)))
        git_dirs.append(path)      
    return git_dirs
  logger.info("Looking for %s dirs in %s" % (include,root_path))
  # print "Looking for %s dirs in %s" % (include,root_path)
  for path, dirs, files in os.walk(os.path.abspath(root_path)):
    if re.match("^.*"+include+"$",str(path)):
      logger.info("Adding %s" % (str(path)))
      if path not in git_dirs:
        git_dirs.append(str(path))
      continue
    for dir in dirs:
        if re.match("^.*"+include+"$",dir):
          if path not in git_dirs:
            logger.info("Adding %s" % (path) )
            git_dirs.append(str(path))
  return git_dirs

def sync_directory(i,queue):
  """syncsDirectory"""
  while queue.empty != True:
    dir = queue.get()
    print "Running on %s" % dir
    if dir in exclude:
      queue.task_done()
    else:
      logger.info("Beginning "+ str(dir) +" copy to " + str(destination))
      command = str(rsync) + " " + str(dir) + " " + str(destination)
      logger.info("Running " + str(command))
      ret = subprocess.call(command,
                shell=True,
                stdout=open(logfile + "stdout.log", 'a'),
                stderr=subprocess.STDOUT)
      #print "running dir on", dir
      queue.task_done()
      logger.info("Finishing "+ str(dir) )
    queuesize = queue.qsize()
    if queuesize > 0:
      logger.info(str(queuesize) + " remaining")
      print queuesize, " remaining"

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
  set_logging(logfile)
  try:
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
  except (KeyboardInterrupt, SystemExit):
    raise