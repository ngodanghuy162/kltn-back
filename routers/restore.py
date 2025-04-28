##api chon duong dan -> hien thi cac ban backup cac ngay --> truyen vao ban backup moi nhat de restore. sua file bash, chon node backup
from configparser import ConfigParser
from datetime import datetime
from pathlib import Path
import re
from ruamel.yaml import YAML # type: ignore
from ruamel.yaml.comments import CommentedMap # type: ignore
from pathlib import Path
from typing import List, Set
from fastapi import FastAPI, HTTPException, Query, APIRouter, Body # type: ignore
import os
import subprocess
from pydantic import BaseModel, Field # type: ignore
from typing import Dict, List
from io import StringIO
from typing import Dict, Any
restore_router = APIRouter()

yaml = YAML()
class BashVariables(BaseModel):
    path_file_resotre: str
    SSH_USER: str
    SSH_PORT: str = "22"
    SSH_PASS: str
    SSH_HOST: str
    SOURCE_FOLDER_HOST: str
    DEST_IN_DEPLOY: str
    CHOSEN_DATE: str
    LOG_PATH: str

FILENAME_PATTERN = re.compile(r"mysqlbackup-(\d{2})-(\d{2})-(\d{4})\d*")
# re.compile(r"mysqlbackup_(\d{2}_\d{2}_\d{4}).*")


@restore_router.get(
    "/listbackup",
    summary="Lấy danh sách ngày backup từ tên file",
    response_description="Trả về danh sách các ngày theo định dạng DD-MM-YYYY từ tên file backup",
)
def list_backup_dates(
    path: str = Query(
        default="/home/kolla-ansible/mariadb/backup/",  # bạn có thể đổi thành folder mặc định của bạn
        title="Đường dẫn thư mục backup",
        description="Đường dẫn chứa các file backup theo định dạng mysqlbackup_DD_MM_YYYY",
        example="/tmp/backup"
    )
):
    folder = Path(path)
    if not folder.exists() or not folder.is_dir():
        return {"error": "Invalid folder path"}

    backup_dates = []

    for file in folder.iterdir():
        # if file.is_file():
            match = FILENAME_PATTERN.match(file.name)
            if match:
                day, month, year = match.groups()
                backup_dates.append(f"{day}-{month}-{year}")
    return {"dates": backup_dates}


#api truyen ngay vao, lay file do sua vao file bash hoac khai bao moi truong xong chay file bash
@restore_router.post("/restore/update_restore_file")
async def update_bash_file(vars: BashVariables):
    path_file = vars.path_file_resotre

    # Đọc và cập nhật file
    with open(path_file, "r") as f:
        lines = f.readlines()

    updated_lines = []
    for line in lines:
        replaced = False
        for key, value in vars.dict().items():
            if line.strip().startswith(f"{key}="):
                updated_lines.append(f'{key}="{value}"\n')
                replaced = True
                break
        if not replaced:
            updated_lines.append(line)
    
    with open(path_file, "w") as f:
        f.writelines(updated_lines)

    # ✅ Chạy file bash vừa truyền vào
    try:
        result = subprocess.run(
            ["bash", path_file],  
            capture_output=True,
            text=True,
            check=True
        )
        output = result.stdout
    except subprocess.CalledProcessError as e:
        raise HTTPException(status_code=500, detail=f"Lỗi khi chạy script: {e.stderr}")

    return {
        "message": "✅ File updated và script đã được thực thi!",
        "output": output,
    }