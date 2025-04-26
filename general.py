
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
from typing import Dict, Any
yaml = YAML()

class InventoryUpdateRequest(BaseModel):
    path_inventory: str
    group: str
    new_nodes: List[str]
    cron_schedule: str
    cron_command: str
    backup_path: str
    varfile_path: str

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