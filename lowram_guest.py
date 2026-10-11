#!/usr/bin/env python3
"""CI experiment: low-RAM variant of the pinned Husk guest, booted with 1024 MiB.
Does not publish or switch the app's default image until the guest passes its gates.
"""
import bz2, hashlib, importlib.util, json, os, socket, struct, subprocess, tarfile, time
from pathlib import Path
spec=importlib.util.spec_from_file_location('resources', 'husk/scripts/prepare_android_runtime.py')
r=importlib.util.module_from_spec(spec); spec.loader.exec_module(r)
w=Path('lowram-work').resolve(); w.mkdir(exist_ok=True)
def run(*args): return subprocess.run([str(a) for a in args],check=True)
r.download(r.IMAGE_URL,w/'source.qcow2',r.IMAGE_SHA)
run('qemu-img','convert','-O','raw',w/'source.qcow2',w/'disk.raw')
r.extract_system(w/'disk.raw',w/'system.img')
mount=w/'system'; mount.mkdir(exist_ok=True)
run('sudo','mount','-o','loop,rw',w/'system.img',mount)
props={'ro.config.low_ram':'true','dalvik.vm.heapstartsize':'8m','dalvik.vm.heapgrowthlimit':'128m','dalvik.vm.heapsize':'256m','dalvik.vm.heaptargetutilization':'0.75','dalvik.vm.heapminfree':'512k','dalvik.vm.heapmaxfree':'8m'}
try:
    # Change existing files in place to retain SELinux xattrs and ownership.
    prop=mount/'system/build.prop'
    assert prop.is_file(), 'system/build.prop missing'
    script="from pathlib import Path\nimport json,sys\np=Path(sys.argv[1]); props=json.loads(sys.argv[2]); lines=p.read_text().splitlines()\nlines=[line for line in lines if line.split('=',1)[0] not in props]\np.write_text(chr(10).join(lines)+chr(10)+chr(10).join(k+'='+v for k,v in props.items())+chr(10))\n"
    run('sudo','python3','-c',script,prop,json.dumps(props))
    # Keep framework, networking, input, launcher, package manager and Husk bridge.
    # Only optional demo/decoration apps may be removed; log exactly what exists.
    removed=[]
    for name in ('EasterEgg','BasicDreams','PhotoTable','HTMLViewer'):
        app=mount/'system/app'/name
        if app.is_dir():
            assert app.resolve().is_relative_to(mount.resolve())
            run('sudo','rm','-r','--',app); removed.append(name)
    print('LOW_RAM_PROPERTIES',json.dumps(props),flush=True)
    print('OPTIONAL_APPS_REMOVED',removed,flush=True)
finally: run('sudo','umount',mount)
run('e2fsck','-fn',w/'system.img')
# Replace the existing system extents; never resize super or change its table.
with (w/'disk.raw').open('r+b') as f, (w/'system.img').open('rb') as system:
    f.seek(512); hdr=r.read_exact(f,92); lba,count,stride=struct.unpack_from('<QII',hdr,72)
    f.seek(lba*512); entries=r.read_exact(f,count*stride); base=struct.unpack_from('<Q',entries,stride+32)[0]*512
    f.seek(base+12288); hdr=r.read_exact(f,256); hs=struct.unpack_from('<I',hdr,8)[0]; ts=struct.unpack_from('<I',hdr,44)[0]
    (po,pn,ps),(eo,en,es)=[struct.unpack_from('<III',hdr,80+12*i) for i in range(2)]
    f.seek(base+12288+hs); table=r.read_exact(f,ts)
    found=False
    for i in range(pn):
        ent=table[po+i*ps:po+(i+1)*ps]
        if ent[:36].split(b'\0')[0] not in (b'system',b'system_a'): continue
        _,first,n,_=struct.unpack_from('<IIII',ent,36)
        for j in range(first,first+n):
            sectors,kind,sector,device=struct.unpack_from('<QIQI',table,eo+j*es)
            assert kind==0 and device==0, 'only existing linear extents supported'
            f.seek(base+sector*512); left=sectors*512
            while left:
                data=r.read_exact(system,min(left,8<<20)); f.write(data); left-=len(data)
        assert not system.read(1); found=True
    assert found
run('qemu-img','convert','-c','-O','qcow2',w/'disk.raw',w/'vda-lowram.qcow2')
run('qemu-img','create','-f','qcow2',w/'vdb.qcow2','16G')
run('qemu-img','create','-f','qcow2',w/'vars.qcow2','64M')
r.download('https://github.com/utmapp/qemu/releases/download/v10.0.12-utm/qemu-10.0.12-utm.tar.xz',w/'qemu.tar.xz','7c9605290b34152debb842e965a55d2e4fbba4793e536ab677b4027e5dc0ba1a')
firmware=w/'edk2-aarch64-code.fd'
with tarfile.open(w/'qemu.tar.xz') as archive:
    member=next(m for m in archive.getmembers() if m.name.endswith('/pc-bios/edk2-aarch64-code.fd.bz2'))
    firmware.write_bytes(bz2.decompress(archive.extractfile(member).read()))
print('HUSK_FIRMWARE_SHA256',hashlib.sha256(firmware.read_bytes()).hexdigest(),flush=True)
cmd=['qemu-system-aarch64','-M','virt,highmem=on','-cpu','max,pauth-impdef=on,sve=off','-smp','4','-m','1024','-accel','tcg,thread=multi,tb-size=128',
'-drive',f'if=pflash,unit=0,format=raw,readonly=on,file={firmware}',
'-drive',f'if=pflash,unit=1,format=qcow2,file={w}/vars.qcow2',
'-device','virtio-blk-pci,drive=vda,bootindex=0','-device','virtio-blk-pci,drive=vdb,bootindex=1',
'-drive',f'if=none,id=vda,format=qcow2,file={w}/vda-lowram.qcow2',
'-drive',f'if=none,id=vdb,format=qcow2,file={w}/vdb.qcow2',
'-device','virtio-net-pci,netdev=net0','-netdev','user,id=net0,hostfwd=tcp:127.0.0.1:15599-:5599',
'-device','virtio-gpu-pci,xres=360,yres=640','-device','qemu-xhci','-device','usb-tablet','-device','usb-kbd','-device','virtio-rng-pci',
'-display','none','-monitor','none','-serial',f'file:{w}/serial.log']
print('BOOT_COMMAND',cmd,flush=True)
def shell(command):
    with socket.create_connection(('127.0.0.1',15599),timeout=3) as s:
        s.settimeout(5); s.sendall((command+'; echo HUSK_TEST_END\nexit\n').encode()); data=b''
        while b'HUSK_TEST_END' not in data and len(data)<65536:
            part=s.recv(4096)
            if not part: break
            data+=part
        return data.decode(errors='replace')
report={'guest_mib':1024,'status':'failed','properties':props,'removed_optional_apps':removed}
with (w/'qemu.log').open('w') as log:
    p=subprocess.Popen(cmd,stdout=log,stderr=log)
    try:
        deadline=time.monotonic()+1200
        while time.monotonic()<deadline and p.poll() is None:
            try:
                result=shell('echo BOOT=$(getprop sys.boot_completed); echo LOW_RAM=$(getprop ro.config.low_ram)')
                if 'BOOT=1' in result and 'LOW_RAM=true' in result:
                    result=shell('cat /proc/meminfo; dumpsys meminfo --oom; service check package; service check activity; service check connectivity; pm list packages | head -20')
                    (w/'backend-check.txt').write_text(result)
                    assert 'MemTotal:' in result and "Service package: found" in result and "Service activity: found" in result and "Service connectivity: found" in result
                    report['status']='booted-backend-services-present'; break
            except (OSError,AssertionError) as e: print('Waiting for guest:',str(e)[:100],flush=True)
            serial=w/'serial.log'
            if serial.exists():
                console=serial.read_text(errors='replace')
                print('SERIAL_TAIL',console[-1600:],flush=True)
                if 'Synchronous Exception' in console or 'Kernel panic' in console:
                    print('Guest firmware/kernel failure; aborting early',flush=True); break
            time.sleep(15)
    finally:
        p.terminate()
        try: p.wait(timeout=15)
        except subprocess.TimeoutExpired: p.kill(); p.wait()
        report['image_sha256']=hashlib.file_digest((w/'vda-lowram.qcow2').open('rb'),'sha256').hexdigest()
        (w/'result.json').write_text(json.dumps(report,indent=2))
print(json.dumps(report),flush=True)
for name in ('qemu.log','serial.log','backend-check.txt'):
    file=w/name
    if file.exists(): print(name, file.read_text(errors='replace')[-12000:], flush=True)
if report['status']=='failed': raise SystemExit('Low-RAM guest did not pass; do not ship it as working')
