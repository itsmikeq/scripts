#!/usr/bin/env python
from threading import Thread
import subprocess, os, sys, getopt, multiprocessing
from Queue import Queue
import os,re,subprocess, logging

# Globals
num_threads = multiprocessing.cpu_count()
os.environ["RSYNC_SSH"]="ssh"
queue = Queue()
rsync = "/usr/bin/rsync -aHS --delete"
global source
global destination
global logfile
global exclude
exclude = []

logger = logging.getLogger(__name__)
try:
  opts, args = getopt.getopt(sys.argv[1:], "vhs:d:l:e:r:", ["verbose","help", "source=", 
    "destination=","logfile=", "exclude=[]", "rsync="])
except getopt.GetoptError, err:
  # print help information and exit:
  print str(err) # will print something like "option -a not recognized"
  usage()
  sys.exit(2)
output = None
verbose = False
def set_logging(logfile):
  logging.formatter='%(asctime)-15s %(processName)s %(user)-8s %(message)s'
  logger.propagate = True
  hdlr = logging.FileHandler(logfile)
  logger.addHandler(hdlr) 
  logger.setLevel(logging.DEBUG)


def usage():
  print '''
  Do some help stuff here
  '''

def find_git_dirs(root_path=os.curdir):
  logger.info("Looking for .git dirs in %s" % root_path)
  print "Looking for .git dirs in %s" % root_path
  git_dirs = []
  for path, dirs, files in os.walk(os.path.abspath(root_path)):
    dir_path = ""
    if dirs in (None,""):
      continue
    for dir in dirs:
      if dir in (None,""):
        continue
      if re.match("\.git",dir):
        print "Adding %s" % (path)
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
    else:
      assert False, "unhandled option"
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
