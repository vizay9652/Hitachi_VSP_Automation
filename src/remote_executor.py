import paramiko
import logging

logger = logging.getLogger(__name__)

class RemoteExecutor:
    """
    Out-of-Band (OOB) SSH Execution Engine.
    Orchestrates command delivery to the remote storage sandbox environment
    """

    def __init__(self, host, username, password=None, key_filename=None, timeout=10):
        self.host = host
        self.username = username
        self.password = password
        self.key_filename = key_filename
        self.timeout = timeout
        self._client = None

    def connect(self):
        """Establishes a secure SSH connection channel to remote node."""
        if self._client is None:
            logger.info(f"Establishing out-of-band fabric link to {self.host}...")
            self._client = paramiko.SSHClient()
            self._client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            self._client.connect(
                hostname= self.host,
                username=self.username,
                password=self.password,
                key_filename=self.key_filename,
                timeout=self.timeout
            )
            logger.info(f"Fabric tunnel successfully secured for {self.username}@{self.host}")

    def execute(self, command, sudo=False, sudo_password=None):
        """
        Executes a targeted shell command out-of-band.
        Returns a tuple containing: (exit_status, stdout_string, stderr_string)
        """
        self.connect()

        # Format for privileged execution context if requested
        if sudo:
            if not sudo_password:
                sudo_password = self.password
            command = f"echo '{sudo_password}' | sudo -S -k {command}"
            
        logger.debug(f"Dispatching remote execution stream: {command}")
        
        # Run command asynchronously over the secure network channel
        stdin, stdout, stderr = self._client.exec_command(command, timeout=self.timeout)
        
        # Read byte streams and decode them cleanly to text strings
        stdout_str = stdout.read().decode('utf-8', errors='ignore')
        stderr_str = stderr.read().decode('utf-8', errors='ignore')
        exit_status = stdout.channel.recv_exit_status()
        
        # Clean up sudo password remnants from automated test logging frames
        if sudo and sudo_password:
            command = command.replace(sudo_password, "********")
            
        logger.info(f"Command executed. Status: [{exit_status}]. Command: {command}")
        
        if exit_status != 0:
            logger.warning(f"Remote command execution returned non-zero status. Error: {stderr_str.strip()}")
            
        return exit_status, stdout_str, stderr_str


    def close(self):
        """Gracefully tearsdown the network connection tunnel channel."""
        if self._client:
            logger.info(f"Closing out-of-band fabric link connection to {self.host}...")
            self._client.close()
            self._client = None
            logger.info("Fabric tunnel channel disconnected safely.")
