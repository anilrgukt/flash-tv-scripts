import os
import numpy as np 

class Bbox():
    def __init__(self, bbox):
        l,t,r,b = bbox['left'], bbox['top'], bbox['right'], bbox['bottom']
        self.prob = bbox['prob']
        if 'lmarks' in bbox.keys():
            self.lmarks = bbox['lmarks']
        else:
            self.lmarks = None
            
        self.l = l
        self.t = t
        self.r = r
        self.b = b
    
    @property
    def width(self):
        w = self.r-self.l+1
        assert w>=0
        return w
    
    @property
    def height(self):
        h = self.b-self.t+1
        assert h>=0
        return h
        
    def area(self):
        A = self.height()*self.width()
        assert A>=0
        return A
    
    def assert_ltrb(self, resolution_hw):
        H = resolution_hw[0]
        W = resolution_hw[1]
        
        l,t,r,b = self.l,self.t,self.r,self.b
        
        l = max(0, l)
        t = max(0, t)
        r = min(r, W)
        b = min(b, H)
        
        self.lmarks[:,0] = self.lmarks[:,0].clip(0,W) # width
        self.lmarks[:,1] = self.lmarks[:,1].clip(0,H) # height

        bbox = {}
        bbox['left'], bbox['top'], bbox['right'], bbox['bottom'] = [int(l),int(t),int(r),int(b)]
        bbox['prob'] = self.prob
        bbox['lmarks'] = self.lmarks.astype(np.int32)
        
        return bbox 
                
    def return_dict(self):
        return {'left':self.l,'top':self.t,'right':self.r,'bottom':self.b, 'prob':self.prob, 'lmarks': self.lmarks}
        
    def add_offset(self, offset_hw):
        l,t,r,b = self.l,self.t,self.r,self.b
        l,t,r,b = l-offset_hw[1], t-offset_hw[0], r+offset_hw[1], b+offset_hw[0]
        
        if self.lmarks is not None:
            #self.lmarks[:,0] # along width
            #self.lmarks[:,1] # along height
            new_lmarks = np.zeros_like(self.lmarks)
            new_lmarks[:,0] = self.lmarks[:,0] + 0 #offset_hw[1]
            new_lmarks[:,1] = self.lmarks[:,1] + 0 #offset_hw[0]
        else:
            new_lmarks = None
        
        bbox = {}
        bbox['left'], bbox['top'], bbox['right'], bbox['bottom'] = l,t,r,b
        bbox['lmarks'] = new_lmarks
        bbox['prob'] = self.prob
        
        return bbox 
        
    def scale(self, scale_hw):
        l,t,r,b = self.l,self.t,self.r,self.b
        l,t,r,b = l*scale_hw[1], t*scale_hw[0], r*scale_hw[1], b*scale_hw[0]
        l,t,r,b = [int(l), int(t), int(r), int(b)]
        
        #new_lmarks = np.zeros_like(self.lmarks)
        if self.lmarks is not None:
            #self.lmarks[:,0] # along width
            #self.lmarks[:,1] # along height
            new_lmarks = np.zeros_like(self.lmarks)
            new_lmarks[:,0] = self.lmarks[:,0] * scale_hw[1]
            new_lmarks[:,1] = self.lmarks[:,1] * scale_hw[0]
            new_lmarks = new_lmarks.astype(np.int32)
        else:
            new_lmarks = None
        
        bbox = {}
        bbox['left'], bbox['top'], bbox['right'], bbox['bottom'] = l,t,r,b
        bbox['lmarks'] = new_lmarks
        bbox['prob'] = self.prob
        
        return bbox
        
    
