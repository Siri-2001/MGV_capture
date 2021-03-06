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

fre = 0.01


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

        # print("clint has been successfully connected")
        # (self.device_name, "RSSI:", self.device_rssi, "addr:", self.device_addr)

    async def rx_callback(self, sender: int, data: bytearray):
        # data = int(data)
        # print(data)
        data = [i for i in data]
        # print('data',data)
        l = len(data)
        # print(l)
        if l == 68 or l == 248:
            finger_data = finger_analyze(data[10:20])
            self.fingers_data = finger_data
            euler_data = euler_analyze(data[20:28])
            self.euler = euler_data
            # self.pry = get_earth_angle(self.euler)

            await asyncio.sleep(1)
        elif l == 48:
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


async def output_device(device1, fre):
    # 主要修改这里
    global glove_data, myo_data, myo_device
    while True:
        glove_data = [float(i) for i in device1.fingers_data] + device1.euler
        myo_data = list(myo_device.emg) + list(np.array(list(myo_device.orientation))[[1, 2, 3, 0]])
        # print(device1.euler,list(myo_device.orientation))
        # print(get_earth_angle(device1.euler),get_earth_angle(np.array(list(myo_device.orientation))[[1, 2, 3, 0]]))
        # 注意这里手套和手环四元数的Z轴是相反的

        # 每打印一个等待 fre 秒
        await asyncio.sleep(fre)


def capture(fre):
    # print('执行capture')
    # 首先asyncio获取一个主循环
    # loop = asyncio.get_event_loop()
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    # 实例化device
    device1 = BluetoothConnector(device_addr=device_addr, device_name=DEVICE_NAME, data_uuid=tx_uuid)
    # eventloop执行初始化链接操作，run until complete是执行完毕才进行下一个操作
    loop.run_until_complete(device1.init_client())
    # loop执行start notify，开始持续接收手套的数据
    loop.run_until_complete(device1.client.start_notify(device1.data_uuid, device1.rx_callback))
    # loop执行打印操作，将device对象中的data打印出来，这里设置的打印频率是1s，逻辑可以自行更改
    loop.run_until_complete(output_device(device1, fre=fre))
    # 结束eventloop
    loop.close()


def save(name, text):
    global glove_data, myo_data
    if os.path.exists('data'):
        if not os.path.exists("data\\" + name + ".txt"):
            while True:
                bool_data = [round(float(i)) > 80 for i in glove_data[1:5]]  # 在这里需要调节开发板和普通版的区别
                if glove_data != [] and all(bool_data):
                    text.insert('0.0', name + ': 开始采集\n')
                    break
            while True:
                # int_data = [round(float(i))  for i in glove_data[0:5]]
                if glove_data != []:
                    print(glove_data + myo_data, file=open("data\\" + name + ".txt", 'a'))
                if get_earth_angle([round(float(i)) for i in glove_data[5:]])[0] > 150:
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
