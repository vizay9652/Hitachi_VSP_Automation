import os 
import yaml 
import pytest
import logging
from src.remote_executor import RemoteExecutor
from src.host_controller import HostController
from src.target_controller import TargetController

logger = logging.getLogger(__name__)

@pytest.fixture(scope="session")
def config():
    config_path = os.path.join(os.path.dirname(__file__), "../config/environment.yaml")
    with open(config_path,"r") as f:
        return yaml.safe_load(f)


@pytest.fixture(scope="session")
def host_executor(config):
    hvm = config["storage_host_vm"]
    executor = RemoteExecutor(
        host = hvm["host"],
        username = hvm["username"],
        password = hvm["password"],
        timeout = hvm["timeout"]
    )
    executor.connect()
    yield executor
    executor.close()

@pytest.fixture(scope="session")
def target_executor(config):
    tvm = config["storage_target_vm"]
    executor = RemoteExecutor(
        host=tvm["host"],
        username=tvm["username"],
        password=tvm["password"],
        timeout=tvm["timeout"]
    )
    executor.connect()
    yield executor
    executor.close()

@pytest.fixture(scope="session", autouse=True)
def storage_infrastructure_fixture(config, target_executor, host_executor):
    """
    [Target & Host] Session fixture handling end-to-end infracture setup
    and teardown automation for the storage fabric
    """
    sf = config["storage_fabric"]
    tvm = config["storage_target_vm"]

    target_ctrl = TargetController(
        executor=target_executor,
        target_iqn=sf["target_iqn"],
        portal_ip=tvm["host"],
        portal_port=sf["portal_port"]
    )

    host_ctrl = HostController(
        executor=host_executor,
        target_ip = tvm["host"],
        target_port=sf["portal_port"]
    )

    logger.info("--- INFRACTURE SETUP: Provisioning Storage Across Dual Nodes ---")

    # 1. Target side setup
    try:
        target_ctrl.setup_backstore("vsp_vol1", "/dev/loop20")
    except Exception:
        logger.info(f"Backstore vsp_vol1 already exists on target")

    target_ctrl.initialize_target_portal_group()

    try:
        target_ctrl.map_lun("vsp_vol1")
    except Exception:
        logger.info("LUN 0 mapping already active on target")

    target_ctrl.whitelist_host_acl(sf["initiator_iqn"])
    target_ctrl.persist_configuration()

    # 2. Host side setup
    host_ctrl.discover_targets()
    host_ctrl.login_target(sf["target_iqn"])

    try:
        host_ctrl.slice_partition(sf["block_device"])
    except Exception:
        logger.info("Partition table has already been inititalized on host block device")

    partition_device = f"{sf["block_device"]}1"

    try:
        host_ctrl.format_filesystem(partition_device)
    except Exception:
        logger.info("Filesystem already been formatted on host.")

    host_ctrl.mount_volume(partition_device,sf["mount_point"])

    logger.info("--- DUAL_NODE INFRASTRUCTURE SETUP COMPLETE ---")

    yield # Tests executed here

    logger.info("--- INFRASTRUCTURE TEARDOWN: Cleaning Up Dual Nodes ---")
    host_ctrl.lazy_unmount(sf["mount_point"])
    host_ctrl.logout_target(sf["target_iqn"])
    logger.info("--- TEARDOWN COMPLETE ---")
    

