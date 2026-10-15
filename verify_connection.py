import os 
import yaml
from src.remote_executor import RemoteExecutor

def main():
    # 1. locate and read the environment configuration file
    config_path = os.path.join("config","environment.yaml")
    print(f"Reading confiuration parameters from: {config_path}")

    with open(config_path,"r") as f:
        config = yaml.safe_load(f)

    vm_params = config["sandbox_vm"]

    # 2. Initialize the out-of-band execution engine
    executor = RemoteExecutor(
        host = vm_params["host"],
        username= vm_params["username"],
        password = vm_params["password"],
        timeout= vm_params["timeout"]
    )

    try:
        # 3. Test out-of-band communication channel connectivity
        print("\n--- Phase 1: Testing connection handshake ---")
        executor.connect()

        #  4. Execute a live kernel log sweep command on remote node
        print("\n--- Phase 2: Pulling Live remote kernel logs ---")
        cmd = "dmesg | grep -E 'scsi|iscsi' | tail -n 5"

        #  Run command as atandard user since we are just checking logs here
        exit_code , stdout, stderr = executor.execute(cmd, sudo=True)

        print(f"\nExecution Return Code: [{exit_code}]")
        print("\nCaptured Remote Output:")
        if stdout.strip():
            print(stdout)
        else:
            print("[System log channel returned empty - no fabric flags caught]")

        if stderr.strip():
            print(f"captured error stream:\n{stderr}")

    except Exception as e:
        print(f"\n[CRITICAL ERROR] Fabric connection pipeline initialization failed: {e}")
        print("Triage Tip: Double-check your Tailscale status and login credentials inside environment.yaml")
                
    finally:
        # 5. Cleanup open network sockets cleanly
        executor.close()

if __name__ == "__main__":
    main()
