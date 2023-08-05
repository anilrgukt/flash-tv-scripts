import os
import sys

def read_errlog(log_path):
   fid = open(log_path,'r')
   lines = fid.readlines()
   lines = [l for l in lines if not l.strip('\n').startswith('can\'t get')]
   #lines = [l for l in lines if not 'Warning' in l]

   error_lines = []
   for l in lines:
       if ('Warning' in l) or ('warn' in l) or ('Deprecated' in l):
           continue
       else:
           error_lines.append(l)

   if len(error_lines) > 8:
       print('Check the error log: ', log_path)
       #print(error_lines)


famid = str(sys.argv[1]) #'123009'
path = '/home/'+os.getlogin()+'/data/'+famid+'_data/'
ext = '_flash_logstderr.log'

read_errlog(path+famid+ext)
path_logs = path + 'logs/'

log_dir_ls = next(os.walk(path_logs))[1]
for dir in log_dir_ls:
   print('checking the log file, ', dir)
   log_path = os.path.join(path_logs, dir, famid+ext)
   #print(log_path)
   read_errlog(log_path)

