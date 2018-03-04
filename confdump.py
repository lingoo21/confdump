#!/usr/bin/env python
#-------------------------------------------------------------------------------
# Name:        configdump.py
# Purpose:     dump the device configuration with ssh
#
# Author:      Sonic
#
# Created:     08/Apr/2016
# Copyright:   (c) Sonic 2016
# Version:     0.1 only support Junos and Screenos
#              0.2 file owner read only
#              o.3 add class for f5 backup
#-------------------------------------------------------------------------------
import argparse
import syslog
from datetime import datetime
from netmiko import ConnectHandler
from netmiko import SCPConn
import os
import pwd
import grp

class ssh_host(object):
    def __init__(self):
        self.conn_dict = {}
        #self.os_cli_lst = [('juniper_junos', 'show configuration | no-more', 'junos'),
        #                   ('juniper', 'get config all', 'screenos')]
        self.os_cli_lst = [('cisco_ios', 'show running-config', 'cisco'),
                           ('cisco_nxos', 'show run', 'cisco')]
        self.args = self._get_args()
        self.filename = self.args.filename
        self.cli = self.os_cli_lst[self.args.os_type][1]
        self.conn_dict['username'] = self.args.username
        self.conn_dict['password'] = self.args.password
        self.conn_dict['ip'] = self.args.ip_addr
        #if self.args.os_type < 2:
            #self.conn_dict['device_type'] = 'juniper'
        #else:
            #self.conn_dict['device_type'] = self.os_cli_lst[self.args.os_type][0]
        self.conn_dict['device_type'] = self.os_cli_lst[self.args.os_type][0]
        self.conn_dict['verbose'] = False


    def _get_args(self):
        now = datetime.now()
        _user = 'cattool'
        len_oc = len(self.os_cli_lst)
        parser = argparse.ArgumentParser()
        parser.add_argument("-t", "--os_type", type=int, choices=range(len_oc),
                            default=0,
                            #required=True,
                            help='Keep it in default setting, 0')
                            #help=str(['Chooce %s for %s: %s\n' % 
                            #         (i, self.os_cli_lst[i][2], self.os_cli_lst[i][1])
                            #         for i in range(len_oc)]))
        parser.add_argument("-u", "--username", default=_user, 
                            help="Default user name: %s" % _user)
        parser.add_argument("-p", "--password", required=True)
        parser.add_argument("-i", "--ip_addr", required=True)
        parser.add_argument("-f", "--filename", required=True,
                            help="Save to the given path.")
        args =  parser.parse_args()
        return args


    def download_config(self):
        #print(self.conn_dict, self.cli)
        try:
            net_connect = ConnectHandler(**self.conn_dict)
            net_connect.enable()
            net_connect.send_command('terminal length 0')
            _out = net_connect.send_command(self.cli)
            net_connect.disconnect()
        except KeyboardInterrupt:
            net_connect.disconnect()
        #print(_out[:300])
        self.config = _out
    

    def _write_config(self):
        with open(self.filename, 'w') as f:
            f.write(self.config)


    def save(self):
        self.download_config()
        self._write_config()
        self.change_priv()


    def change_priv(self):
        if os.path.isfile(self.filename):
            os.chmod(self.filename, 0660)
            uid = pwd.getpwnam("www-data").pw_uid
            gid = grp.getgrnam("www-data").gr_gid
            os.chown(self.filename, uid, gid)
        print("%s: Saved the configuration from %s to %s" %
             (datetime.now().strftime("%b %d %H:%M"), 
              self.conn_dict['ip'],
              self.filename))
           

class ssh_host_f5(ssh_host):
    def __init__(self):
        super(ssh_host_f5, self).__init__()
        self.f5temp_file = '/shared/tmp/config/f5_auto_backup'
        self.f5temp_suffix = '.ucs'
        self._keyword = ' is saved'
        self.os_cli_lst = [(
            'linux',
            'tmsh save /sys ucs {}'.format(self.f5temp_file),
            #'tmsh list ltm pool /Gaming/CasinoHTML5CDNTEG9',
            'f5'
        )]
        self.conn_dict['device_type'] = self.os_cli_lst[self.args.os_type][0]
        self.cli = self.os_cli_lst[self.args.os_type][1]

    
    def cli_ans_chk( self, output='', keyword=''):
        ans = False
        if keyword in output:
            ans = True
        return ans


    def download_config(self):
        _f = self.f5temp_file + self.f5temp_suffix
        with ConnectHandler(**self.conn_dict) as remote_conn:
            _out = remote_conn.send_command(self.cli)
            syslog.syslog('@{} {}'.format(self.conn_dict['ip'], _out))
            if self.cli_ans_chk(_out, _f+self._keyword):
                scp_conn = SCPConn(remote_conn)
                scp_conn.scp_get_file(_f, self.filename)
                syslog.syslog('scp ucs file from {} to {}'.format(
                    self.conn_dict['ip'],
                    self.filename)
                )


    def save(self):
        self.download_config()
        self.change_priv()


if __name__ == "__main__":
    #h1 = ssh_host()
    #h1.save()
    h2 = ssh_host_f5()
    h2.save()
