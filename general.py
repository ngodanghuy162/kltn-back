from ruamel.yaml import YAML # type: ignore
from ruamel.yaml.comments import CommentedMap # type: ignore
from pydantic import BaseModel # type: ignore
from configparser import ConfigParser
import os
from datetime import datetime
from pathlib import Path
import shutil
import subprocess
import re

from ruamel.yaml import YAML # type: ignore
from ruamel.yaml.comments import CommentedMap # type: ignore
from typing import List
from pathlib import Path
from io import StringIO
from typing import Dict, Any, Optional
yaml = YAML()

class RequestKollaBackup(BaseModel):
    path_inventory: Optional[str] = None
    group: Optional[str] = None
    new_nodes: Optional[List[str]] = None
    list_node_bash: Optional[str] = None
    cron_schedule: Optional[str] = None
    cron_command: Optional[str] = None
    backup_dir_path: Optional[str] = None
    script_file_path: Optional[str] = None
    day_datele: Optional[int] = None
    is_enable: Optional[bool] = True
    
class RequestMySQLDump(BaseModel):
    script_file_path: Optional[str] = None
    MyUSER: Optional[str] = None
    MyPASS: Optional[str] = None
    DEST: Optional[str] = None
    MyHOST: Optional[str] = None
    DAYS: Optional[int] = None
    SSH_HOST: Optional[str] = None
    SSH_PASS: Optional[str] = None
    cron_schedule: Optional[str] = None
    cron_command: Optional[str] = None
    is_enable: Optional[bool] = True

class RequestCrontab(BaseModel):
    is_enable: bool = True
    cron_command: str
    cron_schedule: str

def read_yaml(path):
    """Đọc file YAML"""
    try:
        with open(path, "r") as file:
            return yaml.load(file)  # Load YAML thành Python dict
    except Exception as e:
        return {"error": str(e)}

def write_yaml(path,dict_update):
    try:
        # Đọc dữ liệu YAML hiện tại
        with open(path, "r") as file:
            data = yaml.load(file) or {}  # Tránh lỗi nếu file rỗng
        
        # Cập nhật dữ liệu
        for key, value in dict_update.items():
            data[key] = value

        # Ghi lại file
        with open(path, "w") as file:
            yaml.dump(data, file)

        return {"message": "Cập nhật YAML thành công!"}

    except Exception as e:
        return {"error": str(e)}

def read_bash_file_var_for_bk_dump(path_bash : str) -> Dict[str, str]:
    if not os.path.isfile(path_bash):
        return None
    variables = {
        "MyUSER": "N/A",
        "MyPASS": "N/A",
        "DEST": "N/A",
        "MyHOST": "N/A",
        "DAYS": "N/A",
        "SSH_HOST": "N/A",
        "SSH_PASS": "N/A",
        "SSH_USER": "N/A",
    }
    
    with open(path_bash, "r") as f:
        lines = f.readlines()

    for line in lines:
        line = line.strip()
        if "=" in line and not line.startswith("#"):
            key, value = line.split("=", 1)
            key = key.strip()
            value = value.strip().strip('"').strip("'")
            if key in variables:
                variables[key] = value
    return variables


def update_bash_file_vars(req: RequestMySQLDump):
    with open(req.script_file_path, "r") as f:
        lines = f.readlines()
    updated_lines = []
    req_vars = req.dict()
    for line in lines:
        stripped_line = line.strip()
        if "=" in stripped_line and not stripped_line.startswith("#"):
            key = stripped_line.split("=", 1)[0].strip()
            if key in req_vars and req_vars[key] is not None:
                value = req_vars[key]
                updated_lines.append(f'{key}="{value}"\n')
                continue  # đã update rồi, qua dòng tiếp theo
        updated_lines.append(line)
    with open(req.script_file_path, "w") as f:
        f.writelines(updated_lines)


def update_bash_vars_for_mariabk(path_script_file: str, inventory_path: dict,backup_path: str, day_datele:int = 
                                 None, list_node_bash: str = None):
    with open(path_script_file, "r") as f:
        lines = f.readlines()
    updated_lines = []
    if day_datele is None:
        day_datele = 14
    for line in lines:
        stripped_line = line.strip()
        if "=" in stripped_line and not stripped_line.startswith("#"):
            key = stripped_line.split("=", 1)[0].strip()
            if key == "BACKUP_PATH":
                value = backup_path
                updated_lines.append(f'{key}="{value}"\n')
                continue  
            if key == "INVENTORY_PATH":
                value = inventory_path
                updated_lines.append(f'{key}="{value}"\n')
                continue  
            if key == "DAY_DELETE":
                value = day_datele
                updated_lines.append(f'{key}="{value}"\n')
                continue  
            if key == "LIST_IP":
                value = list_node_bash
                updated_lines.append(f'{key}="{value}"\n')
                continue  
        updated_lines.append(line)
    with open(path_script_file, "w") as f:
        f.writelines(updated_lines)

def update_ansible_inventory(path_inventory: str, group: str, new_nodes: list[str]):
    """
    Cập nhật các node trong một group cụ thể của file Ansible inventory INI.

    Args:
        path_inventory (str): Đường dẫn file inventory
        group (str): Tên group cần sửa (ví dụ: "compute")
        new_nodes (list[str]): Danh sách node mới, mỗi phần tử là một dòng (str)
    """
    if not os.path.isfile(path_inventory):
            print(f"Không tìm thấy file inventory!")
            return
    print("Bat dau goi ham")
    with open(path_inventory, 'r') as f:
        lines = f.readlines()

    result = []
    inside_target_group = False
    group_header = f"[{group}]"
    
    for i, line in enumerate(lines):
        stripped = line.strip()

        if stripped == group_header:
        #if group in stripped:
            # Ghi lại header group
            result.append(line)
            inside_target_group = True
            continue

        if inside_target_group:
            # Nếu tới group mới khác => kết thúc group cần update
            if stripped.startswith("[") and stripped.endswith("]"):
                inside_target_group = False
                # Thêm node mới trước khi group mới bắt đầu
                result += [n + "\n" for n in new_nodes]
                result.append(line)
                continue
            # Bỏ qua các dòng node cũ (node cũ không bắt đầu bằng "[" và không phải comment)
            elif stripped and not stripped.startswith("#"):
                continue
            else:
                # Ghi lại các dòng trắng hoặc comment
                continue

        result.append(line)

    # Nếu file không có group mới sau group target -> thêm node mới cuối cùng
    if inside_target_group:
        result += [n + "\n" for n in new_nodes]
    print(result)
    with open(path_inventory, 'w') as f:
        f.writelines(result)
    print(f"✅ Group [{group}] đã được cập nhật thành công.")
def get_hosts_by_group(inventory_path: str, group_name: str) -> str:
    if not os.path.isfile(inventory_path):
            return f"Không tìm thấy file inventory!"
    with open(inventory_path, "r") as f:
        lines = f.readlines()

    in_group = False
    hosts = []

    for line in lines:
        line = line.strip()

        # Bỏ qua dòng trống hoặc comment
        if not line or line.startswith("#"):
            continue

        # Nếu là dòng group mới
        if line.startswith("[") and line.endswith("]"):
            current_group = line[1:-1].strip()
            in_group = (current_group == group_name)
            continue

        # Nếu đang trong group đúng thì lấy IP (cột đầu tiên)
        if in_group:
            parts = line.split()
            if parts:
                host = parts[0]
                hosts.append(host)

    if not hosts:
        return f"Không tìm thấy host nào."

    host_str = ", ".join(hosts)
    return f"Danh sách các node {group_name} là: {host_str}"
