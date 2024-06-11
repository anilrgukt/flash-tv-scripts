from datetime import datetime

import matplotlib
#matplotlib.use("Qt5Agg")
import matplotlib.pyplot as plt

import time
import random

from visualizer import ts2num, num2ts, get_xticks

if __name__ == "__main__":

    l = [0,1,2]

    start_time = datetime.now().time().strftime("%H:%M:%S") # strftime("%Y-%m-%d %H:%M:%S")
    print(start_time)


    num_mins = 5
    start_n = ts2num(start_time)
    window_duration = num_mins*60

    print(start_n, window_duration)

    plt.figure('TV viewing behavior', figsize=(10,2))
    plt.rcParams.update({'font.size': 14})
    plt.yticks([], [])
    plt.ylim([0,1])
    plt.xlim([start_n, start_n + window_duration+5])
    #plt.xlabel('Time stamp (HH:MM)')
    #plt.title('TV viewing behavior')
    
    plt.bar(start_n-3, 1, width=1, color='yellowgreen', label='Gaze')
    plt.bar(start_n-4, 1, width=1, color='deepskyblue', label='No-Gaze')
    plt.legend(bbox_to_anchor=(1.05, 1.0), loc='upper left')
    

    label_xticks = get_xticks(start_n, num_mins)
    print(label_xticks)


    plt.xticks(ticks=range(start_n, start_n + (num_mins+1)*60,60),labels=label_xticks)
    plt.tight_layout()

    for i in range(1000):
        random.shuffle(l)
        val = l[0:1][0]
        
        now_time = datetime.now().time().strftime("%H:%M:%S")
        n_now = ts2num(now_time)
        h,m,s = num2ts(n_now)
        print(now_time, val)

        if val==2:
            time.sleep(0.3)
            continue
            
        colors = 'yellowgreen' if l[0]==1 else 'deepskyblue'
            
        plt.bar(n_now, 1, color=colors, width=1)
        plt.pause(0.01)
        time.sleep(0.3)
        
        if start_n + window_duration == n_now: #(n_now - 1) or start_n + window_duration == (n_now + 1):
            #plt.clf()
            start_n = n_now
            plt.xlim([start_n, start_n + window_duration])
            label_xticks = get_xticks(start_n, num_mins)
            plt.xticks(ticks=range(start_n, start_n + (num_mins+1)*60,60),labels=label_xticks)


    plt.show()
