#!/usr/bin/python
# Following ISCSISR.py as an example, RBDSR provides LVHD SR over rbd block device.
# created by Mark Starikov(mr.mark.starikov@gmail.com)

import ISCSISR, VDI, scsiutil, SR, SRCommand, util, xs_errors, xmlrpclib, LUNperVDI 
import socket, os, copy, sys, pxssh
from xml.dom.minidom import parseString

''' start of modified parameters, pretty much direct copy from ISCSISR.py '''
CAPABILITIES = ["SR_PROBE","VDI_CREATE","VDI_DELETE","VDI_ATTACH",
                "VDI_DETACH", "VDI_INTRODUCE"]

CONFIGURATION = [ [ 'SCSIid', 'The rbd image name' ], \
                  [ 'target', 'IP address or hostname of the ceph monitor' ], \
                  [ 'targetIQN', 'The rbd pool name' ], \
                  [ 'chapuser', 'The ssh username' ], \
                  [ 'chappassword', 'The ssh password' ], \
                  [ 'incoming_chapuser', 'The ceph admin user' ], \
                  [ 'incoming_chappassword', 'The ceph admin password' ], \
                  [ 'port', 'The monitor port number (default 6789) ' ], \
                  [ 'multihomed', 'Enable multi-homing to this target, true or false (optional, defaults to same value as host.other_config:multipathing)' ],
                  [ 'force_tapdisk', 'Force use of tapdisk, true or false (optional, defaults to false)'],
]

DRIVER_INFO = {
    'name': 'RBD',
    'description': 'Base RBD SR driver, provides a LUN-per-VDI. Does not support creation of VDIs but accesses existing LUNs on a target.',
    'vendor': 'Citrix Systems Inc',
    'copyright': '(C) 2008 Citrix Systems Inc',
    'driver_version': '1.0',
    'required_api_version': '1.0',
    'capabilities': CAPABILITIES,
    'configuration': CONFIGURATION
    }

# 2^16 Max port number value
INITIATORNAME_FILE = '/etc/iscsi/initiatorname.iscsi'
SECTOR_SHIFT = 9
MAXPORT = 65535
MAX_TIMEOUT = 15
MAX_LUNID_TIMEOUT = 60
ISCSI_PROCNAME = "iscsi_tcp"
# changing default port to monitor port
DEFAULT_PORT = 6789
''' end of modified definitions of paramters like in ISCSISR.py '''

class RBDSR(ISCSISR.ISCSISR):
    def handles(type):
        if type == "rbd":
            return True
        return False
    handles = staticmethod(handles)

    def load(self, sr_uuid):
        ''' Some repetition since LVHDoISCSI has pretty much everything inside of load method'''
        # Check if minimal amount of parameters(i.e. IP address of monitor) is passed to the call
        if not self.dconf.has_key('target') or not self.dconf['target']:
            raise xs_errors.XenError('ConfigTargetMissing')
        
        self.path = ''
        real_address = ''
        try:
            # For monitors we only need one address, since we get accurate map from the ceph later on in attach. 
            target_string = self.dconf['target'].split(',')
            real_address = socket.gethostbyname(target_string[0])
            util.SMlog('successfully resolved address to %s' % real_address)
        except:
            raise xs_errors.XenError('DNSError')
            
        ''' During XC SR creation, dialog first dicovers IQN and only then LUN.
        So if we have targetIQN in device-config but no SCSIid, means we discovering LUN/RBD image here '''
        if self.dconf.has_key('targetIQN') and not self.dconf.has_key('SCSIid'):
            pool_name = self.dconf['targetIQN']
            
            ### Getting RBD image corresponding to RBD pool
            block_list = self._getCEPH_response('sudo rbd -p %s ls' % pool_name)
            rbd_image_list = self._formatRBD_image(pool_name, block_list)
            ''' We don't attach rbd during discovery of the images, 
            but parent class(LVHDoISCSI) needs 'attached' flag to print LUNs'''
            self.attached = True
            
            ''' If we have SCSIid, means we have discovered targetIQN already and ready to attach rbd block'''    
        elif self.dconf.has_key('SCSIid'):
            self.path = '/dev/disk/by-id/scsi-%s' % self.dconf['SCSIid']
            if os.path.exists('/var/lock/sm/%s/sr' % sr_uuid):
                self.attach(sr_uuid)
                
            ''' This is a bit backwards, but based on the previous two if/elif statements, here we don't have
            either targetIQN nor SCSIid, which means we are at the begining of the XC iSCSI SR create dialog
            and need to discover RBD pools from the monitors.'''
        else:
            ### Getting RBD pool using ssh user and password
            rbd_pool_string = self._getCEPH_response('sudo ceph osd lspools')
            if 'fault' in rbd_pool_string or not rbd_pool_string:
                raise xs_errors.XenError('ISCSILogin')
            else:
                self._cleanCEPH_folder('/var/lib/rbd')
                rbd_pool_list = self._formatRBD_pool(rbd_pool_string)

            '''Discovered list should look like this: ('<ip address>:<port>', '<tgt>', '<iqn>')'''
            map = []
            for pool in rbd_pool_list.split('\n'):
                ''' With new-line-split we end up with last pool entry empty.
                This saves us efforts to append "*" record, which actually useless in this case.
                Should really remove it -> TODO'''
                if not pool:
                     pool = "*"
                map.append((real_address+":"+self.dconf['port'],"0",pool))
            util.SMlog(map)
            # Recycling code here and calling print_entries from ISCSISR.py
            super(RBDSR, self).print_entries(map)
            # User hasn't selected targetIQN yet, so throwing xs_error like in its iSCSI counterpart
            raise xs_errors.XenError('ConfigTargetIQNMissing')

            self.targetIQN = unicode(self.dconf['targetIQN']).encode('utf-8')
            self.attached = False
            
            
    def _formatCEPH_key(self, auth_key_string):
        if not os.path.exists('/etc/rbd'):
            os.makedirs('/etc/rbd')
        a = open('/etc/rbd/auth', 'w')
        for words in auth_key_string:
            if 'key: ' in words:
                rbd_admin_password = words.split('key: ')[1].rstrip()
        a.write(rbd_admin_password)
        a.close()
        return(rbd_admin_password)
        
        
    def _formatMON_list(self, mon_addrs_xml):
        addrs_xml = parseString(mon_addrs_xml[0].rstrip())
        if not os.path.exists('/etc/rbd'):
            os.makedirs('/etc/rbd')
        addr_file = open('/etc/rbd/mons', 'w')
        addr_list = []
        for ip in addrs_xml.getElementsByTagName('addr'):
            addr = ip.firstChild.data.split(':')[0] + '\n'
            addr_list.append(addr)
            addr_file.write(addr)
        addr_file.close()
        return(addr_list)
        
        
    def _formatRBD_pool(self, rbd_pool_string):
        base_path = '/var/lib/rbd/'
        pool_name_list = ''
        for pool in rbd_pool_string[1].split(','):
            if not pool.isspace() and pool != '':
                pool_name = pool.split(' ')[1]
                pool_name_list += pool_name + '\n'
                pool_path = os.path.join(base_path,pool_name)
                if not os.path.exists(pool_path):
                    os.makedirs(pool_path)
        return pool_name_list
        
        
    def _formatRBD_image(self, rbd_pool_name, rbd_image_string):
        base_path = '/var/lib/rbd/'
        pool_path = os.path.join(base_path, rbd_pool_name)
        self._cleanCEPH_folder(pool_path,False)
        for block in rbd_image_string:
            if not 'sudo' in block and '\r' in block: 
                rbd_image_path = os.path.join(base_path, rbd_pool_name, block.rstrip())
                rbd_image = open(rbd_image_path,'w')
                image_info = self._getCEPH_response('sudo rbd --format json -p %s info %s' % (rbd_pool_name, block))[2]
                util.SMlog('RBD info of the image is %s' % image_info)
                rbd_image.write('%s' % image_info)
                rbd_image.close()
        return 'list'
        
        
    def _cleanCEPH_folder(self, path,remove_root=True):
        if os.path.exists(path):
            for root, dirs, files in os.walk(path, topdown=False):
                for name in files:
                    os.remove(os.path.join(root, name))
                for name in dirs:
                    os.rmdir(os.path.join(root, name))
            if remove_root:
                os.rmdir(root)
                
    def _getRBD_index(self, image_name):
        parent_folder = ''
        for root, dirs, files in os.walk('/sys/devices/rbd', topdown=False):
            current_folder = root.split('/')[-1]
            if current_folder.isdigit():
                for file in files:
                    if file == 'name':
                        f = open(os.path.join(root,file), 'rt')
                        rbd_image_name = f.readline()
                        f.close()
                        if image_name in rbd_image_name:
                             parent_folder = current_folder
        return parent_folder
        
        
    def _getCEPH_response(self, cmd):
        s = pxssh.pxssh()
        s.force_password = True
        password = ""
        if self.dconf.has_key('chappassword_secret'):
            password = util.get_secret(self.session, self.dconf['chappassword_secret'])
        elif self.dconf.has_key('chappassword'):
            password = self.dconf['chappassword']
        user = self.srcmd.dconf['chapuser']
        target = self.srcmd.dconf['target'].split(',')[0]
        port = self.srcmd.dconf['port']
        if not s.login(target,user,password):
            util.SMlog('ssh login failed with last message %s' % s)
        else:
            s.sendline (cmd)
            s.prompt()
            result = s.before.split('\n')
            return result
                
                
    def attach(self, sr_uuid):
        ### Getting MON list using admin key above
        ceph_mon_list_xml = self._getCEPH_response('sudo ceph mon_status -f xml')
        ceph_mon_list = self._formatMON_list(ceph_mon_list_xml)
        
        # We got accurate list of monitor addresses, need pass that list of IPs to rbd add srting
        accurate_address_string = ''
        ''' TODO: very long list-to-string conversion, 
        should be something like: address_string = ''.join(ceph_mon_list).replace('\n',',') if len(ceph_mon_list) >= 1'''
        if len(ceph_mon_list) >= 1:
            address_string = ''
            for address in ceph_mon_list:
                address_string += address.replace('\n',',')
            self.dconf['targetlist'] = address_string[:-1]
            accurate_address_string = address_string[:-1]
        else:
            accurate_address_string = ceph_mon_list

        ### Getting admin key using ssh command
        if self.dconf.has_key('SCSIid') and self.dconf['SCSIid']:
            util._testHost(self.dconf['target'].split(',')[0], long(self.dconf['port']), 'RBD Monitor')
            rbd_auth_output =  self._getCEPH_response('sudo ceph auth list| grep admin -A1| grep key')
            rbd_auth_key = self._formatCEPH_key(rbd_auth_output)
            
            rbd_image_name = self.dconf['SCSIid']
            attach_string = '%s name=admin,secret=%s %s %s' % (accurate_address_string, rbd_auth_key, self.dconf['targetIQN'], rbd_image_name)
            if not os.path.exists('/sys/bus/rbd'):
                os.execlp("modprobe", "modprobe", "rbd")
            rbd_disk_path =  '/dev/disk/by-id/scsi-%s' % rbd_image_name
            # TODO: not correctly implemented - in by-scsid it should be a folder containing block links
            rbd_scsi_path =  '/dev/disk/by-scsid/%s' % rbd_image_name
            rbd_block_index = self._getRBD_index(rbd_image_name)
            if not os.path.exists(rbd_disk_path) and not rbd_block_index:
                try:
                    rbd_add = open('/sys/bus/rbd/add','w')
                    rbd_add.write(attach_string)
                    rbd_add.close() 
                    os.symlink('/dev/rbd%s' % str(self._getRBD_index(rbd_image_name)), rbd_disk_path)
                    os.symlink('/dev/rbd%s' % str(self._getRBD_index(rbd_image_name)), rbd_scsi_path)
                    self.attached = True
                except IOError, e:
                    util.SMlog('the error is %s' % e)
                    self.attached = False
        else:
            '''in iSCSI sr we need to attach target to interrogate LUN for size, scsi_id etc etc. 
            We don't need to do this with current way of finding things over ssh'''
            pass
      
      
    def detach(self, sr_uuid):
        if self.dconf.has_key('SCSIid') and self.dconf['SCSIid']:
            rbd_image_name = self.dconf['SCSIid']
            rbd_disk_path =  '/dev/disk/by-id/scsi-%s' % rbd_image_name
            rbd_scsi_path =  '/dev/disk/by-scsid/%s' % rbd_image_name
            rbd_image_index = self._getRBD_index(rbd_image_name)
            if os.path.exists(rbd_disk_path):
                os.unlink(rbd_disk_path)
            if os.path.exists(rbd_scsi_path):
                os.unlink(rbd_scsi_path)
            if os.path.exists('/dev/rbd%s' % rbd_image_index):
                rbd_remove = open('/sys/bus/rbd/remove','w')
                rbd_remove.write(rbd_image_index)
                rbd_remove.close()
        self.attached = False
      
      
    def refresh(self):
        # Unlike iSCSI SR we don't need to refresh paths or rescan sessions
        pass

    def print_LUNs(self):
        self.LUNs = {}
        rbd_size = ''
        rbd_identity = ''
        pool_path = os.path.join('/var/lib/rbd', self.dconf['targetIQN'])
        for file in util.listdir(pool_path):
            lun_path = os.path.join(pool_path, file)
            lun_file = open(lun_path, 'rt')
            lun_info = lun_file.read()
            for params in lun_info.split(','):
                if '"size' in params:
                    rbd_size = params.split(':')[1]
                if 'block_name_prefix' in params:
                    rbd_identity = params.split(':')[1]
            if rbd_size and rbd_identity:
                obj = self.vdi(self.uuid)
                self._divert_query(obj, lun_path,rbd_identity,rbd_size,file)
                self.LUNs[obj.uuid] = obj
      
      
    def _divert_query(self, vdi, path, rbd_id, rbd_size, lun_name):
        vdi.uuid = scsiutil.gen_uuid_from_string(rbd_id)
        vdi.location = self.uuid
        vdi.vendor = 'RADOS'
        vdi.serial = lun_name
        vdi.LUNid = rbd_id.split('.')[1]
        vdi.size = rbd_size
        vdi.SCSIid = lun_name
        vdi.path = path
        sm_config = util.default(vdi, "sm_config", lambda: {})
        sm_config['LUNid'] = str(vdi.LUNid)
        sm_config['SCSIid'] = vdi.SCSIid
        vdi.sm_config = sm_config
      
      
    def _attach_LUN_bySCSIid(self, SCSIid):
        if os.path.exists('/dev/disk/by-id/scsi-%s' % SCSIid):
            return True
        else:
            # Couldn't find what sr_uuid is used in attach, so just calling it with a string
            self.attach('existing-sr-uuid')
            return True
      
if __name__ == '__main__':
    SRCommand.run(RBDSR, DRIVER_INFO)
else:
    SR.registerSR(RBDSR)
