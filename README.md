# RBDSR - CEPH plugin for XenServer 6.5

XenServer demo RBD SR, implemented as an extension of the exsiting iSCSI SR

In XenServer 6.5, rbd module has been enbled on the kernel. As a result, RBD blocks can be attached to Dom0 with sysfs command like the one described here: http://docs.ceph.com/docs/argonaut/rbd/rbd-ko/

Once the RBD block device is mapped, LVM SR can be created on top of it and shared across a XenServer pool.

## Install

You can install this demo script automatically using `rbd-install.py` or apply each command manually.
Run `./rbd-install.py enable` on each host to patch all required files and copy RBDSR.py to `/opt/xensource/sm`.

If for some reason you are having problems with the install script, please [let me know](mailto:mr.mark.starikov@gmail.com) first and then perform following changes on each host in the pool to enable RBD SR:
```
# patch /usr/lib/python2.4/site-packages/pxssh.py pxssh.patch
# patch /etc/lvm.conf lvm.patch
# patch /opt/xensource/sm/LVHDoISCSISR.py LVHDoISCSISR.patch
# echo modprobe rbd >> /etc/rc.modules 
# chmod +x /etc/rc.modules
# cp RBDSR.py /opt/xensource/sm/
```
## Usage

RBDSR.py extends iSCSI SR(lvmoiscsi) functionality to attach rbd images to the Dom0 and place LVHDs(VHD inside of LVM volume) VDIs on top of that block device.

Minimal requirements to create RBDSR are:
* target - IP address or hostname of the ceph monitor
* targetIQN - RBD pool name
* SCSIid - RBD image name
* chapuser - username of sudoer on ceph monitor
* chappassword - password of the ceph user
* port - monitor port number. currently only 6789 will divert LVHDoISCSISR into RBDSR

###### Examples
To create SR you can use ragular sr-create syntax:
```
# xe sr-create type=lvmoiscsi name-label=RADOS-SR shared=true device-config:target=<monitor ip address> device-config:targetIQN=<rbd pool name> device-config:SCSIid=<rbd image name> device-config:chapuser=<monitor sudoer username> device-config:chappassword=<ceph user password>
```
Or via XenCenter:

[XenCenter Create new RBD SR with caption](https://drive.google.com/file/d/0B1PjrwdL2YoLYkdWN1pENW9rRWc/preview)
