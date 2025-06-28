"""
Network configuration for distributed deployment
"""

# Network topology configuration
NETWORK_CONFIG = {
    # Single machine (localhost) configuration
    "local": {
        "sender": {
            "host": "localhost",
            "port": 8000
        },
        "server1": {
            "host": "localhost", 
            "port": 8001,
            "upstream_host": "localhost",
            "upstream_port": 8002
        },
        "server2": {
            "host": "localhost",
            "port": 8002, 
            "upstream_host": "localhost",
            "upstream_port": 8003
        },
        "receiver": {
            "host": "localhost",
            "port": 8003
        }
    },

    # Four-machine distributed configuration
    "distributed_4machines": {
        "sender": {
            "host": "192.168.1.10",
            "port": 8000,
            "server1_host": "192.168.1.11",
            "server1_port": 8000
        },
        "server1": {
            "host": "192.168.1.11",
            "port": 8000,
            "upstream_host": "192.168.1.12",
            "upstream_port": 8000
        },
        "server2": {
            "host": "192.168.1.12",
            "port": 8000,
            "upstream_host": "192.168.1.13",
            "upstream_port": 8000
        },
        "receiver": {
            "host": "192.168.1.13",
            "port": 8000
        }
    },
}

# Protocol configuration
PROTOCOL_CONFIG = {
    "handshake_timeout": 30,
    "transfer_timeout": 300,
    "max_file_size": 100 * 1024 * 1024,
    "buffer_size": 4096,
    "retry_attempts": 3,
    "retry_delay": 5
}

# Security configuration  
SECURITY_CONFIG = {
    "rsa_key_size": 2048,
    "des_key_size": 64,
    "hash_algorithm": "SHA-512",
    "signature_algorithm": "RSA-SHA512"
}

def get_config(deployment_type="local"):
    """Get network configuration for specified deployment type"""
    return NETWORK_CONFIG.get(deployment_type, NETWORK_CONFIG["local"])

def get_machine_config(deployment_type, machine_name):
    """Get configuration for specific machine"""
    config = get_config(deployment_type)
    return config.get(machine_name, {})

def get_role_config(deployment_type, machine_name, role):
    """Get configuration for specific role on specific machine"""
    machine_config = get_machine_config(deployment_type, machine_name)
    return machine_config.get(role, {})

def validate_network_config(deployment_type):
    """Validate network configuration"""
    config = get_config(deployment_type)
    
    # Check if all required machines are defined
    required_machines = ["machine_a", "machine_b", "machine_c"] if deployment_type == "distributed" else []
    
    for machine in required_machines:
        if machine not in config:
            raise ValueError(f"Missing configuration for {machine}")
    
    return True 