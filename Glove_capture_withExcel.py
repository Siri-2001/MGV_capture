# encoding utf-8
import asyncio, threading, time
from bleak import BleakScanner, BleakClient
from util import *
from tkinter import *
import os
from bluetooth import *
import myo, xlrd

# 初始设置
DEVICE_NAME = "CUSTOM_UART"
device_addr = "E0:7D:EA:74:D9:0A"
tx_uuid = "00001002-0000-1000-8000-00805f9b34fb"
bluetoothlist = []
glove_data = []


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
    global glove_data
    while True:
        glove_data = [float(i) for i in device1.fingers_data] + device1.euler
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


def save(text, sign_name,start,end):
    global glove_data
    tag = start
    text.insert('0.0', '第一个需要采集的是' + sign_name[tag] + '\n')
    while(tag<end+1):
        if os.path.exists('data'):
            if not os.path.exists("data\\" + sign_name[tag] + ".txt"):
                while True:
                    # print(glove_data)
                    bool_data = [round(float(i)) > 200 for i in glove_data[1:5]]  # 在这里需要调节开发板和普通版的区别，普通版应该在200
                    if glove_data != [] and all(bool_data):
                        text.insert('0.0', sign_name[tag] + ': 开始采集\n')
                        break
                while True:
                    # int_data = [round(float(i))  for i in glove_data[0:5]]
                    if glove_data != []:
                        print(glove_data , file=open("data\\" + sign_name[tag] + ".txt", 'a'))
                    if get_earth_angle([round(float(i)) for i in glove_data[5:]])[0] > 150:
                        text.insert('0.0', sign_name[tag] + ': 结束采集\n')
                        break
                    time.sleep(fre)
            else:
                text.insert('0.0', sign_name[tag] + ': 已经被采集过了，不可以被重复采集\n')
        else:
            os.mkdir('data')
            save(sign_name[tag], text)
        if (tag+1<=end):
            text.insert('0.0','下一个需要采集的是'+sign_name[tag+1]+'\n')
        else:
            text.insert('0.0', '您选择的从'+str(start)+'到'+str(end)+'全部采集已经结束'+'\n')
        tag+= 1


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
    global root, v, device_addr ,sign_name,E_e,E_s,textvar
    if (E_s.get().isdigit() and E_e.get().isdigit()):
        start_i = int(E_s.get()) - 1
        end_i = int(E_e.get()) - 1
        if (start_i >= end_i):
            textvar.set('开始序号大于结束序号')
            return
        # print('选择从', start_i,'到',end_i)
    else:
        textvar.set('开始和结束序号非数字')
        #root.destroy()
        return
    cap_thread = threading.Thread(target=capture, args=[fre])
    cap_thread.start()
    device_addr = radiobt_list[v.get()][1]


    top = Toplevel()
    top.title('手套采集程序')
    top.geometry('500x500')

    label = Label(top, text="请给硬件三秒时间准备完毕再开始采集,\n关闭后请等待手套蓝光熄灭再进行下一步操作")
    text = Text(top)  # 创建列表组件
    # E1 = Entry(top, bd=5)

    StartButton = Button(top, text="开始采集", command=lambda: threading.Thread(target=save, args=[ text, sign_name,start_i,end_i]).start())
    CloseButton = Button(top, text="关闭", command=top.destroy)

    label.pack(side=TOP)
    CloseButton.pack(side=TOP)

    text.pack(side=BOTTOM)  # 将小部件放置到主窗口中
    StartButton.pack(side=BOTTOM)
    # E1.pack(side=BOTTOM)
    root.withdraw()
    top.mainloop()


if __name__ == "__main__":

    excel_path = 'dict'
    xl = xlrd.open_workbook(os.path.join(excel_path, os.listdir(excel_path)[0]))
    table = xl.sheets()[0]
    sign_name = [str(i) for i in table.col_values(0)[1:] if i!='']
    ziped_sign_name = zip(range(1, len(sign_name)+1),sign_name)
    # print("excel加载完成")

    asyncio.run(get_bluetoothlist())
    root = Tk()
    root.title('手套采集程序')
    root.geometry('700x700')
    confirm_Button = Button(root, text="确定", command=create_cap)
    label = Label(root, text="请选择手套的蓝牙")
    label_start = Label(root, text="起始序号")
    label_end = Label(root, text="结束序号")
    textvar = StringVar()  # 这个就是我们创建的容器，类型为字符串类型
    lable_error = Label(root, textvariable=textvar)
    text = Text(root)
    scroll = Scrollbar()
    scroll.pack(side=RIGHT, fill=Y)
    scroll.config(command=text.yview)
    text.config(yscrollcommand=scroll.set)
    E_s = Entry(root, bd=5)
    E_e = Entry(root, bd=5)
    # E_s.insert("end", '起始序号')
    # E_e.insert("end", '结束序号')
    for s in ziped_sign_name:
        text.insert("end", str(s[0])+s[1]+'\n')
    lable_error.pack(side=BOTTOM)
    confirm_Button.pack(side=BOTTOM)
    E_e.pack(side=BOTTOM)
    label_end.pack(side=BOTTOM)
    E_s.pack(side=BOTTOM)
    label_start.pack(side=BOTTOM)
    text.pack(side=BOTTOM)
    label.pack(side=TOP)

    radiobt_list = []
    num = 0



    for name, address in bluetoothlist:
        radiobt_list.append((name, address, num))
        num += 1
    v = IntVar()
    for name, address, num in radiobt_list:
        b = Radiobutton(root, text='Name:' + str(name) + ' Address:' + str(address), variable=v, value=num)
        b.pack(anchor="w")
    root.mainloop()
