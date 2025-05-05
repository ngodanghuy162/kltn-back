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