# RBDSR - CEPH plugin for XenServer 6.5 and 7(testing)
This plugin automates creation and attaching RBD objects to XenServer as an SR. It creates LVM Volume group on top of the attached RBD object and then uses LVs as LVHD VDIs.

XenServer demo RBD SR, implemented as an extension of the exsiting iSCSI(LVHDoISCSISR) SR. It doesn't mean that it uses iSCSI per se, but rather forks iSCSI storage plugin operation path, to take advantage of creating SR from XenCenter.

In particular, after installing plugin, creating iSCSI SR with port 6789 will redirect code path to the RBDSR.py plugin and allow user to attach RBD object to XenServer and create LVM based SR on top of that object. While allowing RBD SR creation using XenCenter, this method doesn't impact LVHDoISCSISR.py in any other way, leaving iSCSI functionality otherwise unchanged. 

This plugin takes adventage of the following changes in XenServer 6.5. In this version of XenServer, an rbd module has been enbled on the kernel. As a result, RBD blocks can be attached to Dom0 with sysfs command:

```echo "$mons name=$name,secret=$secret $rbddev" > /sys/bus/rbd/add```

like the one described here: line 49 https://github.com/ceph/ceph-docker/blob/master/examples/coreos/rbdmap/rbdmap

Once the RBD block device is mapped, LVM SR can be created on top of it and shared across a XenServer pool.

## Install
Download latest version of the pluging to each host: `wget https://github.com/mstarikov/rbdsr/archive/master.zip`

Unzip the archive(wget on xenserver might strip the extension): `unzip master`

Now you can install this demo script automatically using `rbd-install.py`. 
Run `python ./rbd-install.py enable` on each host to patch all required files and copy RBDSR.py to `/opt/xensource/sm`.

rbd-install.py will automatically detect the version of the XenServer and apply corresponding patches to 6.5 or 7. 

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
# xe sr-create type=lvmoiscsi name-label=RADOS-SR shared=true device-config:target=<monitor ip address> device-config:port=6789 device-config:targetIQN=<rbd pool name> device-config:SCSIid=<rbd image name> device-config:chapuser=<monitor sudoer username> device-config:chappassword=<ceph user password>
```
Or via XenCenter:

![XenCenter Create new RBD SR with caption](https://cloud.githubusercontent.com/assets/15868352/11228256/83176bc8-8ddf-11e5-9394-3a533f1ccf1b.png)
