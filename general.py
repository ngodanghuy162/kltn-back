
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
    cron_schedule: Optional[str] = None
    cron_command: Optional[str] = None
    backup_path: Optional[str] = None
    varfile_path: Optional[str] = None

class RequestMySQLDump(BaseModel):
    script_file_path: Optional[str] = None
    user_dtb_backup: Optional[str] = None
    password_dtb_backup: Optional[str] = None
    backup_folder_path: Optional[str] = None
    ip_host_dtb: Optional[str] = None
    days_delele: Optional[int] = None
    ssh_host: Optional[str] = None
    ssh_pass: Optional[str] = None

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

def read_bash_file_var(path_bash : str) -> Dict[str, str]:
    variables = {
        "user_dtb_backup": "N/A",
        "password_dtb_backup": "N/A",
        "backup_folder_path": "N/A",
        "ip_host_dtb": "N/A",
        "days_delele": "N/A",
        "ssh_host": "N/A",
        "ssh_pass": "N/A",
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

# def read_bash_file_var(req: RequestMySQLDump):
#     with open(req.script_file_path, "r") as f:
#         lines = f.readlines()

#     updated_lines = []
#     for line in lines:
#         replaced = False
#         for key, value in req.dict().items():
#             if value is not None and line.strip().startswith(f"{key}="):
#                 updated_lines.append(f'{key}="{value}"\n')
#                 replaced = True
#                 break
#         if not replaced:
#             updated_lines.append(line)
    
#     with open(req.script_file_path, "w") as f:
#         f.writelines(updated_lines)

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

def update_ansible_inventory(path_inventory: str, group: str, new_nodes: list[str]):
    """
    Cập nhật các node trong một group cụ thể của file Ansible inventory INI.

    Args:
        path_inventory (str): Đường dẫn file inventory
        group (str): Tên group cần sửa (ví dụ: "compute")
        new_nodes (list[str]): Danh sách node mới, mỗi phần tử là một dòng (str)
    """
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

    with open(path_inventory, 'w') as f:
        f.writelines(result)

    # print(f"✅ Group [{group}] đã được cập nhật thành công.")
def get_hosts_by_group(inventory_path: str, group_name: str) -> str:
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
