import logging
import time

logger = logging.getLogger(__name__)

class HostController:

    def __init__(self,executor,target_ip, target_port = 3260):
        self.executor = executor
        self.target_portal = f"{target_ip}:{target_port}"

    def discover_targets(self):
        logger.info(f"Triggering fabric discovery sweep out to portal: {self.target_portal}")
        cmd = f"iscsiadm -m discovery -t sendtargets -p {self.target_portal}"
        exit_code, stdout, stderr = self.executor.execute(cmd, sudo=True)
        if exit_code != 0:
            raise RuntimeError(f"Fabric routine discovery failed: {stderr.strip()}")
        return stdout

    def login_target(self, target_iqn):
        logger.info(f"Executing storage path fabric login handshake to: {target_iqn}")
        cmd = f"iscsiadm -m node -T {target_iqn} -p {self.target_portal} --login"
        exit_code, stdout, stderr = self.executor.execute(cmd, sudo=True)

        if exit_code == 15 or "already present" in stderr.lower():
            logger.info("Host connection path already active. Skipping redundant login handshake")
            return True
        if exit_code != 0:
            raise RuntimeError(f"Fabric login connection negotiation filed: {stderr.strip()}")
        return True

    def logout_target(self, target_iqn):
        logger.info(f"Terminating active fabric connection session for: {target_iqn}")
        cmd = f"iscsiadm -m node -T {target_iqn} -p {self.target_portal} --logout"
        exit_code, stdout, stderr = self.executor.execute(cmd, sudo=True)
        return exit_code == 0

    def slice_partition(self, block_device):
        logger.info(f"Automating non-interactive partitionlayout on: {block_device}")
        sfdisk_script = "echo ',' | sfdisk"
        cmd = f"{sfdisk_script} {block_device}"

        exit_code, stdout, stderr = self.executor.execute(cmd, sudo=True)

        if exit_code != 0:
            raise RuntimeError(f"sfdisk partition initialization failed: {stderr.strip()}")
        
        logger.info(f"Partition block successfully mapped onto: {block_device}1")

        return  True

    def format_filesystem(self, partition_device):
        logger.info(f"Instantiating enterprice Ext4 file management system on: {partition_device}")
        exit_code, stdout, stderr = self.executor.execute(f"mkfs.ext4 -F {partition_device}", sudo= True)
        if exit_code !=0:
            raise RuntimeError(f"Filesystem initialization failed: {stderr.strip()}")
        return True

    def mount_volume(self, partition_device, mount_point):
        logger.info(f"Linking mount directory path tree: {partition_device} --> {mount_point}")
        self.executor.execute(f"mkdir -p {mount_point}", sudo=True)
        _, stdout, _ = self.executor.execute(f"mount | grep {mount_point}", sudo=False)
        if partition_device in stdout:
            logger.info(f"Mount destination path {mount_point} is already active.")
            return True

        exit_code, stdout, stderr = self.executor.execute(f"mount {partition_device} {mount_point}")
        if exit_code != 0:
            raise RuntimeError(f"Mount execution hook failed: {stderr.strip()}")
        return True

    def lazy_unmount(self, mount_point):
        logger.info(f"Forcefully unmounting the directory path tree via lazy unmount: {mount_point}")
        exit_code, stdout, stderr = self.executor.execute(f"umount -l {mount_point}", sudo=True)
        return exit_code == 0

    
