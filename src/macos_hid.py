"""
macOS IOKit HID communication — zero external dependencies.
Uses built-in CoreFoundation and IOKit frameworks via ctypes.
"""
import ctypes
import ctypes.util

_CF = ctypes.CDLL("/System/Library/Frameworks/CoreFoundation.framework/CoreFoundation")
_IK = ctypes.CDLL("/System/Library/Frameworks/IOKit.framework/IOKit")

_P    = ctypes.c_void_p
_U32  = ctypes.c_uint32
_I32  = ctypes.c_int32
_LONG = ctypes.c_long
_INT  = ctypes.c_int
_BOOL = ctypes.c_bool

_kCFStringEncodingUTF8 = 0x08000100
_kCFNumberSInt32Type   = 3
_kIOHIDOptionsTypeNone   = 0
_kIOHIDReportTypeOutput  = 1
_kIOHIDReportTypeFeature = 2
_kIOReturnSuccess        = 0

# CoreFoundation
_CF.CFStringCreateWithCString.restype  = _P
_CF.CFStringCreateWithCString.argtypes = [_P, ctypes.c_char_p, _U32]
_CF.CFNumberGetValue.restype  = _BOOL
_CF.CFNumberGetValue.argtypes = [_P, _INT, ctypes.c_void_p]
_CF.CFRelease.restype  = None
_CF.CFRelease.argtypes = [_P]
_CF.CFSetGetCount.restype  = _LONG
_CF.CFSetGetCount.argtypes = [_P]
_CF.CFSetGetValues.restype  = None
_CF.CFSetGetValues.argtypes = [_P, ctypes.POINTER(_P)]

# IOKit HID
_IK.IOHIDManagerCreate.restype  = _P
_IK.IOHIDManagerCreate.argtypes = [_P, _U32]
_IK.IOHIDManagerSetDeviceMatching.restype  = None
_IK.IOHIDManagerSetDeviceMatching.argtypes = [_P, _P]
_IK.IOHIDManagerOpen.restype  = _INT
_IK.IOHIDManagerOpen.argtypes = [_P, _U32]
_IK.IOHIDManagerCopyDevices.restype  = _P
_IK.IOHIDManagerCopyDevices.argtypes = [_P]
_IK.IOHIDDeviceOpen.restype  = _INT
_IK.IOHIDDeviceOpen.argtypes = [_P, _U32]
_IK.IOHIDDeviceClose.restype  = _INT
_IK.IOHIDDeviceClose.argtypes = [_P, _U32]
_IK.IOHIDDeviceSetReport.restype  = _INT
_IK.IOHIDDeviceSetReport.argtypes = [_P, _U32, _LONG, ctypes.c_char_p, _LONG]
_IK.IOHIDDeviceGetProperty.restype  = _P
_IK.IOHIDDeviceGetProperty.argtypes = [_P, _P]
_IK.IOHIDDeviceGetReport.restype  = _INT
_IK.IOHIDDeviceGetReport.argtypes = [_P, _U32, _LONG, ctypes.c_char_p, ctypes.POINTER(_LONG)]


def _cfstr(s: bytes) -> int:
    return _CF.CFStringCreateWithCString(None, s, _kCFStringEncodingUTF8)


def _int_prop(dev: int, key: bytes):
    k = _cfstr(key)
    v = _IK.IOHIDDeviceGetProperty(dev, k)
    _CF.CFRelease(k)
    if not v:
        return None
    n = _I32(0)
    return int(n.value) if _CF.CFNumberGetValue(v, _kCFNumberSInt32Type, ctypes.byref(n)) else None


def _open_manager():
    mgr = _IK.IOHIDManagerCreate(None, _kIOHIDOptionsTypeNone)
    _IK.IOHIDManagerSetDeviceMatching(mgr, None)  # None = match all
    _IK.IOHIDManagerOpen(mgr, _kIOHIDOptionsTypeNone)
    return mgr


def _copy_devices(mgr):
    ds = _IK.IOHIDManagerCopyDevices(mgr)
    if not ds:
        return []
    count = _CF.CFSetGetCount(ds)
    arr = (_P * count)()
    _CF.CFSetGetValues(ds, arr)
    _CF.CFRelease(ds)
    return list(arr)


def enumerate_hid(vid: int = 0, pid: int = 0) -> list:
    mgr = _open_manager()
    devices = _copy_devices(mgr)
    results = []
    for dev in devices:
        if not dev:
            continue
        dv = _int_prop(dev, b"VendorID") or 0
        dp = _int_prop(dev, b"ProductID") or 0
        if (vid and dv != vid) or (pid and dp != pid):
            continue
        results.append({
            "vendor_id":        dv,
            "product_id":       dp,
            "usage_page":       _int_prop(dev, b"PrimaryUsagePage") or 0,
            "usage":            _int_prop(dev, b"PrimaryUsage") or 0,
            "interface_number": _int_prop(dev, b"InterfaceNumber") or -1,
        })
    _CF.CFRelease(mgr)
    return results


def send_output_report(
    vid: int,
    pid: int,
    usage_page: int,
    data: bytes,
    usage: int = 0,
    report_type: int = None,
) -> None:
    """
    Find device by VID/PID/usage_page (and optionally usage), open it,
    send an output or feature report, then close.

    report_type defaults to kIOHIDReportTypeOutput (1).
    Pass kIOHIDReportTypeFeature (2) for feature reports.
    """
    if report_type is None:
        report_type = _kIOHIDReportTypeOutput

    mgr = _open_manager()
    devices = _copy_devices(mgr)

    target = None
    for dev in devices:
        if not dev:
            continue
        if _int_prop(dev, b"VendorID") != vid:
            continue
        if _int_prop(dev, b"ProductID") != pid:
            continue
        if _int_prop(dev, b"PrimaryUsagePage") != usage_page:
            continue
        if usage and _int_prop(dev, b"PrimaryUsage") != usage:
            continue
        target = dev
        break

    if target is None:
        _CF.CFRelease(mgr)
        raise OSError(
            f"Device VID=0x{vid:04X} PID=0x{pid:04X} "
            f"usagePage=0x{usage_page:04X} not found.\n"
            "Check USB connection and Input Monitoring permission."
        )

    ret = _IK.IOHIDDeviceOpen(target, _kIOHIDOptionsTypeNone)
    if ret != _kIOReturnSuccess:
        _CF.CFRelease(mgr)
        raise OSError(
            f"IOHIDDeviceOpen failed: 0x{ret:08x}\n"
            "Grant Input Monitoring permission in System Settings → "
            "Privacy & Security → Input Monitoring."
        )

    try:
        report_id = data[0]
        payload   = data[1:]
        ret = _IK.IOHIDDeviceSetReport(
            target, report_type, report_id, payload, len(payload)
        )
        if ret != _kIOReturnSuccess:
            raise OSError(f"IOHIDDeviceSetReport failed: 0x{ret:08x}")
    finally:
        _IK.IOHIDDeviceClose(target, _kIOHIDOptionsTypeNone)
        _CF.CFRelease(mgr)


def get_report(
    vid: int,
    pid: int,
    usage_page: int,
    report_id: int,
    length: int = 65,
    report_type: int = None,
    usage: int = 0,
) -> bytes:
    """Read a HID report (default: feature) from the device."""
    if report_type is None:
        report_type = _kIOHIDReportTypeFeature

    mgr = _open_manager()
    devices = _copy_devices(mgr)

    target = None
    for dev in devices:
        if not dev:
            continue
        if _int_prop(dev, b"VendorID") != vid:
            continue
        if _int_prop(dev, b"ProductID") != pid:
            continue
        if _int_prop(dev, b"PrimaryUsagePage") != usage_page:
            continue
        if usage and _int_prop(dev, b"PrimaryUsage") != usage:
            continue
        target = dev
        break

    if target is None:
        _CF.CFRelease(mgr)
        raise OSError(f"Device VID=0x{vid:04X} PID=0x{pid:04X} not found.")

    ret = _IK.IOHIDDeviceOpen(target, _kIOHIDOptionsTypeNone)
    if ret != _kIOReturnSuccess:
        _CF.CFRelease(mgr)
        raise OSError(f"IOHIDDeviceOpen failed: 0x{ret:08x}")

    try:
        buf = ctypes.create_string_buffer(length)
        buf_len = _LONG(length)
        ret = _IK.IOHIDDeviceGetReport(
            target, report_type, report_id, buf, ctypes.byref(buf_len)
        )
        if ret != _kIOReturnSuccess:
            raise OSError(f"IOHIDDeviceGetReport failed: 0x{ret:08x}")
        return bytes(buf[:buf_len.value])
    finally:
        _IK.IOHIDDeviceClose(target, _kIOHIDOptionsTypeNone)
        _CF.CFRelease(mgr)
