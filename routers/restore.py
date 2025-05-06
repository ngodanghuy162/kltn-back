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
from typing import Dict, List, Generator
from io import StringIO
from typing import Dict, Any
from fastapi.responses import StreamingResponse
restore_router = APIRouter()

yaml = YAML()
class RESTORE_FOR_MARIABK(BaseModel):
    path_file_restore: str =""
    LOG_PATH: str ="/home/kolla-ansible/mariadb/restore/mariabackup"
    BACKUP_DIR: str ='/home/kolla-ansible/mariadb/backup/'
    MARIADB_HOST: str="192.168.1.101"  # Make this configurable
    INVENTORY_FILE: str="/root/inventory/multinode"
    RESTORE_FILE: str= ""

class RESTORE_FOR_DUMP(BaseModel):
    path_file_restore: str = ""
    BACKUP_FILE: str = ""  # Set your backup file name here
    BACKUP_DIR: str = "/home/kolla-ansible/mariadb/backup/dump"
    MARIADB_HOST: str = "192.168.1.250"
    MARIA_PW: str = "Ihniqd7DRLCMuy07C8gZV2hYAvAN01YXwrNAzRFD"


FILENAME_PATTERN = re.compile(r".*(\d{2}-\d{2}-\d{4}\d*).*")
# re.compile(r"mysqlbackup_(\d{2}_\d{2}_\d{4}).*")


@restore_router.get(
    "/listbackup",
    summary="Lấy danh sách file backup",
    response_description="Trả về danh sách các file backup",
)
def list_backup_files(
    path: str = Query(
        default="/home/kolla-ansible/mariadb/backup/",  # bạn có thể đổi thành folder mặc định của bạn
        title="Đường dẫn thư mục backup",
        description="Đường dẫn chứa các file backup",
        example="/tmp/backup"
    )
):
    folder = Path(path)
    if not folder.exists() or not folder.is_dir():
        return {
            "status": "error",
            "message": "Không tìm thấy thư mục backup",
            "files": []
        }

    backup_files = []

    for file in folder.iterdir():
        # if file.is_file():
        match = FILENAME_PATTERN.search(file.name)
        if match:
            backup_files.append(file.name)

    return {
        "status": "success",
        "message": "Không tìm thấy bản backup nào trong thư mục này" if not backup_files else None,
        "files": sorted(backup_files)
    }

#api truyen ngay vao, lay file do sua vao file bash hoac khai bao moi truong xong chay file bash
@restore_router.post("/restore/mariabk/")
async def update_and_run_bash_file(vars: RESTORE_FOR_MARIABK):
    path_file = vars.path_file_restore

    # Kiểm tra file có tồn tại không
    if not os.path.exists(path_file):
        raise HTTPException(status_code=404, detail="Không tìm thấy file bash")

    # Kiểm tra file có rỗng không
    if os.path.getsize(path_file) == 0:
        raise HTTPException(status_code=400, detail="File bash rỗng")

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

    def generate_output() -> Generator[str, None, None]:
        try:
            # Sử dụng Popen để chạy process và đọc output theo realtime
            process = subprocess.Popen(
                ["bash", path_file],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                bufsize=1,
                universal_newlines=True
            )

            # Đọc stdout
            for line in process.stdout:
                yield f"data: {line}\n\n"

            # Đọc stderr
            for line in process.stderr:
                yield f"data: Error: {line}\n\n"

            # Đợi process hoàn thành
            process.wait()
            
            if process.returncode != 0:
                yield f"data: Process exited with code {process.returncode}\n\n"
            else:
                yield "data: Process completed successfully\n\n"

        except Exception as e:
            yield f"data: Error: {str(e)}\n\n"
    return StreamingResponse(
        generate_output(),
        media_type="text/event-stream"
    )

@restore_router.post("/restore/dump/")
async def update_and_run_bash_file(vars: RESTORE_FOR_DUMP):
    path_file = vars.path_file_restore

    # Kiểm tra file có tồn tại không
    if not os.path.exists(path_file):
        raise HTTPException(status_code=404, detail="Không tìm thấy file bash")

    # Kiểm tra file có rỗng không
    if os.path.getsize(path_file) == 0:
        raise HTTPException(status_code=400, detail="File bash rỗng")

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

    def generate_output() -> Generator[str, None, None]:
        try:
            # Sử dụng Popen để chạy process và đọc output theo realtime
            process = subprocess.Popen(
                ["bash", path_file],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                bufsize=1,
                universal_newlines=True
            )

            # Đọc stdout
            for line in process.stdout:
                yield f"data: {line}\n\n"

            # Đọc stderr
            for line in process.stderr:
                yield f"data: Error: {line}\n\n"

            # Đợi process hoàn thành
            process.wait()
            
            if process.returncode != 0:
                yield f"data: Process exited with code {process.returncode}\n\n"
            else:
                yield "data: Process completed successfully\n\n"

        except Exception as e:
            yield f"data: Error: {str(e)}\n\n"
    return StreamingResponse(
        generate_output(),
        media_type="text/event-stream"
    )