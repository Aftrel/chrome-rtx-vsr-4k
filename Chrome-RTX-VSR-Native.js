const nativeWidth = 3840;
const nativeHeight = 2160;
let nativeHook;
let nativeFrames = 0;

function enableNative4k() {
    if (nativeHook) return true;
    const driver = Process.findModuleByName('nvwgf2umx.dll');
    if (!driver) return false;

    const scaleCheck = driver.base.add(0xd18e22);
    const areaFlag = driver.base.add(0xd18fce);
    const areaRange = driver.base.add(0xd18ea4);
    const originalLimit = 2560 * 1440;
    const minimumArea = 0x2a300;
    if (scaleCheck.readU32() !== 0x2454b60f || scaleCheck.add(4).readU8() !== 0x22 ||
        areaFlag.readU16() !== 0xf981 || areaFlag.add(2).readU32() !== originalLimit ||
        areaRange.readU16() !== 0xf981 || areaRange.add(2).readU32() !== originalLimit - minimumArea) {
        throw Error('The loaded NVIDIA driver does not match the tested VSR instructions.');
    }

    const nativeArea = nativeWidth * nativeHeight;
    const hook = Interceptor.attach(scaleCheck, function () {
        if (!nativeHook) return;
        const stream = this.context.r14;
        const inputWidth = stream.add(0x48).readS32() - stream.add(0x40).readS32();
        const inputHeight = stream.add(0x4c).readS32() - stream.add(0x44).readS32();
        const outputWidth = stream.add(0x98).readS32() - stream.add(0x90).readS32();
        const outputHeight = stream.add(0x9c).readS32() - stream.add(0x94).readS32();
        if (inputWidth === nativeWidth && inputHeight === nativeHeight &&
            outputWidth === nativeWidth && outputHeight === nativeHeight) {
            this.context.rsp.add(0x22).writeU8(1);
            ++nativeFrames;
        }
    });
    try {
        Memory.patchCode(areaFlag.add(2), 4, code => code.writeU32(nativeArea));
        Memory.patchCode(areaRange.add(2), 4, code => code.writeU32(nativeArea - minimumArea));
        Interceptor.flush();
        nativeHook = hook;
    } catch (error) {
        hook.detach();
        if (areaFlag.add(2).readU32() === nativeArea) {
            Memory.patchCode(areaFlag.add(2), 4, code => code.writeU32(originalLimit));
        }
        if (areaRange.add(2).readU32() === nativeArea - minimumArea) {
            Memory.patchCode(areaRange.add(2), 4, code => code.writeU32(originalLimit - minimumArea));
        }
        throw error;
    }
    return true;
}

rpc.exports = {
    driverPath() { return Process.findModuleByName('nvwgf2umx.dll')?.path ?? null; },
    nativeFrames() { return nativeFrames; },
    enableNative4k
};
