import numpy as np
import struct
import asyncio
from bleak import BleakScanner, BleakClient
# from util import *

import math


# def connect_device(device_addr, device_name, data_uuid):
def get_earth_angle(orientation):
    def compute_angle(a, b):
        def norm(a):
            return np.sqrt(sum([i ** 2 for i in a.tolist()]))

        cos_ = np.dot(a, b) / (norm(a) * norm(b))
        theta = np.arccos(cos_)
        return theta*180/np.pi
    result_list=[]
    q_0 = orientation[0]
    q_1 = orientation[1]
    q_2 = orientation[2]
    q_3 = orientation[3]
    c_b_E=np.array([[1-2*q_2**2-2*q_3**2,2*(q_1*q_2-q_0*q_3),2*(q_1*q_3+q_0*q_2)],
           [2*(q_1*q_2+q_0*q_3),1-2*q_1**2-2*q_3**2,2*(q_2*q_3-q_0*q_1)],
           [2*(q_1*q_3-q_0*q_2),2*(q_2*q_3+q_0*q_1),1-2*q_1**2-2*q_2**2]])
    z_pos = c_b_E.dot(np.array([0, 0, 1]))
    y_pos = c_b_E.dot(np.array([1, 0, 0]))
    result_list.extend([compute_angle(y_pos,np.array([0, 0, -1])),compute_angle( z_pos,np.array([0, 0, 1]))])
    return np.array(result_list)

def finger_analyze(finger_data):

    # print('finger_data',finger_data)
    res = []
    for i in range(0,len(finger_data),2):
        res.append("%.2f"%((finger_data[i]*25.6+float(finger_data[i+1]/10))))
    try:
        res[3], res[4] = res[4], res[3]
    except:
        print('Error!', res,finger_data)
    # print('finger res',res)
    return res

def timestamp_analyze(time_stamp):
    first = time_stamp[0]
    second = time_stamp[1] & 255
    return first*255+second

def finger_analyze_d(finger_data):
    # print('finger_data',finger_data)
    res = []
    for i in range(0,len(finger_data),2):
        res.append("%.2f"%((finger_data[i]*25.6+float(finger_data[i+1]/10))))
    try:
        res[3], res[4] = res[4], res[3]
    except:
        print('Error!', res,finger_data)
    # print('finger res',res)
    return res
def euler_analyze_d(num_data):
    res = []
    for i in range(0, len(num_data), 2):
        negative = 1
        if num_data[i]>127:
            a = str(num_data[i]-127)
            negative = negative*-1
        else:
            a = str(num_data[i])
        b = str(num_data[i+1])

        if len(a)<2:
            a = "0"+a
        if len(b)<2:
            b = "0"+b
        # print(a,b, num_data[i], num_data[i+1])
        res.append(negative*int(a+b)/10000)
    # print('euler res',res)
    return res
def euler_analyze(num_data):
    res = []
    for i in range(0, len(num_data), 2):
        negative = 1
        if num_data[i]>127:
            a = str(num_data[i]-127)
            negative = negative*-1
        else:
            a = str(num_data[i])
        b = str(num_data[i+1])

        if len(a)<2:
            a = "0"+a
        if len(b)<2:
            b = "0"+b
        # print(a,b, num_data[i], num_data[i+1])
        res.append(negative*int(a+b)/10000)
    # print('euler res',res)
    return res

def calculate_pry(data):
    w = data[0]
    x = data[1]
    y = data[2]
    z = data[3]

    pitch = math.asin(2*(w*y-x*z))*180/math.pi
    yaw = math.atan2(2*(w*z+y*x),(1-2*(z*z+y*y)))*180/math.pi
    roll = math.atan2((2*(w*x+y*z)),(1-2*(x*x+y*y)))*180/math.pi

    return [pitch,roll,yaw]

def check_euler(data):
    res = 0
    for i in data:
        res+=i**2
    return res
