## sua cac bien var, xong chay cau lenh deploy :>
# la chay file bash.
import asyncio
from configparser import ConfigParser
from datetime import datetime
from pathlib import Path
import re
from ruamel.yaml import YAML # type: ignore
from ruamel.yaml.comments import CommentedMap # type: ignore
from pathlib import Path
from typing import List, Set
from fastapi import FastAPI, HTTPException, Query, APIRouter, Body # type: ignore
from fastapi.responses import StreamingResponse # type: ignore
import os
import subprocess
from pydantic import BaseModel, Field, ValidationError # type: ignore
from typing import Dict, List
from io import StringIO
from typing import Dict, Any, Optional

from general import write_yaml, read_yaml, update_ansible_inventory
deploy_router = APIRouter()

yaml = YAML()

#api trien khai 1 node: Sua inventory, chay deploy
#3 node: sua inventory, chay deploy
##3 node kem haproxy: Sua inventory 2 group, sua ip vip, deploy :>

PROJECT_DIR = "/root/git/kolla-ansible"
VENV_ACTIVATE = "source /root/virtualenv/bin/activate"
INVENTORY_PATH = "/root/inventory/multinode"

class RequestBody(BaseModel):
    type: int
    path_inventory: str
    new_nodes: List[str] 
    kolla_internal_vip_address: Optional[str] = None
async def run_command_async(command: str):
    full_cmd = f"cd {PROJECT_DIR} && {VENV_ACTIVATE} && {command}"
    process = await asyncio.create_subprocess_shell(
        full_cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.STDOUT,
        executable="/bin/bash"  # Rất quan trọng để hỗ trợ `source`
    )
    while True:
        line = await process.stdout.readline()
        if not line:
            break
        yield line.decode("utf-8")
    await process.wait()
    yield f"\n✅ Done: {command} (exit {process.returncode})\n"

async def deploy_stream(type: int):
    if type == 1:
        cmd_destroy= f"ansible -i {INVENTORY_PATH} -m shell -a 'docker rm -f haproxy keepalived' all"
        cmd_rm_grastate = f"ansible -i {INVENTORY_PATH} -m shell -a 'rm /var/lib/docker/volumes/mariadb/_data/grastate.dat' all"
        run_command_async(cmd_destroy)
        run_command_async(cmd_rm_grastate)
        yield "\n🚀 Destroy Haproxy and Keepalived\n"
    yield "\n🚀 Deploying MariaDB\n"
    cmd_deploy = f"./tools/kolla-ansible -i {INVENTORY_PATH} reconfigure -t haproxy,keepalived,loadbalancer"
    async for log_line in run_command_async(cmd_deploy):
        yield log_line
    yield "✅ Finished Haproxy reconfigure \n"

    yield "\n🚀 Deploying second command\n"
    cmd_deploy2 = f"./tools/kolla-ansible -i {INVENTORY_PATH} deploy -t mariadb"  # Thay đổi lệnh thứ hai ở đây
    async for log_line in run_command_async(cmd_deploy2):
        yield log_line
    yield "✅ Finished Mariadb deploy\n"


@deploy_router.post("/deploy/mariadb")
async def deploy(vars: RequestBody):
    if vars.type == 1:
        update_ansible_inventory(vars.path_inventory,"mariadb",vars.new_nodes)
        my_dict = {
            "enable_haproxy": "no",
            "enable_loadbalancer": "no",
        }
        write_yaml(path="/etc/kolla/globals.yml",dict_update=my_dict)
    elif vars.type == 2:
        update_ansible_inventory(vars.path_inventory,"mariadb", new_nodes=vars.new_nodes)
    elif vars.type == 3:
        update_ansible_inventory(vars.path_inventory,"mariadb", new_nodes=vars.new_nodes)
        # update_ansible_inventory(vars.path_inventory,"loadbalancer:children", new_nodes=["mariadb"])
        # update_ansible_inventory(vars.path_inventory,"hacluster:children", new_nodes=["mariadb"])
        my_dict = {
            "enable_haproxy": "yes",
            "enable_loadbalancer": "yes",
            "kolla_internal_vip_address": str(vars.kolla_internal_vip_address)
        }
        write_yaml(path="/etc/kolla/globals.yml",dict_update=my_dict)
    return StreamingResponse(deploy_stream(vars.type), media_type="text/plain")


    