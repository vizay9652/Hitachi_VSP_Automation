import logging

logger = logging.getLogger(__name__)

def test_iscsi_session_active(host_executor, config):
    """
    [Host] Test case 1: Verify that the host initiator has an active 
    and established ISCSI session with target storage array
    """

    target_iqn = config["storage_fabric"]["target_iqn"]
    logger.info(f"[Host] Verifying active iSCSI session for target: {target_iqn}")

    # Query active session via iscsiadm
    exit_code, stdout, stderr = host_executor.execute("iscsiadm -m session", sudo=True)

    assert exit_code == 0, f"No active iSCSI session found: {stderr.strip()}"
    assert target_iqn in stdout, f"Target IQN {target_iqn} not found in active session list: {stdout}"

def test_block_device_accessibility(host_executor, config):
    """
    [Host] Test case 2: Verify that block device and its partition
    are correctly exposed to the host operating system kernel
    """

    block_device = config["storage_fabric"]["block_device"]
    partition_device = f"{block_device}1"

    logger.info(f"[HOST] checking kernel visiblity for partition: {partition_device}")

    # check if partition file node exists in /sys/block/ or via lsblk
    exit_code, stdout, stderr = host_executor.execute(f"lsblk {partition_device}", sudo= True)

    assert exit_code == 0, f"Block devicec partition {partition_device} is not accessible: {stderr.strip()}"
    assert "part" in stdout or "disk" in stdout, f"Unexpected block device output structure: {stdout}"
    logger.info(f"[Host] SUCCESS: Block device {partition_device} is visible to the kernel")


def test_filesystem_mount_and_rewrite(host_executor, config):
    """
    [Host] Test Case 3: Verify that the ext4 filesystem is successfully mounted
    at the designated path and allows read/write transactions.
    """

    mount_point = config["storage_fabric"]["mount_point"]
    logger.info(f"[Host] Verifying filesystem mount integrity at: {mount_point}")

    # 1. Verify mount status via mount command
    _, stdout, _ = host_executor.execute(f"mount | grep {mount_point}", sudo=False)
    assert mount_point in stdout, f"Mount point {mount_point} is not actively mounted"

    # 2. Execute end-to-end data transaction test (Read/Write verification)
    test_file = f"{mount_point}/qa_baseline_test.txt"
    test_content = "Storage QA Automation Baseline Verification Passed"

    logger.info(f"[Host] Writing test payload to storage fabric: {test_file}")
    write_cmd = f"echo {test_content} | sudo tee {test_file}"
    write_code, _, write_err = host_executor.execute(write_cmd, sudo=False)
    assert write_code == 0, f"Failed to write test file to mount point: {write_err.strip()}"

    # 3. Read back and verify the content
    logger.info(f"[Host] Reading back payload from storage fabric: {test_file}")
    read_code, read_stdout, read_err = host_executor.execute(f"cat {test_file}", sudo=True)
    assert read_code == 0, f"Failed to read test file from mount point: {read_err.strip()}"
    assert test_content in read_stdout, f"Data integrity mismatch! Read content: {read_stdout.strip()}"


    # 4. Clean up the test file
    host_executor.execute(f"rm -f {test_file}", sudo=True)
    logger.info("[Host] SUCCESS: Filesystem read/write data transaction verified successfully.")