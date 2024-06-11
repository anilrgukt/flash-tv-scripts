import os
import sys

import threading
import subprocess
from subprocess import Popen, PIPE
import fcntl

import time
from datetime import datetime

import cv2
import numpy as np 
import math 

from utils.stream import WebcamVideoStream


def create_usb_list():
    device_list = list()
    try:
        lsusb_out = Popen('lsusb -v', shell=True, bufsize=64, stdin=PIPE, stdout=PIPE, close_fds=True).stdout.read().strip().decode('utf-8')
        usb_devices = lsusb_out.split('%s%s' % (os.linesep, os.linesep))
        for device_categories in usb_devices:
            if not device_categories:
                continue
            categories = device_categories.split(os.linesep)
            device_stuff = categories[0].strip().split()
            bus = device_stuff[1]
            device = device_stuff[3][:-1]
            device_dict = {'bus': bus, 'device': device}
            device_info = ' '.join(device_stuff[6:])
            device_dict['description'] = device_info
            for category in categories:
                if not category:
                    continue
                categoryinfo = category.strip().split()
                if categoryinfo[0] == 'iManufacturer':
                    manufacturer_info = ' '.join(categoryinfo[2:])
                    device_dict['manufacturer'] = manufacturer_info
                if categoryinfo[0] == 'iProduct':
                    device_info = ' '.join(categoryinfo[2:])
                    device_dict['device'] = device_info
            path = '/dev/bus/usb/%s/%s' % (bus, device)
            device_dict['path'] = path

            device_list.append(device_dict)
    except Exception as ex:
        print('Failed to list usb devices! Error: %s' % ex)
        #sys.exit(-1)
    return device_list

def reset_usb_device(dev_path):
    USBDEVFS_RESET = 21780
    try:
        f = open(dev_path, 'w', os.O_WRONLY)
        fcntl.ioctl(f, USBDEVFS_RESET, 0)
        print('Successfully reset %s' % dev_path)
        #sys.exit(0)
    except Exception as ex:
        print('Failed to reset device! Error: %s' % ex)
        #sys.exit(-1)

def cam_id():
    dev_list = subprocess.Popen('v4l2-ctl --list-devices'.split(), shell=False, stdout=subprocess.PIPE)
    out, err = dev_list.communicate()
    out = out.decode()
    dev_paths = out.split('\n')
    dev_path = None

    # WEBCAM_NAME = 'HD Pro Webcam C920' # Logitech Webcam C930e
    WEBCAM_NAME1 = 'Logitech Webcam C930e'
    #WEBCAM_NAME2 = 'USB  Live camera: USB  Live cam'
    WEBCAM_NAME2 = 'Anker PowerConf C300: Anker Pow'
    
    dev_name = {WEBCAM_NAME1:'C930e', WEBCAM_NAME2: 'C300'}
    
    which_webcam = None
    for i in range(len(dev_paths)):
        #print(i, dev_paths[i])
        if (WEBCAM_NAME1 in dev_paths[i]):  
            dev_path = dev_paths[i+1].strip()
            which_webcam = WEBCAM_NAME1
            break
            #print(dev_path, dev_path[-1])
        elif (WEBCAM_NAME2 in dev_paths[i]):
            dev_path = dev_paths[i+1].strip()
            which_webcam = WEBCAM_NAME2
            break

    if dev_path is not None:
        cam_idx = int(dev_path[-1])    
    else:
        cam_idx = -1
        
    print('CAMERA identified at: ', cam_idx)
    
    if dev_name[which_webcam] == 'C300':
        print('Do not reset the Anker 120 degree FoV camera.')
        return cam_idx
    
    usb_list = create_usb_list()
    usb_path = None
    for device in usb_list:
        text = '%s %s %s' % (device['description'], device['manufacturer'], device['device'])
        #print(text)
        if dev_name[which_webcam] in text:
            print(dev_name[which_webcam], device['path'])
            usb_path = device['path']
            reset_usb_device(device['path'])
            time.sleep(3)
    
    if usb_path is None:   
        print('Failed to find the the usb path for the camera!', dev_name[which_webcam])
    
    return cam_idx

def write_log_file(log_fname, write_lines):
    fid = open(log_fname,'a')
    for write_line in write_lines:
        write_line = [str(l) for l in write_line]
        write_line = ' '.join(write_line)
        write_line = write_line + '\n'
        fid.write(write_line)
    fid.close()

def check_face_presence(log_file, detector):
    print('CHECKING FACE presence')
    face_p_duration = 0
    face_np_duration = 0
    face_np_time_delay = 0.5 # num secs
    
    idx = cam_id()
    video_reader = WebcamVideoStream()
    video_reader.start(idx, width=608, height=342)

    '''
    cap_yolo = cv2.VideoCapture(idx)
    cap_yolo.set(3, 608)
    cap_yolo.set(4, 342)
    cap_yolo.set(5, 3)
    '''
    
    #cap.set(5, 15)
    #fps = int(cap_yolo.get(5))
    #print('Streaming for Face detection at {}x{} res. for {} FPS'.format(608,342,fps))
    
    frm_counter = log_file[1]
    fname_log = log_file[0]
    
    while face_p_duration < 1:
        #ret, img_cap = cap_yolo.read()
        #retr = cap_yolo.grab()
        #ret, img_cap = cap_yolo.retrieve(retr)
        img_cap = video_reader.read()
        img_cap_time = datetime.now()
        
        #print('starting face det .... ')
        dboxes = detector(img_cap) # face detection 
        
        #DELETE very low confidence faces if any
        ndboxes = []
        for b in dboxes:
            if b['prob'] > 0.09: 
                ndboxes.append(b)
        dboxes = ndboxes
        
        write_line = [img_cap_time, str(frm_counter).zfill(6)]
        write_line = write_line + [str(len(dboxes)), str(0), str(None), str(None), str(None), str(None), str(None), str(None), str(None), str(None)]
        if len(dboxes) < 1: # if no faces continue
            print('Face detector LOG ouput', img_cap_time, np.array([None, None]), 'No face detected')
            if face_np_duration > 45:
                face_np_time_delay = 1.03*face_np_time_delay
                face_np_time_delay = min(15.0, face_np_time_delay)

            face_np_duration += 1
            write_line.append('No-face-detected')
        else:
            face_p_duration += 1 
            print('Face detector LOG ouput', img_cap_time, np.array([None, None]), 'Init face detected')
            face_np_time_delay = 0.3
            write_line.append('Face-detected')
            
        write_log_file(fname_log, [write_line])
        time.sleep(face_np_time_delay)
        frm_counter += 1
        
        imgr = cv2.resize(img_cap, (608,342))
        #detimg = draw_rect_det(imgr[:,:,::-1], dboxes, 'tmp_det.png')
    
    #cap_yolo.release()
    video_reader.stop()
    cv2.destroyAllWindows()
    log_file[1] = frm_counter

    return face_p_duration, log_file


def correct_rotation(a, tc_angle):
    #s0 = output_varr[i,0]
    #s1 = output_varr[i,1]
    
    s0 = a[0]
    s1 = a[1]
    
    x = math.cos(s1)*math.sin(s0) # -40*
    y = math.sin(s1) # -40*
    z = -math.cos(s1)*math.cos(s0)
    
    tangle = -(tc_angle/180)*math.pi
    xt = math.cos(tangle)*x + math.sin(tangle)*y
    yt = -math.sin(tangle)*x + math.cos(tangle)*y
    zt = z
    
    vt = np.array([xt,yt,zt])
    vtnorm = (vt*vt).sum()
    vt = vt / np.sqrt(vtnorm)
    
    ns0 = np.arctan2(vt[0],-vt[2])
    ns1 = np.arcsin(vt[1])
    
    return [ns0, ns1, a[2]]

def make_directories(save_path, famid, frames_path, frames_save_path):

    if not os.path.exists(frames_save_path):
        os.makedirs(frames_save_path)

    if not os.path.exists(frames_path):
        os.makedirs(frames_path)
    else:
        if len(os.listdir(frames_path)) > 0:
            file_ls = next(os.walk(save_path))[1]
            file_ls_ = []
            for f in file_ls: 
                if f.startswith(str(famid)+'_frames'):
                    file_ls_.append(f)
            
            f_ = None
            for i, f in enumerate(file_ls_):
                f_path = os.path.join(save_path, f)
                if len(f_path) > 0:
                    continue
                else:
                    f_ = f
            
            if f_ is None:
                frames_path = os.path.join(save_path, str(famid)+'_frames_'+str(i+2))
                frames_save_path = os.path.join(save_path, str(famid)+'_test_res_'+str(i+2))
                
                os.makedirs(frames_path)
                os.makedirs(frames_save_path)    
                
    return frames_path, frames_save_path
