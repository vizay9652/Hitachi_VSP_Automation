import logging

logger = logging.getLogger(__name__)

class TargetController:

    def __init__(self,executor, target_iqn, portal_ip, portal_port=3260):
        self.executor = executor
        self.target_iqn = target_iqn
        self.portal_ip = portal_ip
        self.portal_port = portal_port

    def run_targetcli_cmd(self, command_path, action):

        full_cmd = f"targetcli {command_path} {action}"
        exit_code, stdout, stderr = self.executor.execute(full_cmd, sudo=True)

        if exit_code != 0:
            raise RuntimeError(f"targetcli failed on {command_path} {action}")
        return stdout

    def setup_backstore(self, volume_name, dev_path):

        logger.info(f"Carving out target lock array storage backstore: {volume_name} -> {dev_path}")
        path = "/backstores/block"
        action = f"create name={volume_name} dev={dev_path}"
        return self.run_targetcli_cmd(path, action)    

    def initialize_target_portal_group(self):
        logger.info(f"instantiating target fabric identity: {self.target_iqn}")

        self.run_targetcli_cmd("/iscsi",f"create {self.target_iqn}")

        portal_path = f"/iscsi/{self.target_iqn}/tpg1/portals"
        logger.info("Clearing wildcard portal listeners to evade configFs collisions")
        try:
            self.run_targetcli_cmd(portal_path, f"delete 0.0.0.0 {self.portal_port}")
        except Exception:
            # If the default wildcard doesn't exist, ignore and skip ahead
            pass

        logger.info(f"Binding target interface gateway portal to listener socket: {self.portal_ip}:{self.portal_port}")
        return self.run_targetcli_cmd(portal_path, f"create {self.portal_ip} {self.portal_port}")

    def map_lun(self, volume_name):
        logger.info(f"Mapping block storage slice to fabric gateway pool layout: LUN 0")
        lun_path = f"/iscsi/{self.target_iqn}/tpg1/luns"
        action = f"create /backstores/block/{volume_name}"
        return self.run_targetcli_cmd(lun_path, action)

    def whitelist_host_acl(self, host_initiator_iqn):
        logger.info(f"Whitelisting host initiator passport clearance: {host_initiator_iqn}")
        acl_path = f"/iscsi/{self.target_iqn}/tpg1/acls"
        return self.run_targetcli_cmd(acl_path, f"create {host_initiator_iqn}")

    def persist_configuration(self):
        logger.info("Writing software-defined target structural changes to persistent JSON memory...")
        return self.run_targetcli_cmd("/","saveconfig")

