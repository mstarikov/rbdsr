#!/usr/bin/python
''' Install script which will do following:
1. add modprobe rbd to rc.modules
2. patch lvm.conf to detect volumes on rbd block devices
3. patch LVHDoISCSISR.py to redirect port 6789 requests to RBDSR.py
4. patch pxssh.py to allow remote commands
5. copy RBDSR.py to /opt/xensource/sm'''

import os, sys, shutil, subprocess

def usage():
    print "Usage: %s enable" % (sys.argv[0])

if __name__ == "__main__":
    if len(sys.argv) != 2:
        usage()
        sys.exit(1)
    version = '6'
    if 'PRODUCT_VERSION=\'7.0.0\'' in open('/etc/xensource-inventory').read():
        version = '7'
    print    ('########################################\nChecking if all files are in place:\n')
    if os.path.exists('RBDSR.py'):
        print('#### found RBDSR.py                 ####')
    else:
        print('Couldn\'t find RBDSR.py here - download package again')
        sys.exit(1)
 
    if os.path.exists('LVHDoISCSISR.patch'):
        print('#### LVHDoISCSISR.patch is here too ####')
    else:
        print('Couldn\'t find LVHDoISCSISR.py here -  download package again')
        sys.exit(1)

    if os.path.exists('lvm.patch'):
        print('#### and lvm.patch is here as well  ####')
    else:
        print('Couldn\'t find lvm.patch here - download package again')
        sys.exit(1)

    if os.path.exists('lvm-master7.patch'):
        print('#### and lvm-master7.patch is here as well  ####')
    else:
        print('Couldn\'t find lvm-master7.patch here - download package again')
        sys.exit(1)


    if os.path.exists('lvm7.patch'):
        print('#### and lvm7.patch is here as well  ####')
    else:
        print('Couldn\'t find lvm7.patch here - download package again')
        sys.exit(1)

    if os.path.exists('pxssh.patch'):
        print('#### and pxssh.patch is here as well  ####')
    else:
        print('Couldn\'t find pxssh.patch here - download package again')
        sys.exit(1)

    if os.path.exists('RBDSR7.patch'):
        print('#### and RBDSR7.patch is here as well  ####')
    else:
        print('Couldn\'t find RBDSR7.patch here - download package again')
        sys.exit(1)

    if os.path.exists('LVHDoISCSISR.patch'):
        print('#### and LVHDoSCSISR7.patch is here as well  ####')
    else:
        print('Couldn\'t find LVHDoISCSISR7.patch here - download package again')
        sys.exit(1)
    print('\n########################################\n\nWe have all files we need, enabling RBDSR:')
    print('Enabling rbd driver on boot via rc.modules(ref https://www.centos.org/docs/)')
    '''TODO: should check if rbd is already in the rc.modules before writing it'''
    
    try:
        rcfile = open('/etc/rc.modules','a')
        rcfile.write('\nmodprobe rbd\n')
        rcfile.close()
    except IOError, e:
        print 'Was unable to add rbd to rc.modules. Error: %s' % e
        sys.exit(1)
   
    try:
        os.chmod('/etc/rc.modules', 0744)
    except OSError, e:
        print 'Couldn\'t set execute permissions to rc.modules. Error: %s [errno=%s]' % (e.args)
        sys.exit(1)
    current_path = os.path.dirname(os.path.realpath(__file__))
    
    if version == '7':
        os.chdir('/usr/lib/python2.7/site-packages/')
        shutil.copy('%s/pxssh.py' % current_path, 'pxssh.py')
        shutil.copy('%s/pexpect.py' % current_path, 'pexpect.py')
    else:
        os.chdir('/usr/lib/python2.4/site-packages/')
        shutil.copy('pxssh.py','pxssh.py-oring')
        try:
            subprocess.call(["patch", "pxssh.py", "%s/pxssh.patch" % current_path])
            print('....\npxssh.py is patched')
        except OSError, e:
            print 'Couldn\'t patch pxssh.py. Error: %s [errno=%s]' % (e.args)
            sys.exit(1)

    os.chdir('/etc/lvm/')
    shutil.copy('lvm.conf','lvm.conf-oring')
    try:
        if version == '7':
            subprocess.call(["patch", "lvm.conf", "%s/lvm7.patch" % current_path])
            os.chdir('/etc/lvm/master')
            shutil.copy('lvm.conf','lvm.conf-oring')
            subprocess.call(["patch", "lvm.conf", "%s/lvm-master7.patch" % current_path])
        else: 
            subprocess.call(["patch", "lvm.conf", "%s/lvm.patch" % current_path])
        print('....\nlvm.conf is patched')
    except OSError, e:
        print 'Couldn\'t patch lvm.conf. Error: %s [errno=%s]' % (e.args)
        sys.exit(1)

    os.chdir('/opt/xensource/sm')
    shutil.copy('LVHDoISCSISR.py','LVHDoISCSISR.py-orig') 
    try:
        if version == '7':
            subprocess.call(["patch", "LVHDoISCSISR.py", "%s/LVHDoISCSISR7.patch" % current_path])
        else:
            subprocess.call(["patch", "LVHDoISCSISR.py", "%s/LVHDoISCSISR.patch" % current_path])
        print('....\nLVHDoISCSISR.py is patched')
    except OSError, e:
        print 'Couldn\'t patch LVHDoISCSISR.py. Error: %s [errno=%s]' % (e.args)
        sys.exit(1)
    
    try:
        shutil.copyfile(current_path + '/RBDSR.py', 'RBDSR.py')
        if version == '7':
            subprocess.call(["patch", "RBDSR.py", "%s/RBDSR7.patch" % current_path])
    except OSError, e:
        print 'Couldn\'t patch RBDSR.py. Error: %s [errno=%s]' % (e.args)
        sys.exit(1)
    print('....\nRBDSR.py has been copied to /opt/xensource/sm')
    
    try:
        if version == '7':
            subprocess.call(["patch", "scsiutil.py", "%s/scsiutil7.patch" % current_path])
    except OSError, e:
        print 'Couldn\'t patch scsiutil.py. Error: %s [errno=%s]' % (e.args)
        sys.exit(1)
        
    sys.exit(0)
