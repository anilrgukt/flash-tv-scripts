import os
import sys

import cv2
import numpy as np



class rotate_frame():
    def __init__(self,):
        self.rotate_flip = None
        self.rotate_angle = None
        self.rotate_count = 0
        self.rotate_count_tc = 0
        self.rotate_bool = [[0,0],[0,1],[0,2],[1,0],[1,1],[1,2]] #,[-1,-1]]
        self.rotate_status = 0
        self.quad = None
        
    def rotate(self,img2):
        self.rotate_flip, self.quad = self.rotate_bool[self.rotate_status]
                    
        if self.rotate_flip >= 0:
            if self.rotate_flip:
                img2 = cv2.rotate(img2[:,:,::-1], cv2.ROTATE_90_CLOCKWISE)
                self.rotate_angle = -90
            else:
                img2 = cv2.rotate(img2[:,:,::-1], cv2.ROTATE_90_COUNTERCLOCKWISE)
                self.rotate_angle = 90
            
            img2 = img2[self.quad*640:(self.quad+1)*640,:,::-1]
        
        self.rotate_count += 1
        return img2
    
    def update(self,tc_present, num_faces):
        #if 0 in idxs:
        if self.rotate_flip<0:
            if not tc_present: # tc not found in 2nd frame
                self.rotate_status = self.rotate_count%6
        else:
            if num_faces<1:
                #rotate_flip = not rotate_flip
                self.rotate_status = self.rotate_count%6
                #print('changing rot stat', rotate_status, rotate_count)
        return None
            
    
    def rotate_transform(self,bbox_ls):
        new_bbox_ls = []
        rotate_angle = self.rotate_angle
        quad = self.quad
        
        for bbox in bbox_ls:
            xl,yt,xr,yb = [bbox['left'],bbox['top'],bbox['right'],bbox['bottom']]
            xl,yt,xr,yb = xl*(1080/608.0),yt*(640/342.0),xr*(1080/608.0),yb*(640/342.0)
            
            lmarks_ = bbox['lmarks'] # x,y
            lmarks_[:,0] = lmarks_[:,0]*(1080/608.0)
            lmarks_[:,1] = lmarks_[:,1]*(640/342.0)
            lmarks = lmarks_.copy()
            
            
            if rotate_angle == 90: # if rotated counter clockwise
                xl1 = -(yb+quad*640-1920)
                yt1 = xl
                xr1 = -(yt+quad*640-1920)
                yb1 = xr
                
                lmarks[:,0] = -(lmarks_[:,1]+quad*640-1920)
                lmarks[:,1] = lmarks_[:,0]
                
            else:
                xl1 = yt + quad*640
                yt1 = -(xr-1080)
                xr1 = yb + quad*640
                yb1 = -(xl-1080)
                
                lmarks[:,1] = -(lmarks_[:,0]-1080)
                lmarks[:,0] = lmarks_[:,1] + quad*640
                
            xl,yt,xr,yb = xl1*(608/1920.0),yt1*(342/1080.0),xr1*(608/1920.0),yb1*(342/1080.0)
            lmarks[:,0] = lmarks[:,0]*(608/1920.0)
            lmarks[:,1] = lmarks[:,1]*(342/1080.0)
            
            bbox['left'],bbox['top'],bbox['right'],bbox['bottom'] = xl,yt,xr,yb
            bbox['lmarks'] = lmarks
            new_bbox_ls.append(bbox)
        return new_bbox_ls
