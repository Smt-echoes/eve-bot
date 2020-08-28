#!/usr/bin/env python
# coding: utf-8

# In[1]:


import time
import win32gui
import win32api
import pyautogui
import cv2
import statistics

from pynput.keyboard import Key, Listener

from PIL import Image
from numpy import *
import threading


# In[2]:


def debug_show(pos, col=(0, 0, 0)):
    if pos is None:
        return
    try:
        dc = win32gui.GetDC(0)
        c = win32api.RGB(col[0], col[1], col[2])
        for i in range(pos[0], pos[0] + pos[2]):
            win32gui.SetPixel(dc, i, pos[1], c)
            win32gui.SetPixel(dc, i, pos[1] + pos[3], c)
        for i in range(pos[1], pos[1] + pos[3]):
            win32gui.SetPixel(dc, pos[0], i, c)
            win32gui.SetPixel(dc, pos[0] + pos[2], i, c)
    except:
        print("reg range error")


class MeasureTime:
    def __init__(self, module="Ttime:"):
        self.start = None
        self.name = module

    def __enter__(self):
        self.start = time.time()

    def __exit__(self, *ctx):
        print(self.name, ":", time.time() - self.start)

class Averager:
    def __init__(self, max_count=None, max_time=None):
        self.max_count = max_count
        self.max_time = max_time
        self.list = []
        self.time = []

    def count(self, elem=None):
        if elem:
            cnt = 0
            for e in self.list:
                if e == elem:
                    cnt += 1
            return cnt

        return len(self.list)

    def unique(self):
        return len( set(self.list))

    def clear(self):
        self.list.clear()
        self.time.clear()

    def __getitem__(self, item):
        return self.list[item]

    def update(self, elem):
        self.list.append(elem)
        self.time.append(time.time())
        if self.max_count and self.count() > self.max_count:
            self.list.pop(0)
            self.time.pop(0)
        if self.max_time:
            last = self.time[-1]
            while self.count() > 2 and last - self.time[0] > self.max_time:
                self.time.pop(0)
                self.list.pop(0)

    def getDiff(self, step=1):
        diff = 0
        time = 0
        if self.count() < 3:
            return 0
        list = []

        for i, _ in enumerate(self.list):
            j = min(max(i,1),len(self.list) -1)
            list.append( statistics.median(self.list[j-1:j+1]))

        for i, _ in enumerate(self.time):
            if i > 0:
                diff += list[i] - list[i - 1]
                time += self.time[i] - self.time[i - 1]
        return diff * step / time

    def getAve(self):
        summ = 0
        if self.count() < 2:
            return 0
        for item in self.list:
            summ += item
        return summ / self.count()


class KeyHandler(threading.Thread):
    pressed = False
    lock = threading.Lock()

    def __init__(self):
        threading.Thread.__init__(self)
        self.pressed = False
        self.start()

    def run(self) -> None:
        with Listener(
                on_press=KeyHandler.on_press,
                on_release=KeyHandler.on_release) as listener:
            listener.join()

    def on_press(key):
        with KeyHandler.lock:
            if key == Key.shift and KeyHandler.pressed == False:
                ScreenObject.control.acquire()
                KeyHandler.pressed = True
                print("Control override")

    def on_release(key):
        with KeyHandler.lock:
            if key == Key.shift and KeyHandler.pressed == True:
                KeyHandler.pressed = False
                ScreenObject.control.release()

# Collect events until released





class TimeControl:
    def __init__(self):
        self.time = None

    def wait(self, delay):
        if self.time:
            t = self.time + delay
            self.time = time.time()
            w = t - self.time
            if w > 0:
                time.sleep(w)
        else:
            self.time = time.time()



class ScreenObject:
    WINDOW_W = 1920
    WINDOW_H = 1080
    FULLSCREEN = False
    anchor = None
    control = threading.RLock()

    def __init__(self, name, static=True, con=0.8, scale=1.0, num=0, ao=None, filter=None):
        self.name = name
        self.img = cv2.imread(name)

        if scale != 1.0:
            self.img = self.img.resize((int(self.img.size[0] * scale), int(self.img.size[1] * scale)), Image.ANTIALIAS)
        self.static = static
        self.con = con
        self.trgt = {}
        self.reg = ()
        self.num = num
        self.anchor_offset = ao
        self.filter_mask = None
        if filter == "red":
            self.filter_mask = self.img.copy()
            for i in range(self.filter_mask.shape[0]):
                for j in range(self.filter_mask.shape[1]):
                    p = self.filter_mask[i,j]
                    s = int(p[2]) - max(p[1],p[0])
                    self.filter_mask[i, j] = (0,0,0) if s < 70 else p
        elif filter == "white":
            self.filter_mask = self.img.copy()
            for i in range(self.filter_mask.shape[0]):
                for j in range(self.filter_mask.shape[1]):
                    p = self.filter_mask[i, j]
                    l = 80
                    s = not(p[2] > l and p[1] > l and p[0] > l)
                    self.filter_mask[i, j] = (0, 0, 0) if  s else p

            #cv2.imshow("mask", self.filter_mask)
            #cv2.waitKey(0)
        elif filter is not None:
            self.filter_mask = cv2.imread(filter)
            for i in range(self.filter_mask.shape[0]):
                for j in range(self.filter_mask.shape[1]):
                    p = self.filter_mask[i,j]
                    self.filter_mask[i, j] = (0,0,0) if tuple(p) != (0,255,0) else self.img[i,j]







    def update(self):

        im = pyautogui.screenshot()
        if ScreenObject.FULLSCREEN:
            im = im.resize((ScreenObject.WINDOW_W, ScreenObject.WINDOW_H))

        if self.reg:
            self.trgt = pyautogui.locate(self.img, im, region=self.reg, confidence=self.con, mask=self.filter_mask)

        if (not self.trgt) and (self.reg == () or not self.static):
            reg = None
            name = "anchor_f.png" if ScreenObject.FULLSCREEN else "anchor.png"
            if self.name != name:
                if ScreenObject.anchor is None:
                    ScreenObject.anchor = ScreenObject(name)
                if ScreenObject.anchor.reg == ():
                    ScreenObject.anchor.update()

                if ScreenObject.anchor.reg != ():
                    reg = (ScreenObject.anchor.reg[0] + (self.anchor_offset[0] if self.anchor_offset else 0),\
                           ScreenObject.anchor.reg[1] + (self.anchor_offset[1] if self.anchor_offset else 0),\
                           ScreenObject.anchor.reg[2] + ScreenObject.WINDOW_W + (self.anchor_offset[3] if self.anchor_offset else 0),\
                           ScreenObject.anchor.reg[3] + ScreenObject.WINDOW_H + (self.anchor_offset[3] if self.anchor_offset else 0))
                else:
                    return
            #if reg:
            #    debug_show(reg)
            self.generator = pyautogui.locateAll(self.img, im, confidence=self.con, region=reg, mask=self.filter_mask)

            for i, trgt in enumerate(self.generator):
                if self.num == i:
                    self.trgt = trgt
                    break

        if self.trgt and (self.reg == () or self.static is False):
            self.reg = (self.trgt.left, self.trgt.top, self.trgt.width, self.trgt.height)

    def status(self):
        return "found" if self.trgt else "not found"

    def reset(self):
        self.generator = None
        self.trgt = None
        self.reg = ()

    def next(self):
        if self.generator:
            try:
                self.trgt = next(self.generator)
                self.reg = (self.trgt.left, self.trgt.top, self.trgt.width, self.trgt.height)
            except StopIteration:
                self.trgt = None
                self.reg = ()
        else:
            self.update()

        return self

    def __iter__(self):
        while True:
            yield self
            self.next()
            if not self.trgt:
                return

    def click(self):
        try:
            if self.trgt:
                trgt = self.trgt;
                if ScreenObject.FULLSCREEN:
                    trgt = tuple([i*2 for i in trgt])
                with ScreenObject.control:
                    pyautogui.click(trgt)
                print("click: ", self.name[:len(self.name) - 4])
        except:
            print("err: click exception")


class ScreenIndicator(ScreenObject):
    MASK_KEY = (0, 255, 0)

    def __init__(self, name, mask, key, scale=1.0, num=0, th=30, con=0.8, ao = None, filter=None):
        ScreenObject.__init__(self, name, static=True, con=con, scale=scale, num=num, ao=ao, filter=filter)
        self.mask = []
        self.mask_pos = []
        self.cur = []
        self.off = []
        for m in mask:
            im = cv2.imread(m)
            if scale != 1.0:
                im = im.resize(tuple([int(s * scale) for s in im.size]), Image.ANTIALIAS)

            pix_arr = []

            rows,cols = im.shape[:2]
            for i in range(rows):  # for every pixel:
                for j in range(cols):
                    if tuple(im[i, j]) == ScreenIndicator.MASK_KEY:
                        pix_arr.append((j,i))

            off = pyautogui.locate(self.img, im)
            if not off:
                off = pyautogui.locate(self.img, im, confidence=0.6)
                if not off:
                    print("err:find offset" ,self.name, m)
            self.off.append(off)
            self.mask.append(im)
            self.mask_pos.append(pix_arr)
            self.cur.append(0.0)

        self.lock = threading.Lock()
        # print(name, self.off)
        self.key = key
        self.th = th


    def scanMask(self):


        im = None
        cur = []
        for i, mask in enumerate(self.mask_pos):
            count = 0
            summ = 0
            key = self.key[i]

            reg = None
            if i == 0 or not\
                (self.off[i].left == self.off[i-1].left and \
                    self.off[i].top == self.off[i-1].top and \
                    self.mask[i].shape[1] <= self.mask[i-1].shape[1] and \
                    self.mask[i].shape[0] <= self.mask[i-1].shape[0]):

                    if self.reg and self.off:
                        reg = (self.reg[0] - self.off[i].left, self.reg[1] - self.off[i].top,
                               self.mask[i].shape[1], self.mask[i].shape[0])

                        if ScreenObject.FULLSCREEN:
                            full_reg = tuple([i * 2 for i in reg])
                            im = pyautogui.screenshot(region=full_reg)
                            im = im.resize((self.mask[i].shape[1], self.mask[i].shape[0]))
                        else:
                            im = pyautogui.screenshot(region=reg)

            for pos in mask:  # for every pixel:
                pix = im.getpixel(pos)
                count += 1
                if abs(pix[0] - key[0]) < self.th and \
                        abs(pix[1] - key[1]) < self.th and \
                        abs(pix[2] - key[2]) < self.th:
                    summ += 1

            cur.append(summ / (count + 1))
            if count == 0:
                print("mask fail:", count, summ, self.name, self.mask, reg)
        return cur

    def update(self):

        with ScreenObject.control:
            pass

        if not self.reg:
            ScreenObject.update(self)

        if self.reg:
            res = self.scanMask()
            with self.lock:
                self.cur = res

    def getValue(self, idx=0):
        with self.lock:
            return self.cur[idx]

    def click(self, mask = False):
        if self.trgt and not mask:
            ScreenObject.click(self)
        else:
            if self.reg:
                print("blind click: ", self.name[:len(self.name) - 4])
                with ScreenObject.control:
                    if mask:
                        pyautogui.click(\
                            self.reg[0] - self.off[0].left + int(self.mask[0].shape[0]/2),\
                            self.reg[1] - self.off[0].top +  int(self.mask[0].shape[0]/2))
                    else:
                        pyautogui.click(self.reg[0] + self.reg[2] / 2, self.reg[1] + self.reg[3] / 2)


class Botton():
    def __init__(self):
        self.expectedState = "inactive"
        self.lock = threading.Lock()

    def switchState(self):
        self.expectedState = ("inactive" if self.expectedState == "active" else "active")
        return self.expectedState

    def State(self):
        return self.expectedState

    def set(self, state):
        with self.lock:
            if self.expectedState != state:
                print("set", self.name, state)
                self.click()
                self.switchState()
                self.vals.clear()


class ModuleBotton(ScreenIndicator, threading.Thread, Botton, TimeControl):
    MAX_VALS = 5
    TIME_PACE = 2

    def __init__(self, name, mask, scale=1.0, num=0):
        threading.Thread.__init__(self)
        Botton.__init__(self)
        ScreenIndicator.__init__(self, name, (mask,), key=((215, 252, 239),), scale=scale, num=num, th=10)
        TimeControl.__init__(self)
        self.vals = Averager(max_count=self.MAX_VALS)
        self.work = True
        self.start()

    def __del__(self):
        self.work = False
        self.join()

    def updateState(self):

        if self.reg == ():
            return

        with ScreenObject.control:
            pass

        with self.lock:
            if self.vals.count() < self.MAX_VALS:
                return
            #if self.name == "ab_btn_2.png":
            #    print("switch", self.name, self.vals.list)
            cnt = self.vals.unique()

            if self.expectedState == "active":
                if cnt > 1:
                    return
            else:
                if cnt < self.MAX_VALS:
                    return
            #print("switch", self.name, self.vals.list)
            self.switchState()
            return

        return

    def update(self):

        ScreenIndicator.update(self)

        if self.reg:
            val = self.getValue()

            self.vals.update(val)

            self.updateState()

    def run(self):
        while self.work:
            self.update()
            self.wait(self.TIME_PACE)


class DroneModule(ScreenObject, Botton, threading.Thread, TimeControl):
    MAX_VALS = 5
    CON_VAL = 1
    TIME_PACE = 0.5

    def __init__(self, name, scale=1.0):
        threading.Thread.__init__(self)
        ScreenObject.__init__(self, name, scale=scale)
        Botton.__init__(self)
        self.attack = ScreenObject("drones_attack.png")
        self.vals = Averager(max_count=self.MAX_VALS)
        self.time = time.time()
        self.lock = threading.Lock()
        self.work = True
        self.start()

    def __del__(self):
        self.work = False
        self.join()

    def update(self):

        with ScreenObject.control:
            pass

        if self.reg:
            self.attack.update()
            self.vals.update("active" if self.attack.status() == "found" else "inactive")

            if self.vals.count() < self.MAX_VALS:
                return

            with self.lock:
                if self.vals.count(self.expectedState) >= self.CON_VAL:
                    return

                self.switchState()
                return

        else:
            ScreenObject.update(self)

        return

    def run(self):
        while self.work:
            if self.State() == "active":
                self.update()
            self.wait(self.TIME_PACE if self.expectedState == "active" else 1)


class Overview:
    ao = (1340, 0, -1340, 0)
    ov_btn = ScreenObject("ov_btn.png", static=False, ao=ao)
    # ov_filter = ScreenObject("ov_open.png", static=False, con=0.9)

    ov_mode = {"loot": ScreenObject("ov_type_loot.png", ao=ao),
               "anomaly": ScreenObject("ov_type_anomaly.png", ao=ao),
               "planet": ScreenObject("ov_type_planet.png", ao=ao),
               "all": ScreenObject("ov_type_all.png", ao=ao),
               "station": ScreenObject("ov_type_station.png", ao=ao),
               "ship": ScreenObject("ov_type_ship.png", ao=ao)}
    sbm_btn = ScreenObject("sbmn_btn.png", ao=ao)
    ao =  (1340, 137, -1340, -137)
    sbm_mode = {"loot": ScreenObject("loot_sbmn.png", ao=ao),
                "anomaly": ScreenObject("anomaly_sbm.png", ao=ao),
                "planet": ScreenObject("planet_sbm.png", ao=ao),
                "all": ScreenObject("all_sbm.png", ao=ao),
                "station": ScreenObject("station_sbm.png", ao=ao),
                "ship": ScreenObject("ships_sbm.png", ao=ao)}

    def __init__(self):
        self.lastMode = None
        return

    def State(self):
        self.sbm_btn.update()
        return "open" if self.sbm_btn.status() == "found" else "closed"

    def Close(self):
        if self.State() == "open":
            self.ov_btn.update()
            self.ov_btn.click()
            time.sleep(1)

    def __exit__(self, *exc):
        self.Close()
        return

    def GetMode(self):

        if self.lastMode is not None:
            self.ov_mode[self.lastMode].update()
            if self.ov_mode[self.lastMode].status() == "found":
                return self.lastMode

        for mode in self.ov_mode:
            self.ov_mode[mode].update()
            if self.ov_mode[mode].status() == "found":
                self.lastMode = mode
                return mode
        return "none"

    def SwitchMode(self, mode):
        if mode != "none":
            while self.GetMode() != mode:
                with ScreenObject.control:
                    while self.State() != "open":
                        self.ov_btn.click()
                        time.sleep(0.5)

                    self.sbm_btn.click()
                    time.sleep(0.3)

                    self.sbm_mode[mode].update()
                    if self.sbm_mode[mode].status() == "found":
                        self.sbm_mode[mode].click()
                        self.lastMode = mode
                        time.sleep(0.5)
                        break

    def Open(self, mode="none"):
        while self.State() != "open":
            self.ov_btn.update()
            self.ov_btn.click()
            time.sleep(0.5)
        print("open", mode)
        self.SwitchMode(mode)
        return self

    def __enter__(self):
        return


class ShipStatus(threading.Thread, TimeControl):
    def __init__(self, obj):
        threading.Thread.__init__(self)
        TimeControl.__init__(self)
        self.bar = ScreenIndicator("bar.png", \
                    ("shield_mask.png", "armor_mask.png", \
                     "structure_mask.png", "energy_mask.png"), \
                   key=((250, 250, 250),(205,205,205),(150,150,150),(255,255,220)))
        self.names = {"shield": 0, "armor": 1, "structure": 2, "energy": 3}
        self.max = {"shield": 0.645, "armor": 0.672, "structure": 0.76, "energy": 0.562}
        self.objects = obj
        self.work = True
        self.hp = Averager(max_time=15)
        self.ave = [Averager(max_time=15) for i in range(4)]
        self.lock = threading.Lock()
        self.start()

    def __del__(self):
        self.work = False
        self.join()

    def update(self):
        with ScreenObject.control:
            pass

        self.bar.update()

        if self.get("structure") < 1:
            #closeAll()  # ensure no open windows
            return #no bar visible

        with self.lock:
            self.hp.update( self.get("shield") + self.get("armor") + self.get("structure") )
            for i,type in enumerate(self.names):
                self.ave[i].update(self.get(type))


        if "rep" in self.objects:
            persent = (90, 80)
            shieldTime = self.estimateLifetime(type="shield")
            for i, r in enumerate(self.objects["rep"] ):
                if self.get("armor") < persent[i] or shieldTime < 10:
                    r.set("active")
                elif self.estimateLifetime() > 500:
                    r.set("inactive")



    def get(self, name):
        if self.bar.reg:
            idx = self.names[name]
            return int(self.bar.getValue(idx=idx) / self.max[name] * 100.)
        else:
            return 0

    def estimateLifetime(self, type = None):
        with self.lock:
            hp = self.hp if type is None else self.ave[self.names[type]]
            diff = hp.getDiff(step=1)
            if hp.count() < 2 or diff >= 0:
                return 999

            return -hp.getAve() / diff

    def run(self):
        while self.work:
            #with MeasureTime("stat"):
            self.update()
            self.wait(1)


# In[3]:


class BaseLogic:
    def __init__(self, obj):
        self.objects = obj

    def execute(self):
        return self

close = ScreenObject("close.png", con=0.95)
def closeAll():
    for i in range(5):
        with ScreenObject.control:
            close.update()
            if close.status() == "found":
                with ScreenObject.control:
                    close.click()
                time.sleep(0.5)
            else:
                break


def ProcessDialogBotton(btn, timeout=100, pop=True):
    btn_close = ScreenObject("close.png")
    start = time.time()
    while True:  # wait dialog open
        btn.update()
        if btn.status() == "found":
            break

        time.sleep(1)
        if time.time() - start > timeout:
            return False

    btn.click()
    time.sleep(0.5)

    while pop:  # check dialog closed
        btn.update()
        if btn.status() != "found":
            break
        print("additional click")
        btn.click()
        time.sleep(1)
        if time.time() - start > timeout:
            btn_close.update()
            if btn_close.status() == "found":
                btn_close.click()
                time.sleep(0.5)
            return False

    return True


class LootingLogic(BaseLogic):
    loot_type = (ScreenObject("loot0.png", static=False, con=0.95), ScreenObject("loot1.png", static=False))
    loot_btn = ScreenObject("loot_btn.png", static=False)
    loot_all = ScreenObject("loot_all.png", static=False)
    btn_close = ScreenObject("close.png")

    def __init__(self, obj):
        BaseLogic.__init__(self, obj)

    def execute(self):
        ov = self.objects["OV"]
        enemy = self.objects["enemy"]
        ab = self.objects["ab"]

        ov.Open(mode="loot")

        while True:
            loot = None
            for loot in self.loot_type:
                loot.update()
                if loot.status() == "found":
                    break

            if loot.status() != "found":
                break
            with ScreenObject.control:
                print("looting")
                loot.click()

                if not ProcessDialogBotton(self.loot_btn, 5):
                    print("loot btn not found")
                    closeAll()
                    continue

            ab.set("active")

            if not ProcessDialogBotton(self.loot_all, 120):
                print("loot_all btn not found")
                closeAll()
                break

            enemy.update()
            if enemy.status() == "found":
                ov.Close()
                return

        ov.Close()
        ab.set("inactive")

class TargetLogic(threading.Thread, TimeControl):

    def __init__(self, obj):
        threading.Thread.__init__(self)
        TimeControl.__init__(self)
        self.objects = obj
        lock_ao = (880, 390, -880,-390)
        self.autolock = (ScreenObject("target.bmp", con=0.7, ao=lock_ao), \
                        ScreenObject("trgt_2.png", con=0.7, ao=lock_ao))
        trgt_ao=(920, 100, -900, -ScreenObject.WINDOW_H + 30)
        self.npc = {"frigate":ScreenIndicator("frigate.png",mask=("frigate_mask.png",), key=((120,110,100),) ,filter="red", con=0.97, ao=trgt_ao),
                    "destr":ScreenIndicator("destr.png",mask=("destr_mask.png",), key=((120,110,100),) ,filter="red", con=0.97, ao=trgt_ao),}
                    #"destr":ScreenObject("npc_destr.png", con=0.7, static=False, ao=trgt_ao),}
                    #"cruiser":ScreenObject("npc_cruiser.png", static=False)}
        self.focus_fire = ScreenObject("focus_fire.png", static=False)
        self.focused = None
        self.targets = {"frigate", "destr"}
        self.active = False
        self.start()

    def setOrder(self, order):
        self.targets = order
        return self

    def __enter__(self):
        self.active = True

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.active = False

    def run(self) -> None:
        update_target_cd = 0
        while True:
            self.wait(1)

            if self.active == False:
                continue

            for lock in self.autolock:
                lock.update()
                if lock.status() == "found":
                    lock.click()
                    break



            for t in self.npc:
                found = False
                while True:
                    ScreenObject.update(self.npc[t])
                    if self.npc[t] == self.focused:
                        if self.npc[t].status() == "found":
                            update_target_cd = 5
                            self.focused = self.npc[t]
                        else:
                            update_target_cd -= 1

                        found = update_target_cd > 0

                    elif self.npc[t].status() == "found":
                        if update_target_cd <= 0 or not self.focused:
                            self.focused = self.npc[t]
                            update_target_cd = 5
                        else:
                            ScreenObject.update(self.focused)
                            update_target_cd -= 1
                        found = True

                    elif self.npc[t].reg != ():
                            self.npc[t].reset()
                            continue
                    break

                if found:
                    break


            if self.focused:
                self.focused.update()
                if self.focused.getValue() < 0.4 and self.focused.status() == "found":
                    print("targeting ", t)
                    with ScreenObject.control:
                        self.focused.click()
                        ProcessDialogBotton(self.focus_fire, 2)
                    if "nosf" in self.objects:
                        self.objects["nosf"].set("inactive")
                    if "web" in self.objects:
                        self.objects["web"].set("inactive")







class BaseCombat(BaseLogic, TimeControl):
    def __init__(self, obj):
        BaseLogic.__init__(self, obj)
        TimeControl.__init__(self)
        self.targeting = TargetLogic(obj)
        self.stat = obj["stat"]
        self.rep = None
        self.wep = {}
        self.cmbt_mod = {}

        self.nosf = None
        self.hrd = None
        self.plate = None

    def retreat(self):
        print("retreat")
        planet = ScreenObject("planet.png", static=False)
        warp = ScreenObject("warp.png", static=False)
        ov = self.objects["OV"]

        with ScreenObject.control:
            ov.Open(mode="planet")

            planet.update()
            if planet.status() == "found":
                planet.click()
            else:
                print("planet not found")
                return False

            if not ProcessDialogBotton(warp, 5):
                print("warp fail")
                return False

        return True

    def onCombat(self):
        stat = self.stat

        lifetime = stat.estimateLifetime()
        ar_lifetime = stat.estimateLifetime(type="armor")
        print("lifetime", lifetime, ar_lifetime)

        if ar_lifetime < 25 or lifetime < 60:
            print("bad prediction lifetime", lifetime)
            print(stat.hp.list)
            if self.plate:
                self.plate.set("active")
            return "retreat"

        if stat.get("armor") < 20 and lifetime < 100:
            print("low armor", stat.get("armor"))
            if self.plate:
                self.plate.set("active")
            return "retreat"

        # print("wep:",objects["web"].status(), objects["web"].State(), objects["web"].getValue())
        # print("nos", objects["nosf"].status(), objects["nosf"].State(), objects["nosf"].getValue())
        print('SH:', stat.get("shield"), "A:", stat.get("armor"), "ST:", stat.get("structure"), "E:",
              stat.get("energy"))

        return "none"

    def onEnemy(self):
        stat = self.stat
        wep = self.wep
        cmbt_mod = self.cmbt_mod

        for w in wep:
            wep[w].set("active")

        if self.nosf:
            self.nosf.set("active")

        if self.ab:
            self.ab.set("active")

        if self.hrd:
            self.hrd.set("active" if stat.get("shield") < 30 else "inactive")

        for mod in cmbt_mod:
            cmbt_mod[mod].set("active" if stat.get("energy") > 30 else "inactive")

        return

    def onCombatExit(self):
        stat = self.stat
        rep = self.rep[0]
        cmbt_mod = self.cmbt_mod

        if self.rep:
            rep.set("active" if stat.get("armor") > 99 else "inactive")

        if self.hrd:
            self.hrd.set("inactive")

        if len(self.rep) > 1:
            rep[1].set("inactive")

        for mod in cmbt_mod:
            cmbt_mod[mod].set("inactive")

        return

    def execute(self):
        outOfCombatTimer = 10
        print("combat logic")
        exitStatus = "none"
        with self.targeting:
            if True:
                while True:

                    objects["enemy"].update()
                    enemy = objects["enemy"].status() == "found"

                    if self.onCombat() == "retreat":
                        if self.retreat():
                            exitStatus = "retreat"
                            break

                    if enemy:
                        print("enemy")
                        exitStatus = "loot"
                        outOfCombatTimer = 5

                        self.onEnemy()

                    else:
                        print("exit combat", outOfCombatTimer)
                        outOfCombatTimer = outOfCombatTimer - 1
                        if outOfCombatTimer < 4:
                            self.ab.set("inactive")

                        if (outOfCombatTimer <= 0):
                            break

                    self.wait(1)

            return exitStatus


class MissionLogic(BaseLogic):
    def __init__(self, obj):
        BaseLogic.__init__(self, obj)
        self.mission_btn = ScreenObject("mis_btn.png", static=False, con=0.7)
        self.news_btn = ScreenObject("news_btn.png")
        self.mis_type = {"combat": ScreenObject("mis_combat.png", static=False, con=0.7),
                         "delivery": ScreenObject("mis_delivery.png", static=False), }
        self.mis_taken = {"combat": ScreenObject("mis_combat_t.png", static=False),
                          "delivery": ScreenObject("mis_delivery_t.png", static=False), }
        self.accept = ScreenObject("accept.png", static=False, con=0.9)
        self.begin = ScreenObject("begin.png", static=False, con=0.9)
        self.confirm = ScreenObject("confirm.png", static=False, con=0.9)
        self.refresh = ScreenObject("refresh.png")
        self.refresh_sts = ScreenObject("refresh_status.png")
        self.delivery_finish = ScreenObject("delivery_finish.png", static=False)
        self.face = (ScreenObject("dialog.png", static=False),
                     ScreenObject("dialog2.png", static=False),
                     ScreenObject("dialog3.png", static=False),)
        self.risk = ScreenObject("risk.png", static=False, con=0.7)
        self.filter = ScreenObject("filter.png")
        self.high_sec = ScreenIndicator("high_sec.png", ("high_sec_mask.png",), key=((228,200,134),), filter="white", con=0.99)

    def filterType(self, type):
        print("select", type)
        self.filter.update()
        if self.filter.status() == "found":
            self.filter.click()
            time.sleep(5)

            for i in range(2):
                self.high_sec.update()
                if self.high_sec.status() == "found":
                    val = self.high_sec.getValue()
                    if (type == "high" and val <= 0.01) or \
                        (type == "low" and val > 0.01):
                        self.high_sec.click(mask=True)
                        self.high_sec.update()
                        if(val == self.high_sec.getValue()):
                            print("err: high sec doesnt change")
                            self.high_sec.reset()
                            continue
                else:
                    self.high_sec.reset()
                    print("err: high sec not found")
                    continue
                break

            self.filter.click()
            time.sleep(5)
        else:
            print("err: filter btn not found")

    def getRidOfFace(self):
        print("fucking faces")
        wereFaces = False
        while True:
            repeat = False
            for face in self.face:
                face.update()
                while face.status() == "found":
                    for i in range(5):
                        face.click()
                        time.sleep(0.3)
                    face.update()
                    repeat = True
                    wereFaces = True
            if repeat == False:
                break
            else:
                time.sleep(1)

        return wereFaces

    def scanMission(self, arr, types=None):
        for type in (types if types != None else arr):
            arr[type].update()
            print("scan:", type)
            if arr[type].status() == "found":
                return arr[type], type
        return None, "None"

    def execute(self, types):
        enemy = self.objects["enemy"]

        for i in range(1, 5):  # check no enemy left
            enemy.update()
            if enemy.status() == "found":
                return "none", None
            time.sleep(1)

        print("finish mission")
        self.getRidOfFace()
        print("starting mission")
        while True:

            with ScreenObject.control:
                if not ProcessDialogBotton(self.mission_btn, 5):
                    closeAll()
                    continue

                print("search for open missions")
                mission, missionType = self.scanMission(arr=self.mis_taken, types=types)

                if mission == None:
                    print("search for new missions")
                    if not ProcessDialogBotton(self.news_btn, 5):
                        closeAll()
                        continue

                    for t in ("low", "high"):
                        self.filterType(t)

                        for i in range(2):
                            mission, missionType = self.scanMission(arr=self.mis_type, types=types)

                            if mission == None:
                                self.refresh_sts.update()
                                self.refresh.update()
                                if self.refresh_sts.status() == "found" and \
                                        self.refresh.status() == "found":
                                    print("refresh")
                                    self.refresh.click()
                                    time.sleep(2)
                                    continue
                                break;

                        if mission:
                            break

                    if mission == None:
                        continue

                    if not ProcessDialogBotton(mission, 5):
                        closeAll()
                        continue

                    if not ProcessDialogBotton(self.accept, 5, pop=False):
                        closeAll()
                        continue

                    self.confirm.update()
                    if self.confirm.status() == "found":
                        if not ProcessDialogBotton(self.confirm, 5):
                            closeAll()
                            continue

                else:
                    print("select open mission")
                    if not ProcessDialogBotton(mission, 5):
                        closeAll()
                        continue

                self.risk.update()

                if not ProcessDialogBotton(self.begin, 5, pop=False):
                    closeAll()
                    continue

            self.getRidOfFace()

            print("mission comuting: ", mission, "risk ", self.risk.status())

            checkFaces = True
            while True:
                time.sleep(0.5)
                self.confirm.update()
                if (self.confirm.status() == "found"):  # confirm everything
                    if not ProcessDialogBotton(self.confirm, 5):
                        continue

                if missionType == "combat":
                    enemy.update()
                    if enemy.status() == "found":
                        break
                elif missionType == "delivery":

                    self.getRidOfFace()

                    self.delivery_finish.update()
                    if self.delivery_finish.status() == "found":
                        ProcessDialogBotton(self.delivery_finish, 5)

                        self.getRidOfFace()
                        break

            return missionType, ("risk" if  self.risk == "found" else None)


class RattingLogic(BaseLogic, TimeControl):
    def __init__(self, obj):
        BaseLogic.__init__(self, obj)
        TimeControl.__init__(self)
        self.types = {"inquisitor": ScreenObject("inquisitor.png", static=False),
                      "scout": ScreenObject("scout.png", static=False),
                      "small": ScreenObject("small.png", static=False),
                      "medium": ScreenObject("medium.png", static=False),
                      "large": ScreenObject("large.png", static=False), }
        self.warp = ScreenObject("warp.png", static=False)
        self.jumpGate = ScreenObject("jumpgate.png", static=False)
        self.activate = ScreenObject("activate.png", static=False)

    def scanAnomalies(self, arr, types=None):
        for type in (types if types != None else arr):
            arr[type].update()
            print("scan:", type)
            if arr[type].status() == "found":
                return arr[type], type
        return None, "none"

    def warping(self, WARP_TIMEOUT=40):
        ov = self.objects["OV"]
        start = time.time()
        print("warping")
        with ov.Open("all"):
            self.jumpGate.update()
            fromJG = self.jumpGate.status() == "found"

            while time.time() - start < WARP_TIMEOUT:

                self.objects["enemy"].update()
                if self.objects["enemy"].status() == "found":
                    break

                self.jumpGate.update()
                if self.jumpGate.status() == "found":
                    if not fromJG:
                        break
                else:
                    fromJG = False;

                if self.objects["stat"].get("armor") < 50:
                    break

                time.sleep(1)

    def jumpFurther(self):
        ov = self.objects["OV"]
        print("activating jumpgate")
        with ScreenObject.control:
            with ov.Open("all"):
                self.jumpGate.update()
                if self.jumpGate.status() != "found":
                    print("no gate")
                    return False

                self.jumpGate.click()
                time.sleep(0.2)

                if not ProcessDialogBotton(self.activate, 5):
                    print("activate fail")
                    closeAll()
                    return False

        self.warping(WARP_TIMEOUT=15)

        return True

    def execute(self, required_types=None):
        print("start ratting")
        ov = self.objects["OV"]

        with ScreenObject.control:
            with ov.Open(mode="anomaly"):

                anomaly, anomalyType = self.scanAnomalies(arr=self.types, types=required_types)

                if anomaly:
                    print("anomaly found:", anomalyType)
                    anomaly.click()
                    time.sleep(0.5)
                else:
                    return "none"

                if not ProcessDialogBotton(self.warp, 5):
                    print("warp fail")
                    closeAll()
                    return "none"

        self.warping()

        return anomalyType, None


class CoerserCombat(BaseCombat):
    def __init__(self, obj):
        # update module size
        objects["rep"] = ModuleBotton("rep_btn.png", "rep_mask.png")
        objects["ab"] = ModuleBotton("ab_btn.png", "ab_mask.png")

        BaseCombat.__init__(self, obj)

        self.rep = (objects["rep"], ModuleBotton("rep_btn.png", "rep_mask.png", num=1))
        self.wep = {"laser": ModuleBotton("wep_btn.png", "wep_mask.png")}

        self.cmbt_mod = {"web": ModuleBotton("web.png", "web_mask.png"),
                         "ab": objects["ab"], }

        self.nosf = ModuleBotton("nosf.png", "nosf_mask.png")
        #self.hrd = ModuleBotton("arm_hrd.png", "arm_hrd_mask.png")


class DragonCombat(BaseCombat):
    def __init__(self, obj):
        # update module size
        objects["rep"] = ModuleBotton("rep_btn.png", "rep_mask.png", scale=0.82)
        objects["ab"] = ModuleBotton("ab_btn.png", "ab_mask.png", scale=0.82)

        BaseCombat.__init__(self, obj)
        self.rep = (objects["rep"],)
        self.wep = {"rockets": ModuleBotton("rocket.png", "rocket_mask.png"),
                    "drones": DroneModule("drones.png")}

        self.cmbt_mod = {"ab": objects["ab"], }

        self.nosf = None
        self.hrd = None

class StabberCombat(BaseCombat):
    def __init__(self, obj):
        # update module size
        objects["rep"] = (ModuleBotton("rep_btn_2.png", "rep_mask_2.png"),)
        objects["ab"] = ModuleBotton("ab_btn_2.png", "ab_mask_2.png")
        objects["nosf"] = ModuleBotton("nosf_btn_2.png", "nosf_mask_2.png")

        BaseCombat.__init__(self, obj)
        self.rep = objects["rep"]
        self.wep = {"cannon": ModuleBotton("cannon.png", "cannon_mask.png"),
                    "drones": DroneModule("drones.png")}

        self.ab = objects["ab"]

        self.nosf = objects["nosf"]

        self.cmbt_mod = {"web": ModuleBotton("web_btn_2.png", "web_mask_2.png")}

        self.hrd = None#ModuleBotton("hrd_btn_2.png", "hrd_mask_2.png")
        self.plate = ModuleBotton("plate.png", "plate_mask.png")
    # In[4]:


keyHandler = KeyHandler()
objects = {}
objects["enemy"] = ScreenObject("enemy.bmp", static=False)
objects["OV"] = Overview()
objects["stat"] = ShipStatus(objects)
combat = StabberCombat(objects)
looting = LootingLogic(objects)
mission = MissionLogic(objects)
ratting = RattingLogic(objects)

work = "mission"
task = "none"
risk = None
while True:
    ret = combat.execute()
    if ret != "retreat":

        if work == "mission":
            mission.getRidOfFace()

        if task[0] == "inquisitor" or task[0] == "scout":
            if ratting.jumpFurther():
                time.sleep(5)
                continue

        if ret == "loot":
            looting.execute()
        print(task)

        if work == "rating":
            combat.retreat()
            time.sleep(20)

    if ret == "retreat":
        print("wait 40")
        time.sleep(40)

    st = objects["stat"].get("structure")
    if st < 98 and st > 0:
        with objects["OV"].Open(mode="station"):
            station = ScreenObject("station.png", static=False)
            station.update()
            if station.status() == "found":
                station.click()
                time.sleep(1)

                dock = ScreenObject("dock.png", static=False)
                ProcessDialogBotton(dock, 5)

                work = "mission"
                dock = ScreenObject("undock.png", static=False)
                ProcessDialogBotton(dock, 60)

            elif objects["stat"].get("structure") < 50:
                print("STOP")
                break




    #if task == "none":
    #    work = "rating" if work == "mission" else "mission"
    #elif work == "mission":
    #    work = "rating"
    if ret != "retreat" and not risk:
        task = ratting.execute(required_types=("inquisitor", "scout"))
        if task != "none":
            work = "rating"
            continue
        else:
            work = "mission"

    if work == "mission":
        (task, risk) = mission.execute({"combat"})
    elif work == "rating":
        (task, risk) = ratting.execute(required_types=("inquisitor", "scout", "small"))
    print("starting ", work, task, risk )

        # task = ratting.execute({"scout"})





