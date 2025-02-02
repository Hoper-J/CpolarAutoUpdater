<div align="center">

[中文](./README.md) | English

</div>

- **This repository provides a simple solution for internal network penetration based on the free version of cpolar**.
  - Since the `host` and `port` of the cpolar free version change periodically, manually updating the information can be cumbersome. This repository addresses this issue with automated scripts.
- **The script will automatically update the configuration file on the client to enable remote access and password-free SSH login**. The steps are as follows:
  - Log in to cpolar to obtain tunnel information.
  - Check for local SSH keys, and automatically generate them if they don’t exist.
  - Upload the public key to the remote server to enable password-free login.
  - Update the local `~/.ssh/config` file to simplify SSH connection configurations.
- **Currently tested only on Windows/Mac/Linux systems.**

------

## Getting Started

> **Definitions of Server and Client**
>
> To clarify, consider the common scenario: "You are using a laptop at home" to remotely connect to "a desktop with a GPU in the lab." In this repository, the remote desktop is referred to as the "server," and your laptop is referred to as the "client."

<details>
    <summary> <h3> Server Configuration </h3> </summary>

Please refer to the [official documentation](https://www.cpolar.com/docs) for configuration according to your system. Below is the configuration for Linux:

1. **Installation**

   - For users in China:

     ```bash
     curl -L https://www.cpolar.com/static/downloads/install-release-cpolar.sh | sudo bash
     ```

   - For users outside China:

     ```bash
     curl -sL https://git.io/cpolar | sudo bash
     ```

2. **Token Authentication**

   Visit cpolar: https://dashboard.cpolar.com/signup, register for an account (email and phone verification are not required), and log in.

   ![Login](https://i-blog.csdnimg.cn/blog_migrate/5525126a4890c9305b47a25620a3569e.png)

   After logging in to the cpolar [dashboard](https://dashboard.cpolar.com/get-started), click on `验证` on the left menu to find your authentication token. Enter the token in the command line:

   ```bash
   cpolar authtoken xxxxxxx
   ```

   ![Authtoken](https://i-blog.csdnimg.cn/blog_migrate/e24196b03a5f25c8bea1b2f2bba20d39.png)

3. **Enable Auto-Start**

   Run the following commands to configure cpolar to start automatically at boot. This ensures connection even after the remote server restarts:

   ```bash
   sudo systemctl enable cpolar  # Add cpolar to system services
   sudo systemctl start cpolar   # Start cpolar service
   sudo systemctl status cpolar  # Check service status
   ```

   If it displays `active`, the service is running successfully.

4. **Check the Username on the Server**

   ```bash
   whoami
   ```

   This will be used later for the client configuration file.

> **[Optional] Check Public Address and Port Number**
>
> You can verify the status of the network tunneling or port forwarding via:
>
> 1. Use the browser on the server to access [127.0.0.1:9200](http://127.0.0.1:9200/#/dashboard) and log into the local cpolar web UI.
> 2. Visit https://dashboard.cpolar.com/status on the client to find the URL corresponding to the `ssh` tunnel.
> 3. Run `script.py` directly (in the client section).
>
> **Example:**
>
> - URL: `tcp://3.tcp.vip.cpolar.cn:10387`  
>   (This is the full address for accessing the service.)
> - Public Address: `3.tcp.vip.cpolar.cn`  
>   (The public hostname provided by cpolar.)
> - Port Number: `10387`  
>   (The port number for accessing the tunnel.)

</details>

### Client Configuration

<details>
    <summary> <h4> Linux / Mac </h4> </summary>

1. **Clone the Repository**

   ```bash
   git clone https://github.com/Hoper-J/CpolarAutoUpdater
   cd CpolarAutoUpdater
   ```

2. **Configuration File**

   Fill in your cpolar username/password and the server username (retrieved using `whoami`) in the `config.txt` file:

   ```txt
   # Please fill in the details correctly
   cpolar_username = your_cpolar_username
   cpolar_password = your_cpolar_password
   server_user     = your_server_user
   
   # Custom settings
   ports           = 8888, 6666
   auto_connect    = True
   
   # The following settings can be left as is
   server_password = 
   ssh_key_path    = ~/.ssh/id_rsa_server
   ssh_host_alias  = server
   ```

   **Parameter Descriptions**

   - `cpolar_username` / `cpolar_password`: Your cpolar account credentials.
   - `server_user` / `server_password`: The SSH username and password for the remote server. You can leave the password blank; the script will prompt for input if not provided.
   - `ports`: Ports to be mapped. Defaults to `8888` and `6006`. Use commas (`,`) to separate multiple ports.
   - `auto_connect`: Determines whether the script automatically connects to the server after running. Defaults to `True`. Set to `False` to disable automatic connection.
   - `ssh_key_path`: Path for storing the SSH private key. If the key does not exist, it will be automatically created.
   - `ssh_host_alias`: Alias for the SSH host in the client configuration, simplifying connection commands.

3. **Environment Setup**

   Install the following dependencies before running the script:

   - `requests`
   - `beautifulsoup4`
   - `paramiko`

   Execute the following command:

   ```bash
   pip install requests beautifulsoup4 paramiko
   ```

4. **Run the Script**

   ```bash
   python auto_tunnel.py
   ```

   The script will automatically connect to the server. Press `Ctrl+D` to exit.

> **Manually Connect to the Server**
>
> Depending on your `ssh_host_alias` (default: `server`), you can log in to the server without a password using the following command:
>
> ```bash
> ssh server
> ```

#### [Optional] Alias Setup

To make it easier to use the script, you can set up an alias so that it can be executed from any directory.

**Check Your Shell Type**

First, check which shell you are using:

```bash
echo $SHELL
```

- If the output is `/bin/bash`, you are using Bash, and the configuration file is `~/.bashrc`.
- If the output is `/bin/zsh`, you are using Zsh, and the configuration file is `~/.zshrc`.

**Add an Alias**

Based on your shell type, run one of the following commands:

- **For Bash**:

  ```bash
  echo "alias tunnel='python $(pwd)/auto_tunnel.py'" >> ~/.bashrc
  source ~/.bashrc
  ```

- **For Zsh**:

  ```bash
  echo "alias tunnel='python $(pwd)/auto_tunnel.py'" >> ~/.zshrc
  source ~/.zshrc
  ```

**Verify Alias Setup**

Once the alias is set up, you can run the script from any directory using the following command:

```bash
tunnel
```

> [!note]
>
> **Change the Alias Name**
>
> If you don’t want to use `tunnel` as the alias, you can replace it with any name you prefer. For example, replace `tunnel` with `my_tunnel`:
>
> ```bash
> echo "alias my_tunnel='python $(pwd)/auto_tunnel.py'" >> ~/.bashrc
> ```
>
> **Remove the Alias**
>
> If you want to delete the alias, you can use the following commands:
>
> - **For macOS**:
>
>   ```bash
>   sed -i '' '/alias tunnel/d' ~/.bashrc && source ~/.bashrc
>   ```
>
> - **For Linux**:
>
>   ```bash
>   sed -i '/alias tunnel/d' ~/.bashrc && source ~/.bashrc
>   ```
>
> If you are using Zsh, replace `~/.bashrc` with `~/.zshrc`.
>
> **Update the Alias Path**
>
> If the script is moved to a different directory, repeat the steps above to update the alias.

</details>

<details>
    <summary> <h4> Windows </h4> </summary>

1. **Install Git**

   a. **Download Git**

   Go to the [official Git download page](https://git-scm.com/download/win). The version used in this demonstration is shown in the image below:

   ![Git Download Version](https://blogby.oss-cn-guangzhou.aliyuncs.com/20250126203356.png)

   Run the downloaded installer. You can keep all the default settings. Once the installation is complete, Git will be automatically added to the system `PATH`.

   b. **Verify Installation**

   Open CMD as shown below:

   ![Open CMD](https://blogby.oss-cn-guangzhou.aliyuncs.com/20250126203411.png)

   Enter the following command to check if Git is installed successfully:

   ```bash
   git --version
   ```

   **Output:**

   ![Git Version Output](https://blogby.oss-cn-guangzhou.aliyuncs.com/20250126203403.png)

   c. **Clone the Repository**

   Run the following commands to clone the repository:

   ```bash
   git clone https://github.com/Hoper-J/CpolarAutoUpdater
   cd CpolarAutoUpdater
   ```

   ![Git Clone Example](https://blogby.oss-cn-guangzhou.aliyuncs.com/20250126203406.png)

2. **Install Python**

   a. **Download Python**

   Visit the [official Python download page](https://www.python.org/downloads/windows/) and select any version (this demonstration uses Python 3.12.8). Run the downloaded installer. Be sure to check the option `Add python.exe to PATH` and click `Install Now` to complete the installation.

   ![Python Install Example](https://blogby.oss-cn-guangzhou.aliyuncs.com/20250126203409.png)

   b. **Verify Installation**

   Open CMD and enter the following command to verify the Python installation:

   ```bash
   python --version
   ```

   **Output:**

   ![Python Version Output](https://blogby.oss-cn-guangzhou.aliyuncs.com/20250126203416.png)

   c. **Environment Setup**

   Install the required dependencies using pip:

   ```bash
   pip install paramiko requests beautifulsoup4
   ```

3. **Configuration File**

   Fill in your cpolar username/password and the server username (retrieved using `whoami`) in the `config.txt` file:

   ```txt
   # Please fill in the details correctly
   cpolar_username = your_cpolar_username
   cpolar_password = your_cpolar_password
   server_user     = your_server_user
   
   # Custom settings
   ports           = 8888, 6666
   auto_connect    = True
   
   # The following settings can be left as is
   server_password = 
   ssh_key_path    = ~/.ssh/id_rsa_server
   ssh_host_alias  = server
   ```

   **Parameter Descriptions**

   - `cpolar_username` / `cpolar_password`: Your cpolar account credentials.
   - `server_user` / `server_password`: The SSH username and password for the remote server. You can leave the password blank; the script will prompt for input if not provided.
   - `ports`: Ports to be mapped. Defaults to `8888` and `6006`. Use commas (`,`) to separate multiple ports.
   - `auto_connect`: Determines whether the script automatically connects to the server after running. Defaults to `True`. Set to `False` to disable automatic connection.
   - `ssh_key_path`: Path for storing the SSH private key. If the key does not exist, it will be automatically created.
   - `ssh_host_alias`: Alias for the SSH host in the client configuration, simplifying connection commands.

4. **Run the Script**

   Run the following command to execute the script:

   ```bash
   python auto_tunnel.py
   ```

   The script will automatically connect to the server. Press `Ctrl+D` to exit.

</details>

## Side Note

It’s important to note that this script is not an out-of-the-box solution and relies on the following prerequisites:

1. **cpolar** has been properly configured on the server side.
2. The client environment must have **Git**, **Python**, and **SSH** installed.

> Currently, no compatible Shell script has been developed. This script was originally created to address personal needs during earlier challenges and is now being shared for others to reference and use.