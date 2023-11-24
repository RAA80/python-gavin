#! /usr/bin/env python3

import logging
import platform
from ctypes import (CFUNCTYPE, POINTER, byref, c_int, c_short, c_ubyte, c_void_p,
                    cast, cdll)
from functools import partial
from os.path import dirname, join

from numpy import frombuffer, int16, uint8

from .gavin import (DEVICE_INFO_LIST, GUIDE_USB_CODE_E, GUIDE_USB_DEVICE_INFO_T,
                    GUIDE_USB_DEVICE_STATUS_E, GUIDE_USB_FRAME_DATA_T)
from .minimjpeg import handle_frame


def _load_lib(arch):
    return cdll.LoadLibrary(join(dirname(__file__), "libs", arch,
                                 "GuideUSB3LiveStream.dll"))


if platform.architecture()[0] == "32bit":
    _lib = _load_lib("x86")
elif platform.architecture()[0] == "64bit":
    _lib = _load_lib("x64")

_logger = logging.getLogger(__name__)
_logger.addHandler(logging.NullHandler())


@CFUNCTYPE(c_void_p, GUIDE_USB_FRAME_DATA_T)
def frame_recv_cb(frame):
    """ Video Stream Callback Function. """

    if frame.frame_rgb_data_length > 0:
        arr_ptr = cast(frame.frame_rgb_data, POINTER(c_ubyte * frame.frame_rgb_data_length))[0]
        img = frombuffer(arr_ptr, uint8).reshape((frame.frame_height, frame.frame_width, 3))
        handle_frame(img, channel="0", ip="", port=80)
    if frame.frame_src_data_length > 0:
        arr_ptr = cast(frame.frame_src_data, POINTER(c_short * frame.frame_src_data_length))[0]
        img = frombuffer(arr_ptr, int16).reshape((frame.frame_height, frame.frame_width))
        handle_frame(img, channel="1", ip="", port=80)
    if frame.frame_yuv_data_length > 0:
        arr_ptr = cast(frame.frame_yuv_data, POINTER(c_short * frame.frame_yuv_data_length))[0]
        img = frombuffer(arr_ptr, int16).reshape((frame.frame_height, frame.frame_width))
        handle_frame(img, channel="2", ip="", port=80)
    if frame.paraLine_length > 0:
        arr_ptr = cast(frame.paraLine, POINTER(c_short * frame.paraLine_length))[0]
        img = frombuffer(arr_ptr, int16).reshape((frame.frame_height, frame.frame_width))
        handle_frame(img, channel="3", ip="", port=80)


@CFUNCTYPE(c_void_p, c_int)
def connect_status_cb(status):
    """ Connect Status Callback Function. """

    _logger.debug("Connect status: %s", GUIDE_USB_DEVICE_STATUS_E(status).name)


class GAVIN_API(c_void_p):
    """ Основной интерфейс для работы с устройствами. """

    _functions_ = {
        "Initialize": CFUNCTYPE(c_int),
        "Exit": CFUNCTYPE(c_int),
        "GetDeviceList": CFUNCTYPE(c_int, POINTER(DEVICE_INFO_LIST)),
        "OpenStream": CFUNCTYPE(c_int, POINTER(GUIDE_USB_DEVICE_INFO_T), c_void_p, c_void_p),
        "OpenStreamByDevID": CFUNCTYPE(c_int, c_int, POINTER(GUIDE_USB_DEVICE_INFO_T), c_void_p, c_void_p),
        "CloseStream": CFUNCTYPE(c_int),
        "SetPalette": CFUNCTYPE(c_int, c_int),
    }

    def __call__(self, *args):
        prototype, *arguments = args

        ret = prototype((self.name, _lib))(*arguments)
        if ret != 1:
            msg = f"{self.name} error {ret} ({GUIDE_USB_CODE_E(ret).name})"
            raise Exception(msg)

        _logger.debug("%s: %d", self.name, ret)
        return ret

    def __getattr__(self, name):
        self.name = name
        if name in self._functions_:
            return partial(self.__call__, self._functions_[name])


class Client:
    """ Python wrapper for gavin library. """

    def __init__(self):
        self._dev = GAVIN_API()

    def __enter__(self):
        if self.Initialize():
            return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.Exit()

    def Initialize(self):
        """ Initialize module, invoke once when the software boot up. """

        return self._dev.Initialize()

    def Exit(self):
        """ Uninitialize module, invoke once when the software exit. """

        return self._dev.Exit()

    def GetDeviceList(self):
        """ Get usb device list info. """

        devices = DEVICE_INFO_LIST()

        if self._dev.GetDeviceList(byref(devices)):
            return devices

    def OpenStream(self, dev_info):
        """ Open the video stream, the first device is default. """

        return self._dev.OpenStream(byref(dev_info), frame_recv_cb,
                                    connect_status_cb)

    def OpenStreamByDevID(self, dev_id, dev_info):
        """ Open the video stream by device id. """

        return self._dev.OpenStreamByDevID(c_int(dev_id), byref(dev_info),
                                           frame_recv_cb, connect_status_cb)

    def CloseStream(self):
        """ Close the video stream. """

        return self._dev.CloseStream()

    def SetPalette(self, index=0):
        """ Set the image Palette. """

        return self._dev.SetPalette(c_int(index))


__all__ = ["Client"]
