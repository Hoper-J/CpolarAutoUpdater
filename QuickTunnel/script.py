#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import re
import stat
import logging
import requests
from bs4 import BeautifulSoup
import paramiko
from getpass import getpass


# ------------------- 日志配置 -------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    handlers=[
        logging.StreamHandler(),  # 输出到控制台
        logging.FileHandler("script.log", mode='a', encoding='utf-8')  # 写入文件
    ]
)
logger = logging.getLogger(__name__)


# ------------------- 读取配置 -------------------
def load_config(config_path):
    """
    从 config_path 读取相关配置信息
    格式示例：
        cpolar_username = your_cpolar_username
        cpolar_password = your_cpolar_password
        server_user     = ubuntu
        server_password = your_server_password
        ssh_key_path    = ~/.ssh/id_rsa_server
        ssh_host_alias  = server
    """
    if not os.path.exists(config_path):
        logger.error(f"配置文件 {config_path} 不存在，请检查路径。")
        raise FileNotFoundError(f"配置文件 {config_path} 不存在，请检查路径。")

    config = {}
    with open(config_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            # 跳过空行和注释
            if not line or line.startswith("#"):
                continue
            key_value = line.split("=", 1)
            if len(key_value) == 2:
                key = key_value[0].strip()
                value = key_value[1].strip()
                config[key] = value
    logger.info(f"成功加载配置文件 {config_path}")
    return config

# ------------------- 获取 cpolar 映射信息 -------------------
def get_csrf_token(session, login_page_url):
    """
    通过 GET 请求登录页，解析出 csrf_token
    """
    response = session.get(login_page_url)
    if response.status_code != 200:
        logger.error(f"获取登录页面失败，状态码：{response.status_code}")
        raise Exception(f"获取登录页面失败，状态码：{response.status_code}")
    
    soup = BeautifulSoup(response.text, 'html.parser')
    # <input type="hidden" name="csrf_token" value="xxx">
    csrf_input = soup.find("input", {"name": "csrf_token"})
    if not csrf_input:
        logger.error("未能在登录页找到 csrf_token 字段，如果出现该问题，那么可能是官方修改了页面结构。")
        raise Exception("未能在登录页找到 csrf_token 字段，如果出现该问题，那么可能是官方修改了页面结构。")

    logger.info("成功获取 csrf_token")
    return csrf_input.get("value")

def do_login(session, login_url, username, password, csrf_token):
    """
    使用 username, password, csrf_token 进行登录
    """
    payload = {
        'login': username,
        'password': password,
        'csrf_token': csrf_token
    }
    response = session.post(login_url, data=payload)
    if response.status_code != 200:
        logger.error(f"登录失败，状态码：{response.status_code}")
        raise Exception(f"登录失败，状态码：{response.status_code}")
    # 页面如果包含 "Logout" 等字样，一般说明登录成功
    if "Logout" not in response.text and "status" not in response.text:
        logger.error("登录失败，可能是用户名或密码错误，或页面结构变化。")
        raise Exception("登录失败，可能是用户名或密码错误，或页面结构变化。")
    logger.info("成功登录 cpolar")

def get_target_string(session, status_url):
    """
    登录成功后，访问 status 页面，解析得到类似于 tcp://xxx:port 的字符串
    """
    response = session.get(status_url)
    if response.status_code != 200:
        logger.error(f"获取隧道信息失败，状态码：{response.status_code}")
        raise Exception(f"获取隧道信息失败，状态码：{response.status_code}")
    
    soup = BeautifulSoup(response.text, 'html.parser')
    # 该部分仅处理单隧道的情况，如果启用了多个隧道，需要更改为指定隧道的筛选逻辑，但暂不做修改，因为该脚本针对于免费版
    target_element = soup.find('a', href="#ZgotmplZ")
    if target_element:
        logger.info("成功获取隧道映射信息")
        logger.info(f"cpolar 映射字符串 = {target_element.text.strip()}")
        return target_element.text.strip()
    else:
        logger.error("未找到隧道信息，可能未激活或页面结构变化。")
        raise Exception("未找到隧道信息，可能未激活或页面结构变化。")

def extract_hostname_and_port(target_string):
    """
    提取 tcp://xxx:port 的 HostName 和 Port
    """
    pattern = r'^tcp://(.*?):(\d+)$'
    matches = re.match(pattern, target_string)
    if matches:
        hostname = matches.group(1)
        port = matches.group(2)
        logger.info(f"成功解析 HostName={hostname}, Port={port}")
        return hostname, port
    else:
        logger.error(f"未找到匹配的字符串，target_string={target_string}")
        raise Exception(f"未找到匹配的字符串，target_string={target_string}")

# ------------------- 生成本地 SSH Key (若无) 并上传到服务器 -------------------
def generate_ssh_key_if_not_exists(private_key_path, comment="generated-by-script"):
    """
    如果本地没有对应的私钥文件，则生成一对 RSA 密钥
    """
    private_key_path = os.path.expanduser(private_key_path)
    if os.path.exists(private_key_path):
        logger.info(f"检测到已有私钥: {private_key_path}")
        pub_path = private_key_path + ".pub"
        if not os.path.exists(pub_path):
            key = paramiko.RSAKey.from_private_key_file(private_key_path)
            public_key_text = f"ssh-rsa {key.get_base64()} {comment}"
            with open(pub_path, "w", encoding="utf-8") as pub_file:
                pub_file.write(public_key_text + "\n")
            logger.info(f"补齐生成公钥: {pub_path}")
    else:
        logger.info(f"未发现私钥 {private_key_path}，开始生成...")
        key = paramiko.RSAKey.generate(2048)
        key.write_private_key_file(private_key_path)
        os.chmod(private_key_path, stat.S_IRUSR | stat.S_IWUSR)

        pub_path = private_key_path + ".pub"
        public_key_text = f"ssh-rsa {key.get_base64()} {comment}"
        with open(pub_path, "w", encoding="utf-8") as pub_file:
            pub_file.write(public_key_text + "\n")
        logger.info(f"已生成新的 SSH 密钥对: 私钥={private_key_path}, 公钥={pub_path}")

def test_ssh_connection(hostname, port, username, key_path, timeout=10):
    """
    尝试使用 SSH 密钥连接到远程服务器。
    返回 True 表示连接成功，False 表示连接失败（认证错误）。
    """
    key_path = os.path.expanduser(key_path)
    try:
        key = paramiko.RSAKey.from_private_key_file(key_path)
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(hostname=hostname, port=int(port), username=username, pkey=key, timeout=timeout)
        ssh.close()
        logger.info("使用 SSH 密钥连接成功，无需上传公钥。")
        return True
    except paramiko.AuthenticationException:
        logger.warning("使用 SSH 密钥连接失败，可能需要上传公钥。")
        return False
    except paramiko.SSHException as e:
        logger.error(f"SSH 连接过程中发生错误: {e}")
        return False
    except Exception as e:
        logger.error(f"连接到服务器时发生错误: {e}")
        return False

def upload_public_key(hostname, port, username, password, local_pubkey_path):
    """
    使用 Paramiko + 密码登录方式，将本地 public key 上传到远程服务器的 ~/.ssh/authorized_keys
    """
    private_key_path = os.path.expanduser(local_pubkey_path)
    pub_path = private_key_path + ".pub"

    with open(pub_path, "r", encoding="utf-8") as f:
        public_key_text = f.read().strip()

    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())

    logger.info(f"正在连接到远程服务器 {username}@{hostname}:{port} ...")
    try:
        ssh.connect(hostname=hostname, port=int(port), username=username, password=password)
        sftp = ssh.open_sftp()

        # 检查 ~/.ssh 目录
        try:
            sftp.stat(".ssh")
            logger.info("远程服务器已存在 ~/.ssh 目录。")
        except FileNotFoundError:
            logger.info("远程服务器不存在 ~/.ssh 目录，正在创建...")
            ssh.exec_command("mkdir -p ~/.ssh && chmod 700 ~/.ssh")
    
        # 检查并创建 authorized_keys 文件
        authorized_keys_path = ".ssh/authorized_keys"
        try:
            sftp.stat(authorized_keys_path)
        except FileNotFoundError:
            logger.info("远程服务器不存在 authorized_keys 文件，正在创建...")
            ssh.exec_command("touch ~/.ssh/authorized_keys && chmod 600 ~/.ssh/authorized_keys")
    
        # 下载 authorized_keys 文件到本地临时文件
        local_temp = "authorized_keys_temp"
        sftp.get(authorized_keys_path, local_temp)
    
        # 读取旧内容并检查是否已存在公钥
        with open(local_temp, "r", encoding="utf-8") as f:
            old_keys = f.read().splitlines()
    
        # 如果 public_key_text 不在文件里，则追加
        if public_key_text not in old_keys:
            with open(local_temp, "a", encoding="utf-8") as f:
                f.write(public_key_text + "\n")
                logger.info("公钥未在远程服务器中，已追加到本地临时文件。")
        else:
            logger.info("公钥已存在于远程服务器的 authorized_keys 文件中，无需追加。")
    
        # 上传更新后的 authorized_keys 文件回服务器
        sftp.put(local_temp, authorized_keys_path)
        ssh.exec_command("chmod 600 ~/.ssh/authorized_keys")
        logger.info(f"成功上传更新后的 authorized_keys 文件到远程服务器: {authorized_keys_path}")
    except paramiko.SSHException as e:
        logger.error(f"SSH 连接过程中发生错误: {e}")
        raise
    except Exception as e:
        logger.error(f"上传公钥过程中发生错误: {e}")
        raise
    finally:
        # 清理本地临时文件和关闭连接
        if os.path.exists(local_temp):
            os.remove(local_temp)
        sftp.close()
        ssh.close()
    logger.info("公钥上传成功，可使用免密方式登录远程服务器。")

# ------------------- 更新本地 ~/.ssh/config -------------------
def ensure_ssh_config_exists(ssh_config_path):
    """
    如果 ssh config 文件不存在，则创建一个空文件
    """
    if not os.path.exists(ssh_config_path):
        with open(ssh_config_path, "w", encoding="utf-8") as f:
            f.write("# SSH config file created by script\n")
        logger.info(f"未检测到 {ssh_config_path}，已自动创建。")

def update_or_create_host_block(ssh_config_path, host_alias, hostname, port, user=None, identity_file=None):
    """
    更新或创建 ~/.ssh/config 中指定 HostAlias 的配置块
    - 如果文件不存在，先创建。
    - 如果不存在 Host <alias> 块，追加新块。
    - 如果已存在，则只更新 HostName, Port, User, IdentityFile, PreferredAuthentications。
    """
    ssh_config_path = os.path.expanduser(ssh_config_path)
    ensure_ssh_config_exists(ssh_config_path)

    with open(ssh_config_path, "r", encoding="utf-8") as f:
        lines = f.readlines()

    found_host_block = False
    updated_host_block = False

    i = 0
    while i < len(lines):
        line_stripped = lines[i].strip()
        # 找到目标 Host <alias>
        if line_stripped == f"Host {host_alias}":
            found_host_block = True
            i += 1

            # 在此 Host 块中检测并更新
            has_preferred_auth = False
            while i < len(lines):
                # 如果下一行到了新 Host 或空行(分段)，就跳出
                if lines[i].strip().startswith("Host ") or lines[i].strip() == "":
                    break

                # 更新 HostName
                if lines[i].strip().startswith("HostName"):
                    old_val = lines[i].split()[-1]
                    if old_val != hostname:
                        lines[i] = f"\tHostName {hostname}\n"
                        updated_host_block = True

                # 更新 Port
                elif lines[i].strip().startswith("Port"):
                    old_val = lines[i].split()[-1]
                    if old_val != port:
                        lines[i] = f"\tPort {port}\n"
                        updated_host_block = True

                # 更新 User
                elif user and lines[i].strip().startswith("User"):
                    old_val = lines[i].split()[-1]
                    if old_val != user:
                        lines[i] = f"\tUser {user}\n"
                        updated_host_block = True

                # 更新 IdentityFile
                elif identity_file and lines[i].strip().startswith("IdentityFile"):
                    old_val = lines[i].split()[-1]
                    if old_val != identity_file:
                        lines[i] = f"\tIdentityFile {identity_file}\n"
                        updated_host_block = True

                # 如果已存在 PreferredAuthentications，则直接修改为 publickey
                elif lines[i].strip().startswith("PreferredAuthentications"):
                    has_preferred_auth = True
                    if "publickey" not in lines[i]:
                        lines[i] = "\tPreferredAuthentications publickey\n"
                        updated_host_block = True

                i += 1

            # 当前 Host 块结束后，如果还没找到 PreferredAuthentications，就插入
            if not has_preferred_auth:
                lines.insert(i, "\tPreferredAuthentications publickey\n")
                i += 1
                updated_host_block = True

            # 完成对当前 Host <alias> 块的处理后跳出
            break
            
        i += 1

    # 如果没有该别名，则追加一个新块
    if not found_host_block:
        new_block = [f"\nHost {host_alias}\n",
                     f"\tHostName {hostname}\n",
                     f"\tPort {port}\n"]
        if user:
            new_block.append(f"\tUser {user}\n")
        if identity_file:
            new_block.append(f"\tIdentityFile {identity_file}\n")
        new_block.append("\tPreferredAuthentications publickey\n\n")
        lines.extend(new_block)
        updated_host_block = True
        logger.info(f"未检测到 Host {host_alias} 块，已在文件末追加配置。")

    if updated_host_block:
        with open(ssh_config_path, "w", encoding="utf-8") as f:
            f.writelines(lines)
        logger.info(f"已更新 {ssh_config_path} 的 Host {host_alias} 配置 (HostName={hostname}, Port={port})")
    else:
        logger.info(f"Host {host_alias} 配置与当前一致，无需更新。")

# ------------------- 主流程 -------------------
def main():
    # 读取配置
    config_path = os.path.expanduser("./config.txt")
    config = load_config(config_path)

    # 取 cpolar 登录信息
    cpolar_username = config.get("cpolar_username")
    cpolar_password = config.get("cpolar_password")
    if not cpolar_username or not cpolar_password:
        raise Exception("config.txt 中缺少 cpolar_username 或 cpolar_password")

    # 取远程服务器登录信息(用于首次密码上传公钥)
    server_user = config.get("server_user", "ubuntu")
    server_password = config.get("server_password")

    # SSH 私钥路径
    ssh_key_path   = config.get("ssh_key_path", "~/.ssh/id_rsa_server")
    host_alias     = config.get("ssh_host_alias", "server")

    # 自动登录 cpolar 并获取隧道信息
    session = requests.Session()
    login_page_url = "https://dashboard.cpolar.com/login"
    login_url      = "https://dashboard.cpolar.com/login"
    status_url     = "https://dashboard.cpolar.com/status"

    csrf_token = get_csrf_token(
        session,
        login_page_url
    )
    do_login(
        session,
        login_url,
        cpolar_username,
        cpolar_password,
        csrf_token
    )

    target_string = get_target_string(
        session,
        status_url
    )
    hostname, port = extract_hostname_and_port(target_string)


    # 本地生成 SSH 密钥(如果没有)
    generate_ssh_key_if_not_exists(
        ssh_key_path,
        comment=f"{server_user}@{hostname}"
    )

    # 尝试使用 SSH 密钥连接
    can_connect_with_key = test_ssh_connection(
        hostname,
        port,
        server_user,
        ssh_key_path
    )
    # 如果 SSH 密钥连接失败，则需要上传公钥
    if not can_connect_with_key: 
        # 如果配置文件 config.txt 没有明文写出密码，则让用户输入
        if not server_password:
            server_password = getpass(f"请输入远程服务器用户 {server_user} 的密码: ")
            
        # 上传公钥到远程服务器
        upload_public_key(
            hostname,
            port,
            server_user,
            server_password,
            ssh_key_path
        )
    
    # 更新本地的 ~/.ssh/config 以便使用 host_alias 登陆
    ssh_config_path = "~/.ssh/config"
    update_or_create_host_block(
        ssh_config_path,
        host_alias,
        hostname,
        port,
        user=server_user,
        identity_file=os.path.expanduser(ssh_key_path)
    )

    logger.info("一切就绪！使用以下命令免密登录到服务器：")
    logger.info(f"\tssh {host_alias}")


if __name__ == "__main__":
    main()

