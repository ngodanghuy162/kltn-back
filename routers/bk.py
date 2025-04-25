#####api 1: neu dung path default khong co, yeu 
# cau nguoi dung nhap path da cai dat va thuc hien api 1 lay thong tin
#####

###api 2:
# truyen dang key value va ghi vao cac file ini, file ini o day dua tren file mau, neu co roi thi thoi, chua co thi sao?
###
from fastapi import APIRouter, Query # type: ignore
from configparser import ConfigParser
import os
from datetime import datetime
from pathlib import Path
import shutil
import subprocess
import re
from ruamel.yaml import YAML # type: ignore
from ruamel.yaml.comments import CommentedMap # type: ignore
from pydantic import BaseModel # type: ignore
from typing import List
from pathlib import Path
from io import StringIO
from typing import Dict, Any
from general import write_yaml, read_yaml, update_ansible_inventory, InventoryUpdateRequest
bk_router = APIRouter()

yaml = YAML()
# class InventoryUpdateRequest(BaseModel):
#     path_inventory: str
#     group: str
#     new_nodes: List[str]
#     cron_schedule: str
#     cron_command: str
#     backup_path: str
#     varfile_path: str
    
# api fetch dau tien:nhiem vu: lay lich backup hang ngay co chua, lay ket qua folder xem backup
# lay backup o node nao?
#api 2: cai dat backup tren cac node



#parse conline
def parse_cron_line(line: str):
    parts = line.strip().split()
    if len(parts) < 6:
        return None  # Không đủ phần để là dòng cron hợp lệ

    minute = parts[0]
    hour = parts[1]
    day = parts[2]
    month = parts[3]
    day_week = parts[4]
    command = " ".join(parts[5:])

    def format_time(h, m):
        return f"{int(h):02d}:{int(m):02d}"

    # Lịch hàng ngày
    if day == "*" and day_week == "*":
        return f"Lịch backup chạy hàng ngày lúc {format_time(hour, minute)}"

    # Lịch hàng tuần
    if day == "*" and day_week != "*":
        weekdays = {
            "0": "Chủ nhật", "1": "Thứ hai", "2": "Thứ ba", "3": "Thứ tư",
            "4": "Thứ năm", "5": "Thứ sáu", "6": "Thứ bảy"
        }
        weekday = weekdays.get(day_week, f"thứ {day_week}")
        return f"Lịch backup chạy hàng tuần vào {weekday} lúc {format_time(hour, minute)}"

    # Lịch theo ngày trong tháng
    if day != "*" and day_week == "*":
        return f"Lịch backup chạy moi {day[2]} ngày lúc {format_time(hour, minute)}"

    # Trường hợp khác (phức tạp hơn)
    return str

#truyen path va group
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
        return f"Không tìm thấy group '{group_name}' hoặc group không có host nào."

    host_str = ", ".join(hosts)
    return f"Danh sách các node {group_name} là: {host_str}"

#lay ngay backup cuoi
def get_latest_backup(folder_path: str):
    BACKUP_PATTERN = re.compile(r"backup_(\d{2})_(\d{2})_(\d{4}).*")
    folder = Path(folder_path)
    if not os.path.exists(folder_path) or not os.path.isdir(folder_path):
        return "os dang khong thay gi"
    if not folder.exists():
        return f"Thư mục {folder_path} không tồn tại"
    if not folder.is_dir():
        return f"{folder_path} không phải là một thư mục"

    backups = []

    for file in folder.iterdir():
        match = BACKUP_PATTERN.fullmatch(file.name)
        print(match)
        if match:
            day, month, year = map(int, match.groups())
            backup_date = datetime(year, month, day)
            backups.append((backup_date))

    if not backups:
        return "No file backup in folder"

    # Sắp xếp theo ngày giảm dần
    latest_date = max(backups)
    return f"Ngày backup cuối cùng là ngày {latest_date.strftime('%d/%m/%Y')}"
#lay thong tin node backup hien tai, truyen vao inventory path va backup folder path
@bk_router.get("/bk/info", response_model=dict)
async def get_backup_info(
    backup_dir: str = Query("/Users/ngodanghuy/KLTN/test", description="Đường dẫn tới thư mục backup"),
    inventory_dir: str = Query("/Users/ngodanghuy/KLTN/back/kltn-back/inventory", description="Đường dẫn tới thư mục test")
):
    try:
        # Lấy các node backup
        node_backup = get_hosts_by_group(inventory_dir, "backup")
        
        # Lấy thông tin backup gần nhất
        last_backup = get_latest_backup(backup_dir)
        
        # Lấy crontab của user hiện tại
        crontab = subprocess.run(["crontab", "-l"], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)

        if crontab.returncode != 0:
            return {"error": "Không có crontab hoặc lỗi khi đọc"}

        lines = crontab.stdout.strip().split("\n")
        parsed = []

        for line in lines:
            # Bỏ qua dòng trống hoặc comment
            if not line.strip() or line.strip().startswith("#"):
                continue
            if "backup" not in line.lower():
                continue
            
            # Parse crontab line
            parsed.append(parse_cron_line(line))
        
        return {
            "crontab": parsed[0],
            "node_Backup": node_backup,
            "last_Backup": last_backup
        }
    except Exception as e:
        return {"error": str(e)}
    
#truyen file inventory, group, danh sach node.
# def update_ansible_inventory(path_inventory: str, group: str, new_nodes: list[str]):
#     """
#     Cập nhật các node trong một group cụ thể của file Ansible inventory INI.

#     Args:
#         path_inventory (str): Đường dẫn file inventory
#         group (str): Tên group cần sửa (ví dụ: "compute")
#         new_nodes (list[str]): Danh sách node mới, mỗi phần tử là một dòng (str)
#     """
#     with open(path_inventory, 'r') as f:
#         lines = f.readlines()

#     result = []
#     inside_target_group = False
#     group_header = f"[{group}]"
    
#     for i, line in enumerate(lines):
#         stripped = line.strip()

#         if stripped == group_header:
#             # Ghi lại header group
#             result.append(line)
#             inside_target_group = True
#             continue

#         if inside_target_group:
#             # Nếu tới group mới khác => kết thúc group cần update
#             if stripped.startswith("[") and stripped.endswith("]"):
#                 inside_target_group = False
#                 # Thêm node mới trước khi group mới bắt đầu
#                 result += [n + "\n" for n in new_nodes]
#                 result.append(line)
#                 continue
#             # Bỏ qua các dòng node cũ (node cũ không bắt đầu bằng "[" và không phải comment)
#             elif stripped and not stripped.startswith("#"):
#                 continue
#             else:
#                 # Ghi lại các dòng trắng hoặc comment
#                 continue

#         result.append(line)

#     # Nếu file không có group mới sau group target -> thêm node mới cuối cùng
#     if inside_target_group:
#         result += [n + "\n" for n in new_nodes]

#     with open(path_inventory, 'w') as f:
#         f.writelines(result)

#     # print(f"✅ Group [{group}] đã được cập nhật thành công.")

def update_crontab(cron_schedule: str, cron_command: str):
    try:
        # Lấy danh sách crontab hiện tại
        result = subprocess.run(
            ["crontab", "-l"], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True
        )

        # Lấy toàn bộ crontab hiện tại
        current_cron = result.stdout

        # Kiểm tra nếu đã có dòng backup
        backup_line = f"backup"
        if backup_line in current_cron:
            # Nếu đã có dòng backup, thay thế nó
            new_cron = current_cron.replace(
                f"backup", f"{cron_schedule} {cron_command}"
            )
  
        else:
            # Nếu chưa có, thêm dòng backup mới
            new_cron = current_cron + f"\n{cron_schedule} {cron_command}\n"
            print("Đã thêm dòng backup mới.")

        # Cập nhật lại crontab
        subprocess.run(["crontab", "-"], input=new_cron, text=True)


    except Exception as e:
        print(f"Đã có lỗi trong quá trình cập nhật crontab: {e}")

@bk_router.post("/bk/update")
async def update_inventory_and_cron(data: InventoryUpdateRequest):
    try:
        # Gọi hàm cập nhật inventory
        update_ansible_inventory(
            path_inventory=data.path_inventory,
            group=data.group,
            new_nodes=data.new_nodes
        )
        # Gọi hàm cập nhật crontab
        update_crontab(
            cron_schedule=data.cron_schedule,
            cron_command=data.cron_command
        )
        dict_tmp = { "backup_path" : data.backup_path}
        print(data.varfile_path)
        print(dict_tmp)
        print(f"✅ Truoc khi goi write yaml")
        write_yaml(path=data.varfile_path, dict_update=dict_tmp)
        print(f"✅✅ Sau khi goi ham write yaml")
        return {"status": "success", "message": "Inventory và Crontab đã được cập nhật."}

    except Exception as e:
        return {"status": "error", "message": str(e)}