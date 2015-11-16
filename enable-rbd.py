#!/usr/bin/python
''' Install script which will do following:
1. enable rbd on boot via modprobe.conf
2. patch lvm.conf to detect volumes on rbd block devices
3. patch LVHDoISCSISR.py to redirect port 6789 requests to RBDSR.py'''

import os, sys, shutil, subprocess

def usage():
    print "Usage: %s enable" % (sys.argv[0])

if __name__ == "__main__":
    if len(sys.argv) != 2:
        usage()
        sys.exit(1)

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
        print('Couldn\'t find lvm.pacth here -download package again')
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
    os.chdir('/usr/lib/python2.4/site-packages/')
    shutil.copy('pxssh.py','pxssh.py-oring')
    try:
        subprocess.call(["patch", "pxssh.py", "%s/pxssh.patch" % current_path])
        print('....\npxssh.py is patched')
    except OSError, e:
        print 'Couldn\'t patch lvm.conf. Error: %s [errno=%s]' % (e.args)
        sys.exit(1)

    os.chdir('/etc/lvm')
    shutil.copy('lvm.conf','lvm.conf-oring')
    try:
        subprocess.call(["patch", "lvm.conf", "%s/lvm.patch" % current_path])
        print('....\nlvm.conf is patched')
    except OSError, e:
        print 'Couldn\'t patch lvm.conf. Error: %s [errno=%s]' % (e.args)
        sys.exit(1)
        
    os.chdir('/opt/xensource/sm')
    shutil.copy('LVHDoISCSISR.py','LVHDoISCSISR.py-orig') 
    try:
        subprocess.call(["patch", "LVHDoISCSISR.py", "%s/LVHDoISCSISR.patch" % current_path])
        print('....\nLVHDoISCSISR.py is patched')
    except OSError, e:
        print 'Couldn\'t patch LVHDoISCSISR.py. Error: %s [errno=%s]' % (e.args)
        sys.exit(1)
    
    shutil.copyfile(current_path + '/RBDSR.py', 'RBDSR.py')
    print('....\nRBDSR.py has been copied to /opt/xensource/sm')

    sys.exit(0)
