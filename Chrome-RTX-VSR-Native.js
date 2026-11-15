const uhdWidth = 3840;
const dciWidth = 4096;
const maxHeight = 2160;
const roundingPixels = 4;
const baseline = 2560 * 1440;
const minimumArea = 0x2a300;
const hooks = [];
let enabled = false;
let eligibleFrames = 0;

function fullScreen4kArea(stream) {
    const inputWidth = stream.add(0x48).readS32() - stream.add(0x40).readS32();
    const inputHeight = stream.add(0x4c).readS32() - stream.add(0x44).readS32();
    if (inputWidth < uhdWidth || inputWidth > dciWidth || inputHeight < 1440 || inputHeight > maxHeight) {
        return 0;
    }

    const outputWidth = stream.add(0x98).readS32() - stream.add(0x90).readS32();
    const outputHeight = stream.add(0x9c).readS32() - stream.add(0x94).readS32();
    // Match the video rectangle, allowing for letterboxing and swap-chain rounding.
    if (outputWidth < uhdWidth - roundingPixels || outputWidth > dciWidth + roundingPixels ||
        outputHeight > maxHeight + roundingPixels ||
        Math.abs(outputHeight - inputHeight * outputWidth / inputWidth) > roundingPixels) {
        return 0;
    }
    return inputWidth * inputHeight;
}

function stop() {
    enabled = false;
    for (const hook of hooks.splice(0)) hook.detach();
    Interceptor.flush();
}

function start() {
    if (enabled) return;
    const driver = Process.getModuleByName('nvwgf2umx.dll');
    const scaleCheck = driver.base.add(0xd18e22);
    const rangeCheck = driver.base.add(0xd18ea4);
    const areaCheck = driver.base.add(0xd18fce);
    if (scaleCheck.readU32() !== 0x2454b60f || scaleCheck.add(4).readU8() !== 0x22 ||
        rangeCheck.readU16() !== 0xf981 || rangeCheck.add(2).readU32() !== baseline - minimumArea ||
        areaCheck.readU16() !== 0xf981 || areaCheck.add(2).readU32() !== baseline) {
        throw Error('The driver instructions differ from the tested version or another tool has already patched them.');
    }

    try {
        hooks.push(Interceptor.attach(scaleCheck, function () {
            if (!enabled || !fullScreen4kArea(this.context.r14)) return;
            this.context.rsp.add(0x22).writeU8(1);
            ++eligibleFrames;
        }));
        // Each comparison consumes ECX and the following code overwrites it.
        for (const [check, offset] of [[rangeCheck, minimumArea], [areaCheck, 0]]) {
            hooks.push(Interceptor.attach(check, function () {
                if (!enabled) return;
                const area = fullScreen4kArea(this.context.r14);
                if (area && this.context.rcx.toUInt32() === area - offset) {
                    this.context.rcx = ptr(baseline - offset);
                }
            }));
        }
        Interceptor.flush();
        enabled = true;
    } catch (error) {
        stop();
        throw error;
    }
}

rpc.exports = {
    driverPath() { return Process.findModuleByName('nvwgf2umx.dll')?.path ?? null; },
    eligibleFrames() { return eligibleFrames; },
    start,
    stop
};
