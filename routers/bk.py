from fastapi import APIRouter, Query , HTTPException# type: ignore
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
from fastapi.responses import JSONResponse # type: ignore
from general import write_yaml, read_yaml, update_ansible_inventory, get_hosts_by_group, update_bash_file_vars, read_bash_file_var_for_bk_dump, update_bash_vars_for_mariabk ,RequestKollaBackup, RequestMySQLDump
bk_router = APIRouter()

yaml = YAML()

#parse conline
def parse_crontab_to_str(keyword: str = "backup"):
    try:
        crontab = subprocess.run(["crontab", "-l"], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        if crontab.returncode != 0:
            return "Hiện tại chưa có lịch crontab"
        lines = crontab.stdout.strip().split("\n")
        line_to_parsed = ""

        for line in lines:
            # Bỏ qua dòng trống hoặc comment
            if not line.strip() or line.strip().startswith("#"):
                continue
            if keyword not in line.lower():
                continue
            # Parse crontab line
            line_to_parsed = line
        parts = line_to_parsed.strip().split()
        if len(parts) < 6:
            if keyword == "auto":
                return f"Chưa được cấu hình tự động chạy..."
            return "Lịch crontab không hợp lệ"  # Không đủ phần để là dòng cron hợp lệ

        minute = parts[0]
        hour = parts[1]
        day = parts[2]
        month = parts[3]
        day_week = parts[4]
        command = " ".join(parts[5:])

        def format_time(h, m):
            return f"{int(h):02d}:{int(m):02d}"

        # Xử lý trường hợp chạy mỗi X phút
        if minute.startswith("*/"):
            minutes = minute[2:]
            if keyword == "auto":
                return minutes
            return f"Lịch {keyword} chạy mỗi {minutes} phút"
        # Lịch hàng ngày
        if day == "*" and day_week == "*":
            return f"Lịch {keyword} chạy hàng ngày lúc {format_time(hour, minute)}"

        # Lịch hàng tuần
        if day == "*" and day_week != "*":
            weekdays = {
                "0": "Chủ nhật", "1": "Thứ hai", "2": "Thứ ba", "3": "Thứ tư",
                "4": "Thứ năm", "5": "Thứ sáu", "6": "Thứ bảy"
            }
            weekday = weekdays.get(day_week, f"thứ {day_week}")
            return f"Lịch {keyword} chạy hàng tuần vào {weekday} lúc {format_time(hour, minute)}"

        # Lịch theo ngày trong tháng
        if day != "*" and day_week == "*":
            return f"Lịch {keyword} chạy moi {day[2]} ngày lúc {format_time(hour, minute)}"

        # Trường hợp khác (phức tạp hơn)
        return line_to_parsed
    except Exception as e:
        return {"error": str(e)}

#truyen path va group
#lay ngay backup cuoi
def get_latest_backup(folder_path: str) -> str:
    # BACKUP_PATTERN = re.compile(r"mysqlbackup-(\d{2})-(\d{2})-(\d{4})*")  
    BACKUP_PATTERN = re.compile(r"mysqlbackup-(\d{2})-(\d{2})-(\d{4}).*")
    folder = Path(folder_path)
    if not os.path.exists(folder_path) or not os.path.isdir(folder_path):
        return "Không tìm thấy bản backup nào"
    if not folder.exists():
        return f"Thư mục {folder_path} không tồn tại"
    if not folder.is_dir():
        return f"{folder_path} không phải là một thư mục"

    backups = []

    for file in folder.iterdir():
        print("--File la:" + str(file.name))
        match = BACKUP_PATTERN.fullmatch(file.name)
        print("Match::" +str(match))
        if match:
            day, month, year = map(int, match.groups())
            backup_date = datetime(year, month, day)
            backups.append((backup_date))

    if not backups:
        return "Chưa có bản backup nào"
    # Sắp xếp theo ngày giảm dần
    latest_date = max(backups)
    return f"Ngày backup cuối cùng là ngày {latest_date.strftime('%d/%m/%Y')}"

@bk_router.get("/bk/info_kolla", response_model=dict)
async def get_backup_kolla_info(
    backup_dir: str = Query("/var/lib/docker/volumes/mariadb_backup/_data/", description="Đường dẫn tới thư mục backup"),
    inventory_dir: str = Query("/root/inventory/inventory_backup", description="Đường dẫn tới thư mục inventory backup")
):
    try:    
        # Lấy các node backup
        # Lấy crontab của user hiện tại
        node_backup = get_hosts_by_group(inventory_dir, "backup_node")
        last_backup = get_latest_backup(backup_dir)
        crontab = parse_crontab_to_str(keyword="mariabackup")
        # Lấy thông tin backup gần nhất
        # node_backup = get_hosts_by_group(inventory_dir, "backup_node")
        # last_backup = get_latest_backup(backup_dir

        
        return {
            "crontab": crontab,
            "node_Backup": node_backup,
            "last_Backup": last_backup
        }
    except Exception as e:
        return {"error": str(e)}
    
@bk_router.get("/bk/info_dump")
async def get_backup_dump_info(backup_dir: str = Query("/var/lib/docker/volumes/mariadb_backup/_data/", description="Đường dẫn tới thư mục backup")):
    result_bash = read_bash_file_var_for_bk_dump(backup_dir)
    list_str_rs = []
    if result_bash is None:
        list_str_rs.append("Không tìm thấy file chạy crontab backup")
        list_str_rs.append("Không tìm thấy file chạy crontab backup")
        list_str_rs.append("Không tìm thấy file chạy crontab backup")
        list_str_rs.append("Không tìm thấy file chạy crontab backup")
        return list_str_rs
    list_str_rs.append(f"Hiện tại đang được backup trên node {result_bash['SSH_HOST']}")
    list_str_rs.append(f"Thư mục folder backup hiện tại: {result_bash['DEST']}")
    list_str_rs.append(get_latest_backup(result_bash["DEST"]))
    list_str_rs.append(parse_crontab_to_str(keyword="dump"))
    return list_str_rs

def update_crontab(cron_schedule: str, cron_command: str, keyword: str = "backup", is_enable: bool = True):
    try:
        # Lấy danh sách crontab hiện tại
        result = subprocess.run(
            ["crontab", "-l"], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True
        )
        current_cron = result.stdout.splitlines()

        new_line = f"{cron_schedule} {cron_command}"
        if not is_enable:
            new_line = f"# {new_line}"
        
        updated = False
        new_cron_lines = []
        
        for line in current_cron:
            if keyword in line:
                if not is_enable:
                    new_line = f"# {line}"
                # Thay thế toàn bộ dòng đó
                else:
                    new_line = f"{cron_schedule} {cron_command}"
                new_cron_lines.append(new_line)
                updated = True
            else:
                new_cron_lines.append(line)

        if not updated:
            # Nếu chưa có dòng backup, thêm mới
            new_cron_lines.append(new_line)
            print(f"Đã thêm dòng {keyword} mới.")

        # Ghép lại nội dung và cập nhật crontab
        final_cron = "\n".join(new_cron_lines) + "\n"
        subprocess.run(["crontab", "-"], input=final_cron, text=True, check=True)
        return True
    except subprocess.CalledProcessError as e:
        print(f"Lỗi khi chạy crontab: {e.stderr}")
        return False
    except Exception as e:
        print(f"Đã có lỗi trong quá trình cập nhật crontab: {e}")
        return False

##can phat trien them ham nay, ho tro backup mysqldump va backup theo mariadb.
##sqldump thi sua cac bien, chay bash la duoc.
@bk_router.post("/bk/update_kolla")
async def update_inventory_and_cron_for_backup(data: RequestKollaBackup):
    try:
        if not os.path.isfile(data.path_inventory):
            return JSONResponse(status_code=400, content={"status": "error", "message": "Không tìm thấy file inventory!"})
        if not os.path.isfile(data.script_file_path):
            return JSONResponse(status_code=400, content={"status": "error", "message": "Không tìm thấy file script backup!"})
        # Gọi hàm cập nhật inventory
        update_ansible_inventory(
            path_inventory=data.path_inventory,
            group=data.group,
            new_nodes=data.new_nodes
        )
        # Gọi hàm cập nhật crontab
        update_crontab(
            cron_schedule=data.cron_schedule,
            cron_command=data.cron_command,
            keyword="mariabackup",
            is_enable=data.is_enable
        )
        update_bash_vars_for_mariabk(path_script_file=data.script_file_path,inventory_path=data.path_inventory,backup_path=data.backup_dir_path, day_datele=data.day_datele, list_node_bash=data.list_node_bash)
        return {"status": "success", "message": "Inventory và Crontab đã được cập nhật."}

    except Exception as e:
        return {"status": "error", "message": str(e)}

#ham update: du tinh la can doc va ghi vao file bash
@bk_router.post("/bk/update_dump")
async def update_backup_crontab_dump(data: RequestMySQLDump):
    try:
        if not os.path.isfile(data.script_file_path):
            return JSONResponse(status_code=400, content={"status": "error", "message": "Không tìm thấy file bash!"})
        
        update_crontab(
            cron_schedule=data.cron_schedule, 
            cron_command=data.cron_command,
            keyword="dump",
            is_enable=data.is_enable
        )    
        update_bash_file_vars(data)

        return {"status": "success", "message": "Cập nhật thành công !!"}
    except Exception as e:
        return {"status": "error", "message": str(e)}

def parse_crontab_to_get_path(keyword: str = "backup") -> str:
    try:
        crontab = subprocess.run(["crontab", "-l"], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        if crontab.returncode != 0:
            return "Không tìm thấy đường dẫn"
        
        lines = crontab.stdout.strip().split("\n")
        for line in lines:
            # Bỏ qua dòng trống hoặc comment
            if not line.strip() or line.strip().startswith("#"):
                continue
            if keyword not in line.lower():
                continue
                
            # Tìm đường dẫn sau từ khóa bash
            parts = line.strip().split()
            for i, part in enumerate(parts):
                if part == "bash" and i + 1 < len(parts):
                    return parts[i + 1]
                    
        return "Không tìm thấy đường dẫn"
    except Exception as e:
        return f"Lỗi khi parse crontab: {str(e)}"

