import asyncio, threading, time
from bleak import BleakScanner, BleakClient
from util import *
from tkinter import *
import os
from bluetooth import *


# 初始设置
DEVICE_NAME = "CUSTOM_UART"
device_addr = "E0:7D:EA:74:D9:0A"
tx_uuid = "00001002-0000-1000-8000-00805f9b34fb"
bluetoothlist = []
cur_data = []
glove_timestamp=0
fre = 0.01

class BluetoothConnector:
    def __init__(self,device_addr, device_name, data_uuid):
        self.device_addr = device_addr
        self.device_name = device_name
        self.data_uuid = data_uuid
        self.device_rssi = None
        self.client = None

        # 数据字段
        self.fingers_data = [0, 0, 0, 0, 0]
        self.euler = [0, 0, 0, 0]
        self.pry=[0, 0, 0]
        self.time_stamp = 0
        # print("clint has been successfully connected")
        # (self.device_name, "RSSI:", self.device_rssi, "addr:", self.device_addr)



    async def rx_callback(self, sender: int, data: bytearray):
        # data = int(data)
        # print(data)
        data = [i for i in data]
        # print('data',data)
        l = len(data)
        #print(l)
        if l == 68 or l == 248:
            self.time_stamp = timestamp_analyze(data[6:8])
            print(self.time_stamp)
            finger_data = finger_analyze(data[10:20])
            self.fingers_data = finger_data
            euler_data = euler_analyze(data[20:28])
            self.euler = euler_data
            # self.pry = get_earth_angle(self.euler)

            await asyncio.sleep(1)
        elif l == 48:
            self.time_stamp = timestamp_analyze(data[6:8])
            print(self.time_stamp)
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

async def output_device(device1,fre):
    # 主要修改这里
    global cur_data
    while True:
        cur_data = [float(i) for i in device1.fingers_data]+device1.euler
        print()
        # print(device1.fingers_data, device1.euler)
        # data.append(device1.fingers_data,device1.euler)
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
def save(name,text):
    global cur_data
    if os.path.exists('data'):
        if not os.path.exists("data\\"+name+".txt"):
            while True:
                bool_data=[round(float(i))> 80 for i in cur_data[1:5]]
                if cur_data != [] and all(bool_data):
                    text.insert('0.0', name+': 开始采集\n')
                    break
            while True:
                # int_data = [round(float(i))  for i in cur_data[0:5]]
                if cur_data!=[]:
                    print(cur_data, file=open("data\\"+name+".txt", 'a'))
                if get_earth_angle([round(float(i))  for i in cur_data[5:]])[0]>150:
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

    StartButton = Button(top, text="开始采集", command=lambda :threading.Thread(target=save, args=[E1.get(),text]).start())
    CloseButton = Button(top, text="关闭", command=top.destroy)

    label.pack(side=TOP)
    CloseButton.pack(side=TOP)

    text.pack(side=BOTTOM)  # 将小部件放置到主窗口中
    StartButton.pack(side=BOTTOM)
    E1.pack(side=BOTTOM)
    root.withdraw()
    top.mainloop()


if __name__ == "__main__":
    asyncio.run(get_bluetoothlist())
    root = Tk()
    root.title('手套采集程序')
    root.geometry('500x500')
    label = Label(root, text="请选择手套的蓝牙")
    label.pack(side=TOP)

    radiobt_list = []
    num=0
    for name, address in bluetoothlist:
        # if name.startswith('WULALA'):
            radiobt_list.append((name, address,num))
            num += 1
            # print(name, address)
            # device_addr = address
    v = IntVar()
    for name, address, num in radiobt_list:
        b = Radiobutton(root, text='Name:'+str(name)+' Address:'+str(address), variable=v, value=num, command=create_cap)
        b.pack(anchor="w")
    root.mainloop()



