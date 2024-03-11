import os
import paramiko
import argparse

def upload_file_to_server(server_ip, server_port, local_file_path):
    try:
        # Create an SSH client object
        ssh = paramiko.SSHClient()

        # Automatically add host keys
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())

        # Connect using SSH key
        ssh.connect(server_ip, port=server_port, username='suibidata2023', key_filename='suibikey.ppk')

        # Create an SFTP client object
        sftp = ssh.open_sftp()

        # Specify the local file and remote file paths
        fileName = local_file_path
        remote_file_path = '/var/www/html/upload/'
        upload_file = remote_file_path + os.path.basename(fileName)

        # Upload the file
        sftp.put(fileName, upload_file)

        # Close the SFTP connection
        sftp.close()

        uploaded_url = f'http://{server_ip}/upload/{os.path.basename(fileName)}'  # Construct the uploaded URL
        print(f'文件 {local_file_path} 已成功上傳到伺服器 {server_ip} 的 {remote_file_path}。')
        print(f'下載網址: {uploaded_url}')

        return uploaded_url  # Return the uploaded URL as a string
    except Exception as e:
        print(f'上傳文件時出現錯誤：{str(e)}')
        return None  # Return None in case of an error
    finally:
        # Close the SSH connection
        ssh.close()

def main():
    # parser = argparse.ArgumentParser(description='Upload a file to a remote server using SSH and Paramiko.')
    # parser.add_argument('server_ip', type=str, help='Remote server IP address or hostname')
    # parser.add_argument('server_port', type=int, help='SSH port on the remote server')
    
    # parser.add_argument('local_file_path', type=str, help='Local file path to upload')
    
    # args = parser.parse_args()
    
    uploaded_url = upload_file_to_server("34.106.250.143", 22 , "A_car.zip")

if __name__ == '__main__':
    main()
