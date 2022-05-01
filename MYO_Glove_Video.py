# encoding utf-8
import asyncio, threading, time
from bleak import BleakScanner, BleakClient
from util import *
from tkinter import *
import os
from bluetooth import *
import myo, xlrd
import tkinter.ttk as ttk

# 初始设置
DEVICE_NAME = "CUSTOM_UART"
device_addr = "E0:7D:EA:74:D9:0A"
tx_uuid = "00001002-0000-1000-8000-00805f9b34fb"
bluetoothlist = []
glove_data = []
myo_data = []
ret_frame=None
fre = 0.01
import cv2 as cv



class BluetoothConnector:
    def __init__(self, device_addr, device_name, data_uuid):
        self.device_addr = device_addr
        self.device_name = device_name
        self.data_uuid = data_uuid
        self.device_rssi = None
        self.client = None

        # 数据字段
        self.fingers_data = [0, 0, 0, 0, 0]
        self.euler = [0, 0, 0, 0]
        self.pry = [0, 0, 0]
        self.time_stamp=0

        # print("clint has been successfully connected")
        # (self.device_name, "RSSI:", self.device_rssi, "addr:", self.device_addr)

    async def rx_callback(self, sender: int, data: bytearray):
        # data = int(data)
        # print(data)
        global finger_thresold
        data = [i for i in data]
        # print('data',data)
        l = len(data)
        #print(l)
        if l == 68 or l == 248:
            #开发板
            self.time_stamp=timestamp_analyze(data[6:8])

            finger_data = finger_analyze(data[10:20])
            self.fingers_data = finger_data
            euler_data = euler_analyze(data[20:28])
            self.euler = euler_data
            # self.pry = get_earth_angle(self.euler)

            await asyncio.sleep(1)
        elif l == 48:
            #普通版
            self.time_stamp = timestamp_analyze(data[6:8])
            finger_data = finger_analyze_d(data[8:18])
            # print(finger_data)
            self.fingers_data = finger_data
            euler_data = euler_analyze_d(data[28:36])
            self.euler = euler_data
            # self.pry = get_earth_angle(self.euler)
            # print(self.pry)
            await asyncio.sleep(1)
        else:
            # print('Error!')
            pass

    async def init_client(self):
        async def detection_callback(device, advertisement_data):
            # global device_addr, device_rssi
            if device.name == self.device_name:
                self.device_addr = device.address
                self.device_rssi = device.rssi

        async def scan():
            scanner = BleakScanner()
            scanner.register_detection_callback(detection_callback)
            await scanner.start()
            await asyncio.sleep(1)
            await scanner.stop()

        async def disconnect_callback(client):
            print("Client with address {} got disconnected!".format(client.address))

        async def connect():
            self.client = BleakClient(self.device_addr)
            self.client.set_disconnected_callback(disconnect_callback)
            try:
                await self.client.connect()
                # await self.client.start_notify(self.data_uuid, rx_callback)

            except Exception as e:
                print(e)
            await asyncio.sleep(1)

        await scan()
        await connect()


async def output_glove(device1, fre):
    # 主要修改这里
    global glove_data
    while True:
        glove_data = [time.perf_counter()]+[float(i) for i in device1.fingers_data] + device1.euler
        #print('glove',time.perf_counter() ,glove_data)
        await asyncio.sleep(fre)

# async def output_myo(device1, fre):
#     # 主要修改这里
#     global myo_data, myo_device
#     while True:
#         myo_data = list(myo_device.emg) + list(np.array(list(myo_device.orientation))[[1, 2, 3, 0]])
#         print(myo_data)
#         await asyncio.sleep(fre)
#
# async def output_video():
#     global ret_frame,videocapture
#     while (videocapture.isOpened()):
#         ret_frame = videocapture.read()


# def output_glove(device1, fre):
#     # 主要修改这里
#     global glove_data
#     while True:
#         glove_data = [float(i) for i in device1.fingers_data] + device1.euler
#         time.sleep(fre)
#
def output_myo(myo_device,fre):
    # 主要修改这里
    global myo_data
    while True:
        if myo_device is not None:
            myo_data = [time.perf_counter()]+list(myo_device.emg)+list(myo_device.acceleration)+list(myo_device.gyroscope)+list(np.array(list(myo_device.orientation))[[1, 2, 3, 0]])
            #print('myo',time.perf_counter() ,myo_data)
        time.sleep(fre)

def output_video():
    global ret_frame,videocapture
    while (videocapture.isOpened()):
        ret,frame = videocapture.read()
        ret_frame=(ret,frame,time.perf_counter())
        cv.imshow('Camera:Front', ret_frame[1])
        cv.waitKey(1)
        #print(ret_frame)



def capture(fre):
    # print('执行capture')
    # 首先asyncio获取一个主循环
    # loop = asyncio.get_event_loop()
    global myo_device
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)


    # 实例化device
    device1 = BluetoothConnector(device_addr=device_addr, device_name=DEVICE_NAME, data_uuid=tx_uuid)
    # eventloop执行初始化链接操作，run until complete是执行完毕才进行下一个操作
    loop.run_until_complete(device1.init_client())
    # loop执行start notify，开始持续接收手套的数据
    loop.run_until_complete(device1.client.start_notify(device1.data_uuid, device1.rx_callback))
    # loop执行打印操作，将device对象中的data打印出来，这里设置的打印频率是1s，逻辑可以自行更改
    myo_thread = threading.Thread(target=output_myo, args=[myo_device,fre])
    myo_thread.start()
    loop.run_until_complete(output_glove(device1,fre))

    # 结束eventloop


    loop.close()


def save(name, text):
    global glove_data, myo_data,fourcc,ret_frame,finger_thresold
    os.mkdir('data/'+name)
    width = int(videocapture.get(cv.CAP_PROP_FRAME_WIDTH))
    height = int(videocapture.get(cv.CAP_PROP_FRAME_HEIGHT))
    # print(width,height)
    outfile = cv.VideoWriter('data\\'+name+'\\' + name +'_video.mp4', fourcc,  50., (width, height))
    if os.path.exists('data'):
        if not os.path.exists("data\\" + name + ".txt"):
            while True:
                bool_data = [round(float(i)) > 150 for i in glove_data[2:6]]  # 在这里需要调节开发板和普通版的区别80&200
                if glove_data != [] and all(bool_data):
                    text.insert('0.0', name + ': 开始采集\n')
                    break
            while True:
                # int_data = [round(float(i))  for i in glove_data[0:5]]
                if glove_data != []:
                    print(glove_data, file=open("data\\"+name+"\\" + name + "_glove.txt", 'a'))
                    print(myo_data, file=open("data\\"+name+"\\"  + name + "_myo.txt", 'a'))
                    if ret_frame is not None and ret_frame[0]:
                        outfile.write(ret_frame[1])  # 写入文件
                        print(ret_frame[2], file=open("data\\" + name + "\\" + name + "_videotime.txt", 'a'))
                if get_earth_angle([round(float(i)) for i in glove_data[6:]])[0] > 150:
                    text.insert('0.0', name + ': 结束采集\n')
                    break
                time.sleep(fre)
        else:
            text.insert('0.0', name + ': 已经被采集过了，不可以被重复采集\n')
    else:
        os.mkdir('data')
        save(name, text)


def start_capture():
    global E1
    save_thread = threading.Thread(target=save, args=[E1.get()])
    save_thread.start()


async def get_bluetoothlist():
    global bluetoothlist
    devices = await BleakScanner.discover()
    for d in devices:
        bluetoothlist.append((d.name, d.address))


def create_cap():
    global root, v, device_addr

    cap_thread = threading.Thread(target=capture, args=[fre])
    cap_thread.start()

    device_addr = radiobt_list[v.get()][1]

    top = Toplevel()
    top.title('手套采集程序')
    top.geometry('500x500')

    label = Label(top, text="请给硬件三秒时间准备完毕再开始采集,\n关闭后请等待手套蓝光熄灭再进行下一步操作")
    text = Text(top)  # 创建列表组件
    E1 = Entry(top, bd=5)

    StartButton = Button(top, text="开始采集", command=lambda: threading.Thread(target=save, args=[E1.get(), text]).start())
    CloseButton = Button(top, text="关闭", command=top.destroy)

    label.pack(side=TOP)
    CloseButton.pack(side=TOP)

    text.pack(side=BOTTOM)  # 将小部件放置到主窗口中
    StartButton.pack(side=BOTTOM)
    E1.pack(side=BOTTOM)
    root.withdraw()
    top.mainloop()


if __name__ == "__main__":
    videocapture = cv.VideoCapture(0, cv.CAP_DSHOW)
    fourcc = cv.VideoWriter_fourcc(*"mp4v")
    # 定义编码方式并创建VideoWriter对象
    myo.init(os.path.dirname(__file__))  # myo初始化，注意路径下要有之前说的dll文件
    feed = myo.Feed()
    hub = myo.Hub()
    hub.run(1000, feed)
    myo_device = feed.get_devices()  # 获得设备列表
    print(myo_device)
    time.sleep(1)
    myo_device = myo_device[0]  # 我们把设备列表中的第一个作为我们要使用的设备
    myo_device.set_stream_emg(myo.StreamEmg.enabled)
    time.sleep(2)
    # 这里建议停一段时间，因为它不会马上就准备好，如果不停会输出一段空值，具体停多久大家可以自己试一下

    video_thread = threading.Thread(target=output_video)
    video_thread.start()

    asyncio.run(get_bluetoothlist())
    root = Tk()
    root.title('手套采集程序')
    root.geometry('500x500')
    label = Label(root, text="请选择手套的蓝牙")
    label.pack(side=TOP)
    tab_main = ttk.Notebook()  # 创建分页栏
    tab_main.place(relx=0.02, rely=0.02, relwidth=0.887, relheight=0.876)

    tab1 = Frame(tab_main)  # 创建第一页框架

    tab1.place(x=0, y=30)
    tab_main.add(tab1, text='第一页')  # 将第一页插入分页栏中
    radiobt_list = []
    num = 0
    for name, address in bluetoothlist:
        radiobt_list.append((name, address, num))
        num += 1
    v = IntVar()
    for name, address, num in radiobt_list:
        b = Radiobutton(root, text='Name:' + str(name) + ' Address:' + str(address), variable=v, value=num,
                        command=create_cap)
        b.pack(anchor="w")
    root.mainloop()
