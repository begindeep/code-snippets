import paramiko
from stat import S_ISDIR
import errno
import os
import stat
import time
import plistlib

IP = '192.168.0.190'
username = 'root'
password = 'alpine'


ssh = paramiko.SSHClient()
# Auto add host to known hosts
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
# Connect to server
ssh.connect(IP, username=username, password=password)

transport = paramiko.Transport((IP, 22))
transport.connect(username=username, password=password)
sftp = paramiko.SFTPClient.from_transport(transport)
 

class App:
    def __init__(self, no, name, path):
        self.no = no
        self.name = name
        self.path = path
        
listApp = []

def exists_remote(sftp_client, path):
    try:
        sftp_client.stat(path)
    except IOError as e:
        if e.errno == errno.ENOENT:
            return False
        raise
    else:
        return True

def get_installed_apps(sftp_client, remote_dir):
    if not exists_remote(sftp_client, remote_dir):
        return
    i = 1
    for filename in sftp_client.listdir(remote_dir):
        if stat.S_ISDIR(sftp_client.stat(remote_dir + filename).st_mode):
            # uses '/' path delimiter for remote server
            if exists_remote(sftp_client, remote_dir + filename + '/iTunesMetadata.plist'):
                app_dir = remote_dir + filename + '/'
                for file in sftp_client.listdir(app_dir):
                    if stat.S_ISDIR(sftp_client.stat(app_dir + file).st_mode):
                        listApp.append(App(i, file[0:len(file)-4], app_dir + file))
                        i+=1
            
def get_app_by_index(index):
    for x in listApp:
        if x.no == int(index):
            return x
    pass
    
def edit_plist_info(suffix, app_path):
    # app_path = /Applications/Facebook2.app
    if not os.path.exists("./tmp"):
        os.mkdir("./tmp")
    plist_file = './tmp/Info.plist'
    print('Download ' + app_path + '/Info.plist')
    sftp.get(app_path + '/Info.plist', plist_file)
    with open(plist_file, 'rb') as f:
        pl = plistlib.load(f)
    
    pl["CFBundleDisplayName"] = pl["CFBundleDisplayName"] + suffix
    pl["CFBundleName"] = pl["CFBundleName"] + suffix
    pl["CFBundleIdentifier"] = pl["CFBundleIdentifier"] + suffix

    with open(plist_file, 'wb') as fp:
        plistlib.dump(pl, fp)
    # upload Info.plist after editing
    (ssh_stdin, ssh_stdout, ssh_stderr) = ssh.exec_command('rm ' + app_path + '/Info.plist')
    exit_status = ssh_stdout.channel.recv_exit_status()
    print ("Delete status: %s" % exit_status)
    sftp.put(plist_file, app_path + '/Info.plist')
    # remove /tmp folder
    try:
        os.remove(plist_file)
        os.rmdir("./tmp")
    except IOError:
        print('Error remove tmp folder')
    
get_installed_apps(sftp, '/var/containers/Bundle/Application/')

for app in listApp:
    print(str(app.no) + '. ' + app.name)
    
notSelect = True
while notSelect:
    selectNo = input('Chọn app muốn nhân bản (gõ số thứ tự): ')
    selectApp = get_app_by_index(selectNo)
    if (selectApp == None):
        print('Chọn sai. Vui lòng chọn lại')
    else:
        notSelect = False

print('----> Nhân bản: ' + selectApp.name)
notSelect = True
while notSelect:
    inputVal = input('Nhập số lượng nhân bản: ')
    if inputVal.isnumeric() and int(inputVal) > 0 and int(inputVal) < 100:
        quantity = int(inputVal)
        notSelect = False
    else:
        print('Vui lòng nhập số từ 1-100')

for index in range(1, quantity + 1):
    print('====== Nhân bản ' + selectApp.name + str(index) + ' ======')
    newAppPath = '/Applications/' + selectApp.name + str(index) + '.app'
    print('Đang copy data ' + selectApp.path)
    # print('cp -r ' + selectApp.path + ' /Applications')
    (ssh_stdin, ssh_stdout, ssh_stderr) = ssh.exec_command('cp -r ' + selectApp.path + ' /Applications')
    exit_status = ssh_stdout.channel.recv_exit_status()
    print ("copy status: %s" % exit_status)
    # move:  mv /Applications/Facebook.app /Applications/Facebook2.app
    # print('mv /Applications/' + selectApp.name + '.app ' + newAppPath)
    (ssh_stdin, ssh_stdout, ssh_stderr) = ssh.exec_command('mv /Applications/' + selectApp.name + '.app ' + newAppPath)
    
    # dir /var/containers/Bundle/Application/8FB44A97-F042-4F16-9C69-10135E0F9DFA/Facebook.app
    # copy tới /Applications/
    # Get status code of command
    exit_status = ssh_stdout.channel.recv_exit_status()
    # Print status code
    print ("move status: %s" % exit_status)
    
    edit_plist_info(str(index), newAppPath)

# chạy refresh ui để các icon app nhân bản show lên
(ssh_stdin, ssh_stdout, ssh_stderr) = ssh.exec_command('uicache')
exit_status = ssh_stdout.channel.recv_exit_status()
print ("Đã nhân bản xong, status: %s" % exit_status)


"""
def download_files(sftp_client, remote_dir, local_dir):
    if not exists_remote(sftp_client, remote_dir):
        return

    if not os.path.exists(local_dir):
        os.mkdir(local_dir)

    for filename in sftp_client.listdir(remote_dir):
        if stat.S_ISDIR(sftp_client.stat(remote_dir + filename).st_mode):
            # uses '/' path delimiter for remote server
            print ("Đang download folder: %s" % (remote_dir + filename))
            download_files(sftp_client, remote_dir + filename + '/', os.path.join(local_dir, filename))
        else:
            if not os.path.isfile(os.path.join(local_dir, filename)):
                sftp_client.get(remote_dir + filename, os.path.join(local_dir, filename))



start = time.time()
download_files(sftp, remote_dir, local_dir)
end = time.time()

print(f"Thời gian download: {(end-start):.02f} s")
"""  
    
# Close ssh connect
ssh.close()
# Close sftp
sftp.close()
transport.close()
