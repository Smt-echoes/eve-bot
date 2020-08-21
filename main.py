#!/usr/bin/env python
# coding: utf-8

# In[1]:


import time
import win32gui
import win32api
import pyautogui
import cv2

from PIL import Image
from numpy import *
import threading


# In[2]:


def debug_show(pos, col=(0, 0, 0)):
    dc = win32gui.GetDC(0)
    c = win32api.RGB(col[0], col[1], col[2])
    for i in range(pos[0], pos[0] + pos[2]):
        win32gui.SetPixel(dc, i, pos[1], c)
        win32gui.SetPixel(dc, i, pos[1] + pos[3], c)
    for i in range(pos[1], pos[1] + pos[3]):
        win32gui.SetPixel(dc, pos[0], i, c)
        win32gui.SetPixel(dc, pos[0] + pos[2], i, c)


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
        if self.count() < 2:
            return 0
        for iteration, item in enumerate(self.time):
            if iteration > 0:
                diff += self.list[iteration] - self.list[iteration - 1]
                time += self.time[iteration] - self.time[iteration - 1]
        return diff * step / time

    def getAve(self, step = 1):
        summ = 0
        if self.count() < 2:
            return 0
        time = self.time[-1] - self.time[0]
        for item in self.list:
            summ += item
        return summ * step / time






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


class ScreenObject:
    WINDOW_W = 1920
    WINDOW_H = 1080
    FULLSCREEN = False
    anchor = None

    def __init__(self, name, static=True, con=0.8, scale=1.0, num=0, ao=None):
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

    def pixcmp(self):

        if not self.reg:
            return 9999999
        reg = (self.reg[0], self.reg[1],
               self.img.size[0], self.img.size[1])
        im = pyautogui.screenshot(region=reg)
        pix = self.img.load()

        sse = 0

        for i in range(1, self.img.size[1]):  # for every pixel:
            left_s = pix[0, i]
            left_i = im.getpixel((0, i))
            for j in range(1, self.img.size[0]):
                top_s = pix[j, i - 1]
                cur_s = pix[j, i]
                top_i = im.getpixel((j, i - 1))
                cur_i = im.getpixel((j, i))

                for c in range(3):
                    d_top = (cur_i[c] - top_i[c]) - (cur_s[c] - top_s[c])
                    d_lef = (cur_i[c] - left_i[c]) - (cur_s[c] - left_s[c])
                    sse += d_top * d_top + d_lef * d_lef

                left_i = cur_i
                left_s = cur_s

        return sse / (self.img.size[1] * self.img.size[0])

    def update(self):

        im = pyautogui.screenshot()
        if ScreenObject.FULLSCREEN:
            im = im.resize((ScreenObject.WINDOW_W, ScreenObject.WINDOW_H))

        if self.reg:
            self.trgt = pyautogui.locate(self.img, im, region=self.reg, confidence=self.con)

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

            if self.num == 0:
                self.trgt = pyautogui.locate(self.img, im, region=reg, confidence=self.con)
            else:
                idx = 0
                for trgt in pyautogui.locateAll(self.img, im, confidence=self.con, region=reg):
                    if self.num == idx:
                        self.trgt = trgt
                        break
                    idx += 1

        if self.trgt and (self.reg == () or self.static is False):
            offset = 0
            self.reg = (self.trgt.left - offset, self.trgt.top - offset, self.trgt.width + offset, self.trgt.height + offset)

    def status(self):
        return "found" if self.trgt else "not found"

    def click(self):
        if self.trgt:
            trgt = self.trgt;
            if ScreenObject.FULLSCREEN:
                trgt = tuple([i*2 for i in trgt])
            pyautogui.click(trgt)
            print("click: ", self.name[:len(self.name) - 4])


class ScreenIndicator(ScreenObject):
    MASK_KEY = (0, 255, 0)
    TREASHOLD = 30

    def __init__(self, name, mask, key, scale=1.0, num=0):
        ScreenObject.__init__(self, name, static=True, con=0.8, scale=scale, num=num)
        self.mask = []
        self.mask_pos = []
        self.cur = []
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

            self.mask.append(im)
            self.mask_pos.append(pix_arr)
            self.cur.append(0.0)


        self.off = pyautogui.locate(Image.open(name), self.mask[0])
        self.lock = threading.Lock()
        # print(name, self.off)
        self.key = key


    def scanMask(self):

        reg = None
        if self.reg and self.off:
            reg = (self.reg[0] - self.off.left, self.reg[1] - self.off.top,
                   self.mask[0].shape[1], self.mask[0].shape[0])
        im = None
        if ScreenObject.FULLSCREEN:
            full_reg = tuple([i * 2 for i in reg])
            im = pyautogui.screenshot(region=full_reg)
            im = im.resize((self.mask[0].shape[1], self.mask[0].shape[0]))
        else:
            im = pyautogui.screenshot(region=reg)

        cur = []
        for i, mask in enumerate(self.mask_pos):
            count = 0
            summ = 0
            key = self.key[i]

            for pos in mask:  # for every pixel:
                pix = im.getpixel(pos)
                count += 1
                if abs(pix[0] - key[0]) < ScreenIndicator.TREASHOLD and \
                        abs(pix[1] - key[1]) < ScreenIndicator.TREASHOLD and \
                        abs(pix[2] - key[2]) < ScreenIndicator.TREASHOLD:
                    summ += 1

            cur.append(summ / (count + 1))
            if count == 0:
                print("mask fail:", count, summ, self.name, self.mask, reg)
        return cur

    def update(self):

        if not self.reg:
            ScreenObject.update(self)

        if self.reg:
            res = self.scanMask()
            with self.lock:
                self.cur = res

    def getValue(self, idx=0):
        with self.lock:
            return self.cur[idx]

    def click(self):
        if self.trgt:
            ScreenObject.click(self)
        else:
            if self.reg:
                print("blind click: ", self.name[:len(self.name) - 4])
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
    TIME_PACE = 0.5

    def __init__(self, name, mask, scale=1.0, num=0):
        threading.Thread.__init__(self)
        Botton.__init__(self)
        ScreenIndicator.__init__(self, name, (mask,), key=((215, 252, 239),), scale=scale, num=num)
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

        with self.lock:
            if self.vals.count() < self.MAX_VALS:
                return

            cnt = self.vals.unique()

            if self.expectedState == "active":
                if cnt > 1:
                    return
            else:
                if cnt < 3:
                    return

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
            self.wait(self.TIME_PACE if self.expectedState == "active" else 1)


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

                while self.State() != "open":
                    self.ov_btn.click()
                    time.sleep(0.5)

                self.sbm_btn.click()
                time.sleep(0.5)

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
    def __init__(self):
        threading.Thread.__init__(self)
        TimeControl.__init__(self)
        self.bar = ScreenIndicator("bar.png", \
                    ("shield_mask.png", "armor_mask.png", \
                     "structure_mask.png", "energy_mask.png"), \
                   key=((250, 250, 250),(205,205,205),(150,150,150),(255,255,220)))
        self.names = {"shield": 0, "armor": 1, "structure": 2, "energy": 3}
        self.max = {"shield": 0.645, "armor": 0.672, "structure": 0.76, "energy": 0.562}
        self.work = True
        self.hp = Averager(max_time=10)
        self.start()

    def __del__(self):
        self.work = False
        self.join()

    def update(self):
        self.bar.update()
        self.hp.update( self.get("shield") + self.get("armor") + self.get("structure") )

    def get(self, name):
        if self.bar.reg:
            idx = self.names[name]
            return int(self.bar.getValue(idx=idx) / self.max[name] * 100.)
        else:
            return 100

    def estimateLifetime(self):
        diff = self.hp.getDiff(step=1)
        if self.hp.count() < 2 or diff >= 0:
            return 999

        return -self.hp[-1] / diff

    def run(self):
        while self.work:
            with MeasureTime("stat"):
                self.update()
                self.wait(delay=0.5)


# In[3]:


class BaseLogic:
    def __init__(self, obj):
        self.objects = obj

    def execute(self):
        return self


def closeAll():
    print("error")
    close = ScreenObject("close.png", con=0.95)
    while True:
        close.update()
        if close.status() == "found":
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

        ab.set("active")

        ov.Open(mode="loot")

        while True:
            loot = None
            for loot in self.loot_type:
                loot.update()
                if loot.status() == "found":
                    break

            if loot.status() != "found":
                break

            print("looting")
            loot.click()
            time.sleep(0.5)

            if not ProcessDialogBotton(self.loot_btn, 5):
                print("loot btn not found")
                closeAll()
                continue

            if not ProcessDialogBotton(self.loot_all, 500):
                print("loot_all btn not found")
                closeAll()

            enemy.update()
            if enemy.status() == "found":
                ov.Close()
                return
        ov.Close()
        if ab.status() == "found" and ab.State() == "active":
            ab.set("inactive")

class TargetLogic(threading.Thread):

    def __init__(self, obj):
        threading.Thread.__init__(self)
        self.objects = obj
        self.npc = {"frigate":ScreenObject("npc_frigate.png", static=False),
                    "destr":ScreenObject("npc_destr.png", static=False),
                    "cruiser":ScreenObject("npc_cruiser.png", static=False)}
        self.focus_fire = ScreenObject("focus_fire.png", static=False)
        self.targets = {"frigate", "destr", "cruiser"}
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
        time = TimeControl()
        while True:
            if self.active == False:
                time.wait(1)
                continue

            trgt = None
            t = None
            for t in ("cruiser",):
                self.npc[t].update()
                if self.npc[t].status() == "found":
                    trgt = self.npc[t]
                    break

            if trgt:
                print("target ", t)
                trgt.click()
                ProcessDialogBotton(self.focus_fire)
            else:
                print("no targets")




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

    def retreat(self):
        print("retreat")
        planet = ScreenObject("planet.png", static=False)
        warp = ScreenObject("warp.png", static=False)
        ov = self.objects["OV"]
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
        persent = (90, 80)
        prev_rep_state = False

        i = 0
        for r in self.rep:
            if r.State() == "active":
                prev_rep_state = True
            r.set("active" if stat.get("armor") < persent[i] else "inactive")
            i += 1

        lifetime = stat.estimateLifetime()
        print("lifetime", lifetime)
        if lifetime < 60 and stat.get("shield") < 20:
            print("looks dangerous")
            self.rep[0].set("active")

        if lifetime < (50 + (10 if prev_rep_state else 0)):
            print("bad prediction lifetime", lifetime)
            return "retreat"

        if stat.get("armor") < 20 and lifetime < 300:
            print("low armor", stat.get("armor"))
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
        outOfCombatTimer = 5
        print("combat logic")
        exitStatus = "none"
        #with self.targeting:
        if True:
            while True:
                objects["enemy"].update()
                enemy = objects["enemy"].status() == "found"

                for target in objects["target"]:
                    target.update()
                    if target.status() == "found":
                        target.click()
                        break

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
                    self.ab.set("inactive")

                    if (outOfCombatTimer <= 0):
                        break
                    else:
                        self.wait(1)

            return exitStatus


class MissionLogic(BaseLogic):
    def __init__(self, obj):
        BaseLogic.__init__(self, obj)
        self.mission_btn = ScreenObject("mis_btn.png", static=False, con=0.7)
        self.news_btn = ScreenObject("news_btn.png")
        self.mis_type = {"combat": ScreenObject("mis_combat.png", static=False),
                         "delivery": ScreenObject("mis_delivery.png", static=False), }
        self.mis_taken = {"combat": ScreenObject("mis_combat_t.png", static=False),
                          "delivery": ScreenObject("mis_delivery_t.png", static=False), }
        self.accept = ScreenObject("accept.png", static=False, con=0.9)
        self.begin = ScreenObject("begin.png", static=False, con=0.9)
        self.confirm = ScreenObject("confirm.png", static=False, con=0.9)
        self.refresh = ScreenObject("refresh.png")
        self.delivery_finish = ScreenObject("delivery_finish.png", static=False)
        self.face = (ScreenObject("dialog.png", static=False),
                     ScreenObject("dialog2.png", static=False),
                     ScreenObject("dialog3.png", static=False),)

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
                return
            time.sleep(1)

        print("finish mission")
        self.getRidOfFace()
        print("starting mission")
        while True:

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

                mission, missionType = self.scanMission(arr=self.mis_type, types=types)

                if mission == None:
                    self.refresh.update()
                    if self.refresh.status() == "found":
                        print("refresh")
                        self.refresh.click()
                        time.sleep(1)
                    closeAll()
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

            if not ProcessDialogBotton(self.begin, 5, pop=False):
                closeAll()
                continue

            self.getRidOfFace()

            print("mission comuting")

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

            return missionType


class RattingLogic(BaseLogic):
    def __init__(self, obj):
        BaseLogic.__init__(self, obj)
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

    def warping(self, WARP_TIMEOUT=30):
        ov = self.objects["OV"]
        WARP_TIMEOUT = 30
        start = time.time()
        print("warping")
        with ov.Open("all"):
            while time.time() - start < 30:

                self.objects["enemy"].update()
                if self.objects["enemy"].status() == "found":
                    break

                self.jumpGate.update()
                if self.jumpGate.status() == "found":
                    break

                if self.objects["stat"].get("armor") < 50:
                    break

                time.sleep(1)

    def jumpFurther(self):
        ov = self.objects["OV"]
        print("activating jumpgate")
        with ov.Open("all"):
            self.jumpGate.update()
            if self.jumpGate.status() != "found":
                print("no gate")
                return False

            self.jumpGate.click()
            time.sleep(0.5)

            if not ProcessDialogBotton(self.activate, 5):
                print("activate fail")
                closeAll()
                return False

        self.warping(WARP_TIMEOUT=15)

        return True

    def execute(self, required_types=None):
        print("start ratting")
        ov = self.objects["OV"]

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

        return anomalyType


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
        objects["rep"] = ModuleBotton("rep_btn_2.png", "rep_mask_2.png")
        objects["ab"] = ModuleBotton("ab_btn_2.png", "ab_mask_2.png")

        BaseCombat.__init__(self, obj)
        self.rep = (objects["rep"],)
        self.wep = {"cannon": ModuleBotton("cannon.png", "cannon_mask.png"),
                    "drones": DroneModule("drones.png")}

        self.ab = objects["ab"]

        self.nosf = ModuleBotton("nosf_btn_2.png", "nosf_mask_2.png")

        self.cmbt_mod = {"web": ModuleBotton("web_btn_2.png", "web_mask_2.png")}

        self.hrd = ModuleBotton("hrd_btn_2.png", "hrd_mask_2.png")
    # In[4]:


objects = {}
objects["target"] = (ScreenObject("target.bmp", con=0.7), ScreenObject("trgt_2.png", con=0.7))
objects["enemy"] = ScreenObject("enemy.bmp", static=False)
objects["OV"] = Overview()
objects["stat"] = ShipStatus()
combat = StabberCombat(objects)
looting = LootingLogic(objects)
mission = MissionLogic(objects)
ratting = RattingLogic(objects)

work = "mission"
task = "none"
while True:
    ret = combat.execute()
    if ret != "retreat":
        if work == "mission":
            mission.getRidOfFace()
        if ret == "loot":
            looting.execute()
        if task == "inquisitor" or task == "scout":
            if ratting.jumpFurther():
                continue
        if work == "rating":
            combat.retreat()
            time.sleep(20)

    if ret == "retreat":
        time.sleep(30)

    if objects["stat"].get("structure") < 90:
        with objects["OV"].Open(mode="station"):
            station = ScreenObject("station.png", static=False)
            station.update()
            if station.status() == "found":
                station.click()
                time.sleep(1)

                dock = ScreenObject("dock.png", static=False)
                ProcessDialogBotton(dock, 5)

                work = "mission"
                time.sleep(25)
            elif objects["stat"].get("structure") < 50:
                break




    #if task == "none":
    #    work = "rating" if work == "mission" else "mission"
    #elif work == "mission":
    #    work = "rating"
    if ret != "retreat":
        task = ratting.execute(required_types=("inquisitor", "scout"))
        if task != "none":
            work = "rating"
            continue
        else:
            work = "mission"

    if work == "mission":
        task = mission.execute({"combat"})
    elif work == "rating":
        task = ratting.execute(required_types=("inquisitor", "scout", "small"))

        # task = ratting.execute({"scout"})





